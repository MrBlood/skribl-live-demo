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
both. README-OFFLINE.txt says so, and makes the environment with
--system-site-packages so that a Playwright already there is used.

THE PROOF follows the README, from the finished zip, in the tree the source
zip carries. HEAD's tracked files are unpacked into a folder with the zip
beside them, and the README's own lines are run there with pip's network
refused: the unzip, the environment, both installs, and harness/bootstrap.sh,
which builds a fresh database and boots the app until it answers. The one
change made to a README line is the port bootstrap.sh is given, a free one,
so the proof never meets a server already up. The proof then checks that
bootstrap.sh named the environment the README built, imports the harness's
own packages there, and stops the app. Only then is the zip written to
OUT_DIR.

A wheelhouse nobody installed from is a claim, not a package -- and so is a
README nobody followed. The v322 seal found the first README did not work as
written: its unzip put the wheels one folder deeper than its pip lines look
("No matching distribution found for alembic"), and its bootstrap.sh line
ignored the environment it had just built and reached for the network. The
proof then installed from the folder it had just built, and passed.
"""
import hashlib
import io
import os
import pathlib
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import time
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXTRAS = ["Flask-WTF", "Pillow"]   # the harness's own, beside the app's lock

README = """Skribl -- Python packages for running it offline
==================================================

These are the exact packages constraints.txt pins (hash-checked), plus the
test harness's Flask-WTF and Pillow, built for linux x86_64 / CPython 3.12.
Put this zip in the folder the source zip unpacks to, where constraints.txt
lives, and run these lines from there:

    unzip skribl-wheels-cp312-linux-x86_64.zip      # makes ./wheels
    python3.12 -m venv --system-site-packages .venv && . .venv/bin/activate
    pip install --no-index --find-links wheels -r constraints.txt --require-hashes
    pip install --no-index --find-links wheels Flask-WTF Pillow      # the harness's own
    harness/bootstrap.sh .venv      # a fresh database; the app at http://127.0.0.1:5001/

--system-site-packages lets the new environment use a Playwright you already
have. Playwright and its Chromium are not included (hundreds of megabytes):
the app runs without them, and the harness's browser suites need both
(START-HERE.md). bootstrap.sh prints how to run a suite and how to stop the app.
"""

# What the proof expects the README's lines to be, in order. A line it cannot
# run stops it, and so does one of these going missing.
EXPECTED = ["unzip", "venv", "pip", "pip", "bootstrap"]


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, check=True, **kw)


def reader_steps(readme):
    """The README's command lines, split as a shell would, `#` comments dropped.

    The proof runs THESE rather than a copy of them, so the instructions and
    the proof cannot drift apart again. Only the indented lines are commands.
    """
    return [shlex.split(line, comments=True) for line in readme.splitlines()
            if line.startswith("    ") and line.strip()]


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


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def listening(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def stop(port):
    """Stop the app bootstrap.sh left up, by port, as bootstrap.sh says to."""
    for cmd in (["fuser", "-k", f"{port}/tcp"], ["sh", "-c", f"kill $(lsof -ti :{port})"]):
        if listening(port) and shutil.which(cmd[0]):
            subprocess.run(cmd, capture_output=True)
    for _ in range(20):
        if not listening(port):
            return
        time.sleep(0.25)
    print(f"  !! the app is still up on port {port}; stop it by hand")


def prove(staged, tmp):
    """Run the README's lines in HEAD's tree, with the finished zip beside it."""
    reader = tmp / "reader"
    reader.mkdir()
    tree = run(["git", "archive", "HEAD"], cwd=ROOT, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(tree)) as tf:
        tf.extractall(reader, filter="data")
    shutil.copy(staged, reader)
    py = reader / ".venv" / "bin" / "python"
    env = dict(os.environ, PIP_NO_INDEX="1")   # pip's network refused, whatever a line says
    ran, port = [], None
    try:
        for cmd in reader_steps(README):
            if cmd[0] == "unzip":
                unzip(cmd, reader)
                ran.append("unzip")
            elif cmd[1:3] == ["-m", "venv"] and "&&" in cmd:
                # `python3.12 -m venv ... .venv && . .venv/bin/activate`: this
                # interpreter makes it, and the lines after call it by path.
                run([sys.executable] + cmd[1:cmd.index("&&")], cwd=reader)
                ran.append("venv")
            elif cmd[:2] == ["pip", "install"]:
                run([py, "-m", "pip", "install", "-q"] + cmd[2:], cwd=reader, env=env)
                ran.append("pip")
            elif cmd[0] == "harness/bootstrap.sh":
                # bootstrap.sh [VENV] [PORT]. Without VENV it builds its own at
                # /tmp/skribl-venv, from the network, ignoring the one above.
                if len(cmd) not in (2, 3):
                    raise SystemExit("the README's bootstrap.sh line has to name the environment it built")
                port = free_port()
                argv = cmd[:2] + [str(port)]
                print("  $", " ".join(argv))
                r = subprocess.run(argv, cwd=reader, env=env, capture_output=True, text=True)
                print(textwrap.indent((r.stdout + r.stderr).rstrip(), "    "))
                if r.returncode != 0:
                    raise SystemExit(f"bootstrap.sh exited {r.returncode}")
                at = re.search(r"^venv:.* at (\S+)$", r.stdout, re.M)
                if not at or (reader / at.group(1)).resolve() != (reader / ".venv").resolve():
                    raise SystemExit("bootstrap.sh booted the app on another environment than the README built")
                ran.append("bootstrap")
            else:
                raise SystemExit(f"README line the proof cannot run: {' '.join(cmd)}")
        if ran != EXPECTED:
            raise SystemExit(f"README lines ran as {ran}, expected {EXPECTED}")
        run([py, "-c", "import flask_wtf, PIL; print('  the harness packages import too')"], cwd=reader)
    finally:
        if port:
            stop(port)


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
        prove(staged, tmp)
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
