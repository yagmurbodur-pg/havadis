"""Obsidian kasası: haberler.jsonl → wikilink'li Markdown notları (Haberler/ + Konular/)."""
from pipeline.kasa import benzersiz_adlar, dosya_adi, kasa_yaz
from pipeline.kulliyat import birlestir
from tests.test_validate import gecerli_sayi, havuz


def test_dosya_adi_yasakli_karakterleri_temizler():
    k = {"tarih": "2026-07-09", "baslik": 'GPT: "üç" / [iş] #1 | soru?'}
    ad = dosya_adi(k)
    assert ad.startswith("2026-07-09 GPT")
    for c in '/\\:#^[]|"?*<>':
        assert c not in ad


def test_dosya_adi_uzunlugu_sinirli():
    k = {"tarih": "2026-07-09", "baslik": "ç" * 300}
    assert len(dosya_adi(k)) <= 80


def test_kasa_haber_notlari(tmp_path):
    butun = birlestir([], gecerli_sayi(), havuz(), "2026-07-09", 1)
    kasa_yaz(tmp_path, butun)
    notlar = list((tmp_path / "Haberler").glob("*.md"))
    assert len(notlar) == 12  # kapak 1 + haber 7 + radar 4 (aynı başlıklar ezişmez)

    adlar = benzersiz_adlar(butun)
    kapak = butun[0]
    icerik = (tmp_path / "Haberler" / (adlar[kapak["id"]] + ".md")).read_text(encoding="utf-8")
    assert "[[OpenAI]]" in icerik
    assert "https://ornek.com/haber-1" in icerik
    assert "Neden önemli?" in icerik
    assert "tarih: 2026-07-09" in icerik


def test_kasa_konu_hublari(tmp_path):
    butun = birlestir([], gecerli_sayi(), havuz(), "2026-07-09", 1)
    kasa_yaz(tmp_path, butun)
    hub = (tmp_path / "Konular" / "Modeller.md").read_text(encoding="utf-8")
    assert hub.count("[[2026-07-09") >= 7  # kapak + 7 haber "Modeller" etiketli


def test_kasa_iliskili_wikilink(tmp_path):
    butun = birlestir([], gecerli_sayi(), havuz(), "2026-07-09", 1)
    eski, yeni = butun[5], butun[1]
    yeni["iliskili"] = [eski["id"]]
    kasa_yaz(tmp_path, butun)
    adlar = benzersiz_adlar(butun)
    icerik = (tmp_path / "Haberler" / (adlar[yeni["id"]] + ".md")).read_text(encoding="utf-8")
    hedef = adlar[eski["id"]]
    assert ("[[" + hedef + "]]") in icerik
    assert (tmp_path / "Haberler" / (hedef + ".md")).exists()  # bağ kör değil
