# Havadis

> Yapay zekâdan taze havadisler — her sabah otomatik üretilen günlük Türkçe dergi.

Her sabah 06:47'de (İstanbul) **launchd, kısa bir Terminal penceresinde** `sabah.command`'ı açar:
17 kaynaktan son 36 saatin haberleri toplanır, **OpenAI-uyumlu API'deki Kimi modeli** (ayarlar
kökteki `.env` dosyasında) 10-14 haberlik kompakt bir Türkçe sayı yazar, sonuç push'lanır;
GitHub Actions yalnızca Pages yayını yapar ve ntfy telefona push bildirimi gönderir. Pencere iş bitince
kendini kapatır; Mac uykudaysa görev uyanınca telafi edilir. Editör üç denemede geçerli sayı üretemezse
güvenlik ağı olarak "mini sayı" yayınlanır — sabah asla boş geçmez.

Not: ntfy.sh anonim e-posta iletimini artık desteklemiyor; e-posta kopyası için ücretsiz bir ntfy hesabı
açıp `.sabah.env`'e `NTFY_TOKEN` eklemek yeterli (kod hazır) — yoksa yalnızca push gider.

## Mimari

```
fetch.py → candidates.json → Kimi (editor.py, EDITORIAL.md) → issue.json → validate.py → render.py → site/ → Pages
                                                                     ├→ kulliyat.py       → veri/haberler.jsonl + arama dizini + veri/bugun.json
                                                                     ├→ Kimi (lugat_editor.py, LUGAT.md) → lugat/ maddeleri → lugat_dogrula.py → lugat_render.py
                                                                     └→ notify.py         → ntfy push
sor "soru?"  → Külliyat+Lugat'tan bağlam seç → Kimi → kaynak numaralı Türkçe yanıt
```

- **Dergi modu:** sayfalar gerçek dergi gibi çevrilir (sürükle/kaydır/ok tuşları), gerçek kâğıt sesi eşlik eder; ≡ düğmesiyle klasik akış görünümü.
- **Külliyat:** her haber konu etiketleri ve `iliskili` bağlarıyla kümülatif bilgi tabanında birikir; `site/kulliyat/` sayfasında Türkçe-toleranslı arama + konu dosyaları.
- **Lugat (LLM wiki):** her sabah ikinci bir editör geçişi, günün haberlerinin dokunduğu kavram/varlık maddelerini günceller — tanım (≤140 kr), ilişkiler, `(haber: id)` çivili gelişme zinciri. Bütünlük `lugat_dogrula.py`'de sert kontroldür: yetim madde, kırık bağ, uydurma id yayına giremez (dictionary-of-ai-coding deseninden).
- **Chatbot:** `./sor "GPT-5.6'da ne oldu?"` — Külliyat+Lugat'tan bağlam seçer, Kimi ile kaynak numaralı yanıt verir.
- **Halüsinasyon engeli:** Editör link yazamaz, aday havuzundan `id` seçer; `validate.py` havuz dışını reddeder (ilişki bağları dahil).
- **Sessiz ölüm engeli:** İş başarısız olursa ntfy'ye yüksek öncelikli uyarı düşer.
- Kaynaklar: `sources.yaml` · İlgi profili: `ilgi.yaml` · Editoryal kurallar: `EDITORIAL.md`

## Yerel çalıştırma

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m pipeline.fetch        # → candidates.json
python3 -m pipeline.editor       # issue.json'ı EDITORIAL.md kurallarıyla Kimi'ye yazdırır (.env gerekir)
python3 -m pipeline.validate     # şema + havuz kontrolü
python3 -m pipeline.render       # → site/
open site/index.html
```

## Sabah otomasyonu (yerel)

- `sabah.sh` — tüm hattı koşan betik (fetch → Kimi editörlüğü → validate/fallback → render/kulliyat → push → notify). Log: `~/Library/Logs/havadis-sabah.log`.
- `~/Library/LaunchAgents/com.havadis.sabah.plist` — her sabah 06:47; elle tetikleme: `launchctl kickstart gui/$(id -u)/com.havadis.sabah`.
- LLM ayarları kökteki `.env` dosyasında (git'e girmez): `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`.
- Diğer yerel ayarlar `.sabah.env` dosyasında (git'e girmez): `NTFY_TOPIC`, `NOTIFY_EMAIL`, `SITE_URL`.

## CI (Actions) — yalnızca yayın

Push geldiğinde `site/` Pages'e yayınlanır; başarısız olursa `NTFY_TOPIC` secret'ıyla alarm bildirimi atılır. Bulutta LLM çağrısı yoktur.

Fontlar SIL OFL lisanslıdır. Haber özetleri kaynaklarına linklidir; içerik hakları kaynaklara aittir.
