/* Külliyat arama & gezinme — tamamen istemci tarafında.
   Türkçe katlama: "acik kaynak" araması "açık kaynak"ı bulur. */
(function () {
  "use strict";

  var TR = { "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u" };
  function katla(s) {
    return (s || "").toLocaleLowerCase("tr").replace(/[çğıöşüâîû]/g, function (k) { return TR[k] || k; });
  }
  function slugla(s) {
    return katla(s).replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  }
  var AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
               "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  function trTarih(iso) {
    if (!iso) return "";
    var p = iso.split("-");
    return parseInt(p[2], 10) + " " + AYLAR[parseInt(p[1], 10) - 1] + " " + p[0];
  }

  var durum = { q: "", konu: null };
  var haberler = [], harita = {}, mini = null;

  var $ = function (id) { return document.getElementById(id); };

  function el(etiket, sinif, metin) {
    var e = document.createElement(etiket);
    if (sinif) e.className = sinif;
    if (metin != null) e.textContent = metin;
    return e;
  }

  function baslat(veri) {
    haberler = (veri && veri.haberler) || [];
    haberler.forEach(function (h) { harita[h.id] = h; });

    if (haberler.length) {
      mini = new MiniSearch({
        fields: ["baslik", "ozet", "neden_onemli", "konular", "kaynak"],
        storeFields: ["id"],
        processTerm: function (t) { var k = katla(t); return k.length > 1 ? k : null; },
        extractField: function (doc, alan) {
          var v = doc[alan];
          return Array.isArray(v) ? v.join(" ") : v;
        }
      });
      mini.addAll(haberler);
    }

    var konuSay = {};
    haberler.forEach(function (h) {
      (h.konular || []).forEach(function (k) { konuSay[k] = (konuSay[k] || 0) + 1; });
    });
    $("istatistik").textContent = haberler.length
      ? haberler.length + " haber · " + Object.keys(konuSay).length + " konu dosyası — arayın ya da bir dosyayı açın"
      : "";

    var kutu = $("konular");
    Object.keys(konuSay)
      .sort(function (a, b) { return konuSay[b] - konuSay[a]; })
      .slice(0, 24)
      .forEach(function (ad) {
        var b = el("button", "cip", ad + " · " + konuSay[ad]);
        b.type = "button";
        b.dataset.ad = ad;
        b.setAttribute("aria-pressed", "false");
        b.addEventListener("click", function () { secKonu(durum.konu === ad ? null : ad); });
        kutu.appendChild(b);
      });

    hashOku();
    ciz();
  }

  function secKonu(ad) {
    durum.konu = ad;
    if (ad) location.hash = "konu/" + slugla(ad);
    else if (location.hash) history.replaceState(null, "", location.pathname);
    ciz();
  }

  function hashOku() {
    var m = location.hash.match(/^#konu\/(.+)$/);
    if (!m) { durum.konu = null; return; }
    var slug = decodeURIComponent(m[1]);
    var bulunan = null;
    haberler.forEach(function (h) {
      (h.konular || []).forEach(function (k) { if (slugla(k) === slug) bulunan = k; });
    });
    durum.konu = bulunan;
  }
  window.addEventListener("hashchange", function () { hashOku(); ciz(); });

  function esle() {
    var liste;
    if (mini && durum.q.trim().length > 1) {
      liste = mini.search(durum.q, { prefix: true, fuzzy: 0.15, boost: { baslik: 3, konular: 2.5 } })
        .map(function (r) { return harita[r.id]; })
        .filter(Boolean);
    } else {
      liste = haberler.slice().sort(function (a, b) {
        return (b.tarih || "").localeCompare(a.tarih || "");
      });
    }
    if (durum.konu) {
      liste = liste.filter(function (h) { return (h.konular || []).indexOf(durum.konu) >= 0; });
    }
    return liste.slice(0, 80);
  }

  function kart(h) {
    var s = el("article", "sonuc");
    s.appendChild(el("p", "ust-not", trTarih(h.tarih) + " · Sayı " + h.sayi_no + " · " + h.bolum));

    var baslik = el("h4");
    var bag = el("a", null, h.baslik || "(başlıksız)");
    bag.href = h.url || "#";
    bag.rel = "noopener";
    baslik.appendChild(bag);
    s.appendChild(baslik);

    if (h.ozet) s.appendChild(el("p", null, h.ozet));
    if (h.neden_onemli) s.appendChild(el("p", "neden", "Neden önemli? " + h.neden_onemli));

    var kunye = el("div", "kunye");
    if (h.url) {
      var kaynak = el("a", "kaynak-link", (h.kaynak || "Kaynak") + " ↗");
      kaynak.href = h.url; kaynak.rel = "noopener";
      kunye.appendChild(kaynak);
    }
    var sayiBag = el("a", null, "Sayı " + h.sayi_no);
    sayiBag.href = "../arsiv/" + h.tarih + ".html";
    kunye.appendChild(sayiBag);
    (h.konular || []).forEach(function (ad) {
      var c = el("a", "cip", ad);
      c.href = "#konu/" + slugla(ad);
      kunye.appendChild(c);
    });
    s.appendChild(kunye);

    var bagli = (h.iliskili || []).map(function (id) { return harita[id]; }).filter(Boolean);
    if (bagli.length) {
      var kutu = el("div", "iliskili-kutu", "Hikâyenin geçmişi: ");
      bagli.forEach(function (eski, i) {
        if (i) kutu.appendChild(document.createTextNode(" · "));
        var b = el("a", null, trTarih(eski.tarih) + " — " + eski.baslik);
        b.href = eski.url || ("../arsiv/" + eski.tarih + ".html");
        b.rel = "noopener";
        kutu.appendChild(b);
      });
      s.appendChild(kutu);
    }
    return s;
  }

  function ciz() {
    var kutu = $("sonuclar");
    kutu.textContent = "";
    document.querySelectorAll("#konular .cip").forEach(function (b) {
      b.setAttribute("aria-pressed", b.dataset.ad === durum.konu ? "true" : "false");
    });
    if (!haberler.length) {
      kutu.appendChild(el("p", "bos-durum", "Külliyat henüz boş — ilk sayıyla dolmaya başlar."));
      return;
    }
    var liste = esle();
    if (!liste.length) {
      kutu.appendChild(el("p", "bos-durum", "Bu aramada bir şey çıkmadı. Farklı bir kelime deneyin ya da konu filtresini kaldırın."));
      return;
    }
    liste.forEach(function (h) { kutu.appendChild(kart(h)); });
  }

  var arama = $("arama"), bekle = null;
  arama.addEventListener("input", function () {
    clearTimeout(bekle);
    bekle = setTimeout(function () { durum.q = arama.value; ciz(); }, 120);
  });

  fetch("dizin.json")
    .then(function (r) { return r.ok ? r.json() : { haberler: [] }; })
    .then(baslat)
    .catch(function () { baslat({ haberler: [] }); });

  // tema düğmesi
  var d = document.querySelector(".tema-dugme");
  function simge() {
    var koyu = document.documentElement.dataset.tema === "koyu" ||
      (!document.documentElement.dataset.tema && matchMedia("(prefers-color-scheme: dark)").matches);
    d.textContent = koyu ? "☀" : "☾";
  }
  d.addEventListener("click", function () {
    var koyu = document.documentElement.dataset.tema === "koyu" ||
      (!document.documentElement.dataset.tema && matchMedia("(prefers-color-scheme: dark)").matches);
    var yeni = koyu ? "acik" : "koyu";
    document.documentElement.dataset.tema = yeni;
    try { localStorage.setItem("havadis-tema", yeni); } catch (e) {}
    simge();
  });
  simge();
  if ("serviceWorker" in navigator && location.protocol.indexOf("http") === 0) {
    navigator.serviceWorker.register("../sw.js");
  }
})();
