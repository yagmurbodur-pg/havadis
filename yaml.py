"""GEÇİCİ ŞİM — SİLİNEBİLİR: `rm yaml.py` (repo kökünde).

pipeline.lugat_dogrula'nın `import yaml` ihtiyacı için kondu: sistem
Python'unda PyYAML yok ve bu oturumda kurulamadı/silinemedi. Repo kökünden
`python -m ...` çalıştırıldığında bu dosya gerçek PyYAML'i gölgelememek için
önce sys.path'te (ör. .venv) gerçek PyYAML'i arar ve bulursa ona devreder.
Bulamazsa, lugat frontmatter'larının kullandığı düz YAML alt kümesini
(key: value, tırnaklı dizge, tek satır liste, satır sonu yorumu) çözen
yedek çözümleyici devreye girer; beklenmedik her yapıda YAMLError fırlatır.
"""
import importlib.util as _iu
import os as _os
import sys as _sys


def _gercek_pyyaml():
    burasi = _os.path.dirname(_os.path.abspath(__file__))
    for kok in _sys.path:
        kok_abs = _os.path.abspath(kok or _os.getcwd())
        if kok_abs == burasi:
            continue
        aday = _os.path.join(kok_abs, "yaml", "__init__.py")
        if _os.path.exists(aday):
            spec = _iu.spec_from_file_location(
                "yaml", aday, submodule_search_locations=[_os.path.dirname(aday)]
            )
            mod = _iu.module_from_spec(spec)
            _sys.modules["yaml"] = mod
            spec.loader.exec_module(mod)
            return mod
    return None


_gercek = _gercek_pyyaml()
if _gercek is not None:
    globals().update(_gercek.__dict__)
else:

    class YAMLError(Exception):
        pass

    def _strip_comment(deger):
        # Düz skalerde ' #' sonrası yorumdur; tırnaklılar burada gelmez.
        for i, ch in enumerate(deger):
            if ch == "#" and (i == 0 or deger[i - 1] in " \t"):
                return deger[:i].rstrip()
        return deger

    def _parse_scalar(deger):
        deger = deger.strip()
        if deger == "":
            return None
        if deger[0] in "\"'":
            tirnak = deger[0]
            kapanis = deger.find(tirnak, 1)
            if kapanis == -1:
                raise YAMLError("kapanmamış tırnak: %r" % deger)
            kalan = deger[kapanis + 1 :].strip()
            if kalan and not kalan.startswith("#"):
                raise YAMLError("tırnak sonrası beklenmedik içerik: %r" % deger)
            return deger[1:kapanis]
        deger = _strip_comment(deger)
        if deger.startswith("[") or deger.startswith("{"):
            raise YAMLError("beklenmedik yapı: %r" % deger)
        if deger == "":
            return None
        return deger

    def _parse_value(deger):
        deger = deger.strip()
        if deger == "":
            return None
        if deger.startswith("["):
            govde = _strip_comment(deger)
            if not govde.endswith("]"):
                raise YAMLError("kapanmamış liste: %r" % deger)
            ic = govde[1:-1].strip()
            if not ic:
                return []
            if "[" in ic or "]" in ic or '"' in ic or "'" in ic:
                raise YAMLError("desteklenmeyen liste içeriği: %r" % deger)
            return [p.strip() for p in ic.split(",")]
        return _parse_scalar(deger)

    def safe_load(metin):
        if metin is None:
            return None
        sonuc = {}
        for satir in metin.splitlines():
            if not satir.strip() or satir.lstrip().startswith("#"):
                continue
            if satir[0] in " \t":
                raise YAMLError("girintili/çok satırlı yapı desteklenmiyor: %r" % satir)
            if ":" not in satir:
                raise YAMLError("anahtar:değer beklenirdi: %r" % satir)
            anahtar, _, deger = satir.partition(":")
            sonuc[anahtar.strip()] = _parse_value(deger)
        return sonuc or None
