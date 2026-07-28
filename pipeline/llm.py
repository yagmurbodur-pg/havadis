"""OpenAI-uyumlu LLM istemcisi — Havadis'in tüm model çağrıları buradan geçer.

Ayarlar kök dizindeki .env dosyasından (ya da ortamdan) gelir:
  OPENAI_BASE_URL · OPENAI_API_KEY · OPENAI_MODEL
Model düşünen (reasoning) bir modeldir; yanıttan önce görünmeyen akıl yürütme
token'ları harcadığından max_tokens cömert tutulur. Uçtaki vekil (proxy) JSON
çıktısının başına bozuk parça yapıştırabildiğinden json_ayikla körlemesine
json.loads yerine metindeki en uzun DENGELİ nesneyi arar.
"""
import json
import os
import re
import time
from pathlib import Path

import httpx

KOK = Path(__file__).resolve().parent.parent


def _env_yukle():
    """Kökteki .env'i ortama yükler; ortamda zaten tanımlı olan değişmez."""
    yol = KOK / ".env"
    if not yol.exists():
        return
    for satir in yol.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#") or "=" not in satir:
            continue
        anahtar, deger = satir.split("=", 1)
        os.environ.setdefault(anahtar.strip(), deger.strip())


def ayarlar():
    _env_yukle()
    taban = (os.environ.get("OPENAI_BASE_URL") or "").rstrip("/")
    anahtar = os.environ.get("OPENAI_API_KEY") or ""
    model = os.environ.get("OPENAI_MODEL") or "qwen"
    if not taban or not anahtar or anahtar.startswith("BURAYA"):
        raise RuntimeError(
            ".env eksik: OPENAI_BASE_URL ve OPENAI_API_KEY tanımlı olmalı (kökteki .env dosyası)."
        )
    return taban, anahtar, model


def sohbet(mesajlar, json_modu=False, max_tokens=16384, zaman_asimi=600, deneme=3):
    """Tek chat tamamlaması; ağ/boş-yanıt hatasında artan beklemeyle yeniden dener."""
    taban, anahtar, model = ayarlar()
    govde = {"model": model, "messages": mesajlar, "max_tokens": max_tokens}
    if json_modu:
        govde["response_format"] = {"type": "json_object"}
    son_hata = None
    for i in range(deneme):
        try:
            yanit = httpx.post(
                f"{taban}/chat/completions",
                headers={"Authorization": f"Bearer {anahtar}"},
                json=govde,
                timeout=zaman_asimi,
            )
            yanit.raise_for_status()
            icerik = (yanit.json()["choices"][0]["message"].get("content") or "").strip()
            if icerik:
                return icerik
            son_hata = RuntimeError("model boş yanıt döndürdü")
        except Exception as hata:  # ağ, HTTP, beklenmedik şema — hepsi yeniden denenir
            son_hata = hata
        if i < deneme - 1:
            time.sleep(15 * (i + 1))
    raise RuntimeError(f"LLM yanıtı alınamadı ({deneme} deneme): {son_hata}")


_CIT = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def json_ayikla(metin):
    """Metindeki en uzun DENGELİ JSON nesnesini döndürür.

    Markdown çiti, modelin açıklama cümleleri ya da vekilin başa yapıştırdığı
    bozuk parça ('{"a{"a": 1}' gözlendi) düz json.loads'u kırar. Burada her '{'
    konumunda gerçek bir çözümleme denenir; en çok karakteri kapsayan nesne
    kazanır (kırık dış nesnenin içindeki küçük parça yerine tam sayı seçilir).
    """
    adaylar = [c.strip() for c in _CIT.findall(metin)]
    adaylar.append(metin)
    cozucu = json.JSONDecoder()
    en_iyi, en_uzun = None, -1
    for parca in adaylar:
        for i, karakter in enumerate(parca):
            if karakter != "{":
                continue
            try:
                nesne, son = cozucu.raw_decode(parca[i:])
            except json.JSONDecodeError:
                continue
            if isinstance(nesne, dict) and son > en_uzun:
                en_iyi, en_uzun = nesne, son
        if en_iyi is not None:
            break  # çitli aday başarılıysa ham metne bakmaya gerek yok
    if en_iyi is None:
        raise ValueError("yanıtta geçerli bir JSON nesnesi bulunamadı")
    return en_iyi
