"""Acil durum: editör (Claude) çıktı üretemezse havuzdan mekanik bir 'mini sayı' kur.

Metinler aday verisinden AYNEN alınır (özet kaynak dilinde kalabilir) — kod uydurmaz,
bu yüzden validate zorunlu değildir. Dergi 'mini sayı' uyarısıyla yayınlanır.
"""
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent


def _kisalt(metin, kelime_siniri):
    kelimeler = str(metin or "").split()
    if len(kelimeler) <= kelime_siniri:
        return " ".join(kelimeler)
    return " ".join(kelimeler[:kelime_siniri]) + "…"


def mini_sayi(havuz):
    adaylar = sorted(
        havuz.get("adaylar", []),
        key=lambda a: (a.get("oncelik", 1), a.get("tarih", "")),
        reverse=True,
    )
    if not adaylar:
        raise SystemExit("Havuz boş — mini sayı bile kurulamıyor.")

    def haber(a):
        return {
            "id": a["id"],
            "baslik": (a.get("baslik") or "")[:110],
            "ozet": _kisalt(a.get("ozet") or a.get("baslik") or "", 55)
            or "Ayrıntı için kaynağa göz at.",
            "neden_onemli": "Editör bugün ulaşılamadı; ayrıntı kaynakta.",
        }

    kapak = adaylar[0]
    gundem = adaylar[1:6]
    radar = adaylar[6:12]

    sayi = {
        "mini": True,
        "kapak": {"kicker": "MİNİ SAYI", **haber(kapak)},
        "bolumler": (
            [{"ad": "Gündem", "haberler": [haber(a) for a in gundem]}] if gundem else []
        ),
        "radar": [
            {"id": a["id"], "cumle": _kisalt(a.get("baslik") or "", 30)} for a in radar
        ],
        "editor_notu": "Bu sabah editör üretimi başarısız oldu; Havadis otomatik mini sayıyla çıktı.",
    }
    return sayi


def main():
    havuz = json.loads((KOK / "candidates.json").read_text(encoding="utf-8"))
    sayi = mini_sayi(havuz)
    (KOK / "issue.json").write_text(
        json.dumps(sayi, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print("Mini sayı kuruldu (fallback).")


if __name__ == "__main__":
    main()
