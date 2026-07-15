"""Havadis'e soru sor — yerel, token'sız chatbot.

Erişim: Türkçe-katlamalı skorlama Külliyat (haberler.jsonl) + Lugat maddelerinden
bağlam seçer; yerel `claude -p` (abonelik oturumu) kaynak numaralı Türkçe yanıt üretir.
Kullanım: ~/havadis/sor "GPT-5.6'da neler oldu?"
"""
import json
import subprocess
import sys
from pathlib import Path

from pipeline.kulliyat import jsonl_oku
from pipeline.lugat_dogrula import _on_yazi_ayir
from pipeline.metin import katla

KOK = Path(__file__).resolve().parent.parent


def _puan(kelimeler, metin):
    duz = katla(metin)
    return sum(duz.count(k) for k in kelimeler)


def baglam_sec(soru, haberler, maddeler, haber_n=12, madde_n=6):
    """Soruyla örtüşen haber ve Lugat maddelerini skorla; yalnızca gerçekten eşleşenleri döndür."""
    kelimeler = [katla(k) for k in soru.split() if len(katla(k)) > 2]

    puanli_haber = []
    for h in haberler:
        metin = f"{h.get('baslik','')} {h.get('ozet','')} {' '.join(h.get('konular', []))}"
        p = _puan(kelimeler, metin)
        if p > 0:
            puanli_haber.append((p, h.get("tarih", ""), h))
    puanli_haber.sort(key=lambda x: (x[0], x[1]), reverse=True)

    puanli_madde = []
    for m in maddeler:
        metin = f"{m.get('ad','')} {m.get('tanim','')} {m.get('govde','')}"
        p = _puan(kelimeler, metin)
        if p > 0:
            puanli_madde.append((p, m))
    puanli_madde.sort(key=lambda x: -x[0])

    return {
        "haberler": [h for _, _, h in puanli_haber[:haber_n]],
        "maddeler": [m for _, m in puanli_madde[:madde_n]],
    }


def lugat_yukle():
    maddeler = []
    for yol in sorted((KOK / "lugat").glob("*.md")):
        if yol.name == "fihrist.md":
            continue
        on_yazi, govde = _on_yazi_ayir(yol.read_text(encoding="utf-8"))
        on_yazi = on_yazi or {}
        maddeler.append(
            {"ad": yol.stem, "tanim": str(on_yazi.get("tanim", "")), "govde": govde.strip()}
        )
    return maddeler


def prompt_kur(soru, secim):
    parcalar = [
        "Sen Havadis'in arşiv asistanısın. Havadis, günlük Türkçe yapay zekâ dergisidir;",
        "aşağıdaki BAĞLAM onun kümülatif arşivi Külliyat'tan ve ansiklopedisi Lugat'tan derlendi.",
        "Soruyu YALNIZCA bu bağlama dayanarak, kolay anlaşılır Türkçeyle yanıtla.",
        "Her önemli iddianın sonuna dayandığı kaynağın numarasını [n] biçiminde koy;",
        "yanıtın en sonunda 'Kaynaklar:' altında [n] başlık — URL listesi ver.",
        "Bağlam yetersizse dürüstçe 'Külliyat'ta bu konuda kayıt yok' de; asla uydurma.",
        "",
        f"SORU: {soru}",
        "",
        "BAĞLAM — Lugat maddeleri:",
    ]
    if secim["maddeler"]:
        for m in secim["maddeler"]:
            parcalar.append(f"### {m['ad']} — {m['tanim']}\n{m['govde'][:2500]}\n")
    else:
        parcalar.append("(eşleşen madde yok)")
    parcalar.append("\nBAĞLAM — Külliyat haberleri:")
    if secim["haberler"]:
        for i, h in enumerate(secim["haberler"], 1):
            parcalar.append(
                f"[{i}] {h.get('tarih','')} · {h.get('kaynak','')} · {h.get('baslik','')}\n"
                f"    {h.get('ozet','')}\n    URL: {h.get('url','')}"
            )
    else:
        parcalar.append("(eşleşen haber yok)")
    return "\n".join(parcalar)


def main():
    if len(sys.argv) < 2 or not " ".join(sys.argv[1:]).strip():
        print('Kullanım: sor "sorunuz"  (ör. sor "GPT-5.6 fiyatı ne?")')
        sys.exit(1)
    soru = " ".join(sys.argv[1:])

    haberler = jsonl_oku(KOK / "veri" / "haberler.jsonl")
    secim = baglam_sec(soru, haberler, lugat_yukle())
    if not secim["haberler"] and not secim["maddeler"]:
        print("Külliyat'ta bu kelimelerle eşleşen kayıt bulunamadı. Farklı kelimelerle dene.")
        sys.exit(0)

    print(f"☕ {len(secim['haberler'])} haber + {len(secim['maddeler'])} lugat maddesi bulundu; yanıt yazılıyor…\n")
    sonuc = subprocess.run(
        ["claude", "-p", prompt_kur(soru, secim), "--max-turns", "1"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if sonuc.returncode != 0:
        print("Yanıt üretilemedi:", (sonuc.stderr or "").strip()[:300])
        sys.exit(1)
    print(sonuc.stdout.strip())


if __name__ == "__main__":
    main()
