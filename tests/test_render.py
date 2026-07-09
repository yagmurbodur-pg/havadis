"""render yardımcıları + uçtan uca dosya üretimi (şablonun gerçek haliyle)."""
from datetime import datetime, timezone

from pipeline.render import okuma_suresi, sayi_numarasi, tr_tarih, uret
from tests.test_validate import gecerli_sayi, havuz


def test_tr_tarih():
    dt = datetime(2026, 7, 9, 7, 0, tzinfo=timezone.utc)
    assert tr_tarih(dt) == "9 Temmuz 2026, Perşembe"


def test_sayi_numarasi(tmp_path):
    arsiv = tmp_path / "arsiv"
    arsiv.mkdir()
    (arsiv / "2026-07-07.html").write_text("x")
    (arsiv / "2026-07-08.html").write_text("x")
    (arsiv / "index.html").write_text("x")  # sayılmaz
    assert sayi_numarasi(arsiv, bugun="2026-07-09") == 3
    # Aynı gün yeniden çalışırsa numara artmaz:
    (arsiv / "2026-07-09.html").write_text("x")
    assert sayi_numarasi(arsiv, bugun="2026-07-09") == 3


def test_okuma_suresi_en_az_1():
    assert okuma_suresi(gecerli_sayi()) >= 1


def test_uret_dosyalari_yazar(tmp_path):
    simdi = datetime(2026, 7, 9, 4, 30, tzinfo=timezone.utc)
    uret(gecerli_sayi(), havuz(), tmp_path, simdi)
    index = (tmp_path / "index.html").read_text()
    assert "Günün en önemli haberi" in index          # kapak başlığı
    assert "https://ornek.com/haber-1" in index        # kapak kaynak linki
    assert "HAVADİS" in index or "Havadis" in index    # masthead
    assert (tmp_path / "arsiv" / "2026-07-09.html").exists()
    assert (tmp_path / "arsiv" / "index.html").exists()
