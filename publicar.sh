#!/usr/bin/env bash
# Genera la web y sube publico/ a la rama gh-pages, que es la que sirve
# GitHub Pages. El código fuente va aparte, en main, con git normal.
set -euo pipefail
cd "$(dirname "$0")"
python3 generar.py
remoto=$(git remote get-url origin)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
cp -r publico/. "$tmp/"
cd "$tmp"
git init -q -b gh-pages
git add -A
git -c user.name="$(git -C "$OLDPWD" config user.name)" -c user.email="$(git -C "$OLDPWD" config user.email)" \
  commit -q -m "Web generada el $(date +%d/%m/%Y\ %H:%M)"
git push -q --force "$remoto" gh-pages
echo "Publicada en la rama gh-pages de $remoto"
