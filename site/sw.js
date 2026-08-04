/* Havadis service worker
   HTML ve dizin: önce ağ (çevrimdışıysa son kopya).
   Varlıklar: önbellekten hızlı servis + arka planda tazeleme (stale-while-revalidate).
   SURUM her basımda damgalanır → yeni sürüm eski önbelleği tamamen süpürür. */
const SURUM = "havadis-202608042034";
const VARLIK = /(\/varliklar\/|minisearch|ikon|manifest|apple-touch|sayfa-sesi)/;

/* respondWith(undefined) tarayıcıya "yanıt yok" der: Safari hata sayfası bile
   göstermeden BOMBOŞ bir sekme bırakır. Ağ da önbellek de yoksa dürüst bir
   çevrimdışı yanıt üretiriz — sayfa asla sessizce boş kalmasın. */
const CEVRIMDISI_HTML = `<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Havadis — çevrimdışı</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#F6F1E5;color:#231D16;
font:400 1rem/1.6 Georgia,serif;text-align:center;padding:2rem}
h1{font-size:1.4rem;margin:0 0 .6rem}p{margin:0 0 1.2rem;opacity:.75}
button{font:600 .8rem/1 system-ui,sans-serif;letter-spacing:.12em;text-transform:uppercase;
padding:.7rem 1.2rem;border:1px solid #231D16;border-radius:8px;background:transparent;cursor:pointer}</style>
</head><body><div><h1>Havadis'e şu an ulaşılamıyor</h1>
<p>Bu sayfanın önbellekte kopyası yok. Bağlantı gelince yeniden dene.</p>
<button onclick="location.reload()">Yeniden dene</button></div></body></html>`;

function cevrimdisiYanit(istek) {
  if (istek.mode === "navigate") {
    return new Response(CEVRIMDISI_HTML, {
      status: 503,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }
  if (istek.url.endsWith("dizin.json")) {
    return new Response('{"haberler":[]}', {
      status: 503,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  }
  return new Response("", { status: 503 });
}

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
        .catch(() =>
          caches.match(istek).then((eski) => eski || cevrimdisiYanit(istek))
        )
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
          .catch(() => eski || cevrimdisiYanit(istek));
        return eski || taze;
      })
    );
  }
});
