# Havadis

> Yapay zekâdan taze havadisler — her sabah otomatik üretilen günlük Türkçe dergi.

Her sabah 06:47'de (İstanbul) **launchd, kısa bir Terminal penceresinde** `sabah.command`'ı açar
(Keychain'deki abonelik kimliğine erişim için — ek anahtar/token gerekmez): 17 kaynaktan son 36 saatin
haberleri toplanır, **yerel Claude** 10-14 haberlik kompakt bir Türkçe sayı yazar, sonuç push'lanır;
GitHub Actions yalnızca Pages yayını yapar ve ntfy telefona push bildirimi gönderir. Pencere iş bitince
kendini kapatır; Mac uykudaysa görev uyanınca telafi edilir. Editör 15 dakikada bitmezse bekçi onu durdurur
ve güvenlik ağı olarak "mini sayı" yayınlanır — sabah asla boş geçmez.

Not: ntfy.sh anonim e-posta iletimini artık desteklemiyor; e-posta kopyası için ücretsiz bir ntfy hesabı
açıp `.sabah.env`'e `NTFY_TOKEN` eklemek yeterli (kod hazır) — yoksa yalnızca push gider.

## Mimari

```
fetch.py → candidates.json → Claude (EDITORIAL.md) → issue.json → validate.py → render.py  → site/  → Pages
                                                                     ├→ kulliyat.py → veri/haberler.jsonl + arama dizini
                                                                     ├→ kasa.py     → kasa/ (Obsidian vault, wikilink'li)
                                                                     └→ notify.py   → ntfy push + e-posta
```

- **Dergi modu:** sayfalar gerçek dergi gibi çevrilir (sürükle/kaydır/ok tuşları), WebAudio ile sentezlenen kâğıt sesi eşlik eder; ≡ düğmesiyle klasik akış görünümü.
- **Külliyat:** her haber konu etiketleri ve `iliskili` bağlarıyla kümülatif bilgi tabanında birikir; `site/kulliyat/` sayfasında Türkçe-toleranslı arama + konu dosyaları.
- **Obsidian kasası:** `kasa/` klasörünü Obsidian'da vault olarak aç — Haberler ↔ Konular wikilink grafiği kendiliğinden oluşur.
- **Halüsinasyon engeli:** Editör link yazamaz, aday havuzundan `id` seçer; `validate.py` havuz dışını reddeder (ilişki bağları dahil).
- **Sessiz ölüm engeli:** İş başarısız olursa ntfy'ye yüksek öncelikli uyarı düşer.
- Kaynaklar: `sources.yaml` · İlgi profili: `ilgi.yaml` · Editoryal kurallar: `EDITORIAL.md`

## Yerel çalıştırma

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m pipeline.fetch        # → candidates.json
# issue.json'ı EDITORIAL.md kurallarıyla üret (CI'da claude-code-action yapar)
python3 -m pipeline.validate     # şema + havuz kontrolü
python3 -m pipeline.render       # → site/
open site/index.html
```

## Sabah otomasyonu (yerel)

- `sabah.sh` — tüm hattı koşan betik (fetch → yerel `claude -p` editörlüğü → validate/fallback → render/kulliyat/kasa → push → notify). Log: `~/Library/Logs/havadis-sabah.log`.
- `~/Library/LaunchAgents/com.havadis.sabah.plist` — her sabah 06:47; elle tetikleme: `launchctl kickstart gui/$(id -u)/com.havadis.sabah`.
- Yerel ayarlar `.sabah.env` dosyasında (git'e girmez): `NTFY_TOPIC`, `NOTIFY_EMAIL`, `SITE_URL`.

## CI (Actions) — yalnızca yayın

Push geldiğinde `site/` Pages'e yayınlanır; başarısız olursa `NTFY_TOPIC` secret'ıyla alarm bildirimi atılır. Bulutta LLM çağrısı yoktur.

Fontlar SIL OFL lisanslıdır. Haber özetleri kaynaklarına linklidir; içerik hakları kaynaklara aittir.
