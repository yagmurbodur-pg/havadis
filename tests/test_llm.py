"""llm.json_ayikla: model/vekil çıktısındaki pürüzlere dayanıklı JSON ayıklama."""
import pytest

from pipeline.llm import json_ayikla


def test_temiz_json():
    assert json_ayikla('{"a": 1}') == {"a": 1}


def test_bastaki_bosluk_ve_metin():
    assert json_ayikla('İşte bugünün sayısı:\n {"a": 1}\nBitti.') == {"a": 1}


def test_markdown_citli():
    assert json_ayikla('Açıklama\n```json\n{"a": [1, 2]}\n```') == {"a": [1, 2]}


def test_vekil_bozuk_onek():
    # skwshr.xyz vekilinde gözlenen gerçek vaka: çıktının başına bozuk parça yapışıyor
    metin = '{"sehir{"sehir": "İstanbul", "kita": "Avrupa ve Asya"}'
    assert json_ayikla(metin) == {"sehir": "İstanbul", "kita": "Avrupa ve Asya"}


def test_en_uzun_nesne_kazanir():
    # kırık dış nesnenin içindeki küçük parça değil, tam olan büyük nesne seçilmeli
    metin = 'önek {"a": 1} sonra {"b": {"c": 2}, "d": [3, 4]} kuyruk'
    assert json_ayikla(metin) == {"b": {"c": 2}, "d": [3, 4]}


def test_ic_ice_turkce_icerik():
    metin = '{"baslik": "Kimi K3\'ün ağırlıkları açıldı", "konular": ["açık kaynak"]}'
    assert json_ayikla(metin) == {
        "baslik": "Kimi K3'ün ağırlıkları açıldı",
        "konular": ["açık kaynak"],
    }


def test_json_yoksa_hata():
    with pytest.raises(ValueError):
        json_ayikla("bugün hiç JSON üretmedim, kusura bakma")
