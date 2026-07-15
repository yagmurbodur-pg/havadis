"""ntfy bildirimi — JSON publish (UTF-8 güvenli; Türkçe karakterli başlıklar header'da bozulur).

Ortam değişkenleri: NTFY_TOPIC (zorunlu), SITE_URL, NOTIFY_EMAIL (isteğe bağlı).
"""
import json
import os
import sys
from pathlib import Path

import httpx

KOK = Path(__file__).resolve().parent.parent


def bildirim_yuku(baslik, mesaj, url, topic, email=None):
    yuk = {
        "topic": topic,
        "title": baslik,
        "message": mesaj,
        "click": url,
        "tags": ["coffee", "newspaper"],
    }
    if email:
        yuk["email"] = email
    return yuk


def main():
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("NTFY_TOPIC tanımlı değil; bildirim atlanıyor.")
        return
    site_url = os.environ.get("SITE_URL", "")
    email = os.environ.get("NOTIFY_EMAIL") or None

    son = json.loads((KOK / "site" / "son.json").read_text(encoding="utf-8"))
    baslik = f"Havadis — Sayı {son['sayi_no']} çıktı ☕"
    if son.get("mini"):
        baslik = f"Havadis — Sayı {son['sayi_no']} (mini) çıktı"
    yuk = bildirim_yuku(baslik, son.get("kapak", ""), site_url, topic, email)

    basliklar = {}
    ntfy_token = os.environ.get("NTFY_TOKEN")  # e-posta kopyası için ntfy hesabı (isteğe bağlı)
    if ntfy_token:
        basliklar["Authorization"] = f"Bearer {ntfy_token}"

    r = httpx.post("https://ntfy.sh", json=yuk, headers=basliklar, timeout=20)
    if r.status_code == 400 and "email" in yuk and "email" in r.text.lower():
        # ntfy.sh anonim e-posta iletimini reddediyor → push'u e-postasız kurtar
        yuk.pop("email", None)
        print("uyarı: ntfy e-posta kopyasını reddetti (hesap gerekli); yalnızca push gönderiliyor.")
        r = httpx.post("https://ntfy.sh", json=yuk, headers=basliklar, timeout=20)
    r.raise_for_status()
    print("Bildirim gönderildi ✓")


if __name__ == "__main__":
    main()
