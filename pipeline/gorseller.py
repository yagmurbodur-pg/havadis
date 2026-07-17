"""Küpür görselleri — seçili haberlerin kaynak sayfalarından og:image çekimi.

Görseller İNDİRİLMEZ; kaynağın kendi sunucusundan, habere atıfla gösterilir
(hotlink + şablonda onerror gizleme). Çekilemeyen haber görselsiz küpürle çıkar.
Çıktı: veri/gorseller.json  {haber_id: gorsel_url}
"""
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

KOK = Path(__file__).resolve().parent.parent
BASLIKLAR = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}


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

    gorseller = {}
    with httpx.Client(headers=BASLIKLAR, timeout=8, follow_redirects=True) as istemci:
        for hid in sayi_idleri(sayi):
            url = urller.get(hid)
            if not url:
                continue
            try:
                yanit = istemci.get(url)
                if yanit.status_code >= 400:
                    continue
                gorsel = og_gorsel_ayikla(yanit.text, url)
                if gorsel:
                    gorseller[hid] = gorsel
            except Exception:
                continue  # tek görsel hatası sabahı ilgilendirmez

    veri = KOK / "veri"
    veri.mkdir(exist_ok=True)
    (veri / "gorseller.json").write_text(
        json.dumps(gorseller, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"Görseller: {len(gorseller)}/{len(sayi_idleri(sayi))} haber için bulundu")


if __name__ == "__main__":
    main()
