"""Lugat doğrulayıcısı — wiki bütünlüğü bir rica değil, yayın şartıdır.

(dictionary-of-ai-coding'in generate-readme.ts dersinden: yetim madde, kırık bağ,
uydurma haber referansı yayına giremez; hepsi burada sert biçimde durdurulur.)
"""
import json
import re
import sys
from pathlib import Path

import yaml

KOK = Path(__file__).resolve().parent.parent
WIKILINK = re.compile(r"\[\[([^\]|#]+?)\]\]")
HABER_REF = re.compile(r"\(haber:\s*([A-Za-z0-9_-]{4,})\)")
TURLER = {"kavram", "kurum", "kisi", "model", "urun", "olay"}


def _on_yazi_ayir(metin):
    if not metin.startswith("---"):
        return None, metin
    parcalar = metin.split("---", 2)
    if len(parcalar) < 3:
        return None, metin
    try:
        return yaml.safe_load(parcalar[1]) or {}, parcalar[2]
    except yaml.YAMLError:
        return None, parcalar[2]


def lugat_dogrula(lugat_dizini, haber_idleri):
    lugat = Path(lugat_dizini)
    hatalar = []

    dosyalar = {p.stem: p for p in lugat.glob("*.md") if p.name != "fihrist.md"}

    fihrist_yolu = lugat / "fihrist.md"
    fihrist_maddeleri = []
    if fihrist_yolu.exists():
        fihrist_maddeleri = [
            m.strip() for m in WIKILINK.findall(fihrist_yolu.read_text(encoding="utf-8"))
        ]
    else:
        hatalar.append("lugat/fihrist.md yok.")

    gorulen = set()
    for madde in fihrist_maddeleri:
        if madde in gorulen:
            hatalar.append(f"Fihrist: '{madde}' birden çok kez listelenmiş.")
        gorulen.add(madde)

    for madde in gorulen:
        if madde not in dosyalar:
            hatalar.append(f"Fihrist: '{madde}' için lugat/ altında dosya yok.")
    for ad in sorted(dosyalar):
        if ad not in gorulen:
            hatalar.append(f"'{ad}.md' fihristte yok (yetim madde) — fihriste ekle.")

    for ad, yol in sorted(dosyalar.items()):
        metin = yol.read_text(encoding="utf-8")
        on_yazi, govde = _on_yazi_ayir(metin)
        if on_yazi is None:
            hatalar.append(f"{ad}: ön yazı (frontmatter) okunamadı.")
            continue
        if str(on_yazi.get("baslik", "")).strip() != ad:
            hatalar.append(f"{ad}: 'baslik' dosya adıyla birebir aynı olmalı (kimlik kuralı).")
        tanim = str(on_yazi.get("tanim") or "")
        if not tanim:
            hatalar.append(f"{ad}: 'tanim' zorunlu (≤140 karakter, tek cümle).")
        elif len(tanim) > 140:
            hatalar.append(f"{ad}: 'tanim' {len(tanim)} karakter; sınır 140.")
        if on_yazi.get("tur") not in TURLER:
            hatalar.append(
                f"{ad}: 'tur' şunlardan biri olmalı: {', '.join(sorted(TURLER))}."
            )
        for hedef in WIKILINK.findall(govde):
            hedef = hedef.strip()
            if hedef not in dosyalar:
                hatalar.append(
                    f"{ad}: kırık bağ [[{hedef}]] — o madde yok; bağı kaldır ya da maddeyi aç."
                )
        for haber_id in HABER_REF.findall(govde):
            if haber_id not in haber_idleri:
                hatalar.append(
                    f"{ad}: (haber: {haber_id}) Külliyat'ta yok — yalnızca gerçek haber id'leri."
                )
    return hatalar


def main():
    jsonl = KOK / "veri" / "haberler.jsonl"
    idler = set()
    if jsonl.exists():
        for satir in jsonl.read_text(encoding="utf-8").splitlines():
            if satir.strip():
                idler.add(json.loads(satir)["id"])
    hatalar = lugat_dogrula(KOK / "lugat", idler)
    if hatalar:
        print("Lugat GEÇERSİZ:")
        for h in hatalar:
            print(" -", h)
        sys.exit(1)
    print("Lugat geçerli ✓")


if __name__ == "__main__":
    main()
