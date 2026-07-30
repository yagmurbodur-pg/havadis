"""Bir günün kayıtlarını veri/haberler.jsonl'den çıkarır (yedek alarak).

Ne zaman gerekir: sabah mini sayı basıldıysa ve gün içinde sayı yeniden üretilecekse.
Külliyat id bazlı idempotent olduğundan, önce o günün kayıtları silinmezse yeni
başlıklar arşive işlenmez. Silme sonrası normal zincir koşulur:
  editor → validate → gorseller → render → kulliyat → lugat_editor → lugat_render

Kullanım: python3 -m pipeline.gunu_sil [--tarih 2026-07-28]   (varsayılan: bugünkü sayı tarihi)
"""
import argparse
import json
import shutil
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent


def main():
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--tarih", help="YYYY-AA-GG; verilmezse site/son.json'daki tarih")
    argumanlar = ayristirici.parse_args()

    tarih = argumanlar.tarih or json.loads(
        (KOK / "site" / "son.json").read_text(encoding="utf-8")
    )["tarih"]

    jsonl = KOK / "veri" / "haberler.jsonl"
    satirlar = [s for s in jsonl.read_text(encoding="utf-8").splitlines() if s.strip()]
    kalan = [s for s in satirlar if json.loads(s)["tarih"] != tarih]
    if len(kalan) == len(satirlar):
        print(f"{tarih} tarihli kayıt yok; dosyaya dokunulmadı.")
        return
    shutil.copy2(jsonl, jsonl.with_suffix(".jsonl.yedek"))
    jsonl.write_text("\n".join(kalan) + "\n", encoding="utf-8")
    print(
        f"{len(satirlar) - len(kalan)} kayıt ({tarih}) çıkarıldı, {len(kalan)} kaldı "
        f"— yedek: {jsonl.name}.yedek"
    )


if __name__ == "__main__":
    main()
