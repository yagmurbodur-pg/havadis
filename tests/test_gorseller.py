"""Küpür görselleri + 𝕏 duyuru bağlantıları: kaynak sayfadan ayıklama."""
from pipeline.gorseller import kurum_x_hesabi, og_gorsel_ayikla, x_link_ayikla


def test_x_status_linki_bulur():
    html = '<a href="https://twitter.com/OpenAI/status/1234567890123">duyuru</a>'
    assert x_link_ayikla(html) == "https://twitter.com/OpenAI/status/1234567890123"


def test_x_com_linki_bulur():
    html = '<p>ayrıntı: https://x.com/AnthropicAI/status/987654321 adresinde</p>'
    assert x_link_ayikla(html) == "https://x.com/AnthropicAI/status/987654321"


def test_x_linki_yoksa_none():
    assert x_link_ayikla("<p>bağlantısız içerik https://ornek.com/a</p>") is None


def test_kurum_hesabi_eslesir():
    assert kurum_x_hesabi("OpenAI") == "https://x.com/OpenAI"
    assert kurum_x_hesabi("Webrazzi YZ") is None


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
