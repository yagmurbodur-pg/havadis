/* Havadis Wiki — tam ekran, keşfedilebilir bilgi ağı.
   Elle yazılmış 3B kuvvet yerleşimi + sol üst arama + arayüz sesleri + arşive bağlı soru-cevap.
   Harici kütüphane yok; veriler wiki-veri.json (Lugat) + dizin.json (Külliyat). */
(function () {
  "use strict";

  /* ————— yardımcılar ————— */
  var TRH = { "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u" };
  function katla(s) {
    return (s || "").toLocaleLowerCase("tr").replace(/[çğıöşüâîû]/g, function (k) { return TRH[k] || k; });
  }
  var DOLGU = ["neler", "nedir", "nasil", "oldu", "olan", "icin", "ile", "hakkinda",
               "son", "sonra", "var", "daha", "cok", "gibi", "kadar", "seyler", "durum"];
  function kelimelereAyir(soru) {
    return katla(soru).split(/[^a-z0-9]+/).filter(function (k) {
      return k.length > 2 && DOLGU.indexOf(k) < 0;
    });
  }
  var AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
               "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  function trTarih(iso) {
    if (!iso) return "";
    var p = iso.split("-");
    return parseInt(p[2], 10) + " " + AYLAR[parseInt(p[1], 10) - 1] + " " + p[0];
  }
  function el(etiket, sinif, metin) {
    var e = document.createElement(etiket);
    if (sinif) e.className = sinif;
    if (metin != null) e.textContent = metin;
    return e;
  }
  var $ = function (id) { return document.getElementById(id); };
  var TUR_ADI = { kurum: "Kurum", model: "Model", urun: "Ürün", kisi: "Kişi", kavram: "Kavram", olay: "Olay" };
  var AZ_HAREKET = matchMedia("(prefers-reduced-motion: reduce)").matches;

  function temaKoyu() {
    return document.documentElement.dataset.tema === "koyu" ||
      (!document.documentElement.dataset.tema && matchMedia("(prefers-color-scheme: dark)").matches);
  }
  var paletCache = null;
  function palet() {
    if (paletCache) return paletCache;
    var s = getComputedStyle(document.documentElement);
    paletCache = {
      kagit: s.getPropertyValue("--kagit").trim(),
      murekkep: s.getPropertyValue("--murekkep").trim(),
      soluk: s.getPropertyValue("--murekkep-soluk").trim(),
      cizgi: s.getPropertyValue("--cizgi").trim(),
      tur: {
        kurum: s.getPropertyValue("--tur-kurum").trim(),
        model: s.getPropertyValue("--tur-model").trim(),
        urun: s.getPropertyValue("--tur-urun").trim(),
        kisi: s.getPropertyValue("--tur-kisi").trim(),
        kavram: s.getPropertyValue("--tur-kavram").trim(),
        olay: s.getPropertyValue("--tur-olay").trim()
      }
    };
    return paletCache;
  }

  /* ————— arayüz sesleri (WebAudio; dosya: yalnız sayfa hışırtısı) ————— */
  var sessiz = false;
  try { sessiz = localStorage.getItem("havadis-ses") === "kapali"; } catch (e) {}
  var ses = { ctx: null, panelBuf: null };
  function sesAc() {
    if (ses.ctx) return;
    try {
      ses.ctx = new (window.AudioContext || window.webkitAudioContext)();
      fetch("../varliklar/sayfa-sesi.mp3")
        .then(function (r) { return r.arrayBuffer(); })
        .then(function (b) { return ses.ctx.decodeAudioData(b); })
        .then(function (d) { ses.panelBuf = d; })
        .catch(function () {});
    } catch (e) {}
  }
  document.addEventListener("pointerdown", sesAc, { once: true });
  document.addEventListener("keydown", sesAc, { once: true });

  function tusSesi() { // klavye tıkırtısı: kısacık süzülmüş gürültü
    if (sessiz || !ses.ctx) return;
    if (ses.ctx.state === "suspended") ses.ctx.resume();
    var c = ses.ctx, n = Math.floor(c.sampleRate * 0.03);
    var buf = c.createBuffer(1, n, c.sampleRate), d = buf.getChannelData(0);
    for (var i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, 3);
    var src = c.createBufferSource(); src.buffer = buf;
    src.playbackRate.value = 0.9 + Math.random() * 0.25;
    var f = c.createBiquadFilter(); f.type = "highpass"; f.frequency.value = 1800;
    var g = c.createGain(); g.gain.value = 0.12;
    src.connect(f); f.connect(g); g.connect(c.destination); src.start();
  }
  function tikSesi() { // düğüm/sonuç seçimi: mekanik tık
    if (sessiz || !ses.ctx) return;
    if (ses.ctx.state === "suspended") ses.ctx.resume();
    var c = ses.ctx, t = c.currentTime;
    var o = c.createOscillator(); o.type = "square";
    o.frequency.setValueAtTime(1250, t);
    o.frequency.exponentialRampToValueAtTime(420, t + 0.045);
    var g = c.createGain();
    g.gain.setValueAtTime(0.16, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + 0.06);
    o.connect(g); g.connect(c.destination); o.start(t); o.stop(t + 0.07);
  }
  function panelSesi() { // panel açılışı: derginin kâğıt hışırtısı, tiz ve kısık
    if (sessiz || !ses.ctx || !ses.panelBuf) return;
    if (ses.ctx.state === "suspended") ses.ctx.resume();
    var src = ses.ctx.createBufferSource(); src.buffer = ses.panelBuf;
    src.playbackRate.value = 1.35;
    var g = ses.ctx.createGain(); g.gain.value = 0.22;
    src.connect(g); g.connect(ses.ctx.destination); src.start();
  }

  /* ————— veri ————— */
  var maddeler = [], baglar = [], haberler = [], komsular = {}, adIndex = {}, secili = null;

  Promise.all([
    fetch("wiki-veri.json").then(function (r) { return r.ok ? r.json() : { maddeler: [], baglar: [] }; }),
    fetch("../kulliyat/dizin.json").then(function (r) { return r.ok ? r.json() : { haberler: [] }; })
  ]).then(function (v) {
    haberler = v[1].haberler || [];
    baglar = v[0].baglar || [];
    maddeler = (v[0].maddeler || []).map(function (m) {
      m.haberler = eslesenHaberler(m);
      adIndex[m.ad] = m;
      return m;
    });
    baglar.forEach(function (b) {
      komsular[b.k] = komsular[b.k] || [];
      komsular[b.h] = komsular[b.h] || [];
      if (komsular[b.k].indexOf(b.h) < 0) komsular[b.k].push(b.h);
      if (komsular[b.h].indexOf(b.k) < 0) komsular[b.h].push(b.k);
    });
    $("sayim").textContent = maddeler.length + " varlık · " + baglar.length + " ilişki · " + haberler.length + " haber";
    lejantKur();
    aramaGoster("");
    grafikBaslat();
    hashOku();
  });

  function eslesenHaberler(m) {
    var adK = katla(m.ad);
    var etiketlerK = (m.etiketler || []).map(katla);
    var liste = haberler.filter(function (h) {
      var konularK = (h.konular || []).map(katla);
      if (etiketlerK.some(function (e) { return konularK.indexOf(e) >= 0; })) return true;
      if (adK.length >= 3 && katla((h.baslik || "") + " " + (h.ozet || "")).indexOf(adK) >= 0) return true;
      return false;
    });
    liste.sort(function (a, b) { return (a.tarih || "").localeCompare(b.tarih || ""); });
    return liste;
  }

  /* ————— lejant ————— */
  function lejantKur() {
    var kutu = $("lejant");
    Object.keys(TUR_ADI).forEach(function (tur) {
      var s = el("span", null, null);
      var i = el("i");
      i.style.background = "var(--tur-" + tur + ")";
      s.appendChild(i);
      s.appendChild(document.createTextNode(TUR_ADI[tur]));
      kutu.appendChild(s);
    });
  }

  /* ————— arama ————— */
  var arama = $("arama"), sonucListesi = $("sonuc-listesi"), etkinIdx = -1, gorunenler = [];

  function aramaGoster(soru) {
    var k = katla(soru.trim());
    gorunenler = maddeler.filter(function (m) {
      if (!k) return true;
      return katla(m.ad + " " + m.tanim + " " + (m.etiketler || []).join(" ")).indexOf(k) >= 0;
    });
    gorunenler.sort(function (a, b) { return b.haberler.length - a.haberler.length; });
    gorunenler = gorunenler.slice(0, 12);
    etkinIdx = -1;
    sonucListesi.textContent = "";
    if (!gorunenler.length) {
      var li = el("li");
      li.appendChild(el("p", "kucuk", "Eşleşme yok."));
      sonucListesi.appendChild(li);
      return;
    }
    gorunenler.forEach(function (m, i) {
      var li = el("li");
      var b = el("button", null, null);
      b.type = "button";
      b.id = "sonuc-" + i;
      b.setAttribute("role", "option");
      var nokta = el("i", "nokta");
      nokta.className = "nokta";
      nokta.style.background = "var(--tur-" + (m.tur || "kavram") + ")";
      b.appendChild(nokta);
      b.appendChild(document.createTextNode(m.ad + " · " + m.haberler.length));
      b.appendChild(el("span", "tur-yazi", TUR_ADI[m.tur] || ""));
      b.addEventListener("click", function () { tikSesi(); sec(m.ad); });
      li.appendChild(b);
      sonucListesi.appendChild(li);
    });
  }

  arama.addEventListener("input", function () { aramaGoster(arama.value); });
  arama.addEventListener("keydown", function (e) {
    if (e.key.length === 1 || e.key === "Backspace") tusSesi();
    var dugmeler = sonucListesi.querySelectorAll("button");
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (!dugmeler.length) return;
      etkinIdx = e.key === "ArrowDown"
        ? Math.min(etkinIdx + 1, dugmeler.length - 1)
        : Math.max(etkinIdx - 1, 0);
      dugmeler.forEach(function (d, i) { d.classList.toggle("etkin", i === etkinIdx); });
      arama.setAttribute("aria-activedescendant", "sonuc-" + etkinIdx);
      dugmeler[etkinIdx].scrollIntoView({ block: "nearest" });
    }
    if (e.key === "Enter" && etkinIdx >= 0 && dugmeler[etkinIdx]) {
      dugmeler[etkinIdx].click();
    } else if (e.key === "Enter" && dugmeler.length) {
      dugmeler[0].click();
    }
    if (e.key === "Escape") { arama.value = ""; aramaGoster(""); arama.blur(); }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "/" && document.activeElement !== arama &&
        !/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) {
      e.preventDefault();
      arama.focus();
    }
    if (e.key === "Escape") { detayKapat(); sohbetKapat(); }
  });

  /* ————— detay paneli ————— */
  function sec(ad) {
    var m = adIndex[ad];
    if (!m) return;
    secili = m;
    history.replaceState(null, "", "#d/" + encodeURIComponent(m.slug));

    var rozet = $("detay-tur");
    rozet.textContent = "";
    var nk = el("i");
    nk.style.background = "var(--tur-" + (m.tur || "kavram") + ")";
    rozet.appendChild(nk);
    rozet.appendChild(document.createTextNode(
      (TUR_ADI[m.tur] || "") + " · " + m.haberler.length + " haber · " + (m.guncelleme || "")
    ));
    $("detay-ad").textContent = m.ad;
    $("detay-tanim").textContent = m.tanim || "";

    var govde = $("detay-govde");
    govde.innerHTML = m.govde_html || "";
    govde.querySelectorAll("a").forEach(function (a) {
      var href = a.getAttribute("href") || "";
      if (/^[^/:]+\.html$/.test(href)) { // madde-içi bağ: sayfa yerine düğümü aç
        a.addEventListener("click", function (e) {
          e.preventDefault();
          var hedef = maddeler.filter(function (x) { return x.slug + ".html" === href; })[0];
          if (hedef) { tikSesi(); sec(hedef.ad); }
        });
      } else {
        a.setAttribute("rel", "noopener");
        a.setAttribute("target", "_blank");
      }
    });

    var baglarKutu = $("detay-baglar");
    baglarKutu.textContent = "";
    (komsular[m.ad] || []).forEach(function (komsu) {
      var c = el("button", "cip", komsu);
      c.type = "button";
      c.addEventListener("click", function () { tikSesi(); sec(komsu); });
      baglarKutu.appendChild(c);
    });

    var zaman = $("detay-zaman");
    zaman.textContent = "";
    if (!m.haberler.length) zaman.appendChild(el("li", "bos-durum", "Henüz haber yok."));
    m.haberler.forEach(function (h) {
      var li = el("li", "zaman-ogesi");
      li.appendChild(el("p", "ust-not", trTarih(h.tarih) + " · " + (h.kaynak || "") + " · Sayı " + h.sayi_no));
      var st = el("h5");
      var a = el("a", null, h.baslik || "(başlıksız)");
      a.href = h.url || "#"; a.rel = "noopener"; a.target = "_blank";
      st.appendChild(a);
      li.appendChild(st);
      if (h.ozet) li.appendChild(el("p", "zaman-ozet", h.ozet));
      zaman.appendChild(li);
    });

    var linkler = $("detay-linkler");
    linkler.textContent = "";
    var lugat = el("a", "kaynak-link", "Lugat sayfası ↗");
    lugat.href = "../lugat/" + m.slug + ".html";
    linkler.appendChild(lugat);
    var kulliyat = el("a", "cip", "Külliyat'ta ara");
    kulliyat.href = "../kulliyat/index.html#konu/" + encodeURIComponent(katla((m.etiketler || [m.ad])[0]).replace(/[^a-z0-9]+/g, "-"));
    linkler.appendChild(kulliyat);

    var panel = $("detay");
    if (!panel.classList.contains("acik")) panelSesi();
    panel.classList.add("acik");
    panel.scrollTop = 0;
  }
  function detayKapat() { $("detay").classList.remove("acik"); secili = null; }
  $("kapat").addEventListener("click", function () { tikSesi(); detayKapat(); });

  function hashOku() {
    var e = location.hash.match(/^#d\/(.+)$/);
    if (!e) return;
    var slug = decodeURIComponent(e[1]);
    var m = maddeler.filter(function (x) { return x.slug === slug; })[0];
    if (m) sec(m.ad);
  }

  /* ————— 3B kuvvet grafiği ————— */
  var tuval = $("ag"), cz = tuval.getContext("2d");
  var GEN, YUK, OPR = window.devicePixelRatio || 1;
  var donusX = -0.28, donusY = 0.4, yakinlik = 1, ODAK = 700;
  var sonEtkilesim = 0, suruklenen = null, dondurme = null, oynadi = false;
  var isaretciler = {}, sonTutamMesafe = 0;

  function boyutla() {
    GEN = innerWidth; YUK = innerHeight;
    tuval.width = GEN * OPR; tuval.height = YUK * OPR;
    cz.setTransform(OPR, 0, 0, OPR, 0, 0);
  }
  addEventListener("resize", boyutla);

  function grafikBaslat() {
    boyutla();
    maddeler.forEach(function (m, i) {
      var u = Math.acos(2 * ((i + 0.5) / maddeler.length) - 1);
      var v = Math.PI * (1 + Math.sqrt(5)) * i;
      var S = 210;
      m.x = S * Math.sin(u) * Math.cos(v);
      m.y = S * Math.sin(u) * Math.sin(v);
      m.z = S * Math.cos(u);
      m.vx = 0; m.vy = 0; m.vz = 0;
      m.r = 7 + 3.2 * Math.sqrt(m.haberler.length);
    });
    tuval.addEventListener("pointerdown", basla);
    tuval.addEventListener("pointermove", oyna);
    tuval.addEventListener("pointerup", birak);
    tuval.addEventListener("pointercancel", birak);
    tuval.addEventListener("wheel", function (e) {
      e.preventDefault();
      yakinlik = Math.max(0.45, Math.min(2.6, yakinlik * (e.deltaY > 0 ? 0.92 : 1.08)));
      sonEtkilesim = performance.now();
    }, { passive: false });
    dongu();
  }

  function izdusum(m) {
    var cosY = Math.cos(donusY), sinY = Math.sin(donusY);
    var cosX = Math.cos(donusX), sinX = Math.sin(donusX);
    var x1 = m.x * cosY + m.z * sinY;
    var z1 = -m.x * sinY + m.z * cosY;
    var y1 = m.y * cosX - z1 * sinX;
    var z2 = m.y * sinX + z1 * cosX;
    var p = ODAK / (ODAK + z2);
    return {
      x: GEN / 2 + x1 * p * yakinlik,
      y: YUK / 2 + y1 * p * yakinlik,
      olcek: p * yakinlik,
      derinlik: z2
    };
  }

  function konum(e) {
    var k = tuval.getBoundingClientRect();
    return { x: e.clientX - k.left, y: e.clientY - k.top };
  }
  function bul(p) {
    var enIyi = null, enIyiD = 1e9;
    maddeler.forEach(function (m) {
      var s = izdusum(m);
      var dx = p.x - s.x, dy = p.y - s.y;
      var r = m.r * s.olcek + 7;
      var d2 = dx * dx + dy * dy;
      if (d2 <= r * r && s.derinlik < enIyiD) { enIyi = m; enIyiD = s.derinlik; }
    });
    return enIyi;
  }

  function basla(e) {
    tuval.setPointerCapture(e.pointerId);
    isaretciler[e.pointerId] = konum(e);
    sonEtkilesim = performance.now();
    if (Object.keys(isaretciler).length === 2) { suruklenen = null; dondurme = null; sonTutamMesafe = 0; return; }
    var p = konum(e);
    var m = bul(p);
    oynadi = false;
    if (m) { suruklenen = m; }
    else { dondurme = p; }
  }
  function oyna(e) {
    var p = konum(e);
    if (isaretciler[e.pointerId]) isaretciler[e.pointerId] = p;
    sonEtkilesim = performance.now();
    var idler = Object.keys(isaretciler);
    if (idler.length === 2) { // tutam (pinch) yakınlaştırma
      var a = isaretciler[idler[0]], b = isaretciler[idler[1]];
      var d = Math.hypot(a.x - b.x, a.y - b.y);
      if (sonTutamMesafe) yakinlik = Math.max(0.45, Math.min(2.6, yakinlik * d / sonTutamMesafe));
      sonTutamMesafe = d;
      return;
    }
    if (suruklenen) {
      oynadi = true;
      // ekran düzlemindeki hareketi dünya uzayına geri döndür
      var s = izdusum(suruklenen);
      var dx = (p.x - s.x) / (s.olcek || 1), dy = (p.y - s.y) / (s.olcek || 1);
      var cosY = Math.cos(-donusY), sinY = Math.sin(-donusY);
      var cosX = Math.cos(-donusX), sinX = Math.sin(-donusX);
      var y1 = dy * cosX; var z1 = -dy * sinX;
      var x2 = dx * cosY + z1 * sinY;
      var z2 = -dx * sinY + z1 * cosY;
      suruklenen.x += x2; suruklenen.y += y1; suruklenen.z += z2;
      suruklenen.vx = suruklenen.vy = suruklenen.vz = 0;
    } else if (dondurme) {
      oynadi = true;
      donusY += (p.x - dondurme.x) * 0.005;
      donusX += (p.y - dondurme.y) * 0.005;
      donusX = Math.max(-1.35, Math.min(1.35, donusX));
      dondurme = p;
    } else {
      var m = bul(p);
      tuval.style.cursor = m ? "pointer" : "grab";
      ipucuGoster(m, e.clientX, e.clientY);
    }
  }
  function birak(e) {
    delete isaretciler[e.pointerId];
    sonTutamMesafe = 0;
    if (suruklenen && !oynadi) { tikSesi(); sec(suruklenen.ad); }
    suruklenen = null; dondurme = null;
  }

  var ipucu = $("ipucu");
  function ipucuGoster(m, x, y) {
    if (!m) { ipucu.style.display = "none"; return; }
    ipucu.textContent = "";
    ipucu.appendChild(el("strong", null, m.ad));
    ipucu.appendChild(el("p", "ust-not", (TUR_ADI[m.tur] || "") + " · " + m.haberler.length + " haber"));
    ipucu.style.display = "block";
    ipucu.style.left = Math.min(x + 14, innerWidth - 250) + "px";
    ipucu.style.top = (y + 14) + "px";
  }

  function adim() {
    var i, j, a, b;
    for (i = 0; i < maddeler.length; i++) {
      a = maddeler[i];
      for (j = i + 1; j < maddeler.length; j++) {
        b = maddeler[j];
        var dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
        var kare = dx * dx + dy * dy + dz * dz + 0.01;
        var it = 5200 / kare;
        var u = Math.sqrt(kare);
        dx /= u; dy /= u; dz /= u;
        a.vx += dx * it; a.vy += dy * it; a.vz += dz * it;
        b.vx -= dx * it; b.vy -= dy * it; b.vz -= dz * it;
      }
    }
    baglar.forEach(function (bag) {
      var k = adIndex[bag.k], h = adIndex[bag.h];
      if (!k || !h) return;
      var dx = h.x - k.x, dy = h.y - k.y, dz = h.z - k.z;
      var u = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;
      var cekim = (u - 120) * 0.004;
      dx /= u; dy /= u; dz /= u;
      k.vx += dx * cekim * u * 0.06; k.vy += dy * cekim * u * 0.06; k.vz += dz * cekim * u * 0.06;
      h.vx -= dx * cekim * u * 0.06; h.vy -= dy * cekim * u * 0.06; h.vz -= dz * cekim * u * 0.06;
    });
    maddeler.forEach(function (m) {
      m.vx -= m.x * 0.004; m.vy -= m.y * 0.004; m.vz -= m.z * 0.004;
      if (m === suruklenen) return;
      m.vx *= 0.86; m.vy *= 0.86; m.vz *= 0.86;
      m.x += m.vx; m.y += m.vy; m.z += m.vz;
    });
    if (!AZ_HAREKET && performance.now() - sonEtkilesim > 5000 && !$("detay").classList.contains("acik")) {
      donusY += 0.0008; // boşta kendi kendine yavaşça döner
    }
  }

  function ciz() {
    var P = palet();
    cz.clearRect(0, 0, GEN, YUK);

    var noktalar = maddeler.map(function (m) {
      var s = izdusum(m); s.m = m; return s;
    });

    cz.lineWidth = 1;
    baglar.forEach(function (bag) {
      var k = adIndex[bag.k], h = adIndex[bag.h];
      if (!k || !h) return;
      var a = izdusum(k), b = izdusum(h);
      var vurgulu = secili && (secili === k || secili === h);
      cz.strokeStyle = P.cizgi;
      cz.globalAlpha = vurgulu ? 0.95 : (secili ? 0.18 : 0.5);
      cz.beginPath(); cz.moveTo(a.x, a.y); cz.lineTo(b.x, b.y); cz.stroke();
    });
    cz.globalAlpha = 1;

    noktalar.sort(function (a, b) { return b.derinlik - a.derinlik; }); // uzaktan yakına
    noktalar.forEach(function (s) {
      var m = s.m;
      var r = Math.max(3, m.r * s.olcek);
      var soluk = secili && secili !== m && (komsular[secili.ad] || []).indexOf(m.ad) < 0;
      var derinlikAlfa = Math.max(0.35, Math.min(1, 1.15 - s.derinlik / 900));
      cz.globalAlpha = (soluk ? 0.25 : 1) * derinlikAlfa;
      cz.beginPath();
      cz.arc(s.x, s.y, r, 0, Math.PI * 2);
      cz.fillStyle = P.tur[m.tur] || P.soluk;
      cz.fill();
      cz.lineWidth = 2;
      cz.strokeStyle = P.kagit; // dataviz: bitişik dolgular arasında yüzey halkası
      cz.stroke();
      if (secili === m) {
        cz.lineWidth = 2.5;
        cz.strokeStyle = P.murekkep;
        cz.stroke();
      }
      cz.fillStyle = P.murekkep;
      cz.font = "600 " + Math.max(9, 11 * Math.min(1.25, s.olcek)) + "px system-ui, sans-serif";
      cz.textAlign = "center";
      cz.fillText(m.ad, s.x, s.y + r + 13);
      cz.globalAlpha = 1;
    });
  }
  function dongu() { adim(); ciz(); requestAnimationFrame(dongu); }

  /* ————— sohbet ————— */
  var KOPRU = "http://127.0.0.1:8747", koprulu = false;
  fetch(KOPRU + "/ping").then(function (r) {
    if (r.ok) { koprulu = true; $("kopru-durum").textContent = "🟢 yerel zekâ bağlı"; }
  }).catch(function () {});

  function sohbetAc() { panelSesi(); $("sohbet-panel").classList.add("acik"); $("sohbet-dok").style.display = "none"; $("soru").focus(); }
  function sohbetKapat() { $("sohbet-panel").classList.remove("acik"); $("sohbet-dok").style.display = ""; }
  $("sohbet-ac").addEventListener("click", function () { tikSesi(); sohbetAc(); });
  $("sohbet-kapat").addEventListener("click", function () { tikSesi(); sohbetKapat(); });
  $("soru").addEventListener("keydown", function (e) {
    if (e.key.length === 1 || e.key === "Backspace") tusSesi();
    if (e.key === "Enter") sorusor();
  });
  $("sor-dugme").addEventListener("click", sorusor);

  function sorusor() {
    var soru = $("soru").value.trim();
    if (!soru) return;
    tikSesi();
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
    } else sentezle(soru);
  }

  function puanla(kelimeler, metin) {
    var m = katla(metin), p = 0;
    kelimeler.forEach(function (k) { p += m.split(k).length - 1; });
    return p;
  }

  function sentezle(soru) {
    var kutu = $("cevap");
    kutu.textContent = "";
    var kelimeler = kelimelereAyir(soru);

    var dEs = maddeler.map(function (m) {
      return { m: m, p: puanla(kelimeler, m.ad + " " + m.tanim + " " + (m.etiketler || []).join(" ")) };
    }).filter(function (x) { return x.p > 0; }).sort(function (a, b) { return b.p - a.p; }).slice(0, 3);

    var hEs = haberler.map(function (h) {
      return { h: h, p: puanla(kelimeler, (h.baslik || "") + " " + (h.ozet || "") + " " + (h.konular || []).join(" ")) };
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
        p.appendChild(el("strong", null, x.m.ad));
        p.appendChild(document.createTextNode(" (" + (TUR_ADI[x.m.tur] || "") + ") — " + (x.m.tanim || "")));
        c.appendChild(p);
      });
    }
    var zincir = [], zincirde = {};
    function ekle(h) { if (!zincirde[h.id]) { zincirde[h.id] = 1; zincir.push(h); } }
    dEs.forEach(function (x) { x.m.haberler.forEach(ekle); });
    hEs.forEach(function (x) { ekle(x.h); });
    zincir.sort(function (a, b) { return (a.tarih || "").localeCompare(b.tarih || ""); });
    zincir = zincir.slice(-9);
    if (zincir.length) {
      c.appendChild(el("h4", "cevap-baslik", "Gelişim zinciri"));
      var ol = el("ol", "zaman-cizgisi kucuk-zaman");
      zincir.forEach(function (h) {
        var li = el("li", "zaman-ogesi");
        li.appendChild(el("p", "ust-not", trTarih(h.tarih)));
        var st = el("h5");
        var a = el("a", null, h.baslik || "");
        a.href = h.url || "#"; a.rel = "noopener"; a.target = "_blank";
        st.appendChild(a);
        li.appendChild(st);
        ol.appendChild(li);
      });
      c.appendChild(ol);
    }
    c.appendChild(el("h4", "cevap-baslik", "Kaynaklar"));
    var kl = el("ul", "kaynak-listesi");
    hEs.slice(0, 6).forEach(function (x, i) {
      var li = el("li");
      var a = el("a", null, "[" + (i + 1) + "] " + (x.h.baslik || "") + " — " + (x.h.kaynak || ""));
      a.href = x.h.url || "#"; a.rel = "noopener"; a.target = "_blank";
      li.appendChild(a);
      kl.appendChild(li);
    });
    c.appendChild(kl);
    c.appendChild(el("p", "kucuk", "Hızlı sentez. Akıcı yanıt için Mac'te ~/havadis/sor-sunucu çalıştır."));
    kutu.appendChild(c);
  }

  /* ————— tema & ses düğmeleri ————— */
  var temaD = document.querySelector(".tema-dugme");
  var sesD = document.querySelector(".ses-dugme");
  function temaSimge() { temaD.textContent = temaKoyu() ? "☀" : "☾"; }
  temaD.addEventListener("click", function () {
    var yeni = temaKoyu() ? "acik" : "koyu";
    document.documentElement.dataset.tema = yeni;
    try { localStorage.setItem("havadis-tema", yeni); } catch (e) {}
    paletCache = null;
    temaSimge();
  });
  temaSimge();
  function sesSimge() { sesD.textContent = sessiz ? "🔇" : "🔊"; }
  sesD.addEventListener("click", function () {
    sessiz = !sessiz;
    try { localStorage.setItem("havadis-ses", sessiz ? "kapali" : "acik"); } catch (e) {}
    sesSimge();
    if (!sessiz) tikSesi();
  });
  sesSimge();

  if ("serviceWorker" in navigator && location.protocol.indexOf("http") === 0) {
    navigator.serviceWorker.register("../sw.js");
  }
})();
