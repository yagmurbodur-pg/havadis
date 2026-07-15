"""Külliyat — Havadis'in kümülatif bilgi tabanı.

Her sayı yayınlandıktan sonra haberler veri/haberler.jsonl'e eklenir (idempotent),
site/kulliyat/dizin.json arama endeksi ve veri/konular_ozet.json (ertesi sabah
editörün göreceği konu endeksi) yeniden üretilir.
"""
import json
from pathlib import Path

from pipeline.metin import slugla

KOK = Path(__file__).resolve().parent.parent


def _kayit(hid, tarih, sayi_no, bolum, baslik, ozet, neden, konular, iliskili, aday):
    return {
        "id": hid,
        "tarih": tarih,
        "sayi_no": sayi_no,
        "bolum": bolum,
        "baslik": baslik,
        "ozet": ozet,
        "neden_onemli": neden,
        "konular": konular,
        "iliskili": iliskili,
        "kaynak": aday.get("kaynak", ""),
        "url": aday.get("url", ""),
        "ek_kaynaklar": aday.get("ek_kaynaklar", []),
    }


def birlestir(butun, sayi, havuz, tarih_iso, sayi_no):
    """Sayıdaki tüm öğeleri (kapak + bölümler + radar) kayda çevirir; zaten olanları atlar."""
    mevcut = {r["id"] for r in butun}
    adaylar = {a["id"]: a for a in havuz.get("adaylar", [])}
    yeni = []

    def ekle(kayit):
        if kayit["id"] not in mevcut:
            mevcut.add(kayit["id"])
            yeni.append(kayit)

    kapak = sayi.get("kapak")
    if kapak:
        ekle(
            _kayit(
                kapak["id"], tarih_iso, sayi_no, "Kapak",
                kapak.get("baslik", ""), kapak.get("ozet", ""),
                kapak.get("neden_onemli", ""), kapak.get("konular", []),
                kapak.get("iliskili", []), adaylar.get(kapak["id"], {}),
            )
        )
    for bolum in sayi.get("bolumler", []):
        for h in bolum.get("haberler", []):
            ekle(
                _kayit(
                    h["id"], tarih_iso, sayi_no, bolum.get("ad", ""),
                    h.get("baslik", ""), h.get("ozet", ""),
                    h.get("neden_onemli", ""), h.get("konular", []),
                    h.get("iliskili", []), adaylar.get(h["id"], {}),
                )
            )
    for r in sayi.get("radar", []):
        aday = adaylar.get(r["id"], {})
        ekle(
            _kayit(
                r["id"], tarih_iso, sayi_no, "Radar",
                aday.get("baslik", ""), r.get("cumle", ""), "", [], [], aday,
            )
        )
    return yeni


def konu_ozeti(butun, son_adet=5):
    """Konu → adet + son haberler. Editörün 'devam eden hikâye' bağları için pusulası."""
    konular = {}
    for kayit in sorted(butun, key=lambda x: x.get("tarih", ""), reverse=True):
        for ad in kayit.get("konular", []):
            k = konular.setdefault(
                ad, {"ad": ad, "slug": slugla(ad), "adet": 0, "son": []}
            )
            k["adet"] += 1
            if len(k["son"]) < son_adet:
                k["son"].append(
                    {"id": kayit["id"], "baslik": kayit["baslik"], "tarih": kayit["tarih"]}
                )
    return {"konular": sorted(konular.values(), key=lambda k: -k["adet"])}


def jsonl_oku(yol):
    if not Path(yol).exists():
        return []
    return [
        json.loads(satir)
        for satir in Path(yol).read_text(encoding="utf-8").splitlines()
        if satir.strip()
    ]


def main():
    veri = KOK / "veri"
    veri.mkdir(exist_ok=True)
    jsonl = veri / "haberler.jsonl"

    butun = jsonl_oku(jsonl)
    sayi = json.loads((KOK / "issue.json").read_text(encoding="utf-8"))
    havuz = json.loads((KOK / "candidates.json").read_text(encoding="utf-8"))
    son = json.loads((KOK / "site" / "son.json").read_text(encoding="utf-8"))

    yeni = birlestir(butun, sayi, havuz, son["tarih"], son["sayi_no"])
    with jsonl.open("a", encoding="utf-8") as f:
        for kayit in yeni:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")

    tumu = butun + yeni
    kulliyat_dizini = KOK / "site" / "kulliyat"
    kulliyat_dizini.mkdir(parents=True, exist_ok=True)
    (kulliyat_dizini / "dizin.json").write_text(
        json.dumps({"haberler": tumu}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    (veri / "konular_ozet.json").write_text(
        json.dumps(konu_ozeti(tumu), ensure_ascii=False, indent=1), encoding="utf-8"
    )
    # Lugat (ansiklopedi) editörünün girdisi: bugünün haberleri — yeniden koşuşta da doğru
    bugun = [k for k in tumu if k.get("tarih") == son["tarih"]]
    (veri / "bugun.json").write_text(
        json.dumps({"tarih": son["tarih"], "haberler": bugun}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"Külliyat: +{len(yeni)} haber → toplam {len(tumu)} · bugün {len(bugun)}")


if __name__ == "__main__":
    main()
