"""Toplama hattı: sources.yaml → RSS/HF/HN → normalize → filtrele → kümele → candidates.json

Saf fonksiyonlar (url_normalize, kimlik, karaliste_mi, anahtar_gecer_mi, pencerede_mi,
temizle_ozet, kumele, hn_filtrele) birim testlidir; ağ kısmı Sayı 0 provasıyla doğrulanır.
"""
import calendar
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import httpx
import yaml
from bs4 import BeautifulSoup
from dateutil import parser as tarih_ayristir
from rapidfuzz import fuzz

KOK = Path(__file__).resolve().parent.parent
BASLIKLAR = {"User-Agent": "Havadis/1.0 (kisisel gunluk YZ dergisi; +https://github.com)"}
IZLEME_PARAMLARI = {"fbclid", "gclid", "ref", "cmpid", "mc_cid", "mc_eid", "s"}
MAKS_ADAY = 150


# ---------- saf fonksiyonlar ----------

def url_normalize(url):
    p = urlsplit((url or "").strip())
    sorgu = [
        (k, v)
        for k, v in parse_qsl(p.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in IZLEME_PARAMLARI
    ]
    yol = p.path.rstrip("/") or "/"
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), yol, urlencode(sorgu), ""))


def kimlik(url):
    return hashlib.sha1(url_normalize(url).encode("utf-8")).hexdigest()[:8]


def karaliste_mi(metin, karaliste):
    m = (metin or "").lower()
    return any(k.lower() in m for k in karaliste)


def anahtar_gecer_mi(metin, filtreler):
    m = (metin or "").lower()
    return any(f.lower() in m for f in filtreler)


def pencerede_mi(tarih, simdi, saat):
    return simdi - timedelta(hours=saat) <= tarih <= simdi + timedelta(hours=2)


def temizle_ozet(html, limit=600):
    metin = BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)
    metin = re.sub(r"\s+", " ", metin).strip()
    metin = re.sub(r"\s+([.,;:!?…])", r"\1", metin)  # etiket sınırında yetim kalan noktalama
    if len(metin) <= limit:
        return metin
    return metin[:limit].rsplit(" ", 1)[0] + "…"


def kumele(adaylar, esik=85):
    """Benzer başlıkları tek habere indirger; birincil = en yüksek öncelikli kaynak."""
    sonuc = []
    sirali = sorted(adaylar, key=lambda a: (-a.get("oncelik", 1), a.get("tarih", "")))
    for aday in sirali:
        ev = None
        for s in sonuc:
            if fuzz.token_set_ratio(aday["baslik"].lower(), s["baslik"].lower()) >= esik:
                ev = s
                break
        if ev is None:
            kopya = dict(aday)
            kopya.setdefault("ek_kaynaklar", [])
            sonuc.append(kopya)
        else:
            ev["ek_kaynaklar"] = ev.get("ek_kaynaklar", []) + [
                {"kaynak": aday["kaynak"], "url": aday["url"], "baslik": aday["baslik"]}
            ]
    return sonuc


def hn_filtrele(hits, min_puan):
    """Algolia sonucu → aday listesi. Puan filtresi İSTEMCİ tarafında (sunucu artık desteklemiyor)."""
    adaylar = []
    for h in hits:
        if (h.get("points") or 0) < min_puan or not h.get("url"):
            continue
        adaylar.append(
            {
                "id": kimlik(h["url"]),
                "kaynak": "Hacker News",
                "oncelik": 1,
                "bolum_ipucu": "gundem",
                "baslik": h.get("title", ""),
                "url": h["url"],
                "tarih": h.get("created_at", ""),
                "ozet": "",
                "puan": h.get("points"),
                "ek_kaynaklar": [
                    {
                        "kaynak": "HN tartışması",
                        "url": f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                        "baslik": "Yorumlar",
                    }
                ],
            }
        )
    return adaylar


# ---------- ağ tarafı ----------

def _entry_tarihi(entry):
    for alan in ("published_parsed", "updated_parsed"):
        t = entry.get(alan)
        if t:
            return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
    for alan in ("published", "updated", "date"):
        if entry.get(alan):
            try:
                dt = tarih_ayristir.parse(entry[alan])
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except (ValueError, OverflowError):
                pass
    return None


