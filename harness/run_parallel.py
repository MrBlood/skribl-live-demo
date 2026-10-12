"""Run named suites side by side, each against a fresh server of its own.

FOR THE LOOP BETWEEN AN EDIT AND A PULL REQUEST, NOT FOR THE RECORD. The suites
a change touches used to run one after another against the one server on 5001
that most of them assumed, and on a day of small fixes that was half of every
change's time (owner: "1 change is 40 minutes? We have an efficiency
problem"). Every suite reads SKRIBL_BASE now, so several can run at once, each
against its own server and its own database.

A RED FROM A SUITE THAT MEASURES IS RE-RUN ALONE BEFORE IT COUNTS.
release_run.py's BATCHES tags each suite that MEASURES (painted pixels,
geometry, frame pacing) or touches a STORE a neighbour could see; a second
Chromium competing for the CPU reads as a moved pixel or a late frame there,
which is why the seal runs them alone. Most of the heavy suites carry that
tag, so running them one at a time here would save almost nothing. Load
makes those checks fail, not pass, so they run side by side with the rest,
and any of them that comes back red runs again alone, nothing beside it, and
that answer is the one reported. A red from an untagged suite is reported as
it is: a re-run is only for contention, never to wash out a flake. The tag
is the one place the decision lives, and this reads it rather than keeping a
second list. Main's full run after every merge still runs them as the seal
does.

WHAT IT DOES NOT DO. It does not write harness/LAST-RUN.txt, stamp the docs
or stand in for a seal, which is still release_run.py. Its result lines are
the runner's own ("verify_x.py: ok -- 12/12 passed"), with each failing
suite's [FAIL] lines said again at the end, so a pull request can quote them.

    python3 harness/run_parallel.py -j 3 verify_parity.py verify_onepill.py ...

Servers come from harness/bootstrap.sh on ports from 5101 up (the suites that
host their own servers use fixed ports below that, or a free one), and are
stopped at the end. The venv is SKRIBL_VENV, or bootstrap's own default.
"""
import argparse
import os
import re
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "harness"
VENV = os.environ.get("SKRIBL_VENV", "/tmp/skribl-venv")
LOGS = Path(os.environ.get("RUN_PARALLEL_LOGS", "/tmp/run_parallel"))


def alone_suites():
    """The suites release_run.py runs alone because they measure or share a store.

    Read from its BATCHES, where each solo batch carries its reason as a tag
    in a trailing comment. Only those two reasons are about neighbours; a solo
    batch for size, or one marked unrecorded, may share a lane here.
    """
    alone = set()
    for line in (HARNESS / "release_run.py").read_text(encoding="utf-8").splitlines():
        m = re.match(r'\s*\[\s*"(verify_\w+\.py)"\s*\],\s*#\s*([a-z ,]+)', line)
        if m and {"measures", "store"} & set(re.split(r"[ ,]+", m.group(2).strip())):
            alone.add(m.group(1))
    return alone


def free(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def boot(port):
    """One fresh server on PORT, as (port, its database), or None with the reason printed.

    THE DATABASE TRAVELS WITH THE ADDRESS. Several suites also open the
    database in-process (a Flask test client, a direct query) through
    DATABASE_URL, which run_harness.sh exports for them; given only the
    server's address they opened an empty default and failed on "no such
    table" (verify_delivery, verify_deletion_foundation, in this tool's first
    full run)."""
    out = subprocess.run([str(HARNESS / "bootstrap.sh"), VENV, str(port)], cwd=ROOT,
                         capture_output=True, text=True, timeout=600)
    db = re.search(r"db:\s*(\S+\.db)", out.stdout)
    if out.returncode != 0 or f"127.0.0.1:{port}" not in out.stdout or not db:
        print(f"  server on {port} did not start:\n{out.stdout[-600:]}{out.stderr[-600:]}")
        return None
    return port, db.group(1)


def stop(port):
    subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)


