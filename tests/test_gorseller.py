"""Küpür görselleri: kaynak sayfadan og:image/twitter:image ayıklama."""
from pipeline.gorseller import og_gorsel_ayikla


def test_og_image_bulur():
    html = '<html><head><meta property="og:image" content="https://ornek.com/g.jpg"></head></html>'
    assert og_gorsel_ayikla(html) == "https://ornek.com/g.jpg"


def test_twitter_image_yedegi():
    html = '<head><meta name="twitter:image" content="https://ornek.com/t.png"></head>'
    assert og_gorsel_ayikla(html) == "https://ornek.com/t.png"


def test_protokolsuz_url_tamamlanir():
    html = '<head><meta property="og:image" content="//cdn.ornek.com/g.jpg"></head>'
    assert og_gorsel_ayikla(html) == "https://cdn.ornek.com/g.jpg"


def test_gorel_koku_taban_ile_cozulur():
    html = '<head><meta property="og:image" content="/statik/g.jpg"></head>'
    assert og_gorsel_ayikla(html, "https://ornek.com/haber/1") == "https://ornek.com/statik/g.jpg"


def test_yoksa_none():
    assert og_gorsel_ayikla("<html><body>hiç</body></html>") is None
