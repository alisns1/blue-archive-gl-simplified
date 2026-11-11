#!/usr/bin/env python3
"""Preflight check: can THIS interpreter actually use sqlcipher3?

Why this exists
---------------
Prebuilt wheels are compiled against the FINAL ABI of a Python version.  An alpha or
beta build of that same version can `import sqlcipher3` successfully and then crash
inside the C extension (access violation, exit code 0xC0000005) as soon as it does real
crypto work.  A plain "is python installed?" check therefore proves nothing.

This probe creates a real encrypted database, writes a row, closes it, reopens it and
reads the row back.  If the interpreter/wheel pair is broken, the failure happens here
with a readable message instead of half-way through a localization run.

Exit codes: 0 = OK, 2 = cannot import, 3 = wrong data back, 4 = crashed / unusable.

NOTE: keep every string literal single-quoted.  On Windows, PowerShell strips embedded
double quotes when it passes arguments to a native command, which would corrupt any
inline `-c` version of this script.
"""
import os
import sys
import tempfile
import traceback

KEY_HEX = '00' * 32


def _cleanup(path):
    for suffix in ('', '-journal', '-wal', '-shm'):
        try:
            os.remove(path + suffix)
        except OSError:
            pass


def _pragma(cur):
    return cur.execute('PRAGMA key = ' + chr(34) + "x'" + KEY_HEX + "'" + chr(34))


def main():
    try:
        import sqlcipher3
    except Exception:
        print('FAIL: cannot import sqlcipher3')
        traceback.print_exc()
        return 2

    path = os.path.join(tempfile.gettempdir(), 'ba_sqlcipher_probe.db')
    _cleanup(path)

    try:
        con = sqlcipher3.connect(path)
        cur = con.cursor()
        _pragma(cur)
        cur.execute('CREATE TABLE t(a)')
        cur.execute('INSERT INTO t VALUES (1)')
        con.commit()
        con.close()

        con = sqlcipher3.connect(path)
        cur = con.cursor()
        _pragma(cur)
        cur.execute('SELECT a FROM t')
        row = cur.fetchone()
        con.close()
        if not row or row[0] != 1:
            print('FAIL: round-trip returned ' + repr(row))
            return 3
    except Exception:
        print('FAIL: sqlcipher3 is unusable in this interpreter')
        traceback.print_exc()
        return 4
    finally:
        _cleanup(path)

    print('PROBE_OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
