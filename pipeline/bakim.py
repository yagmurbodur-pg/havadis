"""Bakım asistanı — Havadis'in işletme/arıza sorularını modele (Kimi) sorar.

Bağlam otomatik yüklenir: DEVIR.md (işletme el kitabı) + README.md + sabah.sh +
sabah logunun kuyruğu. `-d` ile ek dosya(lar) verilebilir.

Kullanım: ./bakim "bu sabah sayı neden mini çıktı?"
          ./bakim -d pipeline/render.py "okuma süresi nasıl hesaplanıyor?"
"""
import argparse
import sys
from pathlib import Path

from pipeline import llm

KOK = Path(__file__).resolve().parent.parent
LOG = Path.home() / "Library" / "Logs" / "havadis-sabah.log"

SISTEM = (
    "Sen Havadis'in işletmecisisin: günlük Türkçe yapay zekâ dergisini üreten bu sistemin "
    "bakımından sorumlusun. Aşağıdaki bağlam (el kitabı, README, sabah betiği, log kuyruğu) "
    "sistemin gerçeğidir. Soruyu kolay anlaşılır Türkçeyle, mümkünse çalıştırılacak somut "
    "komutlarla yanıtla. Bağlamda olmayan şeyi uydurma; bilmiyorsan hangi dosyaya "
    "bakılacağını söyle."
)


def baglam(ek_dosyalar):
    parcalar = []
    for ad in ("DEVIR.md", "README.md", "sabah.sh"):
        yol = KOK / ad
        if yol.exists():
            parcalar.append(f"=== {ad} ===\n{yol.read_text(encoding='utf-8')}")
    if LOG.exists():
        kuyruk = LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-120:]
        parcalar.append("=== sabah logu (son 120 satır) ===\n" + "\n".join(kuyruk))
    for ad in ek_dosyalar:
        yol = Path(ad) if Path(ad).is_absolute() else KOK / ad
        try:
            parcalar.append(f"=== {ad} ===\n{yol.read_text(encoding='utf-8')[:30000]}")
        except OSError as hata:
            parcalar.append(f"=== {ad} === (okunamadı: {hata})")
    return "\n\n".join(parcalar)


def main():
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("soru", nargs="+", help="işletme/arıza sorusu")
    ayristirici.add_argument("-d", "--dosya", action="append", default=[], help="bağlama eklenecek dosya")
    argumanlar = ayristirici.parse_args()
    soru = " ".join(argumanlar.soru).strip()

    print("🔧 Bağlam yükleniyor; yanıt yazılıyor…\n")
    try:
        cevap = llm.sohbet(
            [
                {"role": "system", "content": SISTEM},
                {"role": "user", "content": baglam(argumanlar.dosya) + f"\n\nSORU: {soru}"},
            ],
            zaman_asimi=300,
        )
    except RuntimeError as hata:
        print("Yanıt üretilemedi:", str(hata)[:300])
        sys.exit(1)
    print(cevap)


if __name__ == "__main__":
    main()
