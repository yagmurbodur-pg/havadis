# Havadis — Günlük Yapay Zekâ Dergisi (PWA)

> "Yapay zekâdan taze havadisler."

## Bağlam

Kullanıcı, AI alanındaki güncel gelişmeleri her sabah **gerçek bir dergi okur gibi** takip etmek istiyor: içerik **Türkçe**, dil **çok kolay anlaşılır ve kompakt**, her haberde **asıl kaynağa link**. Dergi masaüstünde ve telefonda açılabilmeli, hazır olduğunda **bildirim** gelmeli. Dizinde mevcut bir haber/dergi çalışması yok — sıfırdan, bağımsız bir proje.

**Netleşen kararlar** (kullanıcıyla soruldu):
| Karar | Seçim |
|---|---|
| Ad | **Havadis** (repo/URL: `havadis`) |
| Platform | GitHub Pages'ta statik **PWA**; üretim **GitHub Actions** (her sabah) |
| LLM erişimi | **Claude aboneliği (OAuth token)** → `claude-code-action` (`claude_code_oauth_token` girdisi bugün mevcut, doğrulandı ✓); yedek: API anahtarı |
| Bildirim | **ntfy** (push) + **e-posta kopyası** |
| Bölümler | Çekirdek (model/ürün + araştırma) + **Türkiye'den** + **Pratik araçlar & ipuçları** |
| Görsel kimlik | **Bağımsız editoryal dergi** (Pavo kurumsal dilinden ayrı) |

## Mimari (günlük akış)

```
GitHub Actions cron "47 3 * * *" (06:47 İstanbul; tepe-saat dakikalarından kaçınıldı, 5-30 dk gecikmeyle sayı ~07:00-07:30 hazır)
 1. fetch.py      → sources.yaml kaynaklarından son 36 saat → normalize + dedupe/kümeleme → candidates.json (her adaya kısa ID)
 2. claude-code-action (abonelik OAuth) → EDITORIAL.md kurallarıyla ID üzerinden seçim + Türkçe yazım → issue.json (Claude URL yazmaz, ID seçer)
 3. validate.py   → pydantic şema + ID/URL havuz kontrolü (uydurma link imkânsız) + uzunluk sınırları; hata → 1 retry → fallback mini sayı
 4. render.py     → Jinja2 → site/ (index.html = bugünkü sayı, arsiv/YYYY-MM-DD.html, arşiv listesi, manifest, sw.js)
 5. arşiv commit'i (repo aktif kalır) + Pages deploy: configure-pages@v6 → upload-pages-artifact@v5 → deploy-pages@v5
 6. notify.py     → ntfy push (Title + Click: dergi URL'i + e-posta kopyası); iş HATA verirse `if: failure()` adımı yüksek öncelikli ntfy uyarısı atar
```

