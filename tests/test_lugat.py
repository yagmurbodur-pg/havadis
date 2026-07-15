"""Lugat doğrulayıcısı: fihrist↔dosya eşleşmesi, tanım sınırı, kırık bağ, uydurma haber id'si."""
import textwrap

from pipeline.lugat_dogrula import lugat_dogrula


def madde(baslik, tanim="Kısa tanım.", govde="Tanım cümlesi.", iliskiler="", gelismeler=""):
    return textwrap.dedent(f"""\
    ---
    baslik: {baslik}
    tur: kurum
    tanim: "{tanim}"
    esanlamlilar: []
    etiketler: [{baslik}]
    olusturulma: 2026-07-15
    son_guncelleme: 2026-07-15
    ---

    {govde}

    ## İlişkiler
    {iliskiler}

    ## Gelişmeler
    {gelismeler}
    """)


def kur(tmp_path, dosyalar, fihrist_maddeleri):
    lugat = tmp_path / "lugat"
    lugat.mkdir()
    for ad, icerik in dosyalar.items():
        (lugat / f"{ad}.md").write_text(icerik, encoding="utf-8")
    satirlar = ["# Fihrist", "", "## Kurumlar"]
    satirlar += [f"- [[{m}]]" for m in fihrist_maddeleri]
    (lugat / "fihrist.md").write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    return lugat


def test_gecerli_lugat_gecer(tmp_path):
    lugat = kur(
        tmp_path,
        {
            "OpenAI": madde("OpenAI", gelismeler="- **2026-07-15** — GPT-5.6 çıktı. (haber: 54ee76ae)"),
            "Anthropic": madde("Anthropic", iliskiler="- [[OpenAI]] — rakibi"),
        },
        ["OpenAI", "Anthropic"],
    )
    assert lugat_dogrula(lugat, {"54ee76ae"}) == []


def test_fihristte_olmayan_dosya_yetimdir(tmp_path):
    lugat = kur(tmp_path, {"OpenAI": madde("OpenAI"), "Gizli": madde("Gizli")}, ["OpenAI"])
    hatalar = lugat_dogrula(lugat, set())
    assert any("Gizli" in h and "fihrist" in h.lower() for h in hatalar)


def test_dosyasi_olmayan_fihrist_kaydi(tmp_path):
    lugat = kur(tmp_path, {"OpenAI": madde("OpenAI")}, ["OpenAI", "Hayalet"])
    hatalar = lugat_dogrula(lugat, set())
    assert any("Hayalet" in h for h in hatalar)


def test_uzun_tanim_reddedilir(tmp_path):
    lugat = kur(tmp_path, {"OpenAI": madde("OpenAI", tanim="ç" * 141)}, ["OpenAI"])
    assert lugat_dogrula(lugat, set()) != []


def test_kirik_wikilink_reddedilir(tmp_path):
    lugat = kur(
        tmp_path,
        {"OpenAI": madde("OpenAI", govde="Tanım. [[Olmayan Madde]] ile çalışır.")},
        ["OpenAI"],
    )
    hatalar = lugat_dogrula(lugat, set())
    assert any("Olmayan Madde" in h for h in hatalar)


def test_uydurma_haber_id_reddedilir(tmp_path):
    lugat = kur(
        tmp_path,
        {"OpenAI": madde("OpenAI", gelismeler="- **2026-07-15** — Bir şey oldu. (haber: yok99999)")},
        ["OpenAI"],
    )
    hatalar = lugat_dogrula(lugat, {"54ee76ae"})
    assert any("yok99999" in h for h in hatalar)


def test_baslik_dosya_adi_uyumsuz(tmp_path):
    lugat = kur(tmp_path, {"OpenAI": madde("Baska Ad")}, ["OpenAI"])
    assert lugat_dogrula(lugat, set()) != []
