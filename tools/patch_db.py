#!/usr/bin/env python3
"""Convert the Traditional Chinese text inside Blue Archive GL's ExcelDB.db to Simplified.

How it works
------------
The game stores its table data in a SQLCipher-encrypted SQLite database
(``ExcelDB.db``).  Every table has the shape ``(<key> INTEGER, Bytes BLOB)`` and each
``Bytes`` value is a FlatBuffer holding the table rows.

We do **equal-length byte substitution** inside those blobs:

* Traditional -> Simplified is almost always a 3-byte UTF-8 CJK swap
  (學園 -> 学院, 檔案 -> 档案, ...).
* Keeping the byte length identical means every offset / length field inside the
  FlatBuffer stays valid, so the structure can never be corrupted.

Runs that would change length are handled character by character, and characters whose
mapping is not length-preserving are simply left alone.

Usage
-----
    python patch_db.py --in ExcelDB.db --out ExcelDB.cn.db
    python patch_db.py --in ExcelDB.db --out ExcelDB.cn.db --dry-run
    python patch_db.py --in ExcelDB.db --out ExcelDB.cn.db --only 'Localize|Dialog'

Provenance / credits
--------------------
* The SQLCipher *interface* parameters (page size 4096, KDF iterations 256000,
  HMAC-SHA512, 80-byte reserve) were confirmed against the community toolchain
  (BlueArchive-Tools, AGPL-3.0) — reference only, **no code from it is used here**.
  Database access is delegated entirely to the independent `sqlcipher3` package.
* The default key is a publicly circulated value, shipped as an overridable default.
* The Traditional->Simplified character mapping comes from the OpenCC dictionaries
  (Apache-2.0, see `dict/`); the blob-walking logic in this file is original.
See THIRD_PARTY.md for the full notice list.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Allow running straight from a checkout that bundles the wheels in ../libs.
_BUNDLED = os.path.join(os.path.dirname(HERE), "libs")
if os.path.isdir(_BUNDLED):
    sys.path.insert(0, _BUNDLED)

import sqlcipher3 as sqlite3  # noqa: E402  (SQLCipher build of sqlite3)

from t2s import Converter  # noqa: E402

# Publicly known key for Blue Archive GL (identical on PC and Android).
# Override with --key if your client/region uses another one.
DEFAULT_KEY = "05f508236ff3dc4e5dc7cb6fcea0ede0d90a89753dc5e5d36c30393e9b072f48"

# Tables whose blobs can contain player-visible text.
DEFAULT_TABLE_PATTERN = r"Localize|Dialog|Scenario|Subtitle|Talk|Mail|Name|Emoji|Voice"


def is_cjk3(b: bytes, i: int, n: int) -> bool:
    """True if a 3-byte UTF-8 CJK ideograph starts at i (U+4E00..U+9FFF range)."""
    return (i + 2 < n and 0xE4 <= b[i] <= 0xE9
            and (b[i + 1] & 0xC0) == 0x80 and (b[i + 2] & 0xC0) == 0x80)


def convert_blob(blob: bytes, conv) -> tuple[bytes | None, int]:
    """Return (new_blob_or_None, number_of_changed_characters)."""
    b = bytearray(blob)
    n = len(b)
    changed = 0
    i = 0
    while i < n:
        if not is_cjk3(b, i, n):
            i += 1
            continue

        # collect a maximal run of 3-byte CJK characters
        j = i
        run = bytearray()
        while is_cjk3(b, j, n):
            run += b[j:j + 3]
            j += 3

        try:
            text = run.decode("utf-8")
        except UnicodeDecodeError:
            i = j
            continue

        new_bytes = conv.convert(text).encode("utf-8")
        if len(new_bytes) == len(run):
            if new_bytes != bytes(run):
                b[i:j] = new_bytes
                changed += sum(1 for a, c in zip(text, new_bytes.decode("utf-8")) if a != c)
        else:
            # Fall back to per-character substitution (still length preserving).
            pos = i
            for ch in text:
                old = ch.encode("utf-8")
                new = conv.convert(ch).encode("utf-8")
                if len(new) == len(old) and new != old:
                    b[pos:pos + len(old)] = new
                    changed += 1
                pos += len(old)
        i = j

    return (bytes(b) if changed else None), changed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="src", required=True, help="original ExcelDB.db")
    ap.add_argument("--out", dest="dst", required=True, help="output (converted) database")
    ap.add_argument("--key", default=DEFAULT_KEY, help="32-byte SQLCipher key as hex")
    ap.add_argument("--mode", default="tw2sp", choices=["tw2sp", "t2s"],
                    help="tw2sp also rewrites Taiwan vocabulary (網路->网络 -> 网络)")
    ap.add_argument("--only", default=None, help="regex limiting which tables to touch")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change without writing anything")
    args = ap.parse_args()

    if not os.path.exists(args.src):
        print(f"input not found: {args.src}")
        return 1

    conv = Converter(args.mode)
    print(f"mode={args.mode}  phrases={len(conv.phrases)}  chars={len(conv.chars)}")

    if args.dry_run:
        target = args.dst + ".dryrun"
    else:
        target = args.dst
    shutil.copy2(args.src, target)

    con = sqlite3.connect(target)
    cur = con.cursor()
    cur.execute(f"PRAGMA key = \"x'{args.key}'\"")
    try:
        cur.execute("SELECT count(*) FROM sqlite_master")
    except Exception as exc:                                  # pragma: no cover
        print(f"could not open database (wrong key?): {exc}")
        return 1

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    pat = re.compile(args.only or DEFAULT_TABLE_PATTERN, re.I)
    todo = [t for t in tables if pat.search(t)]
    print(f"tables={len(tables)}  text tables matched={len(todo)}")

    rows_seen = rows_hit = chars_hit = 0
    for table in todo:
        try:
            cur.execute(f"SELECT rowid, Bytes FROM [{table}]")   # rowid: key column names differ per table
            rows = cur.fetchall()
        except Exception as exc:
            print(f"  [{table}] skipped: {exc}")
            continue

        updates = []
        t_chars = 0
        for rid, blob in rows:
            if not isinstance(blob, (bytes, bytearray)) or len(blob) < 16:
                continue
            new_blob, nchars = convert_blob(bytes(blob), conv)
            if new_blob is not None:
                updates.append((new_blob, rid))
                rows_hit += 1
                t_chars += nchars
        chars_hit += t_chars
        if updates and not args.dry_run:
            cur.executemany(f"UPDATE [{table}] SET Bytes=? WHERE rowid=?", updates)
            con.commit()
        if updates:
            print(f"  [{table}] rows={len(rows)} changed={len(updates)} chars={t_chars}")
        rows_seen += len(rows)

    con.close()
    print()
    print(f"{'[dry-run] ' if args.dry_run else ''}rows scanned={rows_seen} rows changed={rows_hit} chars={chars_hit}")
    print(f"output: {target} ({os.path.getsize(target) / 1048576:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
