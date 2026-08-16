#!/usr/bin/env bash
#
# Publie site/ sur la branche gh-pages, en un commit unique.
#
#   uv run sudoku export --par-niveau 2000 --seed 42 -o out/banque.json
#   uv run python tools/publish.py out/banque.json
#   tools/deploy.sh
#
# La banque n'est pas versionnée sur main : cinq mégaoctets de JSON généré à
# chaque régénération resteraient dans l'historique pour toujours. Elle part
# donc directement sur la branche de publication, dont l'historique est écrasé
# à chaque fois — un commit, jamais deux, et un dépôt qui ne gonfle pas.

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f site/banque/index.json ]; then
  echo "Banque absente : lancer d'abord tools/publish.py." >&2
  exit 1
fi

remote=$(git remote get-url origin)
grids=$(find site/banque -name 'n*-[0-9][0-9][0-9].json' | wc -l | tr -d ' ')
generated=$(python3 -c 'import json; print(json.load(open("site/banque/index.json"))["generated"])')
author=$(git config user.name || echo "sudoku-generator")
mail=$(git config user.email || echo "noreply@localhost")

echo "Publication de $(du -sh site/banque | cut -f1) de banque ($grids paquets) vers $remote"
read -r -p "Écraser la branche gh-pages ? [o/N] " reply
[ "$reply" = "o" ] || { echo "Abandon."; exit 1; }

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

cp -R site/. "$work/"
# Ni les tests ni le manifeste Node n'ont à être servis.
rm -rf "$work/tests" "$work/package.json"
# Dit à Pages de servir les fichiers tels quels, sans passer par Jekyll.
touch "$work/.nojekyll"

git -C "$work" init -q -b gh-pages
git -C "$work" add -A
git -C "$work" -c user.name="$author" -c user.email="$mail" \
  commit -q -m "Site du $(date +%F), banque du $generated"
git -C "$work" push -q --force "$remote" gh-pages

echo "Publié. Régler Pages sur la branche gh-pages, racine /."
