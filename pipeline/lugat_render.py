"""Lugat web basımı: lugat/*.md → site/lugat/ (dizin + madde sayfaları)
+ lugat-tam.md (tek dosyada bütün ansiklopedi — chatbot/LLM tüketimi için)
+ ag.json (düğümler ve bağlar — ilişki grafiği)."""
import json
import sys
from pathlib import Path

import markdown

from pipeline.kulliyat import jsonl_oku
from pipeline.lugat_dogrula import HABER_REF, WIKILINK, _on_yazi_ayir
from pipeline.metin import slugla

KOK = Path(__file__).resolve().parent.parent

TUR_ADI = {
    "kurum": "Kurum", "model": "Model", "urun": "Ürün",
    "kisi": "Kişi", "kavram": "Kavram", "olay": "Olay",
}
TUR_SIRA = ["kurum", "model", "urun", "kisi", "kavram", "olay"]


def _kabuk(baslik, icerik, kok):
    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>try{{var t=localStorage.getItem("havadis-tema");if(t)document.documentElement.dataset.tema=t}}catch(e){{}}</script>
<title>{baslik} — Havadis Lugatı</title>
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#F6F1E5">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#16120C">
<link rel="stylesheet" href="{kok}/varliklar/fontlar/fontlar.css">
<link rel="stylesheet" href="{kok}/varliklar/stil.css">
<link rel="icon" type="image/svg+xml" href="{kok}/ikon.svg">
</head>
<body>
<header class="masthead">
  <h1><a href="{kok}/index.html">HAVADİS</a></h1>
  <p class="slogan">Lugat — haberlerden damıtılan ansiklopedi</p>
</header>
<main>
{icerik}
</main>
<footer class="kuyruk">
  <div class="buyuk-baglar">
    <a class="vurgulu" href="{kok}/wiki/index.html">Havadis Wiki</a>
    <a href="index.html">Lugat dizini</a>
    <a href="{kok}/kulliyat/index.html">Külliyat'ta ara</a>
    <a href="{kok}/index.html">Bugünkü sayı</a>
  </div>
  <p class="kucuk">Lugat her sabah, günün haberlerinin dokunduğu maddelerde güncellenir; her gelişme satırı gerçek bir habere çivilidir.</p>
