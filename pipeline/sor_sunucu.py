"""Yerel zekâ köprüsü — Havadis Wiki'deki chatbot'a Mac'teki Claude'dan yanıt taşır.

Çalıştır: ~/havadis/sor-sunucu  → Wiki sayfası (127.0.0.1:8747'yi görünce) yanıtları
otomatik olarak buradan alır. Token gerekmez; terminaldeki abonelik oturumu kullanılır.
"""
import json
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pipeline.kulliyat import jsonl_oku
from pipeline.sor import KOK, baglam_sec, lugat_yukle, prompt_kur

KAPI = 8747


class Istek(BaseHTTPRequestHandler):
    def _basliklar(self, durum=200, tur="application/json; charset=utf-8"):
        self.send_response(durum)
        self.send_header("Content-Type", tur)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_OPTIONS(self):
        self._basliklar(204)

    def do_GET(self):
        if self.path == "/ping":
            self._basliklar()
            self.wfile.write(b'{"ok": true}')
        else:
            self._basliklar(404)
            self.wfile.write(b'{"hata": "yok"}')

    def do_POST(self):
        if self.path != "/sor":
            self._basliklar(404)
            self.wfile.write(b'{"hata": "yok"}')
            return
        boy = int(self.headers.get("Content-Length", 0))
        try:
            veri = json.loads(self.rfile.read(boy) or b"{}")
        except json.JSONDecodeError:
            veri = {}
        soru = (veri.get("soru") or "").strip()
        if not soru:
            self._basliklar(400)
            self.wfile.write(b'{"hata": "soru bos"}')
            return

        print(f"soru: {soru[:80]}")
        haberler = jsonl_oku(KOK / "veri" / "haberler.jsonl")
        secim = baglam_sec(soru, haberler, lugat_yukle())
        if not secim["haberler"] and not secim["maddeler"]:
            cevap = "Külliyat'ta bu konuda kayıt yok."
        else:
            sonuc = subprocess.run(
                ["claude", "-p", prompt_kur(soru, secim), "--max-turns", "1"],
                capture_output=True, text=True, timeout=280,
            )
            cevap = sonuc.stdout.strip() if sonuc.returncode == 0 else (
                "Yanıt üretilemedi: " + (sonuc.stderr or "").strip()[:200]
            )
        self._basliklar()
        self.wfile.write(json.dumps({"cevap": cevap}, ensure_ascii=False).encode("utf-8"))

    def log_message(self, *args):
        pass  # kendi kısa logumuz yeter


def main():
    print(f"☕ Havadis yerel zekâ köprüsü: http://127.0.0.1:{KAPI} — Wiki sayfası artık")
    print("   yanıtları buradan alacak. Durdurmak için Ctrl-C.")
    ThreadingHTTPServer(("127.0.0.1", KAPI), Istek).serve_forever()


if __name__ == "__main__":
    main()
