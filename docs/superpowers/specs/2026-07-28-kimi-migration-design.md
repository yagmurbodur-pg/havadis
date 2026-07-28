# Havadis'in LLM katmanının Kimi'ye (OpenAI-uyumlu API) taşınması

**Tarih:** 2026-07-28 · **Durum:** Onaylandı (sohbette)

## Amaç ve kısıtlar

Havadis'in günlük üretim hattı bugün 4 noktada yerel `claude -p` (Claude Code aboneliği)
çağırıyor. Hedef: bu bağımlılığı tamamen kaldırmak; tüm model çağrıları kullanıcının
OpenAI-uyumlu API'sindeki modele (`OPENAI_MODEL`, arkada Kimi-K2.7-Code) gitmeli.
Claude token'ı hiçbir koşulda harcanmamalı. İlk sürüm yalnızca metin; vision sonraya.

Ayarlar kökteki `.env` dosyasında (git dışı): `OPENAI_BASE_URL`, `OPENAI_API_KEY`,
`OPENAI_MODEL`.

## Sahadan bulgular (tasarımı şekillendiren)

- Model reasoning üretiyor (`reasoning_content`); görünmeyen token harcıyor →
  `max_tokens` cömert tutulmalı.
- Proxy JSON modunda çıktının başına bozuk parça yapıştırabiliyor
  (`{"sehir{"sehir": …}` gözlendi) → körlemesine `json.loads` yok; dengeli-nesne
  ayıklayıcı + hata döngüsü şart.
- Uçta tool-calling desteği doğrulanmadı → ajan mimarisi yerine deterministik akış.

## Seçilen yaklaşım: deterministik düzenleyici döngüsü

Model "ajan" değil "yazar" olarak kullanılır. Her iş için Python tarafı: bağlamı tek
prompt'ta ver → JSON iste → ayıkla → mevcut doğrulayıcıyı süreç içinde koş → hataları
modele geri gönder → en çok 3 tur. Reddedilen alternatifler: tool-calling mini-ajan
(uç desteği belirsiz, kırılgan), hazır ajan çerçevesi (gereksiz bağımlılık).

## Bileşenler

- **`pipeline/llm.py` (yeni):** tek istemci. `.env`'i ortama yükler (ortam öncelikli),
  `httpx` ile `/chat/completions` (yeni bağımlılık yok), ağ hatasında artan bekleme ile
  3 deneme, `json_ayikla()` metindeki en uzun dengeli JSON nesnesini seçer (markdown
  çiti, açıklama cümlesi ve proxy önek pürüzüne dayanıklı).
- **`pipeline/editor.py` (yeni):** sabah editörü. Sistem prompt'u = sarmalayıcı talimat
  ("dosya yazamazsın, yalnız JSON üret") + EDITORIAL.md aynen. Kullanıcı mesajı =
  candidates.json + ilgi.yaml + konular_ozet.json. Dönen sayı `validate.dogrula()`
  ile denetlenir; hatalar modele geri verilir. 3 turda yeşillenmezse sıfır-dışı çıkış →
  `sabah.sh` bugünkü gibi mini sayıya düşer.
- **`pipeline/lugat_editor.py` (yeni):** lugat editörü. Girdi: LUGAT.md + bugun.json +
  lugat/'ın tamamı. Çıktı sözleşmesi: `{"dosyalar": {"<Madde>.md": "<tam içerik>"}}`
  (değişiklik yoksa boş nesne). Yama önce geçici kopyaya uygulanır, `lugat_dogrula`
  geçerse gerçek `lugat/`'a yazılır; dosya adı guard'ları (yalnız `.md`, yol ayracı yok).
  `--kuru` bayrağı gerçek dizine yazmadan uçtan uca test sağlar. Başarısızlıkta mevcut
  güvenlik ağı korunur (`git checkout -- lugat/`, dünkü lugat kalır).
- **`pipeline/sor.py` + `pipeline/sor_sunucu.py`:** `subprocess claude` çağrısı
  `llm.sohbet()` ile değişir; prompt aynı.
- **`sabah.sh`:** iki `claude -p` bloğu `$PY -m pipeline.editor` / `$PY -m
  pipeline.lugat_editor` olur; deneme döngüleri ve ntfy alarmı aynen kalır; bekçi
  süreçleri kalkar (zaman aşımı artık httpx'te). Keychain/abonelik gereksinimi biter.
- **README.md:** mimari ve kurulum metni güncellenir.

## Hata yönetimi

Her katmanda geri çekilme: ağ hatası → llm 3 deneme · geçersiz JSON/şema → tur döngüsü ·
editör 3 turda başaramazsa → mini sayı · lugat başaramazsa → dünkü lugat. ntfy alarmları
değişmez. API anahtarı hiçbir log/çıktıya yazılmaz.

## Test

- Birim: `tests/test_llm.py` — `json_ayikla` (temiz, çitli, proxy önekli, düzyazı içinde,
  en-uzun-kazanır, bulunamadı).
- Mevcut takım (`pytest`) yeşil kalmalı.
- Gerçek API doğrulaması: editör kuru koşusu (`--hedef` scratchpad), lugat `--kuru`,
  `sor` ile uçtan uca bir soru.

## Kapsam dışı

Vision (küpür eleme vb.), launchd/Terminal düzeninin sadeleştirilmesi, fetch/render
tarafında değişiklik.
