#!/usr/bin/env bash
# Buduje aplikacja/index.html ze zrodel.
# CALLNUM=+48XXXXXXXXX ./build/build.sh  -> wersja testowa (dzwoni na podany numer, zolty pasek TEST)
# ./build/build.sh                       -> wersja docelowa (dzwoni na 112)
set -e
cd "$(dirname "$0")/.."
python3 build/newjs.py >/dev/null
OUT=../aplikacja/index.html
if [ -n "${CALLNUM:-}" ]; then
  sed -i "s#tel:112#tel:${CALLNUM}#g; s#class=\"gtest\" hidden#class=\"gtest\"#" "$OUT"
fi
echo "Zbudowano $OUT ($(wc -c <"$OUT") B), linki tel: $(grep -o 'tel:[0-9+]*' "$OUT" | sort -u | tr '\n' ' ')"
