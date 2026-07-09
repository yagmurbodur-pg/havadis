"""ntfy JSON yükü kurulumu (UTF-8 güvenli; header yerine JSON publish)."""
from pipeline.notify import bildirim_yuku


def test_yuk_alanlari():
    y = bildirim_yuku(
        baslik="Havadis — Sayı 3 çıktı ☕",
        mesaj="Kapak: OpenAI yeni model duyurdu",
        url="https://kullanici.github.io/havadis/",
        topic="havadis-abc123",
        email="okur@ornek.com",
    )
    assert y["topic"] == "havadis-abc123"
    assert y["title"].startswith("Havadis")
    assert y["click"].endswith("/havadis/")
    assert y["email"] == "okur@ornek.com"
    assert "OpenAI" in y["message"]
    assert "tags" in y


def test_email_opsiyonel():
    y = bildirim_yuku("b", "m", "https://u", "t", email=None)
    assert "email" not in y