Günlük commit'ler repo'yu aktif tutar (GitHub'ın 60 günlük "hareketsiz repo'da cron'u kapatma" kuralına doğal önlem).

## Depo yapısı (`~/Desktop/havadis`, public repo)

```
havadis/
├── EDITORIAL.md            # editoryal anayasa: seçim ölçütleri + yazım dili kuralları (Claude'un sabah okuduğu)
├── sources.yaml            # kaynak listesi (ad, url, tip: rss|api, bölüm ipucu, ağırlık)
├── ilgi.yaml               # ilgi profili (ör. ajanlar, kurumsal dönüşüm, Türkçe NLP) → skorlamada bonus
├── pipeline/
│   ├── fetch.py            # toplama + normalize + URL-dedupe + başlık kümeleme (rapidfuzz)
│   ├── validate.py         # pydantic şema + ID/URL havuz kontrolü (Claude URL yazmaz, ID seçer)
│   ├── render.py           # Jinja2 → site/ (sayı + arşiv + manifest + service worker)
│   └── notify.py           # ntfy POST (Title/Click/Tags + X-Email kopyası)
├── templates/dergi.html.j2, arsiv.html.j2
├── assets/                 # self-host woff2 fontlar, ikonlar (PWA), stil
├── site/                   # üretilen statik site (Pages artifact olarak yayınlanır; arşiv git'te birikir)
├── docs/tasarim.md         # bu tasarım dokümanı repoya kopyalanır
└── .github/workflows/havadis.yml
```

Python bağımlılıkları (doğrulandı): `feedparser, httpx, jinja2, pydantic, rapidfuzz, pyyaml, beautifulsoup4, lxml, python-dateutil`.

## Filtreleme yöntemi (kullanıcının istediği "yöntem", açıkça)

1. **Toplama**: tüm kaynaklardan son 36 saat (cron kaymalarına tampon).
2. **Ön eleme (kod)**: URL dedupe → başlık benzerliği ≥85 kümeleme → aynı kümede kaynak önceliği: şirket duyurusu > medya aktarımı; karaliste (webinar, sponsorlu, indirim...).
3. **Editoryal seçim (Claude)**: küme başına önem puanı 1–5 (etki genişliği, somutluk: ürün mü söylenti mi, yenilik; `ilgi.yaml` + Türkiye ilgisi bonus). Kota: kapak 1 + haber 8–12 + Radar 5.
4. **Yazım (Claude)**: aşağıdaki dil kurallarıyla `issue.json`.
5. **Doğrulama (kod)**: şema, uzunluk sınırları, **her URL aday havuzundan mı** (uydurma link imkânsız), tarih sağlığı.
6. **Yayın + bildirim.** Hata durumunda: heuristik "mini sayı" (başlık+link listesi) + ntfy'ye yüksek öncelikli hata bildirimi.

## Yazım dili kuralları (EDITORIAL.md'ye girecek)

- Hedef okur: teknik olmayan, meraklı yetişkin. Cümle ≤ 20 kelime.
- Haber = başlık + 2–3 cümle özet (≤ 60 kelime) + **"Neden önemli?"** tek cümle (≤ 25 kelime) + kaynak linki. Kapak ≤ 120 kelime.
- Teknik terim ilk geçişte parantezle açıklanır: "ajan (kendi başına iş yapan YZ yazılımı)".
- Clickbait yok; sayılar ve tarihler net; doğrulanmamış bilgi "iddiaya göre" ile işaretli.
- Radar: 5 tek cümlelik kısa haber.

## Dergi tasarımı (bağımsız editoryal kimlik)

- **Masthead**: HAVADİS — yüksek kontrastlı serif (Playfair Display / Lora, self-host woff2, Türkçe glif tam); altında "Yapay zekâdan taze havadisler" + "Sayı 12 — 9 Temmuz 2026, Perşembe — ☕ 4 dk".
- **Palet**: gazete kâğıdı sıcaklığı — açık tema: kâğıt `#FAF6EF`, mürekkep `#1A1712`, vurgu "matbaa kırmızısı" `#C4402F`; koyu tema: gece baskısı `#14110C` + sıcak kırık beyaz. `prefers-color-scheme` ile otomatik.
- **Düzen**: tek kolon (≤ 680px), mobil öncelikli. Kapak hikayesi (kicker + büyük serif manşet + özet), bölüm başlıkları zarif filetolarla: Gündem · Araştırma Masası · Türkiye'den · Araç Çantası · Radar. Her kartta kırmızı küçük-harf kicker, manşet, özet, italik "Neden önemli?", kaynak çipi "↗ TechCrunch".
- **Arşiv**: alt kısımda "← Önceki sayı" + tüm sayılar listesi; footer'da "Bugün 14/16 kaynak tarandı" şeffaflık satırı.
- **PWA** (alt dizin `/havadis/` için doğrulanmış kurallar): manifest `start_url: "./"`, `scope: "./"`, tüm yollar göreli, `.nojekyll` dosyası, apple-touch-icon 180px (iOS). Service worker: HTML için network-first + sayı-başına sürümlü cache (Pages'in max-age=600 cache'iyle çakışmasın). iOS'ta kurulum: Paylaş → Ana Ekrana Ekle.

## Kaynaklar (sources.yaml) — 9 Tem 2026'da canlı doğrulandı

| Bölüm | Kaynak | Doğrulanmış uç |
|---|---|---|
| Gündem (kurumsal) | OpenAI | `openai.com/news/rss.xml` ✅ |
| | Anthropic | resmi feed YOK → topluluk feed'i (`Olshansk/rss-feeds`) ✅ + `anthropic.com/news` scrape yedeği |
| | Google AI | `blog.google/technology/ai/rss/` ✅ |
| | Google DeepMind | `deepmind.google/blog/rss.xml` ✅ |
| | Meta AI | `engineering.fb.com/category/ai-research/feed/` ✅ (`ai.meta.com/blog/rss/` ölü) |
| | Mistral | `mistral.ai/rss.xml` ✅ |
| Gündem (medya) | TechCrunch AI | `techcrunch.com/category/artificial-intelligence/feed/` ✅ |
| | The Verge AI | `theverge.com/rss/ai-artificial-intelligence/index.xml` ✅ |
| | Ars Technica AI | `arstechnica.com/ai/feed/` ✅ |
| | MIT Tech Review AI | `technologyreview.com/topic/artificial-intelligence/feed` ✅ |
| Gündem (topluluk) | Hacker News | Algolia API — `points>100` filtresi artık istemci tarafında ✅ |
| Araştırma Masası | HF Daily Papers | `huggingface.co/api/daily_papers` (JSON) ✅ |
| Araç Çantası | Simon Willison | `simonwillison.net/atom/everything/` ✅ |
| | Ben's Bites | `bensbites.com/feed` ✅ |
| Türkiye'den | Webrazzi YZ | `webrazzi.com/kategori/yapay-zeka/feed/` ✅ |
| | ShiftDelete YZ | `shiftdelete.net/yapay-zeka/feed` ✅ |
| | eGirişim | `egirisim.com/feed/` (YZ anahtar kelime filtresiyle) ✅ |

Elenenler: VentureBeat (feed bayat — son öğe 19 Mayıs), The Rundown (çalışan feed yok). `sources.yaml`'da kaynak başına **bayatlık eşiği** tutulur; bayatlayan kaynak dergi footer'ındaki "X/Y kaynak tarandı" sayacına düşer.

## Günlük workflow (doğrulanmış aksiyon sürümleriyle, özet)

```yaml
on:
  schedule: [{cron: "47 3 * * *"}]
  workflow_dispatch: {}
permissions: {contents: write, pages: write, id-token: write}
steps:
  - checkout@v7 → setup-python@v6 (3.12, pip cache) → pip install -r requirements.txt
  - python -m pipeline.fetch                      # candidates.json
  - anthropics/claude-code-action@v1              # claude_code_oauth_token: secrets.CLAUDE_CODE_OAUTH_TOKEN
    #   prompt: "EDITORIAL.md'yi uygula: candidates.json → issue.json"
  - python -m pipeline.validate && python -m pipeline.render
  - git commit (arşiv) + push                     # 60 gün hareketsizlik kuralına doğal önlem
  - configure-pages@v6 → upload-pages-artifact@v5 (site/) → deploy-pages@v5
  - python -m pipeline.notify                     # ntfy push + e-posta kopyası
  - if: failure() → curl -H "Priority: high" ... ntfy   # sessiz ölüm engeli
```

## Bildirim

- ntfy topic: `havadis-<uzun-rastgele>` (topic = şifre gibidir; auth gerekmez — doğrulandı). POST: Title "Havadis — Sayı N çıktı ☕", mesaj = kapak başlığı, `Click` = dergi URL'i, `Email` başlığı = e-posta kopyası (ücretsiz limit 5/gün, ihtiyacımız 1-2 ✓).
- Hata bildirimi ayrı: yüksek öncelik, "Bugünkü sayı üretilemedi: <adım>".

## Senden gerekenler (ön koşullar)

1. GitHub hesabı (`gh auth login`; yoksa hesap açılır — repo public, içerik zaten yayın).
2. Telefona **ntfy** uygulaması (App Store/Play) + özel kanala abonelik (2 dk).
3. `claude setup-token` çalıştırıp çıkan token'ı vermek (Actions secret'ına `CLAUDE_CODE_OAUTH_TOKEN` olarak girilecek).

