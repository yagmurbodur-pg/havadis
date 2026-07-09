#!/bin/zsh
# Havadis — sabah üretim görevi (yerel, token'sız).
# launchd her sabah 06:47'de çalıştırır; Mac uykudaysa uyanınca telafi eder.
set -euo pipefail

KOK="/Users/yagmur/Desktop/havadis"
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

# Editörlük: yerel Claude — mevcut abonelik oturumu, yeni anahtar gerekmez.
claude -p "EDITORIAL.md'yi oku ve aynen uygula: candidates.json'dan bugünün sayısını seç, issue.json'ı depo köküne yaz, 'python3 -m pipeline.validate' yeşil olana dek düzelt. Başka dosyaya dokunma; commit/push yapma." \
  --allowedTools "Read,Write,Edit,Bash(python3 -m pipeline.validate)" \
  --max-turns 40 || echo "uyarı: editör hata verdi; doğrulama/fallback devrede"

"$PY" -m pipeline.validate || "$PY" -m pipeline.fallback
"$PY" -m pipeline.render
"$PY" -m pipeline.kulliyat
"$PY" -m pipeline.kasa

git add site veri kasa
git commit -m "Sayı: $(date '+%F')" || echo "değişiklik yok"
git push origin main   # push → GitHub Actions yalnızca Pages yayını yapar

"$PY" -m pipeline.notify
echo "✓ $(date '+%F %T') — sayı yayında"
