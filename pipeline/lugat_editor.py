"""Lugat editörü — ansiklopedi güncellemesini OpenAI-uyumlu modelle (Kimi) yapar.

Girdi: LUGAT.md sözleşmesi + veri/bugun.json + lugat/'ın tamamı. Modelden yalnızca
değişen/yeni dosyaların TAM içeriği istenir:

  {"dosyalar": {"<Madde Adı>.md": "<tam içerik>", ...}}   (değişiklik yoksa boş nesne)

Yama önce geçici bir kopyaya uygulanır ve lugat_dogrula'dan geçirilir; ancak yeşilse
gerçek lugat/'a yazılır. Hatalar modele geri gönderilir (en çok --tur tur). Başarısız
olursa sıfır-dışı çıkılır — sabah.sh dünkü lugatı korur.

Kullanım: python3 -m pipeline.lugat_editor [--kuru] [--tur 3]
"""
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from pipeline import llm
from pipeline.kulliyat import jsonl_oku
from pipeline.lugat_dogrula import lugat_dogrula

KOK = Path(__file__).resolve().parent.parent

SARMALAYICI = (
    "Aşağıdaki ansiklopedi sözleşmesini uygula. ÖNEMLİ FARK: dosya okuyamaz/yazamaz,\n"
    "komut çalıştıramazsın; bugünün haberleri ve lugatın tamamı bu konuşmada verildi,\n"
    "doğrulamayı sistem çalıştıracak. Görevin: dokunman gereken maddelerin (gerekiyorsa\n"
    'fihrist.md dahil) TAM YENİ içeriğini {"dosyalar": {"<Madde Adı>.md": "<tam içerik>"}}\n'
    "biçiminde TEK bir JSON nesnesi olarak vermek. Verdiğin her dosya eskisinin YERİNE\n"
    'tamamen yazılır; yalnızca değişenleri ver. Değişiklik gerekmiyorsa {"dosyalar": {}}\n'
    "döndür. JSON dışında hiçbir şey yazma.\n\n"
    "=== LUGAT.md ===\n"
)


def _lugat_metni():
    parcalar = []
    for yol in sorted((KOK / "lugat").glob("*.md")):
        parcalar.append(f"--- DOSYA: {yol.name} ---\n{yol.read_text(encoding='utf-8')}")
    return "\n\n".join(parcalar)


def _gecerli_ad(ad):
    return (
        isinstance(ad, str)
        and ad.endswith(".md")
        and len(ad) < 120
        and "/" not in ad
        and "\\" not in ad
        and ".." not in ad
    )


def main():
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--kuru", action="store_true", help="gerçek lugat/'a yazma; yalnızca doğrula")
    ayristirici.add_argument("--tur", type=int, default=3)
    argumanlar = ayristirici.parse_args()

    idler = {k["id"] for k in jsonl_oku(KOK / "veri" / "haberler.jsonl")}
    mesajlar = [
        {"role": "system", "content": SARMALAYICI + (KOK / "LUGAT.md").read_text(encoding="utf-8")},
        {
            "role": "user",
            "content": "=== veri/bugun.json (bugün Külliyat'a giren haberler) ===\n"
            + (KOK / "veri" / "bugun.json").read_text(encoding="utf-8")
            + "\n\n=== lugat/ (mevcut maddelerin tamamı) ===\n"
            + _lugat_metni()
            + "\n\nGerekli güncellemeleri tek JSON nesnesi olarak ver.",
        },
    ]
    for tur in range(1, argumanlar.tur + 1):
        yanit = llm.sohbet(mesajlar, json_modu=True, max_tokens=32768)
        hatalar, dosyalar = [], None
        try:
            dosyalar = llm.json_ayikla(yanit).get("dosyalar")
            if not isinstance(dosyalar, dict):
                raise ValueError('yanıtta "dosyalar" nesnesi yok')
        except ValueError as hata:
            hatalar = [str(hata)]
        if dosyalar is not None:
            kotu = [ad for ad in dosyalar if not _gecerli_ad(ad)]
            if kotu:
                hatalar = [f"geçersiz dosya adı (yalnızca düz '<Ad>.md' olabilir): {kotu}"]
            else:
                with tempfile.TemporaryDirectory() as gecici:
                    deneme = Path(gecici) / "lugat"
                    shutil.copytree(KOK / "lugat", deneme)
                    for ad, icerik in dosyalar.items():
                        (deneme / ad).write_text(str(icerik), encoding="utf-8")
                    hatalar = lugat_dogrula(deneme, idler)
                if not hatalar:
                    if argumanlar.kuru:
                        print(f"lugat editörü (kuru koşu): {len(dosyalar)} dosya geçerli ✓ — yazılmadı")
                    else:
                        for ad, icerik in dosyalar.items():
                            (KOK / "lugat" / ad).write_text(str(icerik), encoding="utf-8")
                        print(f"lugat editörü: {len(dosyalar)} dosya güncellendi ✓")
                    return
        print(f"lugat editörü: {tur}. tur geçersiz ({len(hatalar)} hata): {'; '.join(map(str, hatalar[:3]))}")
        mesajlar.append({"role": "assistant", "content": yanit})
        mesajlar.append({
            "role": "user",
            "content": "Lugat GEÇERSİZ:\n- " + "\n- ".join(map(str, hatalar))
            + "\nHataları düzelt ve düzeltilmiş TAM JSON nesnesini yeniden ver.",
        })
    print("lugat editörü: geçerli güncelleme üretilemedi")
    sys.exit(1)


if __name__ == "__main__":
    main()
