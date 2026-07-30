#!/bin/zsh
# Havadis — sabah üretim görevi (LLM: OpenAI-uyumlu API'deki Kimi; ayarlar kökteki .env'de).
# launchd her sabah 06:47'de çalıştırır; Mac uykudaysa uyanınca telafi eder.
set -euo pipefail

KOK="/Users/yagmur/havadis"
cd "$KOK"
mkdir -p "$HOME/Library/Logs"
LOG="$HOME/Library/Logs/havadis-sabah.log"
exec >>"$LOG" 2>&1
echo "═══ $(date '+%F %T') — sabah koşusu başladı"

[ -f .sabah.env ] && source .sabah.env
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

alarm() {
  # Kimi'den tek satırlık arıza teşhisi iste (onarici asla alarmı engellemez; boş dönebilir)
  TESHIS="$("$PY" -m pipeline.onarici 2>/dev/null || true)"
  curl -sf -H "Priority: high" -H "Tags: rotating_light" \
    -d "Havadis üretilemedi: $1 ($(date '+%H:%M'))${TESHIS:+ · Teşhis: $TESHIS}" \
    "https://ntfy.sh/${NTFY_TOPIC:-}" >/dev/null 2>&1 || true
}
trap 'alarm "beklenmedik hata — ~/Library/Logs/havadis-sabah.log"' ERR

git pull --rebase --autostash origin main || echo "uyarı: pull başarısız (çevrimdışı olabilir), yerelle devam"

PY="$KOK/.venv/bin/python"

"$PY" -m pipeline.fetch

# Editörlük: OpenAI-uyumlu API'deki Kimi modeli, pipeline/editor.py üzerinden (ayarlar .env'de).
# Zaman aşımı ve model-düzeltme döngüsü editor.py'nin içindedir; Claude/Keychain gerekmez.
# Geçici API kopmaları tek denemede mini sayıya düşürmesin: 3 deneme,
# başarı ölçütü validate'in yeşile dönmesi.
rm -f issue.json
DENEME=1
while [ "$DENEME" -le 3 ]; do
  echo "editör denemesi $DENEME/3 başlıyor ($(date '+%H:%M:%S'))"
  "$PY" -m pipeline.editor || echo "uyarı: editör denemesi $DENEME hata verdi"
  if "$PY" -m pipeline.validate; then
    echo "editör denemesi $DENEME başarılı ✓"
    break
  fi
  DENEME=$((DENEME + 1))
  [ "$DENEME" -le 3 ] && { echo "45 sn bekleyip yeniden denenecek"; sleep 45; }
done

"$PY" -m pipeline.validate || "$PY" -m pipeline.fallback
"$PY" -m pipeline.gorseller || echo "uyarı: küpür görselleri çekilemedi (görselsiz devam)"
"$PY" -m pipeline.render
"$PY" -m pipeline.kulliyat

# Ansiklopedi: Lugat güncellemesi (başarısız olursa dergi etkilenmez; dünkü lugat kalır)
LUGAT_DENEME=1
while [ "$LUGAT_DENEME" -le 2 ]; do
  echo "lugat denemesi $LUGAT_DENEME/2 başlıyor ($(date '+%H:%M:%S'))"
  if "$PY" -m pipeline.lugat_editor; then
    break
  fi
  echo "uyarı: lugat denemesi $LUGAT_DENEME hata verdi"
  LUGAT_DENEME=$((LUGAT_DENEME + 1))
  [ "$LUGAT_DENEME" -le 2 ] && sleep 30
done
if ! "$PY" -m pipeline.lugat_dogrula; then
  echo "uyarı: lugat doğrulaması geçmedi — bugünkü wiki değişiklikleri geri alınıyor"
  git checkout -- lugat/ 2>/dev/null || true
fi
"$PY" -m pipeline.lugat_render

git add site veri lugat
git commit -m "Sayı: $(date '+%F')" || echo "değişiklik yok"
git push origin main   # push → GitHub Actions yalnızca Pages yayını yapar

"$PY" -m pipeline.notify
echo "✓ $(date '+%F %T') — sayı yayında"
