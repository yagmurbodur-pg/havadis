/* Havadis service worker
   HTML ve dizin: önce ağ (çevrimdışıysa son kopya).
   Varlıklar: önbellekten hızlı servis + arka planda tazeleme (stale-while-revalidate).
   SURUM her basımda damgalanır → yeni sürüm eski önbelleği tamamen süpürür. */
const SURUM = "havadis-202607211008";
const VARLIK = /(\/varliklar\/|minisearch|ikon|manifest|apple-touch|sayfa-sesi)/;

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (olay) => {
  olay.waitUntil(
    caches
      .keys()
      .then((adlar) =>
        Promise.all(adlar.filter((a) => a !== SURUM).map((a) => caches.delete(a)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (olay) => {
  const istek = olay.request;
  if (istek.method !== "GET") return;
  const url = new URL(istek.url);
  if (url.origin !== location.origin) return;

  // sayfa gezinmeleri + büyüyen arama dizini: önce ağ, çevrimdışıysa son kopya
  if (istek.mode === "navigate" || url.pathname.endsWith("dizin.json")) {
    olay.respondWith(
      fetch(istek)
        .then((yanit) => {
          const kopya = yanit.clone();
          caches.open(SURUM).then((c) => c.put(istek, kopya));
          return yanit;
        })
        .catch(() => caches.match(istek))
    );
    return;
  }

  // fontlar, stil, sesler, ikonlar: önbellekten an, arka planda tazele
  if (VARLIK.test(url.pathname)) {
    olay.respondWith(
      caches.match(istek).then((eski) => {
        const taze = fetch(istek)
          .then((yanit) => {
            const kopya = yanit.clone();
            caches.open(SURUM).then((c) => c.put(istek, kopya));
            return yanit;
          })
          .catch(() => eski);
        return eski || taze;
      })
    );
  }
});
