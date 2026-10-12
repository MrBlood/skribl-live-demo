#!/usr/bin/env python3
"""The Python packages an auditor needs to run Skribl OFFLINE, and proof they do.

    python3 harness/tools/wheelhouse.py OUT_DIR        # build, verify, zip

WHY: the v321 outside audit could not install Flask in its environment (no
package network), so it never opened a page, and most of its "not tested" --
and much of its low score -- came from that alone. The owner: "for the next
audit, include the Python dependencies in the package so the auditor can run
the app offline."

WHAT IT MAKES, in OUT_DIR:
  skribl-wheels-cp312-linux-x86_64.zip   every wheel constraints.txt pins (the
      app) plus the harness's own Flask-WTF and Pillow, and README-OFFLINE.txt
  SHA256SUMS-wheels.txt                  the zip's hash

The wheels are fetched with --require-hashes against constraints.txt, so they
are byte-for-byte the locked set, and they are for the platform that file was
locked on (linux x86_64, CPython 3.12). Playwright is NOT included: its wheel
and its browser are hundreds of megabytes and the v321 auditor already had
both; README-OFFLINE.txt says so.

THE PROOF follows the README, from the finished zip. The zip is unpacked
beside a copy of constraints.txt exactly as README-OFFLINE.txt says, a fresh
virtual environment runs the README's own pip lines with the network refused
(--no-index), then imports the app and creates its tables on a throwaway
SQLite file. Only then is the zip written to OUT_DIR. A wheelhouse that has
not been installed from is a claim, not a package -- and so is a README nobody
followed: the v322 seal found the first README's unzip line put the wheels one
folder deeper than its pip lines look ("No matching distribution found for
alembic"), while the proof, installing from the folder it had just built,
passed.
"""
import hashlib
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXTRAS = ["Flask-WTF", "Pillow"]   # the harness's own, beside the app's lock

README = """Skribl -- Python packages for running it offline
==================================================

These are the exact packages constraints.txt pins (hash-checked), plus the
test harness's Flask-WTF and Pillow, built for linux x86_64 / CPython 3.12.

    unzip skribl-wheels-cp312-linux-x86_64.zip      # makes ./wheels
    python3.12 -m venv .venv && . .venv/bin/activate
    pip install --no-index --find-links wheels -r constraints.txt --require-hashes
    pip install --no-index --find-links wheels Flask-WTF Pillow      # the harness's own
    harness/bootstrap.sh           # or: flask --app app run  (see START-HERE.md)

Put this zip in the folder the source zip unpacks to, where constraints.txt
lives, and run the lines above from there. Playwright and its Chromium are not
included (hundreds of megabytes); install them as START-HERE.md describes if
your environment does not already have them.
"""


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, **kw)


def reader_steps(readme):
    """The README's own `unzip` and `pip install` lines, split as a shell would.

    The proof runs THESE rather than a copy of them, so the instructions and
    the proof cannot drift apart again. Only the indented lines are commands.
    """
    steps = []
    for line in readme.splitlines():
        if not line.startswith("    "):
            continue
        cmd = shlex.split(line, comments=True)
        if cmd[:1] == ["unzip"] or cmd[:2] == ["pip", "install"]:
            steps.append(cmd)
    return steps


def unzip(cmd, cwd):
    """`unzip ZIP` or `unzip ZIP -d DIR`, as the reader's shell would run it."""
    args, dest = cmd[1:], cwd
    if "-d" in args:
        i = args.index("-d")
        dest = cwd / args[i + 1]
        args = args[:i] + args[i + 2:]
    if len(args) != 1 or args[0].startswith("-"):
        raise SystemExit(f"README unzip line not understood: {' '.join(cmd)}")
    print("  $", " ".join(cmd))
    with zipfile.ZipFile(cwd / args[0]) as zf:
        zf.extractall(dest)


def main(out):
    out = pathlib.Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        wheels = tmp / "wheels"
        run([sys.executable, "-m", "pip", "download", "-q", "-r", ROOT / "constraints.txt",
             "--require-hashes", "--only-binary=:all:", "-d", wheels])
        run([sys.executable, "-m", "pip", "download", "-q", "--only-binary=:all:", "-d", wheels] + EXTRAS)
        staged = tmp / "skribl-wheels-cp312-linux-x86_64.zip"
        with zipfile.ZipFile(staged, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README-OFFLINE.txt", README)
            for w in sorted(wheels.iterdir()):
                zf.write(w, "wheels/" + w.name)
        # THE PROOF: a reader's folder holding only constraints.txt and the
        # finished zip, the README's own lines run in it with the network
        # refused, then the app imported and its tables built.
        reader = tmp / "reader"
        reader.mkdir()
        shutil.copy(ROOT / "constraints.txt", reader)
        shutil.copy(staged, reader)
        venv = tmp / "venv"
        run([sys.executable, "-m", "venv", venv])
        py = venv / "bin" / "python"
        steps = reader_steps(README)
        if [c[0] for c in steps].count("pip") != 2:
            raise SystemExit("README-OFFLINE.txt should carry two pip install lines")
        for cmd in steps:
            if cmd[0] == "unzip":
                unzip(cmd, reader)
            else:
                run([py, "-m", "pip", "install", "-q"] + cmd[2:], cwd=reader)
        env = dict(os.environ, DATABASE_URL=f"sqlite:///{tmp}/proof.db", PYTHONPATH=str(ROOT))
        run([py, "-c", "from app import app, db; app.app_context().push(); db.create_all();"
             " import flask_wtf, PIL; print('  offline install imports the app and builds its tables')"],
            cwd=ROOT, env=env)
        z = out / staged.name
        shutil.copy(staged, z)
        digest = hashlib.sha256(z.read_bytes()).hexdigest()
        (out / "SHA256SUMS-wheels.txt").write_text(f"{digest}  {z.name}\n")
        n = len(list(wheels.iterdir()))
        print(f"{z}  {n} wheels, {z.stat().st_size / 1e6:.1f} MB, sha256 {digest[:16]}...")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
