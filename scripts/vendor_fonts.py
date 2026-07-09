"""Google Fonts'tan Fraunces + Newsreader woff2 dosyalarını indirir (latin + latin-ext),
site/varliklar/fontlar/ altına koyar ve fontlar.css'i üretir. Tek seferlik/vendoring aracı.
"""
import re
from pathlib import Path

import httpx

KOK = Path(__file__).resolve().parent.parent
HEDEF = KOK / "site" / "varliklar" / "fontlar"

CSS2 = (
    "https://fonts.googleapis.com/css2"
    "?family=Fraunces:wght@600;900"
    "&family=Newsreader:ital,wght@0,400;0,600;1,400"
    "&display=swap"
)
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}
SUBSETLER = {"latin", "latin-ext"}

BLOK = re.compile(
    r"/\*\s*(?P<subset>[\w-]+)\s*\*/\s*@font-face\s*\{(?P<govde>.*?)\}", re.S
)


def alan(govde, ad):
    m = re.search(rf"{ad}:\s*([^;]+);", govde)
    return m.group(1).strip() if m else ""


def main():
    HEDEF.mkdir(parents=True, exist_ok=True)
    css = httpx.get(CSS2, headers=UA, timeout=30).text
    kurallar = []
    with httpx.Client(timeout=60) as istemci:
        for m in BLOK.finditer(css):
            subset = m.group("subset")
            if subset not in SUBSETLER:
                continue
            govde = m.group("govde")
            aile = alan(govde, "font-family").strip("'\"")
            stil = alan(govde, "font-style")
            agirlik = alan(govde, "font-weight")
            aralik = alan(govde, "unicode-range")
            url = re.search(r"url\((\S+?\.woff2)\)", govde).group(1)
            dosya = f"{aile.lower().replace(' ', '-')}-{agirlik}-{stil}-{subset}.woff2"
            (HEDEF / dosya).write_bytes(istemci.get(url).content)
            kurallar.append(
                "@font-face{font-family:'%s';font-style:%s;font-weight:%s;"
                "font-display:swap;src:url('%s') format('woff2');unicode-range:%s}"
                % (aile, stil, agirlik, dosya, aralik)
            )
            print(f"  {dosya}")
    (HEDEF / "fontlar.css").write_text("\n".join(kurallar) + "\n", encoding="utf-8")
    print(f"{len(kurallar)} yüz · fontlar.css yazıldı")


if __name__ == "__main__":
    main()
