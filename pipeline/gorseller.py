"""Küpür görselleri + 𝕏 duyuru bağlantıları — seçili haberlerin kaynak sayfalarından.

Görseller İNDİRİLMEZ; kaynağın kendi sunucusundan, habere atıfla gösterilir
(hotlink + şablonda onerror gizleme). Aynı geçişte sayfadaki ilk 𝕏/Twitter
status bağlantısı da ayıklanır (ilan sahibinin duyurusu); bulunamazsa
kurumun bilinen 𝕏 hesabına düşülür.
Çıktılar: veri/gorseller.json {id: gorsel_url} · veri/x_baglari.json {id: x_url}
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

KOK = Path(__file__).resolve().parent.parent
BASLIKLAR = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}

X_STATUS = re.compile(r"https?://(?:www\.)?(?:twitter|x)\.com/[A-Za-z0-9_]{1,15}/status/\d+")

# Kurumların bilinen 𝕏 hesapları (kaynak adına göre; duyuru tweet'i bulunamazsa profil bağlanır)
KURUM_X = {
    "OpenAI": "https://x.com/OpenAI",
    "Anthropic": "https://x.com/AnthropicAI",
    "Google AI": "https://x.com/GoogleAI",
    "Google DeepMind": "https://x.com/GoogleDeepMind",
    "Meta AI": "https://x.com/AIatMeta",
    "Mistral": "https://x.com/MistralAI",
    "HF Daily Papers": "https://x.com/huggingface",
}


def x_link_ayikla(html):
    esle = X_STATUS.search(html or "")
    return esle.group(0) if esle else None


def kurum_x_hesabi(kaynak_adi):
    return KURUM_X.get(kaynak_adi)


def og_gorsel_ayikla(html, taban_url=""):
    corba = BeautifulSoup(html or "", "html.parser")
    adaylar = (
        ("meta", {"property": "og:image"}),
        ("meta", {"name": "og:image"}),
        ("meta", {"property": "og:image:url"}),
        ("meta", {"name": "twitter:image"}),
        ("meta", {"property": "twitter:image"}),
        ("meta", {"name": "twitter:image:src"}),
    )
    for etiket, oznitelik in adaylar:
        bulunan = corba.find(etiket, attrs=oznitelik)
        if not bulunan:
            continue
        url = (bulunan.get("content") or "").strip()
        if not url:
            continue
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/") and taban_url:
            url = urljoin(taban_url, url)
        if url.startswith("http"):
            return url
    return None


def sayi_idleri(sayi):
    idler = []
    if sayi.get("kapak", {}).get("id"):
        idler.append(sayi["kapak"]["id"])
    for bolum in sayi.get("bolumler", []):
        for haber in bolum.get("haberler", []):
            idler.append(haber["id"])
    return idler


def main():
    sayi = json.loads((KOK / "issue.json").read_text(encoding="utf-8"))
    havuz = json.loads((KOK / "candidates.json").read_text(encoding="utf-8"))
    urller = {a["id"]: a.get("url", "") for a in havuz.get("adaylar", [])}

    kaynaklar = {a["id"]: a.get("kaynak", "") for a in havuz.get("adaylar", [])}
    gorseller, x_baglari = {}, {}
    with httpx.Client(headers=BASLIKLAR, timeout=8, follow_redirects=True) as istemci:
        for hid in sayi_idleri(sayi):
            url = urller.get(hid)
            if not url:
                continue
            try:
                yanit = istemci.get(url)
                if yanit.status_code >= 400:
                    raise ValueError("erişilemedi")
                gorsel = og_gorsel_ayikla(yanit.text, url)
                if gorsel:
                    gorseller[hid] = gorsel
                x_link = x_link_ayikla(yanit.text)
                if x_link:
                    x_baglari[hid] = x_link
            except Exception:
                pass  # tek sayfa hatası sabahı ilgilendirmez
            if hid not in x_baglari:  # duyuru tweet'i yoksa kurumun bilinen hesabı
                profil = kurum_x_hesabi(kaynaklar.get(hid, ""))
                if profil:
                    x_baglari[hid] = profil

    veri = KOK / "veri"
    veri.mkdir(exist_ok=True)
    (veri / "gorseller.json").write_text(
        json.dumps(gorseller, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (veri / "x_baglari.json").write_text(
        json.dumps(x_baglari, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(
        f"Görseller: {len(gorseller)}/{len(sayi_idleri(sayi))} · 𝕏 bağları: {len(x_baglari)}"
    )


if __name__ == "__main__":
    main()
