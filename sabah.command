#!/bin/zsh
# Havadis sabah görevi — Terminal penceresinde çalışır (Keychain erişimi için; token gerekmez).
# Pencere, iş temiz bitince kendiliğinden kapanır; hata olursa mesajla açık kalır.
echo "☕ Havadis dizgide… (log: ~/Library/Logs/havadis-sabah.log)"
/Users/yagmur/havadis/sabah.sh || { echo "⚠ Havadis sabah görevi hata verdi — loga bak."; sleep 45; }
exit 0
