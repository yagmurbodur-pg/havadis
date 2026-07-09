"""Türkçe metin yardımcıları (paylaşılan: render + kulliyat)."""

_TR = str.maketrans("çğıöşüÇĞİIÖŞÜâÂîÎûÛ", "cgiosucgiiosuaaiiuu")


def katla(metin):
    """Türkçe karakterleri ASCII'ye katlar, küçük harfe indirir (arama/slug için)."""
    return (metin or "").translate(_TR).lower()


def slugla(metin):
    """Konu adı → URL/kimlik dostu slug: 'Açık Kaynak' → 'acik-kaynak'."""
    duz = katla(metin)
    parcalar = []
    kelime = ""
    for karakter in duz:
        if karakter.isalnum():
            kelime += karakter
        elif kelime:
            parcalar.append(kelime)
            kelime = ""
    if kelime:
        parcalar.append(kelime)
    return "-".join(parcalar)
