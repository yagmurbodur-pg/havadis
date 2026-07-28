"""Sabah editörü — issue.json'ı OpenAI-uyumlu API'deki modelle (Kimi) üretir.

Akış: EDITORIAL.md + aday havuzu + ilgi profili + Külliyat özeti tek prompt'ta
modele verilir; dönen JSON validate.dogrula'dan geçirilir; hatalar modele geri
gönderilir (en çok --tur tur). Yeşillenmezse sıfır-dışı çıkılır — sabah.sh mini
sayıya düşer, sabah asla boş geçmez.

Kullanım: python3 -m pipeline.editor [--hedef issue.json] [--tur 3]
"""
import argparse
import json
import sys
from pathlib import Path

from pipeline import llm
from pipeline.kulliyat import jsonl_oku
from pipeline.validate import dogrula

KOK = Path(__file__).resolve().parent.parent

SARMALAYICI = (
    "Aşağıdaki Editoryal Anayasa'yı uygula. ÖNEMLİ FARK: dosya okuyamaz/yazamaz,\n"
    "komut çalıştıramazsın; gereken her dosya bu konuşmada sana verildi ve doğrulamayı\n"
    "sistem çalıştıracak. Görevin YALNIZCA issue.json içeriğini, anayasadaki şemaya\n"
    "birebir uyan TEK bir JSON nesnesi olarak üretmek. JSON dışında hiçbir şey yazma.\n\n"
    "=== EDITORIAL.md ===\n"
)


def kullanici_mesaji():
    parcalar = [
        "=== candidates.json (aday havuzu) ===",
        (KOK / "candidates.json").read_text(encoding="utf-8"),
        "=== ilgi.yaml (okur ilgi profili) ===",
        (KOK / "ilgi.yaml").read_text(encoding="utf-8"),
    ]
    konular = KOK / "veri" / "konular_ozet.json"
    if konular.exists():
        parcalar += [
            "=== veri/konular_ozet.json (Külliyat özeti — 'iliskili' yalnızca buradaki id'lere) ===",
            konular.read_text(encoding="utf-8"),
        ]
    parcalar.append("Bugünün sayısını seç ve issue.json içeriğini tek JSON nesnesi olarak üret.")
    return "\n\n".join(parcalar)


def main():
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--hedef", default=str(KOK / "issue.json"))
    ayristirici.add_argument("--tur", type=int, default=3)
    argumanlar = ayristirici.parse_args()

    havuz = json.loads((KOK / "candidates.json").read_text(encoding="utf-8"))
    eski_idler = {k["id"] for k in jsonl_oku(KOK / "veri" / "haberler.jsonl")}

    mesajlar = [
        {"role": "system", "content": SARMALAYICI + (KOK / "EDITORIAL.md").read_text(encoding="utf-8")},
        {"role": "user", "content": kullanici_mesaji()},
    ]
    for tur in range(1, argumanlar.tur + 1):
        yanit = llm.sohbet(mesajlar, json_modu=True)
        try:
            sayi = llm.json_ayikla(yanit)
            hatalar = dogrula(sayi, havuz, eski_idler)
        except ValueError as hata:
            sayi, hatalar = None, [str(hata)]
        if not hatalar:
            Path(argumanlar.hedef).write_text(
                json.dumps(sayi, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
            )
            print(f"editör: sayı {tur}. turda geçerli ✓ → {argumanlar.hedef}")
            return
        print(f"editör: {tur}. tur geçersiz ({len(hatalar)} hata): {'; '.join(map(str, hatalar[:3]))}")
        mesajlar.append({"role": "assistant", "content": yanit})
        mesajlar.append({
            "role": "user",
            "content": "issue.json GEÇERSİZ:\n- " + "\n- ".join(map(str, hatalar))
            + "\nHataları düzelt ve sayının TAMAMINI tek JSON nesnesi olarak yeniden ver.",
        })
    print("editör: geçerli sayı üretilemedi")
    sys.exit(1)


if __name__ == "__main__":
    main()
