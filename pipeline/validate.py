"""issue.json doğrulayıcı — şema + aday havuzu (ID) kontrolü.

Hata mesajları Türkçe'dir: sabah editörü (Claude) bu çıktıyı okuyup issue.json'ı düzeltir.
Temel güvence: dergiye yalnızca candidates.json havuzundaki id'ler girebilir (uydurma link imkânsız).
"""
import json
import sys
from pathlib import Path

BOLUMLER = ["Gündem", "Araştırma Masası", "Türkiye'den", "Araç Çantası"]

LIMITLER = {
    "kapak_ozet_kelime": 110,
    "haber_ozet_kelime": 70,
    "neden_kelime": 30,
    "baslik_karakter": 110,
    "kicker_karakter": 48,
    "radar_kelime": 35,
    "radar_min": 3,
    "radar_max": 8,
    "toplam_min": 5,
    "toplam_max": 14,
    "bolum_max": 7,
    "notu_kelime": 60,
    "konu_min": 1,
    "konu_max": 4,
    "konu_karakter": 32,
    "iliskili_max": 3,
}


def _kelime(metin):
    return len(str(metin or "").split())


def dogrula(sayi, havuz, eski_idler=None):
    """Sayıyı havuza karşı doğrular; hata listesi döner (boş liste = geçerli).

    eski_idler: Külliyat'taki (veri/haberler.jsonl) geçmiş haber id'leri —
    'iliskili' bağları yalnızca bu kümeye işaret edebilir.
    """
    hatalar = []
    gecerli_idler = {a["id"] for a in havuz.get("adaylar", [])}
    gecmis_idler = set(eski_idler or ())
    kullanilan_idler = set()

    def id_kontrol(cid, yer):
        if cid not in gecerli_idler:
            hatalar.append(
                f"{yer}: '{cid}' aday havuzunda yok — yalnızca candidates.json'daki id'ler kullanılabilir."
            )
        elif cid in kullanilan_idler:
            hatalar.append(f"{yer}: '{cid}' sayıda birden fazla kez kullanılmış.")
        kullanilan_idler.add(cid)

    def haber_kontrol(obj, yer, ozet_siniri):
        for alan in ("id", "baslik", "ozet", "neden_onemli"):
            if not obj.get(alan):
                hatalar.append(f"{yer}: '{alan}' alanı eksik veya boş.")
        if len(obj.get("baslik", "")) > LIMITLER["baslik_karakter"]:
            hatalar.append(
                f"{yer}: başlık çok uzun (≤{LIMITLER['baslik_karakter']} karakter)."
            )
        if _kelime(obj.get("ozet")) > ozet_siniri:
            hatalar.append(
                f"{yer}: özet {_kelime(obj.get('ozet'))} kelime; sınır {ozet_siniri}. Kısalt."
            )
        if _kelime(obj.get("neden_onemli")) > LIMITLER["neden_kelime"]:
            hatalar.append(
                f"{yer}: 'neden_onemli' çok uzun (≤{LIMITLER['neden_kelime']} kelime, tek cümle)."
            )
        if obj.get("id"):
            id_kontrol(obj["id"], yer)

        konular = obj.get("konular")
        if not isinstance(konular, list) or not (
            LIMITLER["konu_min"] <= len(konular) <= LIMITLER["konu_max"]
        ):
            hatalar.append(
                f"{yer}: 'konular' {LIMITLER['konu_min']}-{LIMITLER['konu_max']} "
                "etiketlik liste olmalı (Külliyat endeksi için)."
            )
        else:
            for konu in konular:
                if not konu or len(str(konu)) > LIMITLER["konu_karakter"]:
                    hatalar.append(
                        f"{yer}: konu etiketi boş ya da çok uzun "
                        f"(≤{LIMITLER['konu_karakter']} karakter)."
                    )

        iliskili = obj.get("iliskili") or []
        if len(iliskili) > LIMITLER["iliskili_max"]:
            hatalar.append(
                f"{yer}: 'iliskili' en fazla {LIMITLER['iliskili_max']} bağ içerebilir."
            )
        for eski_id in iliskili:
            if eski_id not in gecmis_idler:
                hatalar.append(
                    f"{yer}: iliskili '{eski_id}' Külliyat geçmişinde yok — "
                    "yalnızca konular_ozet.json'da gördüğün id'ler kullanılabilir."
                )

    # Kapak
    kapak = sayi.get("kapak")
    if not kapak:
        hatalar.append("Kapak eksik: 'kapak' alanı zorunlu.")
    else:
        haber_kontrol(kapak, "Kapak", LIMITLER["kapak_ozet_kelime"])
        if len(kapak.get("kicker", "")) > LIMITLER["kicker_karakter"]:
            hatalar.append(
                f"Kapak: 'kicker' çok uzun (≤{LIMITLER['kicker_karakter']} karakter, ~4 kelime)."
            )

    # Bölümler
    toplam_haber = 0
    gorulen_bolumler = set()
    for bolum in sayi.get("bolumler", []):
        ad = bolum.get("ad", "?")
        if ad not in BOLUMLER:
            hatalar.append(
                f"Bölüm adı geçersiz: '{ad}'. İzin verilenler: {', '.join(BOLUMLER)}."
            )
        if ad in gorulen_bolumler:
            hatalar.append(f"Bölüm tekrarı: '{ad}' listede iki kez var.")
        gorulen_bolumler.add(ad)

        haberler = bolum.get("haberler", [])
        if not haberler:
            hatalar.append(f"'{ad}' bölümü boş — boş bölümü listeye hiç koyma.")
        if len(haberler) > LIMITLER["bolum_max"]:
            hatalar.append(f"'{ad}' bölümünde çok fazla haber (≤{LIMITLER['bolum_max']}).")
        for i, haber in enumerate(haberler, 1):
            haber_kontrol(haber, f"{ad} #{i}", LIMITLER["haber_ozet_kelime"])
        toplam_haber += len(haberler)

    if not (LIMITLER["toplam_min"] <= toplam_haber <= LIMITLER["toplam_max"]):
        hatalar.append(
            f"Kapak hariç toplam haber {toplam_haber}; "
            f"{LIMITLER['toplam_min']}-{LIMITLER['toplam_max']} arası olmalı."
        )

    # Radar
    radar = sayi.get("radar", [])
    if not (LIMITLER["radar_min"] <= len(radar) <= LIMITLER["radar_max"]):
        hatalar.append(
            f"Radar {len(radar)} maddede; {LIMITLER['radar_min']}-{LIMITLER['radar_max']} arası olmalı."
        )
    for i, madde in enumerate(radar, 1):
        if not madde.get("id"):
            hatalar.append(f"Radar #{i}: 'id' eksik.")
        else:
            id_kontrol(madde["id"], f"Radar #{i}")
        if not madde.get("cumle"):
            hatalar.append(f"Radar #{i}: 'cumle' eksik.")
        elif _kelime(madde["cumle"]) > LIMITLER["radar_kelime"]:
            hatalar.append(f"Radar #{i}: cümle çok uzun (≤{LIMITLER['radar_kelime']} kelime).")

    # Editör notu (isteğe bağlı)
    notu = sayi.get("editor_notu")
    if notu and _kelime(notu) > LIMITLER["notu_kelime"]:
        hatalar.append(f"Editör notu çok uzun (≤{LIMITLER['notu_kelime']} kelime).")

    return hatalar


def main():
    kok = Path(__file__).resolve().parent.parent
    try:
        sayi = json.loads((kok / "issue.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("issue.json bulunamadı — editör henüz sayıyı yazmamış.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"issue.json geçerli JSON değil: {e}")
        sys.exit(1)
    havuz = json.loads((kok / "candidates.json").read_text(encoding="utf-8"))

    eski_idler = set()
    jsonl = kok / "veri" / "haberler.jsonl"
    if jsonl.exists():
        for satir in jsonl.read_text(encoding="utf-8").splitlines():
            if satir.strip():
                eski_idler.add(json.loads(satir)["id"])

    hatalar = dogrula(sayi, havuz, eski_idler)
    if hatalar:
        print("issue.json GEÇERSİZ:")
        for h in hatalar:
            print(" -", h)
        sys.exit(1)
    print("issue.json geçerli ✓")


if __name__ == "__main__":
    main()
