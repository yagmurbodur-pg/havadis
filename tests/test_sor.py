"""Chatbot erişim katmanı: Türkçe-katlamalı skorlamayla doğru kayıtları seçmeli."""
from pipeline.sor import baglam_sec


def test_baglam_secimi_turkce_katlar():
    haberler = [
        {"id": "1", "baslik": "Açık kaynak model yayınlandı", "ozet": "Yeni model herkese açık.",
         "konular": ["açık kaynak"], "url": "u1", "tarih": "2026-07-15", "kaynak": "X"},
        {"id": "2", "baslik": "Kripto piyasası düştü", "ozet": "",
         "konular": [], "url": "u2", "tarih": "2026-07-14", "kaynak": "Y"},
    ]
    maddeler = [
        {"ad": "Açık kaynak", "tanim": "Herkesin kullanabildiği yazılım/model.", "govde": "Uzun metin."},
        {"ad": "Nvidia", "tanim": "Çip üreticisi.", "govde": "..."},
    ]
    secim = baglam_sec("acik kaynak modellerde ne oldu", haberler, maddeler)
    haber_idleri = [h["id"] for h in secim["haberler"]]
    madde_adlari = [m["ad"] for m in secim["maddeler"]]
    assert "1" in haber_idleri
    assert "2" not in haber_idleri
    assert "Açık kaynak" in madde_adlari
    assert "Nvidia" not in madde_adlari
