#!/bin/bash
# Daily on the Mac Mini: refresh Land Registry sales and publish if anything changed.
cd "$(dirname "$0")" || exit 1
git pull -q --rebase || exit 1
/opt/homebrew/bin/python3.11 update.py || exit 1
if [ -n "$(git status --porcelain data/)" ]; then
  git add data/sales.json
  git commit -q -m "Land Registry sales $(date +%F)"
  git push -q
fi
