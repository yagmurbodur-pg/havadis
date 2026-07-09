# Havadis

> Yapay zekâdan taze havadisler — her sabah otomatik üretilen günlük Türkçe dergi.

Her sabah ~06:47'de (İstanbul) GitHub Actions çalışır: 17 kaynaktan son 36 saatin haberlerini toplar,
Claude editörlüğünde 10-14 haberlik kompakt bir Türkçe sayı yazılır, dergi GitHub Pages'ta yayınlanır
ve ntfy üzerinden telefona bildirim (+e-posta kopyası) gider.

## Mimari

```
fetch.py → candidates.json → Claude (EDITORIAL.md) → issue.json → validate.py → render.py → site/ → Pages
                                                                                    └→ notify.py → ntfy + e-posta
```

- **Halüsinasyon engeli:** Editör link yazamaz, aday havuzundan `id` seçer; `validate.py` havuz dışını reddeder.
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

## CI kurulumu (Actions secrets)

| Secret | Ne |
|---|---|
| `CLAUDE_CODE_OAUTH_TOKEN` | `claude setup-token` çıktısı (Claude aboneliğiyle editörlük) |
| `NTFY_TOPIC` | ntfy kanal adı (uzun ve rastgele — topic şifre gibidir) |
| `NOTIFY_EMAIL` | Bildirimin e-posta kopyasının gideceği adres |

Fontlar SIL OFL lisanslıdır. Haber özetleri kaynaklarına linklidir; içerik hakları kaynaklara aittir.
