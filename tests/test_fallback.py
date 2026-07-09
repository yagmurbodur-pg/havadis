"""Acil durum mini sayısı: editör ulaşılamazsa havuzdan mekanik, güvenli bir sayı kur."""
from pipeline.fallback import mini_sayi
from tests.test_validate import havuz


def test_mini_sayi_havuzdan_kurulur():
    h = havuz(15)
    s = mini_sayi(h)
    gecerli_idler = {a["id"] for a in h["adaylar"]}
    kullanilan = [s["kapak"]["id"]]
    for b in s["bolumler"]:
        kullanilan += [x["id"] for x in b["haberler"]]
    kullanilan += [r["id"] for r in s["radar"]]
    assert set(kullanilan) <= gecerli_idler
    assert len(kullanilan) == len(set(kullanilan))  # tekrar yok
    assert s.get("mini") is True
    assert len(s["radar"]) >= 3


def test_mini_sayi_kucuk_havuzda_cokmez():
    s = mini_sayi(havuz(3))
    assert s["kapak"]["id"]