def _rss_oku(kaynak, istemci, simdi, pencere, karaliste):
    r = istemci.get(kaynak["url"])
    r.raise_for_status()
    feed = feedparser.parse(r.text)
    adaylar, en_yeni = [], None
    for entry in feed.entries:
        tarih = _entry_tarihi(entry)
        if tarih and (en_yeni is None or tarih > en_yeni):
            en_yeni = tarih
        if not tarih or not pencerede_mi(tarih, simdi, pencere):
            continue
        url = entry.get("link") or ""
        baslik = (entry.get("title") or "").strip()
        if not url or not baslik:
            continue
        ozet = temizle_ozet(entry.get("summary") or entry.get("description") or "")
        if karaliste_mi(baslik + " " + ozet, karaliste):
            continue
        baslik_filtre = kaynak.get("baslik_filtre")
        if baslik_filtre and not anahtar_gecer_mi(baslik, baslik_filtre):
            continue  # yalnız belirli seri/bölüm (ör. Latent.Space içinden AI News)
        filtre = kaynak.get("anahtar_filtre")
        if filtre and not anahtar_gecer_mi(baslik + " " + ozet, filtre):
            continue
        adaylar.append(
            {
                "id": kimlik(url),
                "kaynak": kaynak["ad"],
                "oncelik": kaynak.get("oncelik", 1),
                "bolum_ipucu": kaynak.get("bolum", "gundem"),
                "baslik": baslik,
                "url": url,
                "tarih": tarih.isoformat(),
                "ozet": ozet,
                "ek_kaynaklar": [],
            }
        )
    return adaylar, en_yeni


def _hf_oku(kaynak, istemci, simdi, pencere):
    r = istemci.get(kaynak["url"])
    r.raise_for_status()
    adaylar, en_yeni = [], None
    for oge in r.json():
        makale = oge.get("paper") or {}
        yayim = oge.get("publishedAt") or makale.get("publishedAt")
        try:
            tarih = tarih_ayristir.parse(yayim) if yayim else None
        except (ValueError, TypeError):
            tarih = None
        if tarih and not tarih.tzinfo:
            tarih = tarih.replace(tzinfo=timezone.utc)
        if tarih and (en_yeni is None or tarih > en_yeni):
            en_yeni = tarih
        if not tarih or not pencerede_mi(tarih, simdi, max(pencere, 48)):
            continue  # makaleler için pencereyi biraz geniş tut
        mid = makale.get("id")
        if not mid:
            continue
        url = f"https://huggingface.co/papers/{mid}"
        adaylar.append(
            {
                "id": kimlik(url),
                "kaynak": kaynak["ad"],
                "oncelik": kaynak.get("oncelik", 2),
                "bolum_ipucu": kaynak.get("bolum", "arastirma"),
                "baslik": (makale.get("title") or "").strip().replace("\n", " "),
                "url": url,
                "tarih": tarih.isoformat(),
                "ozet": temizle_ozet(makale.get("summary") or "", 500),
                "begeni": oge.get("numUpvotes") or makale.get("upvotes"),
                "ek_kaynaklar": [],
            }
        )
    return adaylar, en_yeni


def _hn_oku(kaynak, istemci, simdi, pencere):
    if kaynak.get("mod") == "front_page":
        # HN manşet sayfasının kendisi (kesin takip); pencere filtresi yok — manşetteyse günceldir
        r = istemci.get(
            "https://hn.algolia.com/api/v1/search",
            params={"tags": "front_page", "hitsPerPage": 30},
        )
        r.raise_for_status()
        hits = r.json().get("hits", [])
    else:
        esik_ts = int((simdi - timedelta(hours=pencere)).timestamp())
        gorulen, hits = set(), []
        for sorgu in kaynak.get("sorgular", ["AI"]):
            r = istemci.get(
                "https://hn.algolia.com/api/v1/search_by_date",
                params={
                    "query": sorgu,
                    "tags": "story",
                    "numericFilters": f"created_at_i>{esik_ts}",
                    "hitsPerPage": 30,
                },
            )
            r.raise_for_status()
            for h in r.json().get("hits", []):
                if h.get("objectID") not in gorulen:
                    gorulen.add(h.get("objectID"))
                    hits.append(h)
    adaylar = hn_filtrele(hits, kaynak.get("min_puan", 80))
    for aday in adaylar:  # etiket ve öncelik yapılandırmadan gelsin
        aday["kaynak"] = kaynak["ad"]
        aday["oncelik"] = kaynak.get("oncelik", 1)
    return adaylar, None


