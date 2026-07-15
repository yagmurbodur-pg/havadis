"""fetch modülünün saf fonksiyonları: normalize, kimlik, filtreler, pencere, özet temizliği, kümeleme."""
from datetime import datetime, timedelta, timezone

from pipeline.fetch import (
    anahtar_gecer_mi,
    gh_trending_ayristir,
    hn_filtrele,
    karaliste_mi,
    kimlik,
    kumele,
    pencerede_mi,
    temizle_ozet,
    url_normalize,
)


def test_gh_trending_ayristir():
    html = """
    <article class="Box-row"><h2 class="h3"><a href="/acme/super-ai">acme / super-ai</a></h2>
    <p class="col-9">Yapay zekâ ajanları için süper araç</p>
    <span class="d-inline-block float-sm-right">1,234 stars today</span></article>
    <article class="Box-row"><h2 class="h3"><a href="/foo/bar">foo / bar</a></h2></article>
    """
    simdi = datetime(2026, 7, 15, 4, 0, tzinfo=timezone.utc)
    sonuc = gh_trending_ayristir(html, simdi)
    assert len(sonuc) == 2
    assert sonuc[0]["url"] == "https://github.com/acme/super-ai"
    assert "acme/super-ai" in sonuc[0]["baslik"]
    assert "süper araç" in sonuc[0]["ozet"]
    assert "1,234" in sonuc[0]["ozet"]
    assert sonuc[0]["bolum_ipucu"] == "arac_cantasi"
    assert sonuc[1]["ozet"] == ""


def test_url_normalize_utm_temizler():
    a = url_normalize("https://Ornek.com/haber?utm_source=x&utm_medium=rss&id=5")
    assert "utm_" not in a
    assert "id=5" in a
    assert a.startswith("https://ornek.com/")


def test_url_normalize_fragment_ve_slash():
    assert url_normalize("https://ornek.com/haber/#bolum") == url_normalize(
        "https://ornek.com/haber"
    )


def test_kimlik_kararli_ve_8_karakter():
    a = kimlik("https://ornek.com/haber?utm_source=rss")
    b = kimlik("https://ornek.com/haber")
    assert a == b
    assert len(a) == 8


def test_karaliste_yakalar():
    kara = ["webinar", "sponsorlu"]
    assert karaliste_mi("Yeni WEBINAR duyurusu", kara)
    assert not karaliste_mi("Yeni model duyurusu", kara)


def test_anahtar_filtre():
    f = ["yapay zek", "gpt"]
    assert anahtar_gecer_mi("Girişim, yapay zekâ modeli çıkardı", f)
    assert anahtar_gecer_mi("GPT tabanlı asistan", f)
    assert not anahtar_gecer_mi("Yeni e-ticaret yatırımı", f)


def test_pencere():
    simdi = datetime(2026, 7, 9, 6, 0, tzinfo=timezone.utc)
    assert pencerede_mi(simdi - timedelta(hours=35), simdi, 36)
    assert not pencerede_mi(simdi - timedelta(hours=37), simdi, 36)


def test_temizle_ozet_html_soyar_ve_kisaltir():
    html = "<p>Merhaba <b>dünya</b>.</p> " + "<span>kelime</span> " * 300
    t = temizle_ozet(html, limit=100)
    assert "<" not in t
    assert t.startswith("Merhaba dünya.")
    assert len(t) <= 101  # kısaltma + "…"


def aday(cid, baslik, oncelik, kaynak="Kaynak", tarih="2026-07-09T01:00:00+00:00"):
    return {
        "id": cid,
        "baslik": baslik,
        "oncelik": oncelik,
        "kaynak": kaynak,
        "url": f"https://ornek.com/{cid}",
        "tarih": tarih,
        "ozet": "",
        "bolum_ipucu": "gundem",
        "ek_kaynaklar": [],
    }


def test_kumele_benzer_basliklar_birlesir():
    a = aday("a1", "OpenAI launches GPT-6 with new agent tools", 2, "TechCrunch AI")
    b = aday("b1", "OpenAI launches GPT-6", 3, "OpenAI")
    sonuc = kumele([a, b])
    assert len(sonuc) == 1
    birincil = sonuc[0]
    assert birincil["id"] == "b1"  # yüksek öncelik (kurumsal kaynak) kazanır
    assert any(e["url"] == a["url"] for e in birincil["ek_kaynaklar"])


def test_kumele_farkli_basliklar_ayri_kalir():
    a = aday("a1", "OpenAI launches GPT-6", 3)
    b = aday("b1", "Mistral releases new open model for coding", 3)
    assert len(kumele([a, b])) == 2


def test_hn_filtre_puan_esigi():
    hits = [
        {"title": "AI thing", "url": "https://x.com/1", "points": 79,
         "created_at": "2026-07-09T01:00:00Z", "objectID": "1"},
        {"title": "Big AI thing", "url": "https://x.com/2", "points": 80,
         "created_at": "2026-07-09T01:00:00Z", "objectID": "2"},
    ]
    kalan = hn_filtrele(hits, min_puan=80)
    assert len(kalan) == 1
    assert kalan[0]["baslik"] == "Big AI thing"