## Uygulama sırası

1. **İskelet**: `~/Desktop/havadis` repo + dosya yapısı + EDITORIAL.md + sources.yaml + ilgi.yaml; bu plan `docs/tasarim.md` olarak repoya girer.
2. **Pipeline**: fetch → validate → render → notify (her biri yerel test edilerek).
3. **Tasarım**: dergi şablonu + fontlar + PWA manifest/SW (frontend-design + dataviz ilkeleriyle).
4. **Sayı 0 (yerel prova)**: gerçek feed'lerle uçtan uca yerel üretim; Türkçe kalite + link + tema kontrolü; kullanıcı onayı.
5. **GitHub**: repo push, Pages (kaynak: GitHub Actions), secrets: `CLAUDE_CODE_OAUTH_TOKEN`, `NTFY_TOPIC`, `NOTIFY_EMAIL`; `workflow_dispatch` ile manuel uçtan uca test.
6. **Telefon**: ntfy kurulum + bildirim testi; PWA "Ana Ekrana Ekle" testi.
7. **Cron'u aç** + ertesi sabah kontrolü; ilk hafta hata bildirimlerini izle.

## Doğrulama (uçtan uca)

- Yerel: `python pipeline/fetch.py` → candidates.json dolu ve tarihler taze mi; sahte issue.json ile validator'ın uydurma URL'i reddettiğini test et.
- Sayı 0'ı tarayıcıda aç: mobil genişlik, açık/koyu tema, tüm kaynak linkleri tıklanabilir.
- ntfy: test bildirimi telefona düştü mü, Click dergiyi açıyor mu, e-posta kopyası geldi mi.
- Actions: `workflow_dispatch` koşusu yeşil; Pages URL'inde yeni sayı; ertesi sabah cron kendi başına çalıştı mı.
- PWA: telefonda ikon + tam ekran açılış.

