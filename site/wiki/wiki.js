/* Havadis Wiki — bağ haritası + kronolojik akış + arşive bağlı soru-cevap.
   Tamamen istemci tarafında; Mac'te sor-sunucu açıksa yanıtlar yerel Claude'dan gelir. */
(function () {
  "use strict";

  var TR = { "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u" };
  function katla(s) {
    return (s || "").toLocaleLowerCase("tr").replace(/[çğıöşüâîû]/g, function (k) { return TR[k] || k; });
  }
  var AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
               "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  function trTarih(iso) {
    if (!iso) return "";
    var p = iso.split("-");
    return parseInt(p[2], 10) + " " + AYLAR[parseInt(p[1], 10) - 1] + " " + p[0];
  }
  var DOLGU = ["neler", "nedir", "nasil", "oldu", "olan", "icin", "ile", "hakkinda",
               "son", "sonra", "var", "daha", "cok", "gibi", "kadar", "seyler", "durum"];
  function kelimelereAyir(soru) {
    return katla(soru).split(/[^a-z0-9]+/).filter(function (k) {
      return k.length > 2 && DOLGU.indexOf(k) < 0;
    });
  }

  function el(etiket, sinif, metin) {
    var e = document.createElement(etiket);
    if (sinif) e.className = sinif;
    if (metin != null) e.textContent = metin;
    return e;
  }
  var $ = function (id) { return document.getElementById(id); };

  var TUR_ADI = { kurum: "Kurum", model: "Model", urun: "Ürün", kisi: "Kişi", kavram: "Kavram", olay: "Olay" };
  var TUR_RENK = {
    acik: { kurum: "#A83226", model: "#3D6B54", urun: "#8C6A2F", kisi: "#5B5E8C", kavram: "#6D6353", olay: "#31708C" },
    koyu: { kurum: "#DB6E55", model: "#7FAE95", urun: "#C9A25E", kisi: "#9FA3D6", kavram: "#A2957D", olay: "#7FB2D0" }
  };
  function temaKoyu() {
    return document.documentElement.dataset.tema === "koyu" ||
      (!document.documentElement.dataset.tema && matchMedia("(prefers-color-scheme: dark)").matches);
  }

  var dugumler = [], baglar = [], haberler = [], komsular = {}, secili = null;

  /* ————— veri ————— */
  Promise.all([
    fetch("../lugat/ag.json").then(function (r) { return r.ok ? r.json() : { dugumler: [], baglar: [] }; }),
    fetch("../kulliyat/dizin.json").then(function (r) { return r.ok ? r.json() : { haberler: [] }; })
  ]).then(function (sonuc) {
    haberler = sonuc[1].haberler || [];
    baglar = sonuc[0].baglar || [];
    dugumler = (sonuc[0].dugumler || []).map(function (d) {
      d.haberler = eslesenHaberler(d);
      return d;
    });
    baglar.forEach(function (b) {
      komsular[b.k] = komsular[b.k] || [];
      komsular[b.h] = komsular[b.h] || [];
      if (komsular[b.k].indexOf(b.h) < 0) komsular[b.k].push(b.h);
      if (komsular[b.h].indexOf(b.k) < 0) komsular[b.h].push(b.k);
    });
    $("wiki-ozet").textContent = dugumler.length + " varlık · " + baglar.length + " ilişki · " +
      haberler.length + " haber — her sabah kendiliğinden büyür";
    seciciKur();
    grafikBaslat();
    hashOku();
  });

  function eslesenHaberler(dugum) {
    var adK = katla(dugum.ad);
    var etiketlerK = (dugum.etiketler || []).map(katla);
    var liste = haberler.filter(function (h) {
      var konularK = (h.konular || []).map(katla);
      var metinK = katla((h.baslik || "") + " " + (h.ozet || ""));
      var etiketTutar = etiketlerK.some(function (e) { return konularK.indexOf(e) >= 0; });
      var metinTutar = adK.length >= 3 && metinK.indexOf(adK) >= 0;
      return etiketTutar || metinTutar;
    });
    liste.sort(function (a, b) { return (a.tarih || "").localeCompare(b.tarih || ""); }); // kronolojik: eskiden bugüne
    return liste;
  }

  /* ————— seçici + panel ————— */
  function seciciKur() {
    var s = $("dugum-secici");
    dugumler.slice().sort(function (a, b) { return a.ad.localeCompare(b.ad, "tr"); })
      .forEach(function (d) {
        var o = document.createElement("option");
        o.value = d.ad;
        o.textContent = d.ad + " (" + d.haberler.length + " haber)";
        s.appendChild(o);
      });
    s.addEventListener("change", function () { sec(s.value || null); });
  }

  function sec(ad) {
    secili = dugumler.filter(function (d) { return d.ad === ad; })[0] || null;
    $("dugum-secici").value = secili ? secili.ad : "";
    var panel = $("dugum-paneli");
    if (!secili) { panel.hidden = true; return; }
    if (location.hash !== "#d/" + encodeURIComponent(secili.slug))
      history.replaceState(null, "", "#d/" + encodeURIComponent(secili.slug));

    panel.hidden = false;
    $("panel-tur").textContent = (TUR_ADI[secili.tur] || "") + " · " + secili.haberler.length + " haber";
    $("panel-ad").textContent = secili.ad;
    $("panel-tanim").textContent = secili.tanim || "";

    var kutu = $("panel-baglar");
    kutu.textContent = "";
    var madde = el("a", "kaynak-link", "Lugat maddesi ↗");
    madde.href = "../lugat/" + secili.slug + ".html";
    kutu.appendChild(madde);
    (komsular[secili.ad] || []).forEach(function (komsu) {
      var c = el("button", "cip", komsu);
      c.type = "button";
      c.addEventListener("click", function () { sec(komsu); });
      kutu.appendChild(c);
    });

    var zaman = $("zaman-cizgisi");
    zaman.textContent = "";
    if (!secili.haberler.length) {
      zaman.appendChild(el("li", "bos-durum", "Bu varlık için Külliyat'ta henüz haber yok."));
    }
    secili.haberler.forEach(function (h) {
      var li = el("li", "zaman-ogesi");
      li.appendChild(el("p", "ust-not", trTarih(h.tarih) + " · " + (h.kaynak || "") + " · Sayı " + h.sayi_no));
      var b = el("h5");
      var a = el("a", null, h.baslik || "(başlıksız)");
      a.href = h.url || "#"; a.rel = "noopener";
      b.appendChild(a);
      li.appendChild(b);
      if (h.ozet) li.appendChild(el("p", "zaman-ozet", h.ozet));
      zaman.appendChild(li);
    });
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
    ciz();
  }

  function hashOku() {
    var m = location.hash.match(/^#d\/(.+)$/);
    if (!m) return;
    var slug = decodeURIComponent(m[1]);
    var d = dugumler.filter(function (x) { return x.slug === slug; })[0];
    if (d) sec(d.ad);
  }

  /* ————— kuvvet grafiği (elle yazılmış; kütüphane yok) ————— */
  var tuval, cizici, GEN, YUK, opr = window.devicePixelRatio || 1;
  var suruklenen = null, oynadi = false, sicaklik = 1;

  function grafikBaslat() {
    tuval = $("ag");
    cizici = tuval.getContext("2d");
    boyutla();
    window.addEventListener("resize", function () { boyutla(); sicaklik = 0.6; });
    dugumler.forEach(function (d, i) {
      var aci = (i / Math.max(1, dugumler.length)) * Math.PI * 2;
      d.x = GEN / 2 + Math.cos(aci) * GEN / 4;
      d.y = YUK / 2 + Math.sin(aci) * YUK / 4;
      d.vx = 0; d.vy = 0;
      d.r = 6 + 3 * Math.sqrt(d.haberler.length);
    });
    tuval.addEventListener("pointerdown", basla);
    tuval.addEventListener("pointermove", oyna);
    tuval.addEventListener("pointerup", birak);
    tuval.addEventListener("pointercancel", birak);
    dongu();
  }

  function boyutla() {
    GEN = tuval.clientWidth; YUK = tuval.clientHeight;
    tuval.width = GEN * opr; tuval.height = YUK * opr;
    cizici.setTransform(opr, 0, 0, opr, 0, 0);
  }

  function konum(olay) {
    var kutu = tuval.getBoundingClientRect();
    return { x: olay.clientX - kutu.left, y: olay.clientY - kutu.top };
  }
  function bul(p) {
    for (var i = dugumler.length - 1; i >= 0; i--) {
      var d = dugumler[i];
      var dx = p.x - d.x, dy = p.y - d.y;
      if (dx * dx + dy * dy <= (d.r + 8) * (d.r + 8)) return d;
    }
    return null;
  }
  function basla(olay) {
    var d = bul(konum(olay));
    if (d) { suruklenen = d; oynadi = false; tuval.setPointerCapture(olay.pointerId); }
  }
  function oyna(olay) {
    var p = konum(olay);
    tuval.style.cursor = bul(p) ? "pointer" : "default";
    if (suruklenen) {
      suruklenen.x = p.x; suruklenen.y = p.y;
      suruklenen.vx = 0; suruklenen.vy = 0;
      oynadi = true; sicaklik = Math.max(sicaklik, 0.4);
    }
  }
  function birak() {
    if (suruklenen && !oynadi) sec(suruklenen.ad);
    suruklenen = null;
  }

  function adim() {
    var i, j, d, e;
    for (i = 0; i < dugumler.length; i++) {
      d = dugumler[i];
      for (j = i + 1; j < dugumler.length; j++) {
        e = dugumler[j];
        var dx = d.x - e.x, dy = d.y - e.y;
        var kare = dx * dx + dy * dy + 0.01;
        var guc = 1400 / kare;
        var uz = Math.sqrt(kare);
        dx /= uz; dy /= uz;
        d.vx += dx * guc; d.vy += dy * guc;
        e.vx -= dx * guc; e.vy -= dy * guc;
      }
    }
    baglar.forEach(function (b) {
      var k = dugumler.filter(function (x) { return x.ad === b.k; })[0];
      var h = dugumler.filter(function (x) { return x.ad === b.h; })[0];
      if (!k || !h) return;
      var dx = h.x - k.x, dy = h.y - k.y;
      var uz = Math.sqrt(dx * dx + dy * dy) || 1;
      var cek = (uz - 95) * 0.012;
      dx /= uz; dy /= uz;
      k.vx += dx * cek * uz * 0.05; k.vy += dy * cek * uz * 0.05;
      h.vx -= dx * cek * uz * 0.05; h.vy -= dy * cek * uz * 0.05;
    });
    dugumler.forEach(function (d) {
      d.vx += (GEN / 2 - d.x) * 0.0035;
      d.vy += (YUK / 2 - d.y) * 0.0035;
      if (d === suruklenen) return;
      d.vx *= 0.85; d.vy *= 0.85;
      d.x += d.vx * sicaklik; d.y += d.vy * sicaklik;
      d.x = Math.max(d.r + 2, Math.min(GEN - d.r - 2, d.x));
      d.y = Math.max(d.r + 2, Math.min(YUK - d.r - 2, d.y));
    });
    if (sicaklik > 0.02 && !suruklenen) sicaklik *= 0.996;
  }

  function ciz() {
    if (!cizici) return;
    var stil = getComputedStyle(document.documentElement);
    var cizgi = stil.getPropertyValue("--cizgi").trim() || "#D9CDB2";
    var murekkep = stil.getPropertyValue("--murekkep").trim() || "#221B12";
    var renkler = TUR_RENK[temaKoyu() ? "koyu" : "acik"];
    cizici.clearRect(0, 0, GEN, YUK);

    cizici.strokeStyle = cizgi;
    cizici.lineWidth = 1;
    baglar.forEach(function (b) {
      var k = dugumler.filter(function (x) { return x.ad === b.k; })[0];
      var h = dugumler.filter(function (x) { return x.ad === b.h; })[0];
      if (!k || !h) return;
      cizici.beginPath(); cizici.moveTo(k.x, k.y); cizici.lineTo(h.x, h.y); cizici.stroke();
    });

    dugumler.forEach(function (d) {
      cizici.beginPath();
      cizici.arc(d.x, d.y, d.r, 0, Math.PI * 2);
      cizici.fillStyle = renkler[d.tur] || murekkep;
      cizici.globalAlpha = secili && secili !== d &&
        (komsular[secili.ad] || []).indexOf(d.ad) < 0 ? 0.35 : 1;
      cizici.fill();
      if (secili === d) {
        cizici.lineWidth = 2.5;
        cizici.strokeStyle = murekkep;
        cizici.stroke();
      }
      cizici.globalAlpha = 1;
      cizici.fillStyle = murekkep;
      cizici.font = "600 10px system-ui, sans-serif";
      cizici.textAlign = "center";
      cizici.fillText(d.ad, d.x, d.y + d.r + 12);
    });
  }

  function dongu() { adim(); ciz(); requestAnimationFrame(dongu); }

  /* ————— chatbot ————— */
  var KOPRU = "http://127.0.0.1:8747";
  var koprulu = false;
  fetch(KOPRU + "/ping").then(function (r) {
    if (r.ok) { koprulu = true; $("kopru-durum").textContent = "🟢 Yerel zekâ bağlı — yanıtlar Mac'teki Claude'dan gelecek."; }
  }).catch(function () {});

  $("sor-dugme").addEventListener("click", sor);
  $("soru").addEventListener("keydown", function (e) { if (e.key === "Enter") sor(); });

  function sor() {
    var soru = $("soru").value.trim();
    if (!soru) return;
    var kutu = $("cevap");
    kutu.textContent = "";
    kutu.appendChild(el("p", "kucuk", "☕ Külliyat taranıyor…"));
    if (koprulu) {
      fetch(KOPRU + "/sor", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ soru: soru })
      }).then(function (r) { return r.json(); })
        .then(function (v) {
          kutu.textContent = "";
          var c = el("div", "cevap-kutu");
          c.appendChild(el("p", "ust-not", "Yerel Claude yanıtı"));
          (v.cevap || "Yanıt boş döndü.").split(/\n{2,}/).forEach(function (par) {
            c.appendChild(el("p", null, par));
          });
          kutu.appendChild(c);
        })
        .catch(function () { koprulu = false; sentezle(soru); });
    } else {
      sentezle(soru);
    }
  }

  function puan(kelimeler, metin) {
    var m = katla(metin);
    var p = 0;
    kelimeler.forEach(function (k) { p += m.split(k).length - 1; });
    return p;
  }

  function sentezle(soru) {
    var kutu = $("cevap");
    kutu.textContent = "";
    var kelimeler = kelimelereAyir(soru);

    var dEs = dugumler.map(function (d) {
      return { d: d, p: puan(kelimeler, d.ad + " " + d.tanim + " " + (d.etiketler || []).join(" ")) };
    }).filter(function (x) { return x.p > 0; }).sort(function (a, b) { return b.p - a.p; }).slice(0, 3);

    var hEs = haberler.map(function (h) {
      return { h: h, p: puan(kelimeler, (h.baslik || "") + " " + (h.ozet || "") + " " + (h.konular || []).join(" ")) };
    }).filter(function (x) { return x.p > 0; }).sort(function (a, b) { return b.p - a.p; }).slice(0, 12);

    if (!dEs.length && !hEs.length) {
      kutu.appendChild(el("p", "bos-durum", "Külliyat'ta bu kelimelerle kayıt yok. Farklı kelimelerle dene."));
      return;
    }
    var c = el("div", "cevap-kutu");

    if (dEs.length) {
      c.appendChild(el("h4", "cevap-baslik", "Ne biliyoruz"));
      dEs.forEach(function (x) {
        var p = el("p");
        p.appendChild(el("strong", null, x.d.ad));
        p.appendChild(document.createTextNode(" (" + (TUR_ADI[x.d.tur] || "") + ") — " + (x.d.tanim || "")));
        c.appendChild(p);
        var iliskiler = komsular[x.d.ad] || [];
        if (iliskiler.length) {
          var satir = el("div", "kunye");
          satir.appendChild(el("span", "ust-not", "İlişkili:"));
          iliskiler.forEach(function (komsu) {
            var cips = el("button", "cip", komsu);
            cips.type = "button";
            cips.addEventListener("click", function () { sec(komsu); });
            satir.appendChild(cips);
          });
          c.appendChild(satir);
        }
      });
    }

    var zincir = [], zincirdeki = {};
    function zincireEkle(h) {
      if (!zincirdeki[h.id]) { zincirdeki[h.id] = true; zincir.push(h); }
    }
    dEs.forEach(function (x) { x.d.haberler.forEach(zincireEkle); });
    hEs.forEach(function (x) { zincireEkle(x.h); });
    zincir.sort(function (a, b) { return (a.tarih || "").localeCompare(b.tarih || ""); });
    zincir = zincir.slice(-10);

    if (zincir.length) {
      c.appendChild(el("h4", "cevap-baslik", "Gelişim zinciri"));
      var ol = el("ol", "zaman-cizgisi kucuk-zaman");
      zincir.forEach(function (h) {
        var li = el("li", "zaman-ogesi");
        li.appendChild(el("p", "ust-not", trTarih(h.tarih)));
        var a = el("a", null, h.baslik || "");
        a.href = h.url || "#"; a.rel = "noopener";
        var b = el("h5"); b.appendChild(a); li.appendChild(b);
        ol.appendChild(li);
      });
      c.appendChild(ol);
    }

    c.appendChild(el("h4", "cevap-baslik", "Kaynaklar"));
    var kaynakList = el("ul", "kaynak-listesi");
    hEs.slice(0, 6).forEach(function (x, i) {
      var li = el("li");
      var a = el("a", null, "[" + (i + 1) + "] " + (x.h.baslik || "") + " — " + (x.h.kaynak || ""));
      a.href = x.h.url || "#"; a.rel = "noopener";
      li.appendChild(a);
      kaynakList.appendChild(li);
    });
    c.appendChild(kaynakList);
    c.appendChild(el("p", "kucuk", "Bu hızlı sentezdi. Akıcı, yorumlu yanıt için Mac'te ~/havadis/sor-sunucu çalıştırıp sayfayı yenile."));
    kutu.appendChild(c);
  }

  /* ————— tema düğmesi ————— */
  var temaD = document.querySelector(".tema-dugme");
  function simge() { temaD.textContent = temaKoyu() ? "☀" : "☾"; }
  temaD.addEventListener("click", function () {
    var yeni = temaKoyu() ? "acik" : "koyu";
    document.documentElement.dataset.tema = yeni;
    try { localStorage.setItem("havadis-tema", yeni); } catch (e) {}
    simge(); ciz();
  });
  simge();
  if ("serviceWorker" in navigator && location.protocol.indexOf("http") === 0) {
    navigator.serviceWorker.register("../sw.js");
  }
})();
