#!/bin/zsh
# Havadis — sabah üretim görevi (yerel, token'sız).
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
  curl -sf -H "Priority: high" -H "Tags: rotating_light" \
    -d "Havadis üretilemedi: $1 ($(date '+%H:%M'))" \
    "https://ntfy.sh/${NTFY_TOPIC:-}" >/dev/null 2>&1 || true
}
trap 'alarm "beklenmedik hata — ~/Library/Logs/havadis-sabah.log"' ERR

git pull --rebase --autostash origin main || echo "uyarı: pull başarısız (çevrimdışı olabilir), yerelle devam"

PY="$KOK/.venv/bin/python"

"$PY" -m pipeline.fetch

# Editörlük: yerel Claude, headless. Bu script Terminal penceresinde koşar (launchd → open -a Terminal),
# böylece Keychain'deki abonelik kimliği erişilebilir olur — token üretmeye gerek kalmaz.
# Bekçi: editör 15 dakikada bitmezse durdurulur → mini sayı devreye girer; sabah asla bloke olmaz.
# Geçici API kopmaları (ör. "Connection closed mid-response") tek denemede mini sayıya
# düşürmesin: 3 deneme, başarı ölçütü validate'in yeşile dönmesi.
rm -f issue.json
DENEME=1
while [ "$DENEME" -le 3 ]; do
  echo "editör denemesi $DENEME/3 başlıyor ($(date '+%H:%M:%S'))"
  claude -p "EDITORIAL.md'yi oku ve aynen uygula: candidates.json'dan bugünün sayısını seç, issue.json'ı depo köküne yaz, 'python3 -m pipeline.validate' yeşil olana dek düzelt. Başka dosyaya dokunma; commit/push yapma." \
    --allowedTools "Read,Write,Edit,Bash(python3 -m pipeline.validate)" \
    --max-turns 40 &
  CLAUDE_PID=$!
  ( sleep 900; kill "$CLAUDE_PID" 2>/dev/null && echo "uyarı: editör 15 dk'da bitmedi, durduruldu" ) &
  BEKCI_PID=$!
  wait "$CLAUDE_PID" || echo "uyarı: editör denemesi $DENEME hata verdi"
  kill "$BEKCI_PID" 2>/dev/null || true
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
  claude -p "LUGAT.md'yi oku ve aynen uygula: veri/bugun.json'daki haberlerin dokunduğu lugat maddelerini güncelle ya da aç, 'python3 -m pipeline.lugat_dogrula' yeşil olana dek düzelt. Başka dosyaya dokunma; commit/push yapma." \
    --allowedTools "Read,Write,Edit,Bash(python3 -m pipeline.lugat_dogrula)" \
    --max-turns 30 &
  LUGAT_PID=$!
  ( sleep 600; kill "$LUGAT_PID" 2>/dev/null && echo "uyarı: lugat editörü 10 dk'da bitmedi, durduruldu" ) &
  LUGAT_BEKCI=$!
  LUGAT_TAMAM=1
  wait "$LUGAT_PID" || { echo "uyarı: lugat denemesi $LUGAT_DENEME hata verdi"; LUGAT_TAMAM=0; }
  kill "$LUGAT_BEKCI" 2>/dev/null || true
  [ "$LUGAT_TAMAM" -eq 1 ] && break
  LUGAT_DENEME=$((LUGAT_DENEME + 1))
  [ "$LUGAT_DENEME" -le 2 ] && sleep 30
done
if ! "$PY" -m pipeline.lugat_dogrula; then
  echo "uyarı: lugat doğrulaması geçmedi — bugünkü wiki değişiklikleri geri alınıyor"
  git checkout -- lugat/ 2>/dev/null || true
fi
"$PY" -m pipeline.lugat_render
"$PY" -m pipeline.kasa

git add site veri kasa lugat
git commit -m "Sayı: $(date '+%F')" || echo "değişiklik yok"
git push origin main   # push → GitHub Actions yalnızca Pages yayını yapar

"$PY" -m pipeline.notify
echo "✓ $(date '+%F %T') — sayı yayında"
