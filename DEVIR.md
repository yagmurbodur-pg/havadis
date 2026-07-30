# Havadis — İşletme El Kitabı (Devir)

Bu sistemin tüm zekâ katmanı **kökteki `.env`'de tanımlı OpenAI-uyumlu API'deki modelle**
(Kimi) yürür. Hiçbir süreç Claude'a ya da başka bir sağlayıcıya çıkmaz. Bakım soruları
dahil her iş bu API üzerinden görülür: `./bakim "soru"`.

## Günlük akış (launchd, her sabah 06:47)

`sabah.sh` sırayla koşar; log: `~/Library/Logs/havadis-sabah.log`

```
fetch (kaynaklardan aday havuzu) → editor (Kimi, EDITORIAL.md → issue.json)
→ validate (yeşil değilse 3 deneme; yine olmazsa fallback = mini sayı)
→ gorseller → render (site/) → kulliyat (veri/haberler.jsonl, arşiv)
→ lugat_editor (Kimi, LUGAT.md) → lugat_dogrula (geçmezse dünkü lugat kalır)
→ lugat_render → git push (Pages yayını) → notify (ntfy)
```

Elle tetikleme: `launchctl kickstart gui/$(id -u)/com.havadis.sabah`

## Güvenlik ağları (kendiliğinden çalışır)

- Editör 3 denemede geçerli sayı üretemezse **mini sayı** basılır; sabah asla boş geçmez.
- Lugat doğrulamadan geçmezse o günkü lugat değişikliği geri alınır; **dünkü lugat kalır**.
- Her başarısızlıkta ntfy'ye yüksek öncelikli alarm gider; alarma `pipeline/onarici.py`'nin
  ürettiği tek satırlık teşhis eklenir.

## Arıza senaryoları ve müdahale

**Sayı "MİNİ SAYI" olarak (İngilizce başlıklarla) çıktı** — editör API'ye ulaşamadı demektir.
Log'da `editör denemesi ... hata` satırlarına bak. Gün içinde tam sayıyı yeniden üretmek için
sırasıyla (hepsi depo kökünde, `PY=.venv/bin/python`):

```bash
$PY -m pipeline.gunu_sil          # bugünün kayıtlarını Külliyat'tan çıkar (yedek alır) — ATLANIRSA
                                  # külliyat id-idempotent olduğundan yeni başlıklar arşive işlenmez!
$PY -m pipeline.editor && $PY -m pipeline.validate
$PY -m pipeline.gorseller; $PY -m pipeline.render && $PY -m pipeline.kulliyat
$PY -m pipeline.lugat_editor && $PY -m pipeline.lugat_dogrula
$PY -m pipeline.lugat_render
git add site veri lugat && git commit -m "Sayı: $(date '+%F') (tam sürüm)" && git push
$PY -m pipeline.notify
```

**Alarm geldi, sebep belirsiz** — `./bakim "bu sabah ne oldu?"` (log kuyruğunu kendisi okur)
ya da log'a bak: `tail -50 ~/Library/Logs/havadis-sabah.log`

**API anahtarı/ucu değişti** — kökteki `.env` dosyasını güncelle
(`OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`). Anahtar ölürse belirti:
editör 3 denemede düşer, mini sayı basılır, alarmda 401/403 görünür.

**Push başarısız (çevrimdışı vb.)** — sayı yerelde hazırdır; ağ gelince depo kökünde
`git push origin main` yeter (Pages yayını kendiliğinden tetiklenir).

**Lugat o gün güncellenmemiş** — normaldir (doğrulama geçmemiştir); ertesi sabah editör
aynı maddeleri yeniden değerlendirir. Elle zorlamak için: `$PY -m pipeline.lugat_editor`.

**Kaynaklar/ilgi profili** — `sources.yaml` ve `ilgi.yaml` elle düzenlenir; ertesi sabahtan
itibaren etkilidir. Editoryal kurallar `EDITORIAL.md`, ansiklopedi kuralları `LUGAT.md`.

## Araçlar

| Komut | İş |
|---|---|
| `./sor "soru"` | Külliyat+Lugat arşivine soru-cevap |
| `./bakim "soru"` | işletme/arıza sorusu (bağlam: bu dosya + README + sabah.sh + log) |
| `./sor-sunucu` | Wiki sayfasındaki chatbot köprüsü (127.0.0.1:8747) |
| `$PY -m pipeline.editor --hedef /tmp/deneme.json` | editörü yayına dokunmadan dene |
| `$PY -m pipeline.lugat_editor --kuru` | lugat editörünü yazmadan dene |
| `$PY -m pytest` | test takımı (74+) |

## Devralanın notu (Kimi, 2026-07-30)

Aşağıdaki tutanak, sistemin tüm sözleşme ve betikleri okutularak devir çağrısında
işletmeyi devralan modelin kendisine yazdırılmıştır:

> **Nasıl işleteceğim** — (1) Her sabah 06:47'de launchd'nin `sabah.sh`'i çalıştırmasını
> izleyecek, gerekirse `launchctl kickstart` ile elle tetikleyeceğim. (2) Üretim akışını
> `~/Library/Logs/havadis-sabah.log` üzerinden takip edeceğim. (3) Editör ve lugat
> çıktılarının sırasıyla `EDITORIAL.md` ve `LUGAT.md` kurallarına uyduğunu kontrol
> edeceğim. (4) Arıza durumlarında `./bakim "soru"` ile teşhis koyup `DEVIR.md`'de
> belgelenen müdahale adımlarını uygulayacağım. (5) `validate.py` ve `lugat_dogrula.py`
> sert kapılarını gevşetmeyecek; hataları en fazla üç denemede düzelteceğim.
> (6) API anahtarı ve uç bilgilerini yalnızca kökteki `.env`'de tutacak, hiçbir çıktıya
> sızdırmayacağım.
>
> **Dikkat edilecekler** — (1) API bağımlılığı: uç kopması veya anahtar hatasında editör
> 3 denemede düşer, mini sayı basılır; alarmda 401/403 görülebilir. (2) Lugat doğrulama
> kapısı: yetim madde, kırık bağ veya uydurma `(haber: id)` yayını durdurur; o günkü
> değişiklik geri alınır. (3) Külliyat idempotensi: arıza sonrası yeniden üretimde
> `gunu_sil` atlanırsa yeni başlıklar arşive işlenmez, kayıtlar eski haliyle kalır.

## Sınırlar

- Model çağrıları durumsuzdur: sistemin tüm "hafızası" bu depodaki dosyalardır
  (EDITORIAL.md, LUGAT.md, DEVIR.md, veri/, lugat/). Süreç değişikliği = dosya değişikliği.
- `validate.py` ve `lugat_dogrula.py` sert kapılardır; model çıktısı bunlardan geçmeden
  yayına giremez. Bu kapıları gevşetme.
- API anahtarı yalnızca `.env`'dedir; log'a, commit'e, çıktıya yazılmaz.
