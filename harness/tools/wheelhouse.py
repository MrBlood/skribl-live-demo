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

THE PROOF: before zipping, a fresh virtual environment installs from the
wheels with the network refused (--no-index), imports the app, and creates
its tables on a throwaway SQLite file. A wheelhouse that has not been
installed from is a claim, not a package.
"""
import hashlib
import os
import pathlib
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

    unzip skribl-wheels-cp312-linux-x86_64.zip -d wheels
    python3.12 -m venv .venv && . .venv/bin/activate
    pip install --no-index --find-links wheels -r constraints.txt --require-hashes
    pip install --no-index --find-links wheels Flask-WTF Pillow      # the harness's own
    harness/bootstrap.sh           # or: flask --app app run  (see START-HERE.md)

Run from the unpacked source zip, where constraints.txt lives. Playwright and
its Chromium are not included (hundreds of megabytes); install them as
START-HERE.md describes if your environment does not already have them.
"""


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, **kw)


def main(out):
    out = pathlib.Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        wheels = tmp / "wheels"
        run([sys.executable, "-m", "pip", "download", "-q", "-r", ROOT / "constraints.txt",
             "--require-hashes", "--only-binary=:all:", "-d", wheels])
        run([sys.executable, "-m", "pip", "download", "-q", "--only-binary=:all:", "-d", wheels] + EXTRAS)
        # THE PROOF: install with the network refused, then import and build.
        venv = tmp / "venv"
        run([sys.executable, "-m", "venv", venv])
        py = venv / "bin" / "python"
        run([py, "-m", "pip", "install", "-q", "--no-index", "--find-links", wheels,
             "-r", ROOT / "constraints.txt", "--require-hashes"])
        run([py, "-m", "pip", "install", "-q", "--no-index", "--find-links", wheels] + EXTRAS)
        env = dict(os.environ, DATABASE_URL=f"sqlite:///{tmp}/proof.db", PYTHONPATH=str(ROOT))
        run([py, "-c", "from app import app, db; app.app_context().push(); db.create_all();"
             " import flask_wtf, PIL; print('  offline install imports the app and builds its tables')"],
            cwd=ROOT, env=env)
        z = out / "skribl-wheels-cp312-linux-x86_64.zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README-OFFLINE.txt", README)
            for w in sorted(wheels.iterdir()):
                zf.write(w, "wheels/" + w.name)
        digest = hashlib.sha256(z.read_bytes()).hexdigest()
        (out / "SHA256SUMS-wheels.txt").write_text(f"{digest}  {z.name}\n")
        n = len(list(wheels.iterdir()))
        print(f"{z}  {n} wheels, {z.stat().st_size / 1e6:.1f} MB, sha256 {digest[:16]}...")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
