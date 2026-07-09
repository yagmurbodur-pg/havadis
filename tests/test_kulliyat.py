"""Külliyat: sayıların kümülatif bilgi tabanına (haberler.jsonl) idempotent birleşmesi + konu endeksi."""
from pipeline.kulliyat import birlestir, konu_ozeti
from tests.test_validate import gecerli_sayi, havuz


def test_birlestir_tum_ogeleri_isler():
    yeni = birlestir([], gecerli_sayi(), havuz(), "2026-07-09", 1)
    assert len(yeni) == 12  # kapak 1 + haber 7 + radar 4

    kapak = [r for r in yeni if r["bolum"] == "Kapak"][0]
    assert kapak["url"] == "https://ornek.com/haber-1"
    assert kapak["konular"] == ["OpenAI", "Modeller"]
    assert kapak["tarih"] == "2026-07-09"
    assert kapak["sayi_no"] == 1

    radar = [r for r in yeni if r["bolum"] == "Radar"]
    assert len(radar) == 4
    assert radar[0]["baslik"]  # başlık aday havuzundan gelir
    assert radar[0]["url"].startswith("https://ornek.com/")


def test_birlestir_idempotent():
    ilk = birlestir([], gecerli_sayi(), havuz(), "2026-07-09", 1)
    tekrar = birlestir(ilk, gecerli_sayi(), havuz(), "2026-07-09", 1)
    assert tekrar == []


def test_konu_ozeti_sayar_ve_sluglar():
    butun = birlestir([], gecerli_sayi(), havuz(), "2026-07-09", 1)
    ozet = konu_ozeti(butun)
    modeller = [k for k in ozet["konular"] if k["ad"] == "Modeller"][0]
    assert modeller["adet"] >= 7
    assert modeller["slug"] == "modeller"
    assert modeller["son"][0]["id"]
