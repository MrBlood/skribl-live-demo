"""Documentation that cannot quietly lie.

`stamp_docs.py` generates the assertion totals into a marked stanza in three
documents, and its own generated text promised that "verify_docs.py fails if any
doc disagrees with the recorded run." That file did not exist. The mechanism
built to stop unverifiable claims was itself making one, which is the exact
failure it was written to prevent.

It exists now. It also checks the claims that have actually gone stale in this
project before — suite counts, file counts, version strings — because every one
of them was a number typed once into prose and checked never:

  * the editor's hardcoded version drifted NINE releases
  * README said v118 while app.py said v131
  * three documents claimed 646/19, 615/18 and 345/17 assertions
  * SHA256SUMS claimed 50 files while covering 52
  * an archive was named v137 while the code inside declared v131
  * constraints.txt pinned 16 packages after a 17th became required

Source only. No server, no browser.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

results = []
def check(name, ok, detail=""):
    results.append((ok, name)); print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))


BEGIN, END = "<!-- HARNESS-COUNTS -->", "<!-- /HARNESS-COUNTS -->"
# START-HERE.md is the first document a new session reads and was the ONLY one
# not checked here — so it drifted four versions unnoticed, still announcing
# v175's suite and file counts and pointing at a patch that had been renamed.
# The document most likely to be trusted blind is the one that most needs a
# guard.
DOCS = [ROOT / "README.md", ROOT / "harness" / "README.md",
        ROOT / "docs" / "HANDOFF.md", ROOT / "START-HERE.md"]

print("\nDOCS — the generated stanza is present and current")
for doc in DOCS:
    check(f"{doc.relative_to(ROOT)} carries the generated stanza",
          doc.is_file() and BEGIN in doc.read_text(encoding="utf-8"),
          "hand-typed totals drift; generated ones cannot")

# NOTE ON ORDERING: this suite runs inside the loop, so it validates the
# PREVIOUS run's record — the runner does not write LAST-RUN.txt until every
# suite has finished. That used to mean a pass here was invalidated seconds
# later. run_harness.sh now re-stamps immediately after writing the record, so
# the docs are current after any run; what this assertion catches is a tree
# COMMITTED with stale stanzas.
stamp = subprocess.run([sys.executable, "harness/stamp_docs.py", "--check"],
                       cwd=ROOT, capture_output=True, text=True)
check("stamp_docs.py --check reports the docs as current",
      stamp.returncode == 0,
      (stamp.stdout or stamp.stderr).strip().splitlines()[-1:] and
      (stamp.stdout or stamp.stderr).strip().splitlines()[-1] or "")

print("\nDOCS — every file this documentation names actually exists")
# The stanza promised a verify_docs.py that did not exist. Any harness file
# referenced by name in prose must be real.
named = set()
for doc in DOCS + [ROOT / "ARCHIVE-README.md", ROOT / "harness" / "stamp_docs.py"]:
    if doc.is_file():
        named |= set(re.findall(r"\b(verify_[a-z0-9_]+\.py)\b",
                                doc.read_text(encoding="utf-8")))
missing = sorted(n for n in named if not (ROOT / "harness" / n).is_file())
check("no document references a harness suite that does not exist",
      not missing, ", ".join(missing))

# The suite-name check above would not have caught START-HERE.md naming
# `v179-client.patch`, because that is not a verify_*.py. A document that tells
# you how to deploy by applying a patch, and names a patch that is not in the
# tree, is worse than one that says nothing.
paths = set()
for doc in DOCS + [ROOT / "ARCHIVE-README.md"]:
    if doc.is_file():
        body = doc.read_text(encoding="utf-8")
        # Lookbehind, not \b: the docs name `static/skribl/gifenc.min.js`,
        # which is the SERVED url path and not a file in the tree. Matching
        # mid-path turns every correct reference into a false failure.
        paths |= set(re.findall(r"(?<![A-Za-z0-9_/-])((?:docs|skribl|harness)/"
                                r"[A-Za-z0-9_./-]+"
                                r"\.(?:py|md|patch|css|js|html|txt|sh))", body))
gone = sorted(p for p in paths if not (ROOT / p).is_file())
check("no document names a repo file that is not there",
      not gone, ", ".join(gone))

print("\nDOCS — no volatile release fact is typed by hand")
# A tree hash written into prose cannot be kept true: it describes the tree it
# is written into, so writing it changes it. START-HERE.md carried one, it went
# stale within the same session, and an external reviewer reasonably concluded
# the archive could not be trusted to be the tree the recorded run executed on
# — even though it reproduced its LAST-RUN hash exactly. A wrong hash in a
# document is worse than no hash, because it looks like provenance.
# The stamped stanza already carries the tree; docs must point at it.
_HEXY = re.compile(r"\b[0-9a-f]{32,}\b")
typed = []
for doc in DOCS + [ROOT / "ARCHIVE-README.md"]:
    if not doc.is_file():
        continue
    body = doc.read_text(encoding="utf-8")
    body = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), "", body, flags=re.S)
    if _HEXY.search(body):
        typed.append(doc.relative_to(ROOT))
check("no current document hand-types a tree hash outside the generated stanza",
      not typed, ", ".join(str(d) for d in typed))

print("\nDOCS — the two generated-file lists agree")
# run_harness.sh and release_run.py each exclude generated documents from the
# tree hash. They must exclude the SAME ones: START-HERE.md was added to
# stamp_docs.py without being added to run_harness.sh, and the tree hash
# immediately stopped reproducing. Drift between these lists is silent.
_sh = (ROOT / "harness" / "run_harness.sh").read_text(encoding="utf-8")
_py = (ROOT / "harness" / "release_run.py").read_text(encoding="utf-8")
# Only the generated-DOCUMENT exclusions are comparable. run_harness.sh also
# excludes path CLASSES from its `git ls-files` branch (__pycache__, .pyc,
# instance/) which the find branch gets from find's own -not clauses and which
# release_run.py hardcodes in tree_files() — those are the same rule expressed
# three ways, not a list that can drift out of step with GENERATED.
_sh_names = {n for n in re.findall(r"-e '([^']+)'", _sh)
             if not n.startswith("^") and not n.startswith("\\.")
             and not n.endswith("/")}
_py_names = set(re.findall(r'"([A-Za-z0-9_./-]+\.(?:md|txt))"',
                           re.search(r"GENERATED = \{(.*?)\}", _py, re.S).group(1)))
_py_names.add("SHA256SUMS")
check("run_harness.sh and release_run.py exclude the same generated files",
      _sh_names == _py_names,
      f"only in run_harness: {sorted(_sh_names - _py_names)}; "
      f"only in release_run: {sorted(_py_names - _sh_names)}")

print("\nDOCS — the deployed runtime is pinned, and it is the one tested")
# constraints.txt is a hash-locked cp312 environment. Render's default Python
# depends on when the service was created and can move under you, so an
# unpinned deployment resolves requirements.txt fresh at build time and runs
# versions no assertion here ever exercised — two applications, one repo. The
# pin lives in .python-version (and should be mirrored by PYTHON_VERSION on the
# service) so it travels with the code rather than living in a dashboard.
_pyver = ROOT / ".python-version"
check("the repository pins a Python version", _pyver.is_file(),
      "an unpinned runtime means the lock describes an environment nobody runs")
if _pyver.is_file():
    _want = _pyver.read_text().strip()
    _have = f"{sys.version_info.major}.{sys.version_info.minor}"
    check("and the harness is running on that version",
          _want.split(".")[:2] == _have.split(".")[:2],
          f"pinned {_want!r}, running {_have!r} — evidence produced on a "
          "different interpreter from the deployed one describes nothing")
    check("the lock is built for the pinned version",
          f"cp{_want.replace('.', '')}" in (ROOT / "constraints.txt").read_text(),
          f"constraints.txt carries no cp{_want.replace('.', '')} marker")

print("\nDOCS — the archive reports one version, everywhere")
# The delivered zip was once named v180 while the directory, SKRIBL_VERSION and
# every document said v179. One artifact, one identity.
_ver = re.search(r'SKRIBL_VERSION\s*=\s*"([^"]+)"',
                 (ROOT / "skribl" / "core.py").read_text(encoding="utf-8"))
_v = _ver.group(1) if _ver else None
# The archive is distributed as skribl-<version>/, and the name carrying the
# version is how you can tell two unpacked drops apart in a downloads folder.
# A GIT CHECKOUT is named after the repository, not the release, so this cannot
# apply there — it would fail permanently for everyone working in the repo,
# which is how an assertion gets ignored rather than fixed.
if (ROOT / ".git").exists():
    check("archive naming: skipped, this is a git checkout",
          True, f"directory {ROOT.name!r} — the version lives in skribl/core.py")
else:
    check("the archive directory name carries SKRIBL_VERSION",
          bool(_v) and ROOT.name.endswith(_v),
          f"directory {ROOT.name!r} against SKRIBL_VERSION {_v!r}")

print("\nDOCS — suite counts match what is on disk")
on_disk = sorted(p.name for p in (ROOT / "harness").glob("verify_*.py"))
claims = []
# docs/HANDOFF.md is a CHANGELOG: "112 assertions across 8 suites (was 60 across
# 5)" is a true statement about v-something, not a claim about this tree. Only
# documents that describe the current state are checked.
_current = [ROOT / "README.md", ROOT / "harness" / "README.md",
            ROOT / "ARCHIVE-README.md", ROOT / "START-HERE.md"]
for doc in _current:
    if not doc.is_file():
        continue
    body = doc.read_text(encoding="utf-8")
    # Ignore numbers inside the generated stanza — those are stamped, not typed.
    body = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), "", body, flags=re.S)
    for m in re.finditer(r"\b(\d+)\s+suites\b", body):
        claims.append((doc.relative_to(ROOT), int(m.group(1))))
wrong = [(d, n) for d, n in claims if n != len(on_disk)]
check(f"no hand-typed suite count disagrees with the {len(on_disk)} on disk",
      not wrong, "; ".join(f"{d} says {n}" for d, n in wrong))

print("\nDOCS — the version string is single-sourced")
src = None
for cand in (ROOT / "skribl" / "core.py", ROOT / "app.py"):
    if cand.is_file() and "SKRIBL_VERSION" in cand.read_text(encoding="utf-8"):
        src = cand
        break
check("SKRIBL_VERSION is defined exactly once, in one file", src is not None)
if src:
    version = re.search(r'SKRIBL_VERSION\s*=\s*"([^"]+)"',
                        src.read_text(encoding="utf-8")).group(1)
    print(f"    SKRIBL_VERSION = {version}")
    # Any vNNN in prose that is NOT the current version must be historical
    # narrative, never a claim about what this tree IS.
    readme = (ROOT / "ARCHIVE-README.md")
    if readme.is_file():
        head = readme.read_text(encoding="utf-8")[:600]
        check("ARCHIVE-README states the real source version up front",
              version in head,
              f"the archive must lead with {version}, not a stage label")

print("\nDOCS — version and file-count claims match reality")
# These are the exact claims that went stale and were NOT caught: README said
# "Current version v118" while the code said v135, pointed at app.py for a
# constant that lives in skribl/core.py, and said SHA256SUMS "covers all 50
# files" while it covered 82. The checker claimed to prevent this class of drift
# and did not test for it.
if src:
    for doc in [ROOT / "README.md", ROOT / "ARCHIVE-README.md"]:
        if not doc.is_file():
            continue
        body = doc.read_text(encoding="utf-8")
        body_nostanza = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), "",
                               body, flags=re.S)
        stated = re.findall(r"[Cc]urrent version[^\n]*?\*\*(v\d+)\*\*",
                            body_nostanza)
        stated += re.findall(r"Source version:[^\n]*?\"(v\d+)\"", body_nostanza)
        wrong_v = [v for v in stated if v != version]
        check(f"{doc.relative_to(ROOT)} states the real version",
              not wrong_v, f"says {wrong_v}, code says {version}")

        # Any claim of the form "covers all N files" must match SHA256SUMS.
        sums = ROOT / "SHA256SUMS"
        if sums.is_file():
            actual = len(re.findall(r"^[0-9a-f]{64}\s", sums.read_text(encoding="utf-8"), re.M))
            claims_n = [int(n) for n in re.findall(r"covers all (\d+) files", body_nostanza)]
            bad_n = [n for n in claims_n if n != actual]
            check(f"{doc.relative_to(ROOT)}: any file-count claim matches SHA256SUMS",
                  not bad_n, f"claims {bad_n}, manifest has {actual}")

    # The constant must be documented where it actually lives.
    rel = str(src.relative_to(ROOT))
    readme = (ROOT / "README.md")
    if readme.is_file():
        body = readme.read_text(encoding="utf-8")
        misdirect = re.findall(r"`SKRIBL_VERSION` in `([^`]+)`", body)
        check("README points at the file that really defines SKRIBL_VERSION",
              all(m == rel for m in misdirect),
              f"points at {misdirect}, it lives in {rel}")

    # Model-table counts drift the same way.
    init = (ROOT / "skribl" / "__init__.py")
    if init.is_file():
        # Count the mapped tables by PARSING models.py, not by importing the
        # package — importing skribl pulls in Flask, and this suite is
        # deliberately source-only so it runs anywhere.
        models_src = (ROOT / "skribl" / "models.py").read_text(encoding="utf-8")
        n_tables = len(re.findall(r"^\s*__tablename__\s*=", models_src, re.M))
        words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
        claimed = [words[w] for w in re.findall(
            r"Skribl's (one|two|three|four|five)\s*\n?\s*tables",
            init.read_text(encoding="utf-8"))]
        check("the documented model-table count matches the metadata",
              all(c == n_tables for c in claimed),
              f"claims {claimed}, metadata has {n_tables}")

print("\nDOCS — the two generated records describe the SAME run")
# There are two generators: run_harness.sh writes LAST-RUN.txt (and stamp_docs.py
# stamps the docs from it), and release_run.py writes RELEASE.md. release_run
# drives the runner one BATCH at a time, so LAST-RUN.txt described only the last
# batch — and a finished 42-suite release published "78 assertions across 2
# suites" in README.md beside "1693 across 42" in RELEASE.md. Two machine-
# generated numbers contradicting each other is not better than one typed one.
_rel = ROOT / "harness" / "RELEASE.md"
_lr = ROOT / "harness" / "LAST-RUN.txt"
# Only comparable when LAST-RUN.txt was written BY a release run. A targeted
# `run_harness.sh verify_x.py` legitimately overwrites the record with one
# suite, and demanding that agree with RELEASE.md would fail every ordinary
# invocation. Like the stamped stanzas, this therefore validates the PREVIOUS
# release — verify_docs runs inside the suite loop, so it cannot see a record
# that has not been written yet.
if _rel.is_file() and _lr.is_file() and "whole release run" in _lr.read_text(encoding="utf-8"):
    _rel_n = re.search(r"^\s*assertions\s+(\d+)", _rel.read_text(encoding="utf-8"), re.M)
    _lr_n = re.search(r"^assertions passed:\s*(\d+)", _lr.read_text(encoding="utf-8"), re.M)
    check("RELEASE.md and LAST-RUN.txt agree on the assertion count",
          bool(_rel_n and _lr_n) and _rel_n.group(1) == _lr_n.group(1),
          f"RELEASE.md says {_rel_n.group(1) if _rel_n else '?'}, "
          f"LAST-RUN.txt says {_lr_n.group(1) if _lr_n else '?'} — a release run "
          "must rewrite the record for the WHOLE run, not leave the final batch "
          "standing as it")
    _rel_t = re.search(r"^\s*tree hash\s+([0-9a-f]{64})", _rel.read_text(encoding="utf-8"), re.M)
    _lr_t = re.search(r"^Tree SHA-256\s*:\s*([0-9a-f]{64})", _lr.read_text(encoding="utf-8"), re.M)
    check("and on the tree they were produced from",
          bool(_rel_t and _lr_t) and _rel_t.group(1) == _lr_t.group(1),
          "one of them describes a different tree")

print("\nDOCS — a run with skips is not published as 'all green'")# The runner reports PASS WITH SKIPS when nothing failed but something was
# skipped; the stanza generator decided on failures alone and wrote "all green",
# then listed the skipped suites and said a skip is not evidence of coverage —
# two contradictory claims in one generated block. Now that a bare run expands to
# every suite, PASS WITH SKIPS is the ORDINARY outcome: a SQLite run skips the
# PostgreSQL suite and a Chromium without H.264 skips the MP4 suite.
sys.path.insert(0, str(ROOT / "harness"))
import stamp_docs as _sd

_base = dict(assertions=10, suites=1, engine="sqlite", version="vX", tree="t")
_clean = _sd._headline(dict(_base, skipped=[], problems=[]))
_skips = _sd._headline(dict(_base, skipped=["verify_mp4.py"], problems=[]))
_fails = _sd._headline(dict(_base, skipped=[], problems=["verify_feed.py"]))
check("a clean run is reported as all green", "all green" in _clean, _clean[:50])
check("a run WITH SKIPS is not called all green", "all green" not in _skips,
      _skips[:60])
check("and is reported as PASS WITH SKIPS", "PASS WITH SKIPS" in _skips,
      _skips[:60])
check("a run with failures is reported as NOT GREEN",
      "NOT GREEN" in _fails and "all green" not in _fails, _fails[:60])

print("\nDOCS — CI cannot report a green run that tested nothing")
# Both CI jobs invoked ./harness/run_harness.sh with NO arguments. The suite loop
# ran zero times and the script printed "PASS — every requested suite exited 0"
# and exited 0, because every one of the zero requested suites did pass. A green
# job that tested nothing, under a comment claiming CI runs the full harness.
_runner = (ROOT / "harness" / "run_harness.sh").read_text(encoding="utf-8")
check("a bare invocation defaults to every suite",
      'set -- verify_*.py' in _runner,
      "no zero-argument default — an empty run would report PASS")
check("and an empty suite list is refused rather than reported",
      "refusing to report a" in _runner)

_wf = ROOT / ".github" / "workflows" / "harness.yml"
if _wf.is_file():
    _y = _wf.read_text(encoding="utf-8")
    # Every harness invocation in CI must either name suites or rely on a
    # default that is now guaranteed to be non-empty.
    check("the CI workflow still invokes the harness",
          "run_harness.sh" in _y)
    check("the workflow does not claim a full run it cannot deliver",
          ("set -- verify_*.py" in _runner) or ("verify_" in _y),
          "CI runs the runner bare and the runner has no default")

print("\nDOCS — the archive-verification command states the real file count")
# This number is the FIRST thing a new session runs, so when it is wrong the
# session opens by disbelieving the archive. It had drifted to 110 against a
# manifest of 121 — the file-count check above only reads README and
# ARCHIVE-README and only matches the phrase "covers all N files", so the
# `# expect N` comment on the verify command was covered by nothing.
# Matched off the command itself rather than a bare "expect N" so that prose
# elsewhere cannot accidentally satisfy or trip it.
_sums = ROOT / "SHA256SUMS"
if _sums.is_file():
    _actual = len(re.findall(r"^[0-9a-f]{64}\s", _sums.read_text(encoding="utf-8"), re.M))
    for _doc in sorted(ROOT.rglob("*.md")):
        if not _doc.is_file() or ".git" in _doc.parts:
            continue
        _claims = [int(n) for n in re.findall(
            r"sha256sum -c SHA256SUMS[^\n]*?expect (\d+)",
            _doc.read_text(encoding="utf-8"))]
        if not _claims:
            continue
        _bad = [n for n in _claims if n != _actual]
        check(f"{_doc.relative_to(ROOT)}: the verify command expects the real count",
              not _bad,
              f"tells the reader to expect {_bad}, manifest has {_actual} — "
              "a wrong number here makes a sound archive look tampered with")

print("\nDOCS — the dependency lock covers every requirement")
req = (ROOT / "requirements.txt")
lock = (ROOT / "constraints.txt")
if req.is_file() and lock.is_file():
    def norm(n):
        return re.sub(r"[-_.]+", "-", n).lower()
    wanted = {norm(re.split(r"[<>=\[]", l.strip())[0])
              for l in req.read_text(encoding="utf-8").splitlines()
              if l.strip() and not l.startswith("#")}
    locked = {norm(m) for m in re.findall(r"^([A-Za-z][A-Za-z0-9_.-]*)==",
                                          lock.read_text(encoding="utf-8"), re.M)}
    absent = sorted(wanted - locked)
    check("every requirement appears in the pinned lockfile", not absent,
          ", ".join(absent) + "  — a strict hashed install would omit it")
    check("the lockfile documents the install command that actually works",
          "--require-hashes" in lock.read_text(encoding="utf-8"))

bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
# This suite printed its failures and then exited 0, so run_harness.sh — which
# takes ok/FAIL from the exit code — reported it as "ok — 32/33 passed" and the
# aggregate counted the run as PASS with a failed assertion in it. A suite that
# fails must SAY so in the only channel the runner reads.
import sys
sys.exit(1 if bad else 0)
