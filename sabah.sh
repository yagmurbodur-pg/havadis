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
claude -p "EDITORIAL.md'yi oku ve aynen uygula: candidates.json'dan bugünün sayısını seç, issue.json'ı depo köküne yaz, 'python3 -m pipeline.validate' yeşil olana dek düzelt. Başka dosyaya dokunma; commit/push yapma." \
  --allowedTools "Read,Write,Edit,Bash(python3 -m pipeline.validate)" \
  --max-turns 40 &
CLAUDE_PID=$!
( sleep 900; kill "$CLAUDE_PID" 2>/dev/null && echo "uyarı: editör 15 dk'da bitmedi, durduruldu" ) &
BEKCI_PID=$!
wait "$CLAUDE_PID" || echo "uyarı: editör hata verdi; doğrulama/fallback devrede"
kill "$BEKCI_PID" 2>/dev/null || true

"$PY" -m pipeline.validate || "$PY" -m pipeline.fallback
"$PY" -m pipeline.render
"$PY" -m pipeline.kulliyat

# Ansiklopedi: Lugat güncellemesi (başarısız olursa dergi etkilenmez; dünkü lugat kalır)
claude -p "LUGAT.md'yi oku ve aynen uygula: veri/bugun.json'daki haberlerin dokunduğu lugat maddelerini güncelle ya da aç, 'python3 -m pipeline.lugat_dogrula' yeşil olana dek düzelt. Başka dosyaya dokunma; commit/push yapma." \
  --allowedTools "Read,Write,Edit,Bash(python3 -m pipeline.lugat_dogrula)" \
  --max-turns 30 &
LUGAT_PID=$!
( sleep 600; kill "$LUGAT_PID" 2>/dev/null && echo "uyarı: lugat editörü 10 dk'da bitmedi, durduruldu" ) &
LUGAT_BEKCI=$!
wait "$LUGAT_PID" || echo "uyarı: lugat editörü hata verdi"
kill "$LUGAT_BEKCI" 2>/dev/null || true
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
