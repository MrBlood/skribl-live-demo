"""bootstrap.sh finishes an install it was cut off in the middle of.

A session after v328: the first bootstrap was reaped at a turn boundary part
way through its pip installs, and the second skipped installing because the
venv's python3 was already there. It created no tables ("No module named
'flask'") and a third run did the same. The script now marks a venv it makes
until both installs have finished, and installs again while the mark is there.

No browser, no server, no network: bootstrap.sh is run against a stand-in
python3.12 whose venv's python3 and pip only write down what they were asked.
Every run stops at the tables, which the stand-in cannot create, so no server
is ever started. The stand-in's pip fails on request, which is the cut-off
install.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assertions import make_check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PIN = (ROOT / ".python-version").read_text().strip()
results = []
check = make_check(results)

# The venv's python3 and pip: write down a pip call, fail when asked to, and
# fail at anything else (the tables), which ends the run before the server.
TOOL = """#!/bin/sh
case "$*" in
  *pip*|install*) echo "pip $*" >> "$STUB_LOG"; exit "${STUB_PIP_EXIT:-0}" ;;
esac
exit 1
"""
# The interpreter .python-version pins: `-m venv DIR` makes the venv's tools.
PY = """#!/bin/sh
[ "$1" = "-m" ] && [ "$2" = "venv" ] || exit 1
mkdir -p "$3/bin"
for t in python3 pip; do cat "$STUB_TOOL" > "$3/bin/$t"; chmod +x "$3/bin/$t"; done
echo "venv $3" >> "$STUB_LOG"
"""


def bootstrap(tmp, venv, pip_exit=0):
    log = tmp / "calls.log"
    log.write_text("")
    env = dict(os.environ, PATH=f"{tmp / 'bin'}:{os.environ['PATH']}", STUB_LOG=str(log),
               STUB_TOOL=str(tmp / "tool.sh"), STUB_PIP_EXIT=str(pip_exit))
    r = subprocess.run([str(ROOT / "harness" / "bootstrap.sh"), str(venv), "1"], cwd=ROOT,
                       env=env, capture_output=True, text=True, timeout=60)
    return r.returncode, log.read_text().splitlines(), r.stdout + r.stderr


print("BOOTSTRAP — an install cut off part way is finished on the next run")
with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    (tmp / "bin").mkdir()
    (tmp / "tool.sh").write_text(TOOL)
    stub = tmp / "bin" / f"python{PIN}"
    stub.write_text(PY)
    stub.chmod(0o755)
    venv = tmp / "venv"

    code, calls, out = bootstrap(tmp, venv, pip_exit=1)
    check("a run whose pip fails makes the venv and stops, without booting", code != 0
          and calls[:1] == [f"venv {venv}"] and "server:" not in out, f"{code} {calls} {out[-300:]}")
    check("...and leaves the venv marked unfinished", (venv / ".bootstrap-installing").exists(),
          str(sorted(p.name for p in venv.iterdir())))

    code, calls, out = bootstrap(tmp, venv)
    pips = [c for c in calls if c.startswith("pip")]
    check("the next run installs again into the venv it found", len(pips) == 3
          and not any(c.startswith("venv") for c in calls), str(calls))
    check("...the lock with its hashes and the harness's own, both",
          any("constraints.txt --require-hashes" in c for c in pips)
          and any("harness/requirements.txt" in c for c in pips), str(pips))
    check("...and takes the mark off once both have finished",
          not (venv / ".bootstrap-installing").exists(), str(sorted(p.name for p in venv.iterdir())))

    code, calls, out = bootstrap(tmp, venv)
    check("a finished venv is not installed into again", calls == [], str(calls))

    other = tmp / "offline-venv"
    (other / "bin").mkdir(parents=True)
    for t in ("python3", "pip"):
        (other / "bin" / t).write_text(TOOL)
        (other / "bin" / t).chmod(0o755)
    code, calls, out = bootstrap(tmp, other)
    check("a venv somebody else made (README-OFFLINE's, no package network) is used as it is",
          calls == [], str(calls))

passed = sum(1 for ok_, _ in results if ok_)
bad = [n for ok_, n in results if not ok_]
print(f"\n{passed}/{len(results)} passed" + ("" if not bad else "  FAILURES: " + ", ".join(bad)))
sys.exit(1 if bad else 0)
