/* Havadis Wiki v3 — canlı hücreler.
   Sakin, tek renkli bilgi ağı: yazınca ağ süzülür, hücreye dokununca yalnızca
   ilişkililer kalır ve bağlar görünür. Tür renkleri isteğe bağlıdır (🎨).
   Tamamı özgün, kütüphanesiz kod; veri: wiki-veri.json + ../kulliyat/dizin.json */
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
      damga: s.getPropertyValue("--damga").trim(),
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

  /* ————— arayüz sesleri ————— */
  var sessiz = false;
  try { sessiz = localStorage.getItem("havadis-ses") === "kapali"; } catch (e) {}
  var ses = { ctx: null, panelBuf: null };
  function sesHazirla() {
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
  document.addEventListener("pointerdown", sesHazirla, { once: true });
  document.addEventListener("keydown", sesHazirla, { once: true });

  function tusSesi() {
    if (sessiz || !ses.ctx) return;
    if (ses.ctx.state === "suspended") ses.ctx.resume();
    var c = ses.ctx, n = Math.floor(c.sampleRate * 0.028);
    var buf = c.createBuffer(1, n, c.sampleRate), d = buf.getChannelData(0);
    for (var i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, 3);
    var src = c.createBufferSource(); src.buffer = buf;
    src.playbackRate.value = 0.9 + Math.random() * 0.25;
    var f = c.createBiquadFilter(); f.type = "highpass"; f.frequency.value = 1900;
    var g = c.createGain(); g.gain.value = 0.1;
    src.connect(f); f.connect(g); g.connect(c.destination); src.start();
  }
  function tikSesi() {
    if (sessiz || !ses.ctx) return;
    if (ses.ctx.state === "suspended") ses.ctx.resume();
    var c = ses.ctx, t = c.currentTime;
    var o = c.createOscillator(); o.type = "square";
    o.frequency.setValueAtTime(1150, t);
    o.frequency.exponentialRampToValueAtTime(430, t + 0.04);
    var g = c.createGain();
    g.gain.setValueAtTime(0.13, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + 0.055);
    o.connect(g); g.connect(c.destination); o.start(t); o.stop(t + 0.06);
  }
  function panelSesi() {
    if (sessiz || !ses.ctx || !ses.panelBuf) return;
    if (ses.ctx.state === "suspended") ses.ctx.resume();
    var src = ses.ctx.createBufferSource(); src.buffer = ses.panelBuf;
    src.playbackRate.value = 1.4;
    var g = ses.ctx.createGain(); g.gain.value = 0.18;
    src.connect(g); g.connect(ses.ctx.destination); src.start();
  }

  /* ————— durum ————— */
  var maddeler = [], baglar = [], haberler = [], komsular = {}, adIndex = {};
  var arananSoru = "", odak = null, renkliMod = false, ustunde = null;

  function gorunur(m) {
    if (odak) return m === odak || (komsular[odak.ad] || []).indexOf(m.ad) >= 0;
    if (arananSoru) return m.eslesir;
    return true;
  }

  /* ————— veri ————— */
  Promise.all([
    fetch("wiki-veri.json").then(function (r) { return r.ok ? r.json() : { maddeler: [], baglar: [] }; }),
    fetch("../kulliyat/dizin.json").then(function (r) { return r.ok ? r.json() : { haberler: [] }; })
  ]).then(function (v) {
    haberler = v[1].haberler || [];
    baglar = v[0].baglar || [];
    maddeler = (v[0].maddeler || []).map(function (m) {
      m.haberler = eslesenHaberler(m);
      m.alfa = 1; m.hedefAlfa = 1;
      m.faz = Math.random() * Math.PI * 2;
      adIndex[m.ad] = m;
      return m;
    });
    baglar.forEach(function (b) {
      komsular[b.k] = komsular[b.k] || [];
      komsular[b.h] = komsular[b.h] || [];
      if (komsular[b.k].indexOf(b.h) < 0) komsular[b.k].push(b.h);
      if (komsular[b.h].indexOf(b.k) < 0) komsular[b.h].push(b.k);
    });
    maddeler.forEach(function (m) { m.derece = (komsular[m.ad] || []).length; });
    lejantKur();
    grafikBaslat();
    hashOku();
  });

  function eslesenHaberler(m) {
    var adK = katla(m.ad);
    var etiketlerK = (m.etiketler || []).map(katla);
    var liste = haberler.filter(function (h) {
      var konularK = (h.konular || []).map(katla);
      if (etiketlerK.some(function (e) { return konularK.indexOf(e) >= 0; })) return true;
      return adK.length >= 3 && katla((h.baslik || "") + " " + (h.ozet || "")).indexOf(adK) >= 0;
    });
    liste.sort(function (a, b) { return (a.tarih || "").localeCompare(b.tarih || ""); });
    return liste;
  }

  /* ————— arama hapı: ağın kendisi süzülür ————— */
  var hap = $("arama-hap"), arama = $("arama"), sayac = $("terim-sayisi");

  function aramaUygula() {
    arananSoru = arama.value.trim();
    hap.classList.toggle("dolu", !!arananSoru);
    var k = katla(arananSoru);
    var n = 0;
    maddeler.forEach(function (m) {
      m.eslesir = !k || katla(m.ad + " " + m.tanim + " " + (m.etiketler || []).join(" ")).indexOf(k) >= 0;
      if (k && m.eslesir) n++;
    });
    sayac.textContent = k ? n + " TERİM" : "";
    if (k && odak) odakTemizle(false);
  }
  function aramaAc() {
    hap.classList.add("acik");
    arama.focus();
  }
  function aramaKapat() {
    arama.value = "";
    aramaUygula();
    hap.classList.remove("acik");
    arama.blur();
  }
  $("arama-ac").addEventListener("click", function () {
    if (hap.classList.contains("acik") && !arama.value) aramaKapat();
    else { tikSesi(); aramaAc(); }
  });
  $("arama-sil").addEventListener("click", function () { tikSesi(); arama.value = ""; aramaUygula(); arama.focus(); });
  arama.addEventListener("input", aramaUygula);
  arama.addEventListener("keydown", function (e) {
    if (e.key.length === 1 || e.key === "Backspace") tusSesi();
    if (e.key === "Escape") { aramaKapat(); }
    if (e.key === "Enter") {
      e.preventDefault();
      var ilk = maddeler.filter(function (m) { return m.eslesir; })
        .sort(function (a, b) { return b.haberler.length - a.haberler.length; })[0];
      if (ilk) { tikSesi(); sec(ilk.ad); }
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "/" && !/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) {
      e.preventDefault(); aramaAc();
    }
    if (e.key === "Escape") {
      if ($("sohbet-panel").classList.contains("acik")) sohbetKapat();
      else if (odak) odakTemizle(true);
      else if (!$("hakkinda").hidden) $("hakkinda").hidden = true;
    }
  });

  /* ————— odak: yalnız ilişkililer kalır ————— */
  function sec(ad) {
    var m = adIndex[ad];
    if (!m) return;
    odak = m;
    history.replaceState(null, "", "#d/" + encodeURIComponent(m.slug));
    panelDoldur(m);
    var panel = $("detay");
    if (!panel.classList.contains("acik")) panelSesi();
    panel.classList.add("acik");
    panel.scrollTop = 0;
    ipucuGizle();
    $("ipucu-hap").classList.add("sonuk");
  }
  function odakTemizle(paneliKapat) {
    odak = null;
    history.replaceState(null, "", location.pathname);
    if (paneliKapat) $("detay").classList.remove("acik");
  }
  $("kapat").addEventListener("click", function () { tikSesi(); odakTemizle(true); });

  function panelDoldur(m) {
    var rozet = $("detay-tur");
    rozet.textContent = "";
    var nk = el("i");
    if (renkliMod) nk.style.background = "var(--tur-" + (m.tur || "kavram") + ")";
    rozet.appendChild(nk);
    rozet.appendChild(document.createTextNode(
      (TUR_ADI[m.tur] || "") + " · " + m.haberler.length + " haber · " + (m.derece || 0) + " bağ"
    ));
    $("detay-ad").textContent = m.ad;
    $("detay-tanim").textContent = m.tanim || "";

    var govde = $("detay-govde");
    govde.innerHTML = m.govde_html || "";
    govde.querySelectorAll("a").forEach(function (a) {
      var href = a.getAttribute("href") || "";
      if (/^[^/:]+\.html$/.test(href)) {
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
    kulliyat.href = "../kulliyat/index.html#konu/" +
      encodeURIComponent(katla((m.etiketler || [m.ad])[0]).replace(/[^a-z0-9]+/g, "-"));
    linkler.appendChild(kulliyat);
  }

  function hashOku() {
    var e = location.hash.match(/^#d\/(.+)$/);
    if (!e) return;
    var slug = decodeURIComponent(e[1]);
    var m = maddeler.filter(function (x) { return x.slug === slug; })[0];
    if (m) sec(m.ad);
  }

  /* ————— 3B canlı hücre ağı ————— */
  var tuval = $("ag"), cz = tuval.getContext("2d");
  var GEN, YUK, OPR = window.devicePixelRatio || 1;
  var donusX = -0.22, donusY = 0.35, yakinlik = 1, hedefYakinlik = 1, ODAK_UZ = 720;
  var merkez = { x: 0, y: 0, z: 0 }, hedefMerkez = { x: 0, y: 0, z: 0 };
  var sonEtkilesim = 0, suruklenen = null, dondurme = null, oynadi = false;
  var isaretciler = {}, sonTutamMesafe = 0, zaman = 0;

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
      var S = 205;
      m.x = S * Math.sin(u) * Math.cos(v);
      m.y = S * Math.sin(u) * Math.sin(v);
      m.z = S * Math.cos(u);
      m.vx = 0; m.vy = 0; m.vz = 0;
      m.r = 6.5 + 3 * Math.sqrt(m.haberler.length);
    });
    tuval.addEventListener("pointerdown", basla);
    tuval.addEventListener("pointermove", oyna);
    tuval.addEventListener("pointerup", birak);
    tuval.addEventListener("pointercancel", birak);
    tuval.addEventListener("wheel", function (e) {
      e.preventDefault();
      hedefYakinlik = Math.max(0.45, Math.min(2.8, hedefYakinlik * (e.deltaY > 0 ? 0.9 : 1.1)));
      sonEtkilesim = performance.now();
      $("ipucu-hap").classList.add("sonuk");
    }, { passive: false });
    dongu();
  }

  function izdusum(m) {
    var cosY = Math.cos(donusY), sinY = Math.sin(donusY);
    var cosX = Math.cos(donusX), sinX = Math.sin(donusX);
    var px = m.x - merkez.x, py = m.y - merkez.y, pz = m.z - merkez.z;
    var x1 = px * cosY + pz * sinY;
    var z1 = -px * sinY + pz * cosY;
    var y1 = py * cosX - z1 * sinX;
    var z2 = py * sinX + z1 * cosX;
    var p = ODAK_UZ / (ODAK_UZ + z2);
    return { x: GEN / 2 + x1 * p * yakinlik, y: YUK / 2 + y1 * p * yakinlik, olcek: p * yakinlik, derinlik: z2 };
  }

  function konum(e) {
    var k = tuval.getBoundingClientRect();
    return { x: e.clientX - k.left, y: e.clientY - k.top };
  }
  function bul(p) {
    var enIyi = null, enIyiD = 1e9;
    maddeler.forEach(function (m) {
      if (m.alfa < 0.35) return;
      var s = izdusum(m);
      var dx = p.x - s.x, dy = p.y - s.y;
      var r = m.r * s.olcek + 8;
      if (dx * dx + dy * dy <= r * r && s.derinlik < enIyiD) { enIyi = m; enIyiD = s.derinlik; }
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
    if (m) suruklenen = m;
    else dondurme = p;
  }
  function oyna(e) {
    var p = konum(e);
    if (isaretciler[e.pointerId]) isaretciler[e.pointerId] = p;
    var idler = Object.keys(isaretciler);
    if (idler.length === 2) {
      var a = isaretciler[idler[0]], b = isaretciler[idler[1]];
      var d = Math.hypot(a.x - b.x, a.y - b.y);
      if (sonTutamMesafe) hedefYakinlik = Math.max(0.45, Math.min(2.8, hedefYakinlik * d / sonTutamMesafe));
      sonTutamMesafe = d;
      sonEtkilesim = performance.now();
      return;
    }
    if (suruklenen) {
      oynadi = true;
      sonEtkilesim = performance.now();
      var s = izdusum(suruklenen);
      var dx = (p.x - s.x) / (s.olcek || 1), dy = (p.y - s.y) / (s.olcek || 1);
      var cosY = Math.cos(-donusY), sinY = Math.sin(-donusY);
      var cosX = Math.cos(-donusX), sinX = Math.sin(-donusX);
      var y1 = dy * cosX, z1 = -dy * sinX;
      var x2 = dx * cosY + z1 * sinY;
      var z2 = -dx * sinY + z1 * cosY;
      suruklenen.x += x2; suruklenen.y += y1; suruklenen.z += z2;
      suruklenen.vx = suruklenen.vy = suruklenen.vz = 0;
    } else if (dondurme) {
      oynadi = true;
      sonEtkilesim = performance.now();
      donusY += (p.x - dondurme.x) * 0.0048;
      donusX += (p.y - dondurme.y) * 0.0048;
      donusX = Math.max(-1.35, Math.min(1.35, donusX));
      dondurme = p;
      $("ipucu-hap").classList.add("sonuk");
    } else {
      var m = bul(p);
      tuval.style.cursor = m ? "pointer" : "grab";
      if (m !== ustunde) { ustunde = m; }
      ipucuGoster(m, e.clientX, e.clientY);
    }
  }
  function birak(e) {
    delete isaretciler[e.pointerId];
    sonTutamMesafe = 0;
    if (suruklenen && !oynadi) { tikSesi(); sec(suruklenen.ad); }
    else if (dondurme && !oynadi && odak) { odakTemizle(true); }
    suruklenen = null; dondurme = null;
  }

  var ipucu = $("ipucu");
  function ipucuGoster(m, x, y) {
    if (!m || suruklenen || dondurme) { ipucuGizle(); return; }
    ipucu.textContent = "";
    ipucu.appendChild(el("strong", null, m.ad));
    ipucu.appendChild(el("p", "ust-not",
      (TUR_ADI[m.tur] || "") + " · " + m.haberler.length + " haber · " + (m.derece || 0) + " bağ"));
    ipucu.style.display = "block";
    ipucu.style.left = Math.min(x + 14, innerWidth - 260) + "px";
    ipucu.style.top = (y + 14) + "px";
  }
  function ipucuGizle() { ipucu.style.display = "none"; ustunde = null; }

  function adim() {
    zaman += 0.016;
    var i, j, a, b;
    var aktif = maddeler.filter(gorunur);
    for (i = 0; i < aktif.length; i++) {
      a = aktif[i];
      for (j = i + 1; j < aktif.length; j++) {
        b = aktif[j];
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
      if (!k || !h || !gorunur(k) || !gorunur(h)) return;
      var dx = h.x - k.x, dy = h.y - k.y, dz = h.z - k.z;
      var u = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;
      var hedefUz = odak ? 95 : 118;
      var cekim = (u - hedefUz) * 0.0045;
      dx /= u; dy /= u; dz /= u;
      k.vx += dx * cekim * u * 0.06; k.vy += dy * cekim * u * 0.06; k.vz += dz * cekim * u * 0.06;
      h.vx -= dx * cekim * u * 0.06; h.vy -= dy * cekim * u * 0.06; h.vz -= dz * cekim * u * 0.06;
    });
    maddeler.forEach(function (m) {
      var g = gorunur(m);
      m.hedefAlfa = g ? 1 : 0;
      m.alfa += (m.hedefAlfa - m.alfa) * 0.09;
      if (!g) return;
      m.vx -= m.x * 0.004; m.vy -= m.y * 0.004; m.vz -= m.z * 0.004;
      if (m === suruklenen) return;
      m.vx *= 0.86; m.vy *= 0.86; m.vz *= 0.86;
      m.x += m.vx; m.y += m.vy; m.z += m.vz;
    });

    // kamera: odak varken hücreye süzül, yoksa merkeze dön
    if (odak) { hedefMerkez = { x: odak.x, y: odak.y, z: odak.z }; hedefYakinlik = Math.max(hedefYakinlik, 1.25); }
    else hedefMerkez = { x: 0, y: 0, z: 0 };
    merkez.x += (hedefMerkez.x - merkez.x) * 0.06;
    merkez.y += (hedefMerkez.y - merkez.y) * 0.06;
    merkez.z += (hedefMerkez.z - merkez.z) * 0.06;
    yakinlik += (hedefYakinlik - yakinlik) * 0.08;

    if (!AZ_HAREKET && !odak && performance.now() - sonEtkilesim > 6000) donusY += 0.0006;
  }

  function ciz() {
    var P = palet();
    cz.clearRect(0, 0, GEN, YUK);

    // bağlar
    baglar.forEach(function (bag) {
      var k = adIndex[bag.k], h = adIndex[bag.h];
      if (!k || !h) return;
      var ortakAlfa = Math.min(k.alfa, h.alfa);
      if (ortakAlfa < 0.04) return;
      var a = izdusum(k), b = izdusum(h);
      var vurgulu = odak && (odak === k || odak === h);
      cz.strokeStyle = vurgulu ? P.soluk : P.cizgi;
      cz.lineWidth = vurgulu ? 1.4 : 1;
      cz.globalAlpha = ortakAlfa * (vurgulu ? 0.95 : (ustunde && (ustunde === k || ustunde === h) ? 0.9 : 0.55));
      cz.beginPath(); cz.moveTo(a.x, a.y); cz.lineTo(b.x, b.y); cz.stroke();
    });
    cz.globalAlpha = 1;

    // hücreler (uzaktan yakına)
    var noktalar = maddeler
      .filter(function (m) { return m.alfa > 0.02; })
      .map(function (m) { var s = izdusum(m); s.m = m; return s; })
      .sort(function (a, b) { return b.derinlik - a.derinlik; });

    var maksDerece = 1;
    maddeler.forEach(function (m) { if (m.derece > maksDerece) maksDerece = m.derece; });

    noktalar.forEach(function (s) {
      var m = s.m;
      var nefes = AZ_HAREKET ? 1 : 1 + 0.035 * Math.sin(zaman * 1.3 + m.faz);
      var r = Math.max(2.5, m.r * s.olcek * nefes);
      var derinlikAlfa = Math.max(0.3, Math.min(1, 1.12 - s.derinlik / 950));
      var vurgu = (odak === m) || (ustunde === m);

      // ton: tek renkte koyuluk = bağlantı zenginliği (referansın grameri)
      var taban = 0.4 + 0.55 * (m.derece / maksDerece);
      cz.globalAlpha = m.alfa * derinlikAlfa * (vurgu ? 1 : taban);
      cz.fillStyle = renkliMod ? (P.tur[m.tur] || P.soluk) : P.murekkep;
      cz.beginPath();
      cz.arc(s.x, s.y, r, 0, Math.PI * 2);
      cz.fill();

      if (vurgu) { // canlı hale: yumuşak halka
        cz.globalAlpha = m.alfa * 0.35;
        cz.lineWidth = 5;
        cz.strokeStyle = renkliMod ? (P.tur[m.tur] || P.soluk) : P.murekkep;
        cz.beginPath();
        cz.arc(s.x, s.y, r + 5 + (AZ_HAREKET ? 0 : Math.sin(zaman * 2.4 + m.faz) * 1.4), 0, Math.PI * 2);
        cz.stroke();
      }

      // etiket: hücrenin üstünde, mono, büyük harf
      var etiketAlfa = m.alfa * derinlikAlfa * (vurgu ? 1 : (odak || arananSoru ? 0.9 : Math.min(0.85, 0.3 + m.derece / maksDerece)));
      if (etiketAlfa > 0.12) {
        cz.globalAlpha = etiketAlfa;
        cz.fillStyle = P.murekkep;
        cz.font = (vurgu ? "700 " : "600 ") + Math.max(8.5, 10 * Math.min(1.2, s.olcek)) + "px 'SF Mono', Menlo, monospace";
        cz.textAlign = "center";
        cz.fillText(m.ad.toLocaleUpperCase("tr"), s.x, s.y - r - 6);
      }
      cz.globalAlpha = 1;
    });
  }
  function dongu() { adim(); ciz(); requestAnimationFrame(dongu); }

  /* ————— lejant + renk modu ————— */
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
  $("renk-dugme").addEventListener("click", function () {
    tikSesi();
    renkliMod = !renkliMod;
    this.setAttribute("aria-pressed", String(renkliMod));
    $("lejant").hidden = !renkliMod;
    if (odak) panelDoldur(odak);
  });

  /* ————— hakkında ————— */
  $("hakkinda-ac").addEventListener("click", function () {
    tikSesi();
    $("hakkinda").hidden = !$("hakkinda").hidden;
  });

  /* ————— sohbet ————— */
  var KOPRU = "http://127.0.0.1:8747", koprulu = false, kopruDenendi = false;
  function kopruYokla() { // yalnız sohbet ilk açıldığında (kapalı köprü konsolu kirletmesin)
    if (kopruDenendi) return;
    kopruDenendi = true;
    fetch(KOPRU + "/ping").then(function (r) {
      if (r.ok) { koprulu = true; $("kopru-durum").textContent = "🟢 yerel zekâ bağlı"; }
    }).catch(function () {});
  }

  function sohbetKapat() { $("sohbet-panel").classList.remove("acik"); }
  $("sohbet-ac").addEventListener("click", function () {
    tikSesi();
    var p = $("sohbet-panel");
    if (p.classList.contains("acik")) { sohbetKapat(); return; }
    kopruYokla();
    panelSesi();
    p.classList.add("acik");
    $("soru").focus();
  });
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
  var temaD = $("tema-dugme"), sesD = $("ses-dugme");
  function temaSimge() { temaD.textContent = temaKoyu() ? "☀" : "☾"; }
  temaD.addEventListener("click", function () {
    tikSesi();
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

  // test kancası (Playwright doğrulaması için)
  window.__wiki = { sec: sec, odakTemizle: odakTemizle };

  if ("serviceWorker" in navigator && location.protocol.indexOf("http") === 0) {
    navigator.serviceWorker.register("../sw.js");
  }
})();
