#!/usr/bin/env python3
"""Replace the CJK font assets inside Blue Archive GL's UI bundle.

Why this is needed
------------------
The Global Android build renders all UI text with two built-in fonts whose names say
"TC" but which are used for every language: ``NotoSansTC-Medium`` and
``NotoSansTC-Bold``.  Their cmap covers only ~20,748 characters, so many simplified-only
glyphs (U+5385, U+89C8, U+7F16, U+8D2D, U+8F89, U+529E, ...) are missing.  The engine then
falls back to a system
font per missing glyph, and the mixed fonts make some characters look thinner or smaller
than their neighbours.

The fix is to swap the ``m_FontData`` of those two ``Font`` assets for a Simplified
Chinese font (Noto Sans SC), keeping the asset name and PathID unchanged, then
restore the bundle's original CRC32.

Three things must be right, or the game will silently ignore the patch:

1. ``env.save(pack="original")``.  The default ``pack="lz4"`` rewrites the header flags
   from ``0x243`` to ``0xC2`` and the game refuses to load the bundle.
2. Restore the original file CRC32.  The Addressables catalog stores a hash per bundle;
   a changed CRC makes the client consider the file stale and re-download it, which looks
   exactly like "the patch did nothing".
3. The bundle is looked up under ``Preload/Android/``, and its file name contains a build
   date and a hash, so it changes with every game update.  Use ``--find`` to locate it
   again instead of hard-coding a name.

Usage
-----
    python tools/patch_font.py --find "<...>/Preload/Android"
    python tools/patch_font.py --bundle <original.bundle> \\
        --regular NotoSansSC-Regular.otf --bold NotoSansSC-Bold.otf \\
        --out <patched.bundle>
    python tools/patch_font.py --bundle ... --regular ... --bold ... --out ... --dry-run

Run ``--find`` first: it scans ``*.bundle`` files for the plaintext ``NotoSansTC``
container name and prints the one bundle that owns the fonts.  If exactly one match is
found it is used automatically, so ``--find`` can replace ``--bundle`` in the command
above.

Requirements
------------
UnityPy **1.25.2**.  1.25.4 depends on ``tpk_ar`` (sdist only, needs Rust) and does not
install on a normal machine::

    pip install UnityPy==1.25.2

A copy under ``../libs`` (git-ignored) is picked up automatically if present.

Output is ASCII only on purpose: this tool is run from cmd.exe / PowerShell where
non-ASCII output gets mangled by the console code page.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import random
import shutil
import struct
import sys
import tempfile
import uuid
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Allow running straight from a checkout that bundles the wheels in ../libs.
_BUNDLED = os.path.join(os.path.dirname(HERE), "libs")
if os.path.isdir(_BUNDLED):
    sys.path.insert(0, _BUNDLED)

# Asset name -> which --regular/--bold font replaces it.
FONT_MAP = {
    "NotoSansTC-Medium": "regular",
    "NotoSansTC-Bold": "bold",
}
FONT_ASSET_NEEDLE = b"NotoSansTC"
UNITYPY_WANTED = "1.25.2"
BUNDLE_SUFFIX = ".bundle"


# --------------------------------------------------------------------------- helpers
def show(value) -> str:
    """Return a path/string that is safe to print on an ASCII-only console."""
    return str(value).encode("ascii", "backslashreplace").decode("ascii")


def fail(message: str) -> "NoReturn":  # noqa: F821 - typing only
    print("ERROR: " + message)
    raise SystemExit(1)


def crc32_bytes(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def crc32_file(path: str) -> int:
    crc = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            crc = zlib.crc32(chunk, crc)
    return crc & 0xFFFFFFFF


def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------- UnityFS header
def parse_header(data: bytes) -> tuple[int, int, int]:
    """Return (offset_of_size_field, declared_size, flags).

    UnityFS layout::

        "UnityFS\\0"          8-byte cstring signature (NOT 16 bytes)
        u32                   format version
        cstring               unity player version
        cstring               unity engine version
        i64                   total bundle size   <- rewritten after appending CRC
        u32                   compressed blocks-info size
        u32                   uncompressed blocks-info size
        u32                   flags
    """
    if not data.startswith(b"UnityFS\x00"):
        fail("not a UnityFS bundle (signature=%s)" % data[:8].hex())
    pos = 8 + 4  # signature + format version
    try:
        pos = data.index(b"\x00", pos) + 1  # player version
        pos = data.index(b"\x00", pos) + 1  # engine version
    except ValueError:
        fail("truncated UnityFS header")
    if pos + 8 > len(data):
        fail("truncated UnityFS header")
    size = struct.unpack_from(">q", data, pos)[0]
    flags_pos = pos + 8 + 4 + 4
    flags = struct.unpack_from(">I", data, flags_pos)[0] if flags_pos + 4 <= len(data) else 0
    return pos, size, flags


# ------------------------------------------------------------------- CRC32 restore
def _crc_append4(data: bytes, target: int) -> bytes:
    """Return 4 bytes x such that crc32(data || x) == target.

    CRC32 is affine over GF(2).  For a fixed prefix the map
    ``x (32 bits) -> crc32(data || x)`` is affine, so we build 32 column vectors
    (one per bit of x) and solve the resulting 32x32 linear system by Gaussian
    elimination.  zlib accepts a starting state, so each column is O(1) instead of
    re-hashing the whole bundle 32 times.
    """
    state = crc32_bytes(data)
    zero = zlib.crc32(b"\x00\x00\x00\x00", state) & 0xFFFFFFFF
    diff = target ^ zero

    basis: dict[int, tuple[int, int]] = {}  # pivot bit -> (vector, solution mask)
    for i in range(32):
        vec = (zlib.crc32((1 << i).to_bytes(4, "big"), state) & 0xFFFFFFFF) ^ zero
        mask = 1 << i
        while vec:
            pivot = vec.bit_length() - 1
            if pivot in basis:
                bvec, bmask = basis[pivot]
                vec ^= bvec
                mask ^= bmask
            else:
                basis[pivot] = (vec, mask)
                vec = 0
    if len(basis) != 32:  # pragma: no cover - the map is invertible in practice
        fail("CRC32 linear system is singular (cannot restore this CRC)")

    rest = diff
    solution = 0
    while rest:
        pivot = rest.bit_length() - 1
        if pivot not in basis:  # pragma: no cover
            fail("CRC32 target is not reachable for this file")
        bvec, bmask = basis[pivot]
        rest ^= bvec
        solution ^= bmask

    suffix = solution.to_bytes(4, "big")
    if (zlib.crc32(suffix, state) & 0xFFFFFFFF) != target:  # pragma: no cover
        fail("internal CRC32 solver error")
    return suffix


def crc_self_test() -> int:
    """Solve a handful of random targets before touching real data."""
    rng = random.Random(0xC0FFEE)
    cases = 0
    for length in (0, 1, 7, 64, 4096, 100000):
        data = bytes(rng.getrandbits(8) for _ in range(length))
        target = rng.getrandbits(32)
        out = data + _crc_append4(data, target)
        if len(out) != length + 4 or out[:length] != data or crc32_bytes(out) != target:
            fail("CRC32 self-test failed at length %d" % length)
        cases += 1
    # "copy the CRC of an unrelated blob" - the realistic shape of the real job
    a = bytes(rng.getrandbits(8) for _ in range(1024))
    b = bytes(rng.getrandbits(8) for _ in range(2048))
    out = a + _crc_append4(a, crc32_bytes(b))
    if crc32_bytes(out) != crc32_bytes(b):
        fail("CRC32 self-test failed on borrowed target")
    cases += 1
    print("crc32 self-test: OK (%d cases)" % cases)
    return cases


# ------------------------------------------------------------------- font / bundle io
def read_font(path: str, label: str) -> bytes:
    if not os.path.isfile(path):
        fail("%s font not found: %s" % (label, show(path)))
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 1024:
        fail("%s font looks too small (%d bytes): %s" % (label, len(data), show(path)))
    magic = data[:4]
    if magic not in (b"OTTO", b"\x00\x01\x00\x00", b"true", b"ttcf"):
        print("WARNING: %s font does not start with a known sfnt magic (%s)"
              % (label, magic.hex()))
    print("%-7s: %s (%d bytes, md5 %s)"
          % (label, show(os.path.basename(path)), len(data), md5_bytes(data)))
    return data


def file_contains(path: str, needle: bytes, chunk_size: int = 1 << 22) -> bool:
    """Chunked substring search (bundles are compressed, but container names are plain)."""
    overlap = len(needle) - 1
    tail = b""
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                return False
            buf = tail + chunk
            if needle in buf:
                return True
            tail = buf[-overlap:] if overlap else b""


def iter_bundles(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames, key=str.lower):
            if name.lower().endswith(BUNDLE_SUFFIX):
                yield os.path.join(dirpath, name)


def find_bundles(root: str) -> list[str]:
    if not os.path.isdir(root):
        fail("--find directory not found: %s" % show(root))
    files = list(iter_bundles(root))
    if not files:
        fail("no *%s files under %s" % (BUNDLE_SUFFIX, show(root)))
    print("scanning %d bundle(s) under %s for %s ..."
          % (len(files), show(root), FONT_ASSET_NEEDLE.decode("ascii")))
    hits = [p for p in files if file_contains(p, FONT_ASSET_NEEDLE)]
    if not hits:
        fail("no bundle contains %r under %s" % (FONT_ASSET_NEEDLE, show(root)))
    print("found %d bundle(s):" % len(hits))
    for p in hits:
        print("  %s  (%d bytes)" % (show(p), os.path.getsize(p)))
    return hits


def make_tempdir(out_path: str) -> str:
    """Pick a writable scratch directory.

    The system temp dir is preferred, but some sandboxes / locked-down Windows
    profiles make it read-only.  Fall back to the output directory (when it already
    exists) and then to the current directory.
    """
    out_dir = os.path.dirname(os.path.abspath(out_path))
    candidates = [tempfile.gettempdir(), out_dir, os.getcwd()]
    last_error = None
    for base in candidates:
        for _ in range(3):
            path = os.path.join(base, "patch_font_" + uuid.uuid4().hex[:10])
            try:
                os.makedirs(path)
            except FileExistsError:  # pragma: no cover - extremely unlikely
                continue
            except OSError as exc:
                last_error = exc
                break
            try:
                probe = os.path.join(path, "write-test")
                with open(probe, "wb") as f:
                    f.write(b"x")
                os.remove(probe)
                return path
            except OSError as exc:
                last_error = exc
                shutil.rmtree(path, ignore_errors=True)
                break
    fail("no writable temporary directory (%s); set TEMP to a writable path"
         % type(last_error).__name__)


def load_unitypy():
    try:
        import UnityPy
    except ImportError:
        print("ERROR: UnityPy is not installed.")
        print("Install the version that can save bundles with pack=\"original\":")
        print("    pip install UnityPy==1.25.2")
        print("(1.25.4 depends on tpk_ar, which only ships as sdist and needs Rust.)")
        raise SystemExit(1)

    version = getattr(UnityPy, "__version__", "unknown")
    print("UnityPy %s" % version)
    if version != UNITYPY_WANTED:
        print("WARNING: tested with UnityPy %s, you have %s."
              % (UNITYPY_WANTED, version))
        print("         If saving fails or flags change, switch versions.")
    return UnityPy


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Replace NotoSansTC-Medium/Bold inside a Blue Archive GL bundle "
                    "and restore the bundle CRC32.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run with --find first to locate the bundle, then pass it as --bundle.")
    ap.add_argument("--bundle", help="original UnityFS bundle to patch")
    ap.add_argument("--find", metavar="DIR",
                    help="scan DIR (Preload/Android) for the bundle containing NotoSansTC")
    ap.add_argument("--regular", help="NotoSansSC-Regular.otf, replaces NotoSansTC-Medium")
    ap.add_argument("--bold", help="NotoSansSC-Bold.otf, replaces NotoSansTC-Bold")
    ap.add_argument("--out", help="patched bundle to write (must differ from --bundle)")
    ap.add_argument("--target-crc", metavar="HEX", default=None,
                    help="CRC32 to restore (default: CRC32 of the input bundle)")
    ap.add_argument("--dry-run", action="store_true",
                    help="do all the work and report, but do not write --out")
    args = ap.parse_args()

    hits: list[str] = []
    if args.find:
        hits = find_bundles(args.find)
        if not (args.regular or args.bold or args.out or args.bundle):
            # discovery-only invocation
            print()
            print("Pass one of these as --bundle in the next command, e.g.:")
            print("  python tools/patch_font.py --bundle \"%s\" --regular ... --bold ... --out ..."
                  % show(hits[0]))
            return 0

    if args.bundle:
        bundle = args.bundle
    elif len(hits) == 1:
        bundle = hits[0]
    elif len(hits) > 1:
        fail("--find matched %d bundles; pick one explicitly with --bundle" % len(hits))
    else:
        fail("either --bundle or --find is required")

    if not (args.regular and args.bold and args.out):
        fail("--regular, --bold and --out are required (with or without --find)")
    if not os.path.isfile(bundle):
        fail("bundle not found: %s" % show(bundle))
    if os.path.abspath(args.out) == os.path.abspath(bundle):
        fail("--out must differ from --bundle (keep the original for rollback)")

    target_crc = crc32_file(bundle)
    if args.target_crc is not None:
        try:
            target_crc = int(args.target_crc, 16) & 0xFFFFFFFF
        except ValueError:
            fail("--target-crc must be a hex CRC32, got %r" % args.target_crc)

    crc_self_test()
    print()

    with open(bundle, "rb") as f:
        original = f.read()
    in_crc = crc32_bytes(original)
    size_pos, declared, in_flags = parse_header(original)
    print("input  : %s" % show(os.path.basename(bundle)))
    print("         size=%d  crc32=%08X  flags=0x%08X  header_size=%d"
          % (len(original), in_crc, in_flags, declared))

    regular = read_font(args.regular, "regular")
    bold = read_font(args.bold, "bold")
    wanted = {"regular": regular, "bold": bold}

    UnityPy = load_unitypy()
    env = UnityPy.load(bundle)

    before: dict[str, tuple[int, int, str]] = {}  # name -> (path_id, size, md5)
    targets: dict[str, object] = {}
    other_fonts: list[str] = []
    for obj in env.objects:
        if obj.type.name != "Font":
            continue
        asset = obj.read()
        name = str(getattr(asset, "m_Name", ""))
        if name not in FONT_MAP:
            other_fonts.append(name)
            continue
        data = bytes(asset.m_FontData)
        before[name] = (getattr(obj, "path_id", 0), len(data), md5_bytes(data))
        targets[name] = asset
        print("found  : %-20s path_id=%d  old_size=%d  old_md5=%s"
              % (name, before[name][0], before[name][1], before[name][2]))

    missing = sorted(set(FONT_MAP) - set(targets))
    if missing:
        fail("font asset(s) not found: %s (bundle has %d other Font asset(s): %s)"
             % (", ".join(missing), len(other_fonts),
                ", ".join(sorted(show(n) for n in other_fonts)) or "none"))
    if not targets:
        fail("no Font assets found in this bundle")

    print()
    for name, asset in targets.items():
        key = FONT_MAP[name]
        data = wanted[key]
        asset.m_FontData = data
        asset.save()
        print("replace: %-20s <- %s (%d -> %d bytes)"
              % (name, show(os.path.basename(args.regular if key == "regular" else args.bold)),
                 before[name][1], len(data)))

    # --- save with the original packing flags; any other packer breaks the game
    tmpdir = make_tempdir(args.out)
    try:
        env.save(pack="original", out_path=tmpdir)
        candidates = [os.path.join(tmpdir, n) for n in os.listdir(tmpdir)]
        expected = os.path.join(tmpdir, os.path.basename(bundle))
        if os.path.isfile(expected):
            saved_path = expected
        elif len(candidates) == 1:
            saved_path = candidates[0]
        else:
            fail("env.save() produced %d files, expected one" % len(candidates))
        with open(saved_path, "rb") as f:
            saved = f.read()
        print("saved  : pack=original  %d bytes" % len(saved))

        saved_size_pos, saved_declared, saved_flags = parse_header(saved)
        if saved_size_pos != size_pos:
            fail("header layout changed while saving; refusing to patch the size field")
        if saved_flags != in_flags:
            print("WARNING: bundle flags changed 0x%08X -> 0x%08X; pack=\"original\" failed?"
                  % (in_flags, saved_flags))

        # --- make room for the 4 CRC bytes, then update the header size field
        new_len = len(saved) + 4
        body = bytearray(saved)
        struct.pack_into(">q", body, size_pos, new_len)
        if int.from_bytes(body[size_pos:size_pos + 8], "big", signed=True) != new_len:
            fail("could not update the header size field")

        out = bytes(body) + _crc_append4(bytes(body), target_crc)
        out_size_pos, out_declared, out_flags = parse_header(out)
        out_crc = crc32_bytes(out)
        if len(out) != new_len or out_declared != len(out):
            fail("output size mismatch (len=%d header=%d)" % (len(out), out_declared))
        if out_flags != in_flags:
            fail("bundle flags changed 0x%08X -> 0x%08X" % (in_flags, out_flags))
        if out_crc != target_crc:
            fail("CRC32 mismatch: got %08X, wanted %08X" % (out_crc, target_crc))

        # --- reopen the exact bytes we are about to write and compare the font data
        verify_path = os.path.join(tmpdir, "verify_" + os.path.basename(bundle))
        with open(verify_path, "wb") as f:
            f.write(out)
        verify_env = UnityPy.load(verify_path)
        seen_after: dict[str, tuple[int, int, str]] = {}
        for obj in verify_env.objects:
            if obj.type.name != "Font":
                continue
            asset = obj.read()
            name = str(getattr(asset, "m_Name", ""))
            if name in FONT_MAP:
                data = bytes(asset.m_FontData)
                seen_after[name] = (getattr(obj, "path_id", 0), len(data), md5_bytes(data))
        for name in FONT_MAP:
            if name not in seen_after:
                fail("verification: %s disappeared from the saved bundle" % name)
            if seen_after[name][0] != before[name][0]:
                fail("verification: %s path_id changed (%d -> %d)"
                     % (name, before[name][0], seen_after[name][0]))
            if seen_after[name][2] != md5_bytes(wanted[FONT_MAP[name]]):
                fail("verification: %s font data does not match the input font" % name)
        print("verify : fonts and path_ids re-read OK")

        print()
        print("original crc32 : %08X" % in_crc)
        print("new crc32      : %08X  target=%08X  match=%s"
              % (out_crc, target_crc, out_crc == target_crc))
        print("output size    : %d bytes" % len(out))
        print("output md5     : %s" % md5_bytes(out))

        if args.dry_run:
            print()
            print("[dry-run] nothing written (would write %s)" % show(args.out))
            return 0

        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "wb") as f:
            f.write(out)
        print("output file    : %s" % show(args.out))
        print("                 md5 on disk = %s" % md5_file(args.out))
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:  # pragma: no cover - piped output closed early
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - keep console output ASCII and tidy
        print("ERROR: %s: %s" % (type(exc).__name__,
                                 str(exc).encode("ascii", "backslashreplace").decode("ascii")))
        sys.exit(1)