def gh_trending_ayristir(html, simdi, kaynak_adi="GitHub Trending", oncelik=1, en_cok=15):
    """github.com/trending HTML'inden aday listesi çıkarır (resmî API/RSS yok)."""
    corba = BeautifulSoup(html or "", "html.parser")
    adaylar = []
    for satir in corba.select("article.Box-row")[:en_cok]:
        h2 = satir.find("h2")
        baglanti = h2.find("a") if h2 else None
        if not baglanti or not baglanti.get("href"):
            continue
        depo = baglanti["href"].strip("/")
        url = f"https://github.com/{depo}"
        p = satir.find("p")
        aciklama = temizle_ozet(p.get_text(" ", strip=True) if p else "", 300)
        yildiz_dugum = satir.find(string=re.compile(r"stars today"))
        yildiz = " ".join(str(yildiz_dugum).split()) if yildiz_dugum else ""
        ozet = aciklama
        if yildiz:
            ozet = (ozet + " — " if ozet else "") + f"⭐ {yildiz}"
        adaylar.append(
            {
                "id": kimlik(url),
                "kaynak": kaynak_adi,
                "oncelik": oncelik,
                "bolum_ipucu": "arac_cantasi",
                "baslik": f"{depo}: GitHub'da bugün yükselen depo",
                "url": url,
                "tarih": simdi.isoformat(),
                "ozet": ozet,
                "ek_kaynaklar": [],
            }
        )
    return adaylar


def _gh_trending_oku(kaynak, istemci, simdi):
    r = istemci.get(
        kaynak.get("url", "https://github.com/trending?since=daily"),
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    )
    r.raise_for_status()
    adaylar = gh_trending_ayristir(
        r.text, simdi, kaynak.get("ad", "GitHub Trending"), kaynak.get("oncelik", 1)
    )
    return adaylar, None


def topla(ayar, simdi=None):
    simdi = simdi or datetime.now(timezone.utc)
    pencere = ayar.get("pencere_saat", 36)
    karaliste = ayar.get("karaliste", [])
    tum_adaylar, durumlar = [], []

    with httpx.Client(headers=BASLIKLAR, timeout=25, follow_redirects=True) as istemci:
        for kaynak in ayar["kaynaklar"]:
            try:
                if kaynak.get("tip") == "hf_api":
                    adaylar, en_yeni = _hf_oku(kaynak, istemci, simdi, pencere)
                elif kaynak.get("tip") == "hn_api":
                    adaylar, en_yeni = _hn_oku(kaynak, istemci, simdi, pencere)
                elif kaynak.get("tip") == "gh_trending":
                    adaylar, en_yeni = _gh_trending_oku(kaynak, istemci, simdi)
                else:
                    adaylar, en_yeni = _rss_oku(kaynak, istemci, simdi, pencere, karaliste)
                durum = "ok"
                bayat_gun = kaynak.get("bayat_gun")
                if bayat_gun and en_yeni and en_yeni < simdi - timedelta(days=bayat_gun):
                    durum = "bayat"
                durumlar.append({"ad": kaynak["ad"], "durum": durum, "adet": len(adaylar)})
                tum_adaylar.extend(adaylar)
            except Exception as e:  # tek kaynak hatası sabahı durdurmaz
                durumlar.append(
                    {"ad": kaynak["ad"], "durum": "hata", "adet": 0, "detay": str(e)[:200]}
                )

    # URL tekilleştirme (aynı id → yüksek öncelikli kalır)
    essiz = {}
    for a in sorted(tum_adaylar, key=lambda x: -x.get("oncelik", 1)):
        essiz.setdefault(a["id"], a)
    kumelenmis = kumele(list(essiz.values()))
    kumelenmis = sorted(kumelenmis, key=lambda a: a.get("tarih", ""), reverse=True)[:MAKS_ADAY]

    return {
        "meta": {
            "olusturma": simdi.isoformat(),
            "pencere_saat": pencere,
            "kaynak_ok": sum(1 for d in durumlar if d["durum"] != "hata"),
            "kaynak_toplam": len(durumlar),
            "kaynak_durum": durumlar,
        },
        "adaylar": kumelenmis,
    }


def main():
    ayar = yaml.safe_load((KOK / "sources.yaml").read_text(encoding="utf-8"))
    havuz = topla(ayar)
    (KOK / "candidates.json").write_text(
        json.dumps(havuz, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    m = havuz["meta"]
    print(f"{len(havuz['adaylar'])} aday · {m['kaynak_ok']}/{m['kaynak_toplam']} kaynak")
    for d in m["kaynak_durum"]:
        isaret = {"ok": "✓", "bayat": "~", "hata": "✗"}[d["durum"]]
        print(f" {isaret} {d['ad']}: {d['adet']}" + (f" ({d.get('detay','')})" if d["durum"] == "hata" else ""))
    if not havuz["adaylar"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
