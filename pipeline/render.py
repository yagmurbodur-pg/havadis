"""issue.json + candidates.json → site/ (bugünkü sayı, tarihli arşiv sayfası, arşiv dizini)."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pipeline.metin import slugla

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Europe/Istanbul")
except Exception:  # zoneinfo verisi yoksa UTC'de kal
    IST = timezone.utc

KOK = Path(__file__).resolve().parent.parent

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def tr_tarih(dt):
    return f"{dt.day} {AYLAR[dt.month - 1]} {dt.year}, {GUNLER[dt.weekday()]}"


def sayi_numarasi(arsiv_dizini, bugun):
    """Sayı no = bugünden önceki arşiv sayfası adedi + 1 (aynı gün yeniden koşmak numarayı artırmaz)."""
    arsiv = Path(arsiv_dizini)
    if not arsiv.exists():
        return 1
    onceki = [p for p in arsiv.glob("????-??-??.html") if p.stem != bugun]
    return len(onceki) + 1


def _k(metin):
    return len(str(metin or "").split())


def okuma_suresi(sayi):
    kelime = 0
    kapak = sayi.get("kapak", {})
    kelime += _k(kapak.get("baslik")) + _k(kapak.get("ozet")) + _k(kapak.get("neden_onemli"))
    for bolum in sayi.get("bolumler", []):
        for h in bolum.get("haberler", []):
            kelime += _k(h.get("baslik")) + _k(h.get("ozet")) + _k(h.get("neden_onemli"))
    for r in sayi.get("radar", []):
        kelime += _k(r.get("cumle"))
    return max(1, round(kelime / 180))


def uret(sayi, havuz, site_dizini, simdi, gorseller=None, x_baglari=None):
    site = Path(site_dizini)
    (site / "arsiv").mkdir(parents=True, exist_ok=True)

    yerel = simdi.astimezone(IST)
    bugun = yerel.strftime("%Y-%m-%d")
    no = sayi_numarasi(site / "arsiv", bugun)
    adaylar = {a["id"]: a for a in havuz.get("adaylar", [])}

    env = Environment(
        loader=FileSystemLoader(str(KOK / "templates")),
        autoescape=select_autoescape(["html", "j2"]),
    )
    env.filters["slugla"] = slugla

    onceki_stemler = sorted(
        p.stem for p in (site / "arsiv").glob("????-??-??.html") if p.stem < bugun
    )
    onceki = {"iso": onceki_stemler[-1]} if onceki_stemler else None

    baglam = {
        "sayi": sayi,
        "aday": adaylar,
        "sayi_no": no,
        "tarih": tr_tarih(yerel),
        "tarih_iso": bugun,
        "saat": yerel.strftime("%H:%M"),
        "okuma": okuma_suresi(sayi),
        "onceki": onceki,
        "meta": havuz.get("meta", {}),
        "gorsel": gorseller or {},
        "x_bag": x_baglari or {},
    }
    dergi = env.get_template("dergi.html.j2")
    (site / "index.html").write_text(dergi.render(kok=".", **baglam), encoding="utf-8")
    (site / "arsiv" / f"{bugun}.html").write_text(
        dergi.render(kok="..", **baglam), encoding="utf-8"
    )

    arsiv_tpl = env.get_template("arsiv.html.j2")
    kronolojik = sorted(p.stem for p in (site / "arsiv").glob("????-??-??.html"))
    sayilar = [
        {
            "iso": stem,
            "no": i + 1,
            "etiket": tr_tarih(datetime.strptime(stem, "%Y-%m-%d")),
        }
        for i, stem in enumerate(kronolojik)
    ][::-1]
    (site / "arsiv" / "index.html").write_text(
        arsiv_tpl.render(sayilar=sayilar, kok=".."), encoding="utf-8"
    )

    # service worker sürüm damgası: her basım varlık önbelleğini tazeler (bayat CSS/JS kalmasın)
    sw_yolu = site / "sw.js"
    if sw_yolu.exists():
        import re as _re

        sw_metin = sw_yolu.read_text(encoding="utf-8")
        damga = "havadis-" + yerel.strftime("%Y%m%d%H%M")
        sw_yolu.write_text(
            _re.sub(r'const SURUM = "[^"]*"', f'const SURUM = "{damga}"', sw_metin),
            encoding="utf-8",
        )

    # notify + service worker sürümü için küçük durum dosyası
    (site / "son.json").write_text(
        json.dumps(
            {
                "sayi_no": no,
                "tarih": bugun,
                "kapak": sayi.get("kapak", {}).get("baslik", ""),
                "mini": bool(sayi.get("mini")),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return site / "index.html"


def main():
    sayi = json.loads((KOK / "issue.json").read_text(encoding="utf-8"))
    havuz = json.loads((KOK / "candidates.json").read_text(encoding="utf-8"))
    gorsel_yolu = KOK / "veri" / "gorseller.json"
    gorseller = (
        json.loads(gorsel_yolu.read_text(encoding="utf-8")) if gorsel_yolu.exists() else {}
    )
    x_yolu = KOK / "veri" / "x_baglari.json"
    x_baglari = json.loads(x_yolu.read_text(encoding="utf-8")) if x_yolu.exists() else {}
    hedef = uret(sayi, havuz, KOK / "site", datetime.now(timezone.utc), gorseller, x_baglari)
    print(f"Dergi üretildi: {hedef}")


if __name__ == "__main__":
    main()
