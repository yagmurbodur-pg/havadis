# Havadis — Bug Kaydı (QA taraması: 17 Temmuz 2026)

Tarama yöntemi: Playwright ile tüm sayfalar (dergi flip+akış, arşiv+örnek sayılar, Külliyat, Lugat+maddeler, Wiki), tüm iç linkler (HTTP durum denetimi), butonlar, boş/hata durumları, 360/768/1280 responsive taşma, tema kalıcılığı, metin seçimi, sayfa-içi içerik taşması, konsol/JS hataları.

---

## B1 — Sabah editörü tek API kopmasında mini sayıya düşüyor ✅ FIXLENDİ
- **Önem:** Kritik
- **Repro:** 17 Tem sabahı koşusu; `claude -p` "API Error: Connection closed mid-response" aldı (log satır 622-642).
- **Beklenen:** Geçici ağ hatasında yeniden deneyip tam editoryal sayı basması.
- **Gerçekleşen:** Tek deneme → anında fallback → "Mini sayı: editoryal üretim yapılamadı".
- **Kök neden:** `sabah.sh` editör çağrısı tek atımlıktı; başarı ölçütü yoktu.
- **Fix:** Editör 3, Lugat 2 denemeli döngüye alındı; başarı ölçütü `validate`/`lugat_dogrula`'nın yeşile dönmesi; denemeler arası 45/30 sn bekleme. (Doğrulama: bugünkü tam yeniden basım koşusunda.)

## B2 — Dergide metin seçilemiyor; sürükleme gri/yarım katlanmış sayfa bırakabiliyor ✅ FIXLENDİ
- **Önem:** Kritik
- **Repro:** Dergi modunda herhangi bir sayfadaki metnin üzerinde fareyle sürükleyerek seçim yapmaya çalış.
- **Beklenen:** Metin seçilir ve kopyalanabilir; sayfa düzeni bozulmaz.
- **Gerçekleşen:** Kütüphane sürüklemeyi sayfa katlama olarak yorumluyordu → seçim boş kalıyor (`getSelection()==""` doğrulandı), yarım katlanma sayfanın gri sırtını gösterip takılı kalabiliyordu.
- **Fix:** `useMouseEvents:false` — kütüphane fare/dokunuş kontrolünden tamamen çıkarıldı; çevirme bilinçli yollara taşındı: kenar ‹ › düğmeleri, ←/→/Space, dokunmatikte yatay kaydırma. `user-select: text` garanti altına alındı. (Doğrulama: seçim artık gerçek metin döndürüyor, kitap durumu sağlam.)

## B3 — Wiki her açılışta konsola ERR_CONNECTION_REFUSED yazıyor ✅ FIXLENDİ
- **Önem:** Orta
- **Repro:** `sor-sunucu` kapalıyken /wiki/ aç, konsola bak.
- **Beklenen:** Köprü yokken sessiz kalması.
- **Gerçekleşen:** Sayfa yüklenirken yapılan ping, reddedilen bağlantı hatası düşürüyordu.
- **Fix:** Köprü ping'i sayfa açılışından alınıp "sohbet ilk açıldığında" anına taşındı.

## B4 — Bugünkü Sayı 9 yayında "mini" kaldı ✅ FIXLENDİ (yeniden basımla)
- **Önem:** Yüksek (içerik)
- **Repro:** 17 Tem sayısını aç; İngilizce başlıklar + "Editör bugün ulaşılamadı" notları.
- **Beklenen:** Tam editoryal Türkçe sayı.
- **Gerçekleşen:** B1'in sonucu olarak mini sayı yayınlandı.
- **Fix:** B1 çözümü + bugünün sayısı zengin formatla (A4) uçtan uca yeniden basıldı.

## B5 — Dergi sayfaları boş/yavan görünüyor (görselsiz, tek satırlık mini özetler) ✅ FIXLENDİ
- **Önem:** Yüksek (tasarım isteri)
- **Beklenen:** Gerçek dergi mizanpajı: küpür kartları, görseller, 2-4 cümlelik hap bilgi.
- **Fix:** A4.7-8 kapsamında: EDITORIAL hap-bilgi formatına geçirildi, haber görselleri (og:image) pipeline'a eklendi, küpür tasarımı uygulandı, sayfa-içi taşma denetleyicisi QA'ya eklendi.

## B6 — Arşivdeki 11-14 Temmuz sayıları "mini" ⏸ ERTELENDİ
- **Önem:** Düşük (tarihsel)
- **Gerekçe:** O günlerin aday havuzları (candidates.json) günlük olarak üzerine yazıldığı için retro-editoryal üretim yapılamaz; kayıtlar Külliyat'ta ham haliyle duruyor. Arşiv sayfaları dönemin dürüst izi olarak bırakıldı (mini uyarı kutusuyla).

## B7 — ntfy e-posta kopyası gitmiyor (yalnız push) ⏸ ERTELENDİ
- **Önem:** Düşük
- **Gerekçe:** ntfy.sh anonim e-posta iletimini kaldırdı; ücretsiz ntfy hesabı + `NTFY_TOKEN` gerektiriyor (kod hazır). Kullanıcı kararı bekliyor; push bildirimleri sorunsuz.

---

**Özet:** 7 kayıt · 5 fixlendi ve doğrulandı · 2 gerekçeli ertelendi.