## Riskler & karar noktaları

- **OAuth-in-Actions**: `claude_code_oauth_token` girdisi bugün resmen mevcut (doğrulandı); ileride kaldırılırsa API anahtarına geçilir — Sonnet 5 tanıtım fiyatı $2/$10 MTok (31 Ağu 2026'ya dek), tahmini ~3-15$/ay hacme göre. Karar noktası olarak işaretli.
- **Sessiz ölüm zinciri**: pipeline sessizce bozulursa günlük commit durur → GitHub 60 gün sonra cron'u kapatır. Önlem: `if: failure()` ntfy uyarısı + footer'daki "X/Y kaynak" sayacı.
- **Cron gecikmesi**: 5-30+ dk tipik, tepe saatte iş düşebilir → off-minute `47 3` + `workflow_dispatch` elle tetik yedeği.
- **Anthropic topluluk feed'i** sessizce bayatlayabilir (resmi feed yok) → kaynak başına bayatlık eşiği + scrape yedeği (VentureBeat vakası bu riski doğruladı).
- **HN Algolia**: `points` filtresi sunucudan kalktı (400 dönüyor) → puan filtresi istemci tarafında.
- **iOS PWA**: kurulum istemi yok (elle Ana Ekrana Ekle); Safari uzun süre kullanılmayan SW/cache'i temizler → çevrimdışı kalıcılığa güvenme (bildirim zaten ntfy uygulamasında).
- **Halüsinasyon**: Claude URL yazamaz (ID seçer) + validator havuz dışını reddeder; LLM çıktısı şemayla zorlanır, bozuksa dünkü sayı yayında kalır.
- **Maliyet**: altyapı 0$ (public repo Actions + Pages + ntfy); günde 1 editoryal koşu abonelik hakkından kullanır.
