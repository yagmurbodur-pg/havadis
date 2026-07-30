"""Arıza teşhisçisi — sabah koşusu hata verdiğinde log kuyruğunu modele gösterip
tek satırlık teşhis üretir; sabah.sh bunu ntfy alarmına ekler.

Sözleşme: NE OLURSA OLSUN alarmı geciktirmez/engellemez — teşhis üretilemezse
boş çıktıyla 0 döner. Tek deneme, kısa zaman aşımı.

Kullanım: python3 -m pipeline.onarici   (çıktı: tek satır teşhis ya da boş)
"""
import sys
from pathlib import Path

from pipeline import llm

LOG = Path.home() / "Library" / "Logs" / "havadis-sabah.log"


def main():
    try:
        kuyruk = "\n".join(
            LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-150:]
        )
        cevap = llm.sohbet(
            [
                {
                    "role": "system",
                    "content": (
                        "Sen Havadis'in (günlük Türkçe YZ dergisi; hat: fetch → editör → validate → "
                        "render → külliyat → lugat → kasa → push → notify) nöbetçi işletmecisisin. "
                        "Aşağıdaki log kuyruğuna bak; hatanın en olası nedenini ve ilk müdahaleyi "
                        "TEK cümlede, ≤40 kelimeyle, Türkçe söyle. Emin değilsen 'log'da şunu kontrol et' de."
                    ),
                },
                {"role": "user", "content": kuyruk},
            ],
            zaman_asimi=90,
            deneme=1,
            max_tokens=4096,
        )
        print(" ".join(cevap.split())[:300])
    except Exception:
        pass  # sessiz düş: alarm teşhissiz de gitmeli
    sys.exit(0)


if __name__ == "__main__":
    main()
