"""Lugat web basımı: madde HTML'i, wikilink→link, (haber: id)→kaynak, dizin, ag.json."""
import json
import textwrap

from pipeline.lugat_render import uret


def _madde(baslik, govde):
    on_yazi = textwrap.dedent(f"""\
    ---
    baslik: {baslik}
    tur: kurum
    tanim: "{baslik} için kısa tanım."
    esanlamlilar: []
    etiketler: [{baslik}]
    olusturulma: 2026-07-15
    son_guncelleme: 2026-07-15
    ---
    """)
    return on_yazi + "\n" + govde + "\n"


def test_uret_madde_ve_dizin(tmp_path):
    lugat = tmp_path / "lugat"
    lugat.mkdir()
    (lugat / "OpenAI.md").write_text(
        _madde("OpenAI", "Tanım cümlesi. [[Anthropic]] ile yarışır.\n\n## Gelişmeler\n- **2026-07-15** — Model çıktı. (haber: abc12345)"),
        encoding="utf-8",
    )
    (lugat / "Anthropic.md").write_text(_madde("Anthropic", "Tanım."), encoding="utf-8")
    (lugat / "fihrist.md").write_text("- [[OpenAI]]\n- [[Anthropic]]\n", encoding="utf-8")

    haberler = [{"id": "abc12345", "url": "https://ornek.com/h", "baslik": "Model haberi"}]
    hedef = tmp_path / "site-lugat"
    uret(lugat, haberler, hedef, kok="..")

    dizin = (hedef / "index.html").read_text(encoding="utf-8")
    assert "OpenAI" in dizin and "kısa tanım" in dizin

    sayfa = (hedef / "openai.html").read_text(encoding="utf-8")
    assert 'href="anthropic.html"' in sayfa          # wikilink çözüldü
    assert "https://ornek.com/h" in sayfa            # haber referansı kaynağa bağlandı
    assert "Gelişmeler" in sayfa

    wiki = json.loads((tmp_path / "wiki" / "wiki-veri.json").read_text(encoding="utf-8"))
    openai_madde = [m for m in wiki["maddeler"] if m["ad"] == "OpenAI"][0]
    assert 'href="anthropic.html"' in openai_madde["govde_html"]
    # RAG için yapılandırılmış gelişme üçlüleri (tarih + cümle + kaynak id'leri)
    assert openai_madde["gelismeler"][0]["tarih"] == "2026-07-15"
    assert openai_madde["gelismeler"][0]["haberler"] == ["abc12345"]
    assert "Model çıktı" in openai_madde["gelismeler"][0]["cumle"]

    ag = json.loads((hedef / "ag.json").read_text(encoding="utf-8"))
    assert any(k["k"] == "OpenAI" and k["h"] == "Anthropic" for k in ag["baglar"])
    openai = [d for d in ag["dugumler"] if d["ad"] == "OpenAI"][0]
    assert openai["etiketler"] == ["OpenAI"]  # wiki sayfası haber eşleştirmesi için
    assert (hedef / "lugat-tam.md").exists()
