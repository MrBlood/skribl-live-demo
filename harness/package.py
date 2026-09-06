#!/usr/bin/env python3
"""Build the release packages: runtime, source, evidence.

WHY SPLIT. The v281 archive shipped one 2.4 MB zip containing the application,
the harness that proves it, 2.7 MB of regression fixtures, and every historical
document. A deployment needs none of that except the application. The v281
declutter review measured a rough runtime-only package at roughly 42% of the
full archive without deleting a line of product code, and asked for the split
to be made real — its words: "It is not yet a release artifact — I have not
proven that exact minimal set contains every deployment input."

PROVING IT IS THE POINT, so `--verify` boots the built runtime package in a
scratch directory against a fresh database and exercises it over HTTP. An
allowlist nobody boots is a guess.

    python3 harness/package.py <outdir>            # build all three
    python3 harness/package.py <outdir> --verify   # ...and boot the runtime one

THE RUNTIME SET IS DERIVED, not enumerated: everything git tracks under
skribl/, plus the root files a process genuinely needs to start. That second
list is short and hand-written because there is no way to derive "what a
deployment runs" from the tree — which is exactly why --verify exists.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The only hand-maintained list here. Each entry is load-bearing at boot:
#   app.py           the WSGI entry point Procfile names
#   Procfile         how the host starts it
#   requirements.txt / constraints.txt   the pinned dependency set
#   alembic.ini      migrations config; skribl/migrations is useless without it
#   .python-version  the interpreter the lock was resolved for
RUNTIME_ROOT = ["app.py", "Procfile", "requirements.txt", "constraints.txt",
                "alembic.ini", ".python-version"]

# .env.example ships because a deployer configures from it; it is 4 KB and its
# absence is the kind of thing discovered at 2am.
RUNTIME_ROOT += [".env.example"]


def tracked(prefix=None):
    # An empty pathspec is an ERROR to git, not a wildcard, so the whole-tree
    # call has to omit the argument rather than pass "".
    cmd = ["git", "-C", str(ROOT), "ls-files", "-z"]
    if prefix:
        cmd.append(prefix)
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return [p for p in out.split("\0") if p]


def runtime_files():
    return sorted(set(tracked("skribl")) | {f for f in RUNTIME_ROOT
                                            if (ROOT / f).is_file()})


def evidence_files():
    keep = set(tracked("harness")) | set(tracked(".github")) | set(tracked("docs"))
    keep |= {f for f in ("DECISIONS.md", "START-HERE.md", "FUTURE.md",
                         "DESIGN-DIRECTION.md", "CLAUDE.md", "ARCHIVE-README.md")
             if (ROOT / f).is_file()}
    # Generated evidence is gitignored by design but belongs in this package.
    keep |= {p for p in ("harness/RELEASE.md", "harness/LAST-RUN.txt",
                         "harness/MP4-ATTESTATION.txt") if (ROOT / p).is_file()}
    return sorted(keep)


def copy_set(files, dest):
    for rel in files:
        src = ROOT / rel
        if not src.is_file():
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)


def manifest(dirpath):
    """SHA256SUMS over every file, excluding itself — a file cannot carry its
    own digest, which ARCHIVE-README.md already explains to the reader."""
    lines = []
    for p in sorted(dirpath.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS":
            h = subprocess.run(["sha256sum", str(p.relative_to(dirpath))],
                               capture_output=True, text=True, cwd=dirpath).stdout
            lines.append(h.rstrip("\n"))
    (dirpath / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def build(out, version):
    made = []
    for name, files in (("runtime", runtime_files()),
                        ("source", sorted(set(tracked()))),
                        ("evidence", evidence_files())):
        d = out / f"skribl-{version}-{name}"
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
        copy_set(files, d)
        n = manifest(d)
        zipname = f"{d.name}.zip"
        subprocess.run(["zip", "-qr", zipname, d.name], cwd=out, check=True)
        size = (out / zipname).stat().st_size
        made.append((name, n, size, out / zipname))
    return made


def verify_runtime(pkg_dir):
    """Boot the built runtime package and exercise it. Returns a list of
    failures; empty means the allowlist contains every input THIS EXERCISES.

    WHAT IT PROVES: alembic reaches head from an empty database, the app
    imports and serves all four pages, a post round-trips through create ->
    player -> share card -> revoke-with-issued-key. Calibrated by removal —
    dropping alembic.ini, app.py or skribl/migrations each fails it by name.

    WHAT IT DOES NOT PROVE, and the distinction matters because "VERIFIED"
    reads stronger than it is:
      * .python-version is read by the PLATFORM, not the app, so this cannot
        tell whether omitting it breaks a deploy. It ships because the lock
        file was resolved for that interpreter.
      * .env.example is operator documentation; nothing at runtime opens it.
      * gunicorn is what the Procfile actually runs; this uses the Flask
        development server, so a WSGI-server-specific failure would pass here.
      * PostgreSQL is not exercised — this runs on SQLite.
    """
    import json as _json
    import os
    import time
    import urllib.error
    import urllib.request

    fails = []
    env = dict(os.environ)
    env["SKRIBL_DATABASE_URL"] = f"sqlite:///{pkg_dir / 'verify.db'}"
    env["DATABASE_URL"] = env["SKRIBL_DATABASE_URL"]
    env["SECRET_KEY"] = "packaging-verification-only"
    env["SKRIBL_RATE_MAX_POSTS"] = "10000"

    # MIGRATE THE WAY PRODUCTION DOES. The Procfile reads
    #     web: python -m alembic upgrade head && gunicorn app:app
    # so the schema comes from the migration chain, not db.create_all(). The
    # first version of this check used create_all and therefore never touched
    # alembic.ini or skribl/migrations — it would have called a runtime package
    # missing either of them VERIFIED. Boot the real path or prove nothing.
    mig = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                         cwd=pkg_dir, env=env, capture_output=True, text=True)
    if mig.returncode != 0:
        fails.append("alembic upgrade head failed: "
                     + (mig.stderr or mig.stdout)[-400:])
        return fails
    head = subprocess.run(
        [sys.executable, "-c",
         "from app import app, db\n"
         "app.app_context().push()\n"
         "from sqlalchemy import inspect, text\n"
         "names = inspect(db.engine).get_table_names()\n"
         "assert 'skribl_posts' in names, names\n"
         "v = db.session.execute(text('select version_num from alembic_version')).scalar()\n"
         "print('migrated-to', v)"],
        cwd=pkg_dir, env=env, capture_output=True, text=True)
    if "migrated-to" not in head.stdout:
        fails.append(f"schema is not the migrated one: {(head.stderr or head.stdout)[-400:]}")
        return fails
    print(f"    {head.stdout.strip()}")

    port = "5177"
    srv = subprocess.Popen([sys.executable, "-m", "flask", "--app", "app",
                            "run", "--port", port, "--no-reload"],
                           cwd=pkg_dir, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(base + "/skribl-pad", timeout=1).read()
                break
            except Exception:
                time.sleep(0.5)
        else:
            fails.append("server never answered on /skribl-pad")
            return fails

        for path in ("/skribl-pad", "/flip", "/library", "/feed"):
            try:
                code = urllib.request.urlopen(base + path, timeout=10).status
                if code != 200:
                    fails.append(f"GET {path} -> {code}")
            except Exception as e:
                fails.append(f"GET {path} raised {e}")

        payload = {"title": "packaging check", "visibility": "public",
                   "payload": {"version": 1, "schemaVersion": 1, "fps": 12,
                               "playbackMode": "flip",
                               "canvasSize": {"cssWidth": 816, "cssHeight": 612, "dpr": 1},
                               "frames": [{"strokes": [
                                   {"x": 10, "y": 10, "color": "#fff", "size": 3,
                                    "t": 0, "start": True, "erase": False},
                                   {"x": 90, "y": 90, "color": "#fff", "size": 3,
                                    "t": 30, "start": False, "erase": False}]}]}}
        req = urllib.request.Request(base + "/api/skribls",
                                     data=_json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            body = _json.loads(urllib.request.urlopen(req, timeout=20).read())
            pid, tok = body.get("id"), body.get("deleteToken")
            if not pid:
                fails.append(f"POST /api/skribls returned no id: {body}")
            else:
                if urllib.request.urlopen(f"{base}/s/{pid}", timeout=10).status != 200:
                    fails.append("player page did not serve the new post")
                if urllib.request.urlopen(f"{base}/s/{pid}/card.png", timeout=20).status != 200:
                    fails.append("share card did not render")
                d = urllib.request.Request(f"{base}/api/skribls/{pid}", method="DELETE",
                                           data=_json.dumps({"deleteToken": tok}).encode(),
                                           headers={"Content-Type": "application/json"})
                if urllib.request.urlopen(d, timeout=20).status not in (200, 204):
                    fails.append("revocation with the issued key failed")
        except urllib.error.HTTPError as e:
            fails.append(f"POST /api/skribls -> {e.code}: {e.read()[:200]}")
        except Exception as e:
            fails.append(f"post/delete journey raised {e}")
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except Exception:
            srv.kill()
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    import re
    version = re.search(r'SKRIBL_VERSION\s*=\s*"([^"]+)"',
                        (ROOT / "skribl" / "core.py").read_text(encoding="utf-8")).group(1)
    out = Path(args.outdir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    made = build(out, version)
    full = next((s for n, _, s, _ in made if n == "source"), 0)
    for name, n, size, path in made:
        share = f"{100 * size // full}% of source" if full else ""
        print(f"  {name:9} {n:>4} files  {size:>9,} B  {share}")
    if args.verify:
        pkg = out / f"skribl-{version}-runtime"
        print("\n  verifying the runtime package boots and serves...")
        fails = verify_runtime(pkg)
        for f in fails:
            print(f"    FAIL {f}")
        print("  runtime package: " + ("VERIFIED" if not fails else f"{len(fails)} failure(s)"))
        return 1 if fails else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
