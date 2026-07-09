"""validate.dogrula sözleşmesi: editör çıktısı (issue) + aday havuzu → Türkçe hata listesi (boş = geçerli)."""
import copy

import pytest

from pipeline.validate import dogrula


def havuz(n=20):
    return {
        "meta": {"kaynak_ok": 15, "kaynak_toplam": 17},
        "adaylar": [
            {
                "id": f"c{i}",
                "kaynak": "TechCrunch AI",
                "oncelik": 2,
                "bolum_ipucu": "gundem",
                "baslik": f"Aday haber {i}",
                "url": f"https://ornek.com/haber-{i}",
                "tarih": "2026-07-09T01:00:00+00:00",
                "ozet": "Kısa özet.",
                "ek_kaynaklar": [],
            }
            for i in range(1, n + 1)
        ],
    }


def gecerli_sayi():
    def haber(cid):
        return {
            "id": cid,
            "baslik": "Net ve kısa bir başlık",
            "ozet": "İki cümlelik kısa özet. Ne olduğu burada anlatılıyor.",
            "neden_onemli": "Okurun işine dokunan tek cümle.",
            "konular": ["Modeller"],
        }

    return {
        "kapak": {
            "id": "c1",
            "kicker": "MODEL SAVAŞLARI",
            "baslik": "Günün en önemli haberi",
            "ozet": "Kapak özeti burada. Birkaç cümleden oluşuyor. Yeterince kısa.",
            "neden_onemli": "Çok kişiyi etkileyecek somut bir gelişme.",
            "konular": ["OpenAI", "Modeller"],
        },
        "bolumler": [
            {"ad": "Gündem", "haberler": [haber(f"c{i}") for i in range(2, 7)]},
            {"ad": "Araştırma Masası", "haberler": [haber("c7")]},
            {"ad": "Araç Çantası", "haberler": [haber("c8")]},
        ],
        "radar": [
            {"id": f"c{i}", "cumle": "Tek cümlelik kısa bir not."} for i in range(9, 13)
        ],
    }


def test_gecerli_sayi_gecer():
    assert dogrula(gecerli_sayi(), havuz()) == []


def test_havuz_disi_id_reddedilir():
    s = gecerli_sayi()
    s["kapak"]["id"] = "uydurma99"
    hatalar = dogrula(s, havuz())
    assert any("uydurma99" in h for h in hatalar)


def test_tekrarli_id_reddedilir():
    s = gecerli_sayi()
    s["radar"][0]["id"] = "c2"  # c2 zaten Gündem'de
    hatalar = dogrula(s, havuz())
    assert any("c2" in h for h in hatalar)


def test_bilinmeyen_bolum_adi_reddedilir():
    s = gecerli_sayi()
    s["bolumler"][0]["ad"] = "Magazin"
    hatalar = dogrula(s, havuz())
    assert any("Magazin" in h for h in hatalar)


def test_cift_bolum_adi_reddedilir():
    s = gecerli_sayi()
    s["bolumler"].append(copy.deepcopy(s["bolumler"][1]))
    s["bolumler"][-1]["haberler"][0]["id"] = "c13"
    hatalar = dogrula(s, havuz())
    assert any("Araştırma Masası" in h for h in hatalar)


def test_bos_bolum_reddedilir():
    s = gecerli_sayi()
    s["bolumler"].append({"ad": "Türkiye'den", "haberler": []})
    assert dogrula(s, havuz()) != []


def test_uzun_haber_ozeti_reddedilir():
    s = gecerli_sayi()
    s["bolumler"][0]["haberler"][0]["ozet"] = "kelime " * 71
    assert dogrula(s, havuz()) != []


def test_uzun_kapak_ozeti_reddedilir():
    s = gecerli_sayi()
    s["kapak"]["ozet"] = "kelime " * 136
    assert dogrula(s, havuz()) != []


def test_uzun_neden_onemli_reddedilir():
    s = gecerli_sayi()
    s["bolumler"][0]["haberler"][0]["neden_onemli"] = "kelime " * 31
    assert dogrula(s, havuz()) != []


def test_uzun_baslik_reddedilir():
    s = gecerli_sayi()
    s["kapak"]["baslik"] = "ç" * 111
    assert dogrula(s, havuz()) != []


def test_radar_az_reddedilir():
    s = gecerli_sayi()
    s["radar"] = s["radar"][:2]
    assert dogrula(s, havuz()) != []


def test_toplam_haber_az_reddedilir():
    s = gecerli_sayi()
    s["bolumler"] = [{"ad": "Gündem", "haberler": s["bolumler"][0]["haberler"][:3]}]
    assert dogrula(s, havuz()) != []


def test_kapak_yoksa_reddedilir():
    s = gecerli_sayi()
    del s["kapak"]
    assert dogrula(s, havuz()) != []


def test_editor_notu_varsa_gecer():
    s = gecerli_sayi()
    s["editor_notu"] = "Bugün gündem sakindi."
    assert dogrula(s, havuz()) == []


def test_uzun_editor_notu_reddedilir():
    s = gecerli_sayi()
    s["editor_notu"] = "kelime " * 61
    assert dogrula(s, havuz()) != []


# ————— Külliyat alanları: konular + iliskili —————

def test_konular_eksik_reddedilir():
    s = gecerli_sayi()
    del s["bolumler"][0]["haberler"][0]["konular"]
    assert dogrula(s, havuz()) != []


def test_konular_fazla_reddedilir():
    s = gecerli_sayi()
    s["kapak"]["konular"] = ["a", "b", "c", "d", "e"]
    assert dogrula(s, havuz()) != []


def test_konu_cok_uzunsa_reddedilir():
    s = gecerli_sayi()
    s["kapak"]["konular"] = ["ç" * 33]
    assert dogrula(s, havuz()) != []


def test_iliskili_gecmiste_yoksa_reddedilir():
    s = gecerli_sayi()
    s["bolumler"][0]["haberler"][0]["iliskili"] = ["eski1"]
    hatalar = dogrula(s, havuz(), eski_idler=set())
    assert any("eski1" in h for h in hatalar)


def test_iliskili_gecmisteyse_gecer():
    s = gecerli_sayi()
    s["bolumler"][0]["haberler"][0]["iliskili"] = ["eski1"]
    assert dogrula(s, havuz(), eski_idler={"eski1"}) == []


def test_iliskili_fazlaysa_reddedilir():
    s = gecerli_sayi()
    s["bolumler"][0]["haberler"][0]["iliskili"] = ["e1", "e2", "e3", "e4"]
    hatalar = dogrula(s, havuz(), eski_idler={"e1", "e2", "e3", "e4"})
    assert hatalar != []
