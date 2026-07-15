"""Obsidian kasası — Külliyat'ın Markdown/wikilink görünümü.

Her sabah veri/haberler.jsonl'den kasa/ klasörünü TAM yeniden üretir:
  kasa/Haberler/YYYY-MM-DD Başlık.md  (frontmatter + [[konu]] + [[ilişkili haber]])
  kasa/Konular/Konu.md                (kronolojik hub sayfası)
Klasör Obsidian'da vault olarak açıldığında bağ grafiği kendiliğinden oluşur.
"""
import re
import shutil
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
YASAK = set('/\\:#^[]|"?*<>')


def dosya_adi(kayit):
    baslik = kayit.get("baslik") or "not"
    temiz = "".join(c for c in baslik if c not in YASAK)
    temiz = re.sub(r"\s+", " ", temiz).strip()[:60].strip()
    return f"{kayit.get('tarih', '')} {temiz}".strip()


def benzersiz_adlar(butun):
    """id → dosya adı; aynı gün aynı başlık çakışırsa kısa id eklenir (sessiz ezme olmaz)."""
    adlar, kullanilmis = {}, set()
    for kayit in butun:
        ad = dosya_adi(kayit)
        ek = 4
        while ad in kullanilmis:
            ad = f"{dosya_adi(kayit)} {kayit['id'][:ek]}"
            ek += 1
        kullanilmis.add(ad)
        adlar[kayit["id"]] = ad
    return adlar


def _on_yazi(kayit):
    konular = ", ".join('"%s"' % k.replace('"', "'") for k in kayit.get("konular", []))
    return (
        "---\n"
        f"tarih: {kayit.get('tarih', '')}\n"
        f"sayi: {kayit.get('sayi_no', '')}\n"
        f"bolum: {kayit.get('bolum', '')}\n"
        f"kaynak: \"{(kayit.get('kaynak') or '').replace(chr(34), chr(39))}\"\n"
        f"url: \"{kayit.get('url', '')}\"\n"
        f"konular: [{konular}]\n"
        "---\n"
    )


def kasa_yaz(hedef, butun, lugat_kaynagi=None):
    hedef = Path(hedef)
    haberler_dizini = hedef / "Haberler"
    konular_dizini = hedef / "Konular"
    for dizin in (haberler_dizini, konular_dizini):  # tam yeniden üretim: bayat not kalmasın
        if dizin.exists():
            shutil.rmtree(dizin)
    haberler_dizini.mkdir(parents=True, exist_ok=True)
    konular_dizini.mkdir(parents=True, exist_ok=True)

    harita = {k["id"]: k for k in butun}
    adlar = benzersiz_adlar(butun)
    konu_defteri = {}

    for kayit in butun:
        parcalar = [_on_yazi(kayit), f"# {kayit.get('baslik', '')}\n"]
        if kayit.get("ozet"):
            parcalar.append(kayit["ozet"] + "\n")
        if kayit.get("neden_onemli"):
            parcalar.append(f"**Neden önemli?** {kayit['neden_onemli']}\n")
        if kayit.get("konular"):
            parcalar.append(
                "Konular: " + " · ".join(f"[[{ad}]]" for ad in kayit["konular"]) + "\n"
            )
        bagli = [harita[i] for i in kayit.get("iliskili", []) if i in harita]
        if bagli:
            parcalar.append(
                "İlişkili: " + " · ".join(f"[[{adlar[b['id']]}]]" for b in bagli) + "\n"
            )
        if kayit.get("url"):
            parcalar.append(f"[Kaynak — {kayit.get('kaynak') or 'bağlantı'}]({kayit['url']})\n")

        (haberler_dizini / (adlar[kayit["id"]] + ".md")).write_text(
            "\n".join(parcalar), encoding="utf-8"
        )
        for ad in kayit.get("konular", []):
            konu_defteri.setdefault(ad, []).append(kayit)

    # Lugat (editör-bakımlı ansiklopedi) kopyası: [[konu]] bağları gerçek maddelere çözülsün
    lugat_adlari = set()
    if lugat_kaynagi and Path(lugat_kaynagi).exists():
        lugat_dizini = hedef / "Lugat"
        if lugat_dizini.exists():
            shutil.rmtree(lugat_dizini)
        lugat_dizini.mkdir(parents=True, exist_ok=True)
        for kaynak_dosya in sorted(Path(lugat_kaynagi).glob("*.md")):
            shutil.copy2(kaynak_dosya, lugat_dizini / kaynak_dosya.name)
            if kaynak_dosya.stem != "fihrist":
                lugat_adlari.add(kaynak_dosya.stem)

    for ad, kayitlar in konu_defteri.items():
        if ad in lugat_adlari:
            continue  # Lugat maddesi varsa otomatik hub'ı gölgeler (Obsidian'da tek isim)
        kayitlar = sorted(kayitlar, key=lambda x: x.get("tarih", ""), reverse=True)
        govde = ["---\ntur: konu\n---\n", f"# {ad}\n", f"{len(kayitlar)} haber\n"]
        govde += [f"- [[{adlar[x['id']]}]] — {x.get('tarih', '')}, {x.get('bolum', '')}" for x in kayitlar]
        hub_adi = "".join(c for c in ad if c not in YASAK).strip() or "konu"
        (konular_dizini / (hub_adi + ".md")).write_text("\n".join(govde) + "\n", encoding="utf-8")

    (hedef / "OKUBENI.md").write_text(
        "# Havadis Kasası\n\n"
        "Bu klasörü Obsidian'da **vault olarak aç** (Open folder as vault): "
        "Haberler ↔ Konular wikilink'leri sayesinde bağ grafiği ve backlink'ler kendiliğinden oluşur.\n\n"
        "Klasör her sabah Havadis tarafından yeniden üretilir — elle düzenleme yapma; "
        "notlarını ayrı bir klasörde tutup buraya [[bağ]] ver.\n",
        encoding="utf-8",
    )


def main():
    from pipeline.kulliyat import jsonl_oku

    butun = jsonl_oku(KOK / "veri" / "haberler.jsonl")
    kasa_yaz(KOK / "kasa", butun, lugat_kaynagi=KOK / "lugat")
    print(f"Kasa: {len(butun)} not yazıldı → kasa/")


if __name__ == "__main__":
    main()
