#!/usr/bin/env bash
# Blue Archive GL: Traditional Chinese -> Simplified Chinese, on-device (Linux / macOS / WSL).
#
# Usage:
#   ./localize_phone.sh                 # auto-pick the first non-emulator device
#   ./localize_phone.sh <serial>        # target a specific device
#   DRY_RUN=1 ./localize_phone.sh       # pull + convert + patch catalog, do not push
#   BA_KEY=<hex> ./localize_phone.sh    # override the SQLCipher key
#
# Requirements: adb in PATH, python3 with `pip install -r requirements.txt`.
set -euo pipefail

PKG=com.nexon.bluearchive
BASE="/sdcard/Android/data/$PKG/files/PUB/Resource"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$ROOT/work"
ADB="${ADB:-adb}"
PY="${PYTHON:-python3}"
DRY_RUN="${DRY_RUN:-0}"

command -v "$ADB" >/dev/null || { echo "!! adb not found in PATH"; exit 1; }
command -v "$PY"  >/dev/null || { echo "!! python3 not found in PATH"; exit 1; }

echo "=== locating device ==="
"$ADB" start-server >/dev/null 2>&1 || true
mapfile -t DEVICES < <("$ADB" devices | awk '$2=="device"{print $1}')
if [ "${1:-}" != "" ]; then
    DEV="$1"
    printf '%s\n' "${DEVICES[@]:-}" | grep -qx "$DEV" || { echo "!! device '$DEV' not found"; exit 1; }
else
    DEV=""
    for d in "${DEVICES[@]:-}"; do
        case "$d" in emulator-*) continue;; esac
        DEV="$d"; break
    done
    [ -n "$DEV" ] || DEV="${DEVICES[0]:-}"
fi
[ -n "$DEV" ] || { echo "!! no device connected (enable USB debugging)"; exit 1; }
echo "  [ok] device = $DEV"

mkdir -p "$WORK"
ORIG_DB="$WORK/ExcelDB.orig.db"
ORIG_CAT="$WORK/TableCatalog.orig.bytes"
CN_DB="$WORK/ExcelDB.cn.db"
CN_CAT="$WORK/TableCatalog.cn.bytes"

echo "=== stopping the game and pulling the current files (backup kept) ==="
"$ADB" -s "$DEV" shell "am force-stop $PKG" >/dev/null 2>&1 || true
"$ADB" -s "$DEV" pull "$BASE/Preload/TableBundles/ExcelDB.db" "$ORIG_DB"
"$ADB" -s "$DEV" pull "$BASE/Catalog/TableBundles/TableCatalog.bytes" "$ORIG_CAT"

echo "=== converting Traditional -> Simplified ==="
KEY_ARGS=()
[ -n "${BA_KEY:-}" ] && KEY_ARGS=(--key "$BA_KEY")
"$PY" -u "$ROOT/tools/patch_db.py" --in "$ORIG_DB" --out "$CN_DB" "${KEY_ARGS[@]}"

echo "=== patching the catalog CRC32 ==="
"$PY" -u "$ROOT/tools/patch_catalog.py" --catalog "$ORIG_CAT" --db "$CN_DB" \
      --out "$CN_CAT" --expect-crc-db "$ORIG_DB"

if [ "$DRY_RUN" != "0" ]; then
    echo "=== dry run: nothing pushed ==="
    exit 0
fi

echo "=== pushing the patched files back ==="
"$ADB" -s "$DEV" push "$CN_DB" "$BASE/Preload/TableBundles/ExcelDB.db"
"$ADB" -s "$DEV" push "$CN_CAT" "$BASE/Catalog/TableBundles/TableCatalog.bytes"

cat <<EOF

=== done ===
Launch the game; the UI and story text should now be Simplified Chinese.

Notes:
  * Re-run after every game update (the database changes).
  * Do not use the in-game repair / redownload button; it restores the original files.
  * Original files are backed up in: $WORK
EOF