def run(suite, server, timeout):
    port, db = server
    LOGS.mkdir(parents=True, exist_ok=True)
    log = LOGS / (suite[:-3] + ".log")
    # What run_harness.sh gives a suite: its server, that server's database,
    # and the posting limit the harness raises (bootstrap raised it for the
    # server; a suite that posts in-process needs it too).
    env = dict(os.environ, SKRIBL_BASE=f"http://127.0.0.1:{port}",
               DATABASE_URL=f"sqlite:///{db}",
               SKRIBL_RATE_MAX_POSTS=os.environ.get("SKRIBL_RATE_MAX_POSTS", "100000"))
    # A suite that reads SKRIBL_BASE with NO default treats "unset" as "bring
    # your own server" (verify_deletion_foundation needs the local media
    # store, which the shared server does not use), so it gets none, as under
    # run_harness.sh. Read off the call itself, not a list of names.
    if re.search(r"""os\.environ\.get\(\s*["']SKRIBL_BASE["']\s*\)""",
                 (HARNESS / suite).read_text(encoding="utf-8", errors="replace")):
        env.pop("SKRIBL_BASE")
    t0 = time.monotonic()
    with open(log, "w", encoding="utf-8") as fh:
        try:
            code = subprocess.run([sys.executable, str(HARNESS / suite)], cwd=ROOT, env=env,
                                  stdout=fh, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
    text = log.read_text(encoding="utf-8", errors="replace")
    counts = re.findall(r"^\s*(\d+)/(\d+) passed", text, re.M)
    fails = [l.strip()[:300] for l in text.splitlines() if re.match(r"\s*\[FAIL\]", l)][:8]
    skip = re.search(r"^SUITE-SKIPPED:\s*(.*)$", text, re.M)
    return {"suite": suite, "code": code, "counts": counts[-1] if counts else None,
            "fails": fails or ([] if code == 0 else text.splitlines()[-6:]),
            "skip": skip.group(1).strip() if skip else None,
            "secs": time.monotonic() - t0, "log": str(log)}


def verdict(r):
    """ok, skip or fail. Exit 77 is a suite declining to run for a missing
    prerequisite (verify_mp4 without real Chrome): run_harness.sh reports it as
    SKIPPED, apart from the passes and not as a failure, and so does this."""
    if r["code"] == 77:
        return "skip"
    ok = r["code"] == 0 and r["counts"] and r["counts"][0] == r["counts"][1]
    return "ok" if ok else "fail"


def line(r):
    v = verdict(r)
    if v == "skip":
        return v, f"  {r['suite']}: SKIPPED (0 assertions) -- {r['skip'] or 'no reason given'}"
    got = f"{r['counts'][0]}/{r['counts'][1]} passed" if r["counts"] else "no summary"
    state = "ok" if v == "ok" else f"FAIL -- exit {r['code']}"
    return v, f"  {r['suite']}: {state} -- {got} ({r['secs'] / 60:.1f} min)"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-j", type=int, default=3, help="servers, and suites at once (default 3)")
    ap.add_argument("--timeout", type=int, default=3000, help="seconds per suite")
    ap.add_argument("suites", nargs="+")
    a = ap.parse_args()
    suites = [s if s.endswith(".py") else s + ".py" for s in a.suites]
    missing = [s for s in suites if not (HARNESS / s).is_file()]
    if missing:
        sys.exit("no such suite: " + ", ".join(missing))
    alone = alone_suites()
    n = max(1, min(a.j, len(suites)))

    ports, p = [], 5101
    while len(ports) < n:
        if free(p):
            ports.append(p)
        p += 1
    with ThreadPoolExecutor(n) as ex:
        up = [x for x in ex.map(boot, ports) if x]
    if not up:
        sys.exit("no server started")
    print(f"{len(up)} server(s) on {', '.join(str(s[0]) for s in up)}; {len(suites)} suite(s), "
          f"{sum(s in alone for s in suites)} of them re-run alone if red")

    results, lock = [], threading.Lock()
    queue = list(suites)

    def worker(server):
        while True:
            with lock:
                if not queue:
                    return
                suite = queue.pop(0)
            r = run(suite, server, a.timeout)
            with lock:
                results.append(r)
                print(line(r)[1], flush=True)

    t0 = time.monotonic()
    try:
        threads = [threading.Thread(target=worker, args=(server,)) for server in up]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Every other suite has finished: nothing runs beside these.
        for i, r in enumerate(results):
            if r["suite"] in alone and verdict(r) == "fail":
                again = run(r["suite"], up[0], a.timeout)
                again["suite"] = r["suite"]
                print(line(again)[1] + "  <- alone, after a red beside others", flush=True)
                results[i] = again
    finally:
        for port, _db in up:
            stop(port)

    bad = [r for r in results if verdict(r) == "fail"]
    skipped = [r for r in results if verdict(r) == "skip"]
    ok = len(results) - len(bad) - len(skipped)
    print(f"\n{ok}/{len(results)} suites ok in {(time.monotonic() - t0) / 60:.1f} min (logs in {LOGS})")
    if skipped:
        print(f"{len(skipped)} skipped, so their coverage is NOT shown by this run: "
              + ", ".join(r["suite"] for r in skipped))
    if bad:
        print("\n================ WHAT FAILED ================")
        for r in bad:
            for f in r["fails"]:
                print(f"{r['suite']} | {f}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
