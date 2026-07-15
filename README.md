# Havadis

> Yapay zekâdan taze havadisler — her sabah otomatik üretilen günlük Türkçe dergi.

Her sabah 06:47'de (İstanbul) **Mac'te launchd** `sabah.sh`'ı çalıştırır: 17 kaynaktan son 36 saatin
haberleri toplanır, **yerel Claude** (mevcut abonelik oturumu — ek anahtar/token gerekmez) 10-14 haberlik
kompakt bir Türkçe sayı yazar, sonuç push'lanır; GitHub Actions yalnızca Pages yayını yapar ve ntfy
üzerinden telefona bildirim (+e-posta kopyası) gider. Mac uykudaysa görev uyanınca telafi edilir.

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
