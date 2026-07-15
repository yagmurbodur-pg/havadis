---
baslik: Dependabot
tur: urun
tanim: "GitHub'ın, projelerdeki bağımlılıkları otomatik güncelleyen robotu."
esanlamlilar: []
etiketler: [araçlar, güvenlik]
olusturulma: 2026-07-15
son_guncelleme: 2026-07-15
---

Dependabot, GitHub'ın bağımlılık güncelleme robotudur: bir projenin kullandığı paketlerin (bağımlılıkların) yeni sürümlerini izler ve sürüm çıktığında projeye otomatik güncelleme önerisi açar. Temmuz 2026'da davranışı değişti: araç artık bir paketin yeni sürümü çıktıktan sonra üç gün bekliyor, güncelleme önerisini ondan sonra açıyor. Bu bekleme varsayılan hâle geldi ve hiçbir ayar gerektirmiyor. Amaç, sorunlu ya da zararlı paket sürümlerinin ekosistemde hemen yayılmasını önlemek: tedarik zinciri saldırılarında (yaygın bir pakete zararlı kod sokarak onu kullanan projelere bulaşma) zararlı sürümler çoğu zaman ilk günlerde tespit edilip geri çekiliyor; üç günlük tampon, bu sürümlerin otomatik güncellemelerle projelere girmesini büyük ölçüde engelliyor. Kullanıcı açısından sonuç, kendiliğinden azalmış bir güvenlik riski.

## Gelişmeler
- **2026-07-15** — Yeni paket sürümleri için varsayılan olarak üç günlük bekleme süresi getirdi. (haber: b8295173)
