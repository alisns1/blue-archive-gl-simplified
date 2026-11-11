"""Locate and rewrite the CRC32 of the ``ExcelDB.db`` entry inside ``TableCatalog.bytes``.

Why this is needed
------------------
The client verifies each resource file against the CRC32 recorded in the local
``TableCatalog.bytes``.  We changed the database, so its CRC32 changed; unless we also
update the catalog the client treats the file as corrupt and re-downloads it.

Entry layout
------------
    i32 keylen + key string      ("ExcelDB.db")
    i8, i32
    i32 namelen + name string
    i64 crc32                    <-- this is what we rewrite (upper 4 bytes are 0)
    bool
    i32 includes                 (-1 == none)

Note: the **Global** catalog stores only a CRC (no file size).  The Japanese catalog has
an extra size field - do not reuse a JP parser here.

Provenance
----------
The field layout above was derived from `assistance/patch_table_catalog.py` in
asfu222/BlueArchiveLocalizationTools (MIT License, Copyright (c) 2025 anon).
This file is an independent implementation: it locates the entry by searching for the
key string and validating the offset, instead of parsing the whole catalog sequentially.
See THIRD_PARTY.md.

All messages are ASCII on purpose: this tool is run from cmd.exe / PowerShell where
non-ASCII output gets mangled by the console code page.
"""
import argparse
import binascii
import struct


def crc32_file(path):
    crc = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            crc = binascii.crc32(b, crc)
    return crc & 0xFFFFFFFF


def find_entries(data, needle=b"ExcelDB.db"):
    """Locate candidate entries: length-prefixed key -> name -> i64 CRC."""
    out = []
    idx = 0
    while True:
        i = data.find(needle, idx)
        if i < 0:
            break
        idx = i + 1
        if i < 4:
            continue
        keylen = struct.unpack("<i", data[i - 4:i])[0]
        if keylen != len(needle):
            continue
        p = i + len(needle)
        p += 1 + 4                                   # i8, i32
        if p + 4 > len(data):
            continue
        namelen = struct.unpack("<i", data[p:p + 4])[0]
        if namelen < 0 or namelen > 200 or p + 4 + namelen + 8 > len(data):
            continue
        p += 4
        name = data[p:p + namelen].decode("utf-8", "replace")
        p += namelen
        crc_pos = p
        crc = struct.unpack("<q", data[p:p + 8])[0]
        out.append(dict(name=name, crc=crc & 0xFFFFFFFF, crc_pos=crc_pos))
    return out


def main():
    ap = argparse.ArgumentParser(description="Patch the ExcelDB.db CRC32 in TableCatalog.bytes")
    ap.add_argument("--catalog", required=True, help="TableCatalog.bytes pulled from the device")
    ap.add_argument("--db", required=True, help="the converted database (its CRC32 is written)")
    ap.add_argument("--out", required=True, help="patched catalog to write")
    ap.add_argument("--expect-crc", default="", help="old CRC32 in hex, used to confirm the entry")
    ap.add_argument("--expect-crc-db", default="", help="compute --expect-crc from this file")
    ap.add_argument("--list-only", action="store_true")
    args = ap.parse_args()

    if args.expect_crc_db:
        args.expect_crc = "%08X" % crc32_file(args.expect_crc_db)
    expect = int(args.expect_crc, 16) if args.expect_crc else None

    data = bytearray(open(args.catalog, "rb").read())
    entries = find_entries(data)
    print("catalog: %d bytes, %d candidate entry/entries" % (len(data), len(entries)))
    for e in entries:
        mark = "   <== this one (CRC matches the original db)" if (expect is not None and e["crc"] == expect) else ""
        print("  name=%-16s crc=0x%08X @%d%s" % (repr(e["name"]), e["crc"], e["crc_pos"], mark))

    if args.list_only:
        return 0

    new_crc = crc32_file(args.db)
    print("new database: %s" % args.db)
    print("  crc32 = 0x%08X" % new_crc)

    target = None
    for e in entries:
        if expect is not None and e["crc"] == expect:
            target = e
            break
    if target is None and entries:
        target = entries[0]
    if target is None:
        print("ERROR: could not locate the ExcelDB.db entry")
        return 1

    struct.pack_into("<q", data, target["crc_pos"], new_crc)
    open(args.out, "wb").write(bytes(data))
    print("wrote %s" % args.out)

    check = find_entries(bytearray(open(args.out, "rb").read()))
    for e in check:
        if e["crc_pos"] == target["crc_pos"]:
            status = "OK" if e["crc"] == new_crc else "MISMATCH"
            print("verify: crc=0x%08X (expected 0x%08X)  %s" % (e["crc"], new_crc, status))
            if e["crc"] != new_crc:
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