</footer>
</body>
</html>
"""


def yukle(lugat_dizini):
    maddeler = {}
    for yol in sorted(Path(lugat_dizini).glob("*.md")):
        if yol.name in ("fihrist.md",):
            continue
        on_yazi, govde = _on_yazi_ayir(yol.read_text(encoding="utf-8"))
        maddeler[yol.stem] = {"ad": yol.stem, "on": on_yazi or {}, "govde": govde.strip()}
    return maddeler


def uret(lugat_dizini, haberler, hedef_dizini, kok=".."):
    hedef = Path(hedef_dizini)
    hedef.mkdir(parents=True, exist_ok=True)
    maddeler = yukle(lugat_dizini)
    haber_haritasi = {h["id"]: h for h in haberler}
    slug_haritasi = {ad: slugla(ad) for ad in maddeler}
    baglar = []
    wiki_maddeleri = []

    for ad, madde in maddeler.items():
        govde = madde["govde"]

        for hedef_ad in WIKILINK.findall(govde):
            hedef_ad = hedef_ad.strip()
            if hedef_ad in maddeler and hedef_ad != ad:
                baglar.append({"k": ad, "h": hedef_ad})

        def wikilink_cevir(esle):
            hedef_ad = esle.group(1).strip()
            if hedef_ad in slug_haritasi:
                return f'<a href="{slug_haritasi[hedef_ad]}.html">{hedef_ad}</a>'
            return hedef_ad

        def haber_cevir(esle):
            haber = haber_haritasi.get(esle.group(1))
            if not haber:
                return ""
            baslik = (haber.get("baslik") or "").replace('"', "'")
            return f' <a class="haber-ref" href="{haber.get("url", "#")}" title="{baslik}" rel="noopener">↗</a>'

        islenmis = WIKILINK.sub(wikilink_cevir, govde)
        islenmis = HABER_REF.sub(haber_cevir, islenmis)
        icerik_html = markdown.markdown(islenmis)

        wiki_maddeleri.append(
            {
                "ad": ad,
                "slug": slug_haritasi[ad],
                "tur": madde["on"].get("tur", ""),
                "tanim": madde["on"].get("tanim", ""),
                "etiketler": [str(e) for e in (madde["on"].get("etiketler") or [ad])],
                "guncelleme": str(madde["on"].get("son_guncelleme", "")),
                "govde_html": icerik_html,
            }
        )

        on = madde["on"]
        tur = TUR_ADI.get(on.get("tur", ""), "")
        etiket = (on.get("etiketler") or [ad])[0]
        sayfa = (
            f'<p class="ust-not">{tur} · son güncelleme {on.get("son_guncelleme", "")}</p>\n'
            f'<h2 class="liste-baslik">{ad}</h2>\n'
            f'<p class="alt-aciklama">{on.get("tanim", "")}</p>\n'
            f"{icerik_html}\n"
            f'<p class="kunye" style="margin-top:1.4rem"><a class="cip" '
            f'href="{kok}/kulliyat/index.html#konu/{slugla(str(etiket))}">Külliyat\'ta tüm haberleri</a></p>'
        )
        (hedef / f"{slug_haritasi[ad]}.html").write_text(
            _kabuk(ad, sayfa, kok), encoding="utf-8"
        )

    # dizin: türlere göre gruplu
    bolumler = []
    for tur in TUR_SIRA:
        grup = sorted(
            (m for m in maddeler.values() if m["on"].get("tur") == tur),
            key=lambda m: m["ad"].lower(),
        )
        if not grup:
            continue
        ogeler = "\n".join(
            f'<li><a href="{slug_haritasi[m["ad"]]}.html"><span><strong>{m["ad"]}</strong> — '
            f'{m["on"].get("tanim", "")}</span></a></li>'
            for m in grup
        )
        bolumler.append(f'<h3 class="bolum-baslik">{TUR_ADI[tur]}lar</h3>\n<ul class="sayi-listesi">{ogeler}</ul>')
    dizin = (
        '<h2 class="liste-baslik">Lugat</h2>\n'
        f'<p class="alt-aciklama">{len(maddeler)} madde — haberler biriktikçe büyür; '
        "her madde ilişkileri ve gelişme zinciriyle birlikte yazılır.</p>\n" + "\n".join(bolumler)
        if maddeler
        else '<h2 class="liste-baslik">Lugat</h2>\n<p class="bos-durum">Lugat henüz boş — ilk maddeler bugünkü sayıyla açılır.</p>'
    )
    (hedef / "index.html").write_text(_kabuk("Lugat", dizin, kok), encoding="utf-8")

    # tek dosya derleme (LLM tüketimi) + ilişki grafiği
    parcalar = ["# Havadis Lugatı — tam derleme\n"]
    for ad in sorted(maddeler, key=str.lower):
        m = maddeler[ad]
        parcalar.append(f"\n## {ad}\n\n_{m['on'].get('tanim', '')}_\n\n{m['govde']}\n")
    (hedef / "lugat-tam.md").write_text("\n".join(parcalar), encoding="utf-8")

    (hedef / "ag.json").write_text(
        json.dumps(
            {
                "dugumler": [
                    {
                        "ad": ad,
                        "slug": slug_haritasi[ad],
                        "tur": m["on"].get("tur", ""),
                        "tanim": m["on"].get("tanim", ""),
                        "etiketler": [str(e) for e in (m["on"].get("etiketler") or [ad])],
                    }
                    for ad, m in maddeler.items()
                ],
                "baglar": baglar,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Havadis Wiki sayfasının tam veri paketi (madde gövdeleri dahil)
    wiki_dizini = hedef.parent / "wiki"
    wiki_dizini.mkdir(parents=True, exist_ok=True)
    (wiki_dizini / "wiki-veri.json").write_text(
        json.dumps(
            {"maddeler": wiki_maddeleri, "baglar": baglar}, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    return len(maddeler)


def main():
    haberler = jsonl_oku(KOK / "veri" / "haberler.jsonl")
    adet = uret(KOK / "lugat", haberler, KOK / "site" / "lugat", kok="..")
    print(f"Lugat basıldı: {adet} madde → site/lugat/")


if __name__ == "__main__":
    main()
