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

# ...and the converse, which nothing checked: every suite ON DISK must be
# named in at least one .md. Six suites sat undocumented while this file
# stayed green — a reader of the docs had no way to learn they existed, and a
# suite nobody can find is a suite nobody maintains. Scans every tracked .md
# in the repo, not just DOCS: a suite documented only in e.g. DECISIONS.md is
# documented.
_all_md_text = "\n".join(
    p.read_text(encoding="utf-8")
    for p in ROOT.rglob("*.md")
    if "__pycache__" not in p.parts and p.is_file())
_undocumented = sorted(
    p.name for p in (ROOT / "harness").glob("verify_*.py")
    if p.name not in _all_md_text)
check("every harness suite on disk is named in at least one .md",
      not _undocumented,
      ", ".join(_undocumented) + " — add each to harness/README.md at least")

# v223: the same rule for the SHARED MODULES, and for the same reason. lib/ is
# where a rule lives once instead of twice, so a module nobody can find is a
# module that gets reimplemented in one of the two editors — which is the exact
# drift verify_parity.py and verify_sharedrules.py exist to catch. Eight of the
# thirty-six were named in no document at all when this check was written, among
# them pressure.js and brushes.js, which both editors depend on.
_undoc_libs = sorted(
    p.name for p in (ROOT / "skribl" / "static" / "lib").glob("*.js")
    if p.name not in _all_md_text)
check("every shared module in lib/ is named in at least one .md",
      not _undoc_libs,
      ", ".join(_undoc_libs) + " — START-HERE.md carries the index of all of them")

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
_py_names = set(re.findall(r'"([A-Za-z0-9_./-]+\.(?:md|txt|log))"',
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

# ---------------------------------------------------------------------------
# v212 — a one-batch run cannot overwrite release-wide evidence.
#
# release_run.py drives run_harness.sh ONE BATCH AT A TIME, so the record left
# behind describes only the final batch; it already rewrites LAST-RUN.txt to
# cover every batch and re-stamps. That holds only while the release run is the
# LAST harness invocation. A bare `run_harness.sh verify_docs.py` afterwards
# rewrites LAST-RUN.txt and re-stamps from it — observed at the v212 seal,
# publishing "36 assertions across 1 suites" beside a RELEASE.md recording 2400
# across 61, on the same tree.
#
# That is WORSE than a hand-typed number: it is machine-generated, so it carries
# the authority this project grants generated figures, and it is wrong. The
# generated-not-typed rule assumes ONE generator; there are two, and they can
# disagree. stamp_docs.py now refuses a stamp that would narrow the record for
# the same tree.
#
# RUN IN AN ISOLATED TEMP ROOT, and this is the load-bearing detail. The first
# version of this pin drove the REAL stamp_docs against the REAL files, and it
# could not work: stamp_docs resolves ROOT from __file__, so it read the live
# RELEASE.md — which, DURING a release run, describes the PREVIOUS tree, because
# release_run.py writes RELEASE.md at the end. The guard correctly declines to
# gate on a record for a different tree, so there would be nothing to refuse and
# the assertion would fail inside the very run that seals the archive. It also
# restored "the real record" from disk, which at that moment WAS the damaged
# narrow one. Copying the script into a temp ROOT with fabricated inputs makes
# the pin independent of both.
print("\nDOCS — a single batch cannot narrow release-wide evidence")
import shutil as _shutil, subprocess as _sub, tempfile as _tf

def _fake_root(tmp, assertions, rel_assertions, tree="a1b2c3d4e5f6" + "0" * 52):
    """A minimal tree: the real stamp_docs.py, a fabricated run and release."""
    (tmp / "harness").mkdir(parents=True, exist_ok=True)
    _shutil.copy(ROOT / "harness" / "stamp_docs.py", tmp / "harness" / "stamp_docs.py")
    (tmp / "harness" / "LAST-RUN.txt").write_text("\n".join([
        "================ RUN CONTEXT ================",
        f"Tree SHA-256            : {tree}",
        "SKRIBL_VERSION          : v212",
        "DATABASE_URL class      : sqlite",
        "============================================",
        "",
        "================ AGGREGATE (machine-generated) ================",
        "suites requested : 1",
        f"  verify_probe.py: ok — {assertions}/{assertions} passed",
        f"assertions passed: {assertions}   (skipped suites contribute 0)",
        "suites skipped   : 0",
        "suites with problems: 0",
        "",
    ]))
    (tmp / "harness" / "RELEASE.md").write_text(
        "# Release evidence\n\n"
        "    result           PASS\n"
        f"    tree hash        {tree}\n"
        "    suites on disk   61\n"
        "    suites reported  61\n"
        f"    assertions       {rel_assertions}\n"
        "    skipped          0\n")
    doc = tmp / "README.md"
    doc.write_text("# x\n\n" + BEGIN + "\nPLACEHOLDER\n" + END + "\n")
    return doc

def _run_stamp(tmp):
    return _sub.run([sys.executable, str(tmp / "harness" / "stamp_docs.py")],
                    capture_output=True, text=True, cwd=str(tmp))

with _tf.TemporaryDirectory() as _td:
    # (a) narrower than the release record on the SAME tree -> refuse
    _t = Path(_td) / "narrow"
    _doc = _fake_root(_t, assertions=3, rel_assertions=2400)
    _before = _doc.read_text(encoding="utf-8")
    _r = _run_stamp(_t)
    check("stamp_docs.py REFUSES to stamp a record narrower than "
          "RELEASE.md on the same tree",
          _r.returncode != 0 and "REFUSED" in (_r.stdout + _r.stderr),
          f"exit {_r.returncode}")
    check("...and it left the stamped stanza untouched "
          "(refusing loudly then writing anyway would pass on exit code alone)",
          _doc.read_text(encoding="utf-8") == _before,
          "unchanged" if _doc.read_text(encoding="utf-8") == _before else "REWRITTEN")

    # (b) NEGATIVE CONTROL: the release-wide record itself must still stamp, or
    # the guard is just a script that never works.
    _t2 = Path(_td) / "wide"
    _doc2 = _fake_root(_t2, assertions=2400, rel_assertions=2400)
    _r2 = _run_stamp(_t2)
    check("...and a release-wide record DOES stamp "
          "(the guard blocks narrowing, not stamping)",
          _r2.returncode == 0 and "2400" in _doc2.read_text(encoding="utf-8"),
          f"exit {_r2.returncode}")

    # (c) A DIFFERENT tree must not gate at all: a release record for some other
    # tree says nothing about this run, and gating on it would wedge the next
    # build — which is exactly the state the real tree is in mid-release.
    _t3 = Path(_td) / "othertree"
    _doc3 = _fake_root(_t3, assertions=3, rel_assertions=2400)
    (_t3 / "harness" / "RELEASE.md").write_text(
        (_t3 / "harness" / "RELEASE.md").read_text().replace("a1b2c3d4e5f6", "999999999999"))
    _r3 = _run_stamp(_t3)
    check("...and a RELEASE.md for a DIFFERENT tree does not gate the stamp",
          _r3.returncode == 0,
          f"exit {_r3.returncode}: {(_r3.stdout or _r3.stderr).strip().splitlines()[:1]}")


# --- v225: a documented skip must name a lane that really exists -------------
# release_run.SKIP_COVERAGE lets RELEASE.md say "this skip is covered by the
# `mp4` CI job". That sentence is worth exactly as much as the job's existence,
# so the job name is checked against the workflow rather than trusted. The v224
# outside review filed the MP4 skip as an open gap while the lane that closes it
# was shipping inside the archive it reviewed — the lane was real and the
# evidence never mentioned it.
print("\nDOCS — every claimed skip-coverage lane exists in the workflow")
_wf = ROOT / ".github" / "workflows" / "harness.yml"
check("the CI workflow is in the tree", _wf.is_file(), str(_wf.relative_to(ROOT)))
if _wf.is_file():
    _wf_text = _wf.read_text(encoding="utf-8")
    sys.path.insert(0, str(ROOT / "harness"))
    import release_run as _rr
    check("some skip actually claims coverage", bool(_rr.SKIP_COVERAGE),
          "an empty table would make every assertion below vacuous")
    for _suite, _job in sorted(_rr.SKIP_COVERAGE.items()):
        check(f"the '{_job}' job exists for {_suite}",
              re.search(r"^  %s:$" % re.escape(_job), _wf_text, re.M) is not None,
              "claimed in release_run.SKIP_COVERAGE")
        check(f"...and the '{_job}' job actually runs {_suite}",
              _suite in _wf_text,
              "a job that never invokes the suite covers nothing")
    check("the mp4 lane FAILS on a skip rather than reporting green",
          "SKIPPED on the job that exists to run it" in _wf_text,
          "a lane that tolerates the skip it exists to prevent is not a lane")
    # THE MINUTES ARE A FINITE RESOURCE AND THIS PROJECT EXHAUSTED THEM.
    # Three jobs of 20-30 minutes started on every push; without a concurrency
    # group the superseded runs finished anyway, against commits nobody would
    # merge. Pinned here because the symptom -- runs dying in a second with 404
    # logs -- looks nothing like its cause, and the block is one deletable
    # stanza that nothing else in the workflow depends on.
    check("superseded pull-request runs are cancelled rather than paid for",
          re.search(r"^concurrency:$", _wf_text, re.M) is not None
          and "cancel-in-progress:" in _wf_text,
          "no concurrency group — every push leaves the previous three jobs running")
    check("...and main's runs are NOT cancelled, so each shipped commit keeps "
          "its own verification record",
          "github.event_name == 'pull_request'" in _wf_text,
          "a flat cancel-in-progress: true would drop the run for a commit that "
          "shipped when the next one lands on top of it")
    check("a suite claiming coverage is not itself missing from disk",
          all((ROOT / "harness" / s).is_file() for s in _rr.SKIP_COVERAGE))


# --- v225: capability claims, not just counts --------------------------------
# WHY THIS SECTION EXISTS, and it is the most useful thing in this file.
#
# Everything above checks facts that go stale NUMERICALLY — a suite count, a
# file count, an assertion total, a tree hash, a version string. Every one of
# those is a number typed once and checked never, and catching them is why this
# suite was written.
#
# It cannot catch a SENTENCE. The v224 outside review found that
# FOR-THE-REVIEWER.md still called durable drafts and pointer identity
# "NOT deferrable prerequisites" two releases after both shipped, that
# DESIGN-DIRECTION.md stated the draft problem as current, and that
# START-HERE.md said Pad's autosave "holds strokes but not media bytes" seven
# hundred lines above its own paragraph explaining that the bytes go to
# IndexedDB. A 3,328-assertion harness did not notice, because not one of those
# is a number.
#
# It cost more than embarrassment: the reviewer read a stale docstring in
# models.py claiming the database limiter was "NOT yet verified on PostgreSQL
# across processes" and filed a MEDIUM finding asking for a test that
# verify_postgres.py has been running for releases — four gunicorn worker
# PROCESSES, twelve barrier-released requests, quota two, no over-admission and
# no under-admission. Stale prose does not merely mislead a reader; it spends a
# reviewer's attention on work already done.
#
# THE RULE. Each entry below pairs a capability with the artifact that PROVES it
# shipped, and with the phrasings that would only appear if it had not. When the
# proof holds, no current-facing document may deny it.
#
# WHAT THIS DOES NOT DO, said plainly because overclaiming here would be the
# same sin. It catches denials it has PATTERNS for. A newly-invented stale
# sentence about some other capability sails through exactly as before. This is
# a ratchet over the claims that have actually rotted, not a semantic
# understanding of the prose — adding a capability means adding an entry, and
# nothing but this comment says so.
print("\nDOCS — a shipped capability may not be described as unshipped")

# Documents that describe the CURRENT state and are read as guidance.
# FOR-THE-REVIEWER.md and HANDOFF-NEXT-SESSION.md were on this list until the
# v263 cleanup retired both files (each described a seal thirty-odd versions
# stale); the list names what exists, not what used to.
CURRENT_DOCS = ["START-HERE.md", "DESIGN-DIRECTION.md",
                "README.md", "ARCHIVE-README.md",
                "FUTURE.md", "docs/INTEGRATION.md"]
# Never scanned: a changelog SHOULD say "before v222 the bytes were lost", and a
# review response should record what was true at the time. Their whole job is to
# state a superseded fact accurately.
#
# A current-facing document may still carry one, if it says so. A line is exempt
# when it or the six lines above it carry an explicit marker — which is how
# docs/HANDOFF.md keeps its v105 media paragraph verbatim under a "BOTH
# SENTENCES ABOVE ARE SUPERSEDED" note.
# Deliberately a SMALL CLOSED LIST of explicit markers, not a general notion of
# past tense. Every entry is an escape hatch, so adding one is a decision: it
# must be a phrase a writer uses to say "the following is a quotation of, or a
# statement about, something that is no longer true". "requirement, as written"
# is how DESIGN-DIRECTION.md keeps a superseded brief verbatim beside what
# shipped, which is worth more than deleting it.
EXEMPT = re.compile(r"SUPERSEDED|\(history\)|\(historical|historical from here|"
                    r"was DECLARED|used to (say|read|be|end|state|claim)|no longer|"
                    r"requirement, as written|"
                    r"until v\d|before v\d|as of v\d", re.I)

# (label, proof, denial patterns, extra files to scan beyond CURRENT_DOCS)
#
# The `extra` column exists because the v224 reviewer's false finding did not
# come from a document at all — it came from a docstring in skribl/models.py.
# A capability claim is release-critical wherever it is written down, and code
# comments are read more literally than prose, not less. Only the claim that
# names a file scans it, so validation.py can keep saying (truthfully) that
# compressed-audio duration is bounded by bytes alone.
CLAIMS = [
    ("durable media drafts",
     ("harness/verify_drafts.py", r"bytes are in the draft store"),
     [r"autosave[^.\n]{0,60}but not media bytes",
      r"strokes but not media bytes",
      r"localStorage cannot hold them",
      r"drops media when the quota",
      r"durable drafts[^.\n]{0,80}(prerequisite|not deferrable)"]),
    ("pointer identity / contact ownership",
     ("skribl/static/lib/eventpoint.js", r"targetTouches"),
     [r"Migrate to Pointer Events",
      r"pointer identity[^.\n]{0,60}(prerequisite|not deferrable|still open)"]),
    ("PostgreSQL cross-process rate limiting",
     ("harness/verify_postgres.py", r"no OVER-admission"),
     [r"NOT yet verified on PostgreSQL across processes",
      r"not[^.\n]{0,30}verified[^.\n]{0,40}across processes"],
     ["skribl/models.py", "skribl/ratelimit.py"]),
    ("media resource limits (dimensions, WAV duration)",
     ("harness/verify_medialimits.py", r"MAX_IMAGE_PIXELS"),
     [r"(dimensions and duration|duration and dimensions)[^.\n]{0,60}\bNOT\b"]),
    ("the feed_filter seam",
     ("harness/verify_hostseams.py", r"set_feed_filter|feed_filter"),
     [r"feed_filter[^.\n]{0,40}does not exist yet"]),
    ("a runnable orphan sweep",
     ("skribl/sweep.py", r"def main"),
     [r"nothing shipped could (run|invoke) it"]),
    ("selection and move in Flip",
     ("harness/verify_select.py", r"check\("),
     [r"every mistake is currently undo-and-redraw"]),
]


def _proof_holds(path, needle):
    f = ROOT / path
    return f.is_file() and re.search(needle, f.read_text(encoding="utf-8")) is not None


def _denials(text, patterns):
    """Where a capability is denied, by PARAGRAPH, not by line.

    The first version of this matched line by line and missed the first thing it
    was pointed at afterwards: FUTURE.md still listed "Selection and transform.
    Lasso, move, scale, rotate ... every mistake is currently undo-and-redraw"
    as ship-worthy, months after all of it shipped, and the gate passed it
    because the phrase wraps between "is" and "currently". Markdown wraps at
    eighty columns, so nearly every multi-word claim straddles a line and a
    line-scoped matcher would have missed most of what this exists to catch.

    Paragraphs are the unit prose is actually written in, so whitespace is
    normalised across the whole paragraph before matching and the reported line
    is where the paragraph starts. The exemption window is the paragraph itself
    plus the six lines above it, which is how a "SUPERSEDED" note above a block
    still covers the block.
    """
    lines = text.splitlines()
    hits = []
    start = None
    for i in range(len(lines) + 1):
        blank = i >= len(lines) or not lines[i].strip()
        if not blank:
            if start is None:
                start = i
            continue
        if start is None:
            continue
        para_lines = lines[start:i]
        para = re.sub(r"\s+", " ", " ".join(para_lines))
        if any(re.search(pat, para, re.I) for pat in patterns):
            window = "\n".join(lines[max(0, start - 6):i])
            if not EXEMPT.search(window):
                hits.append((start + 1, para.strip()[:100]))
        start = None
    return hits


_claim_failures = 0
for _entry in CLAIMS:
    label, (proof_path, proof_needle), patterns = _entry[:3]
    extra = _entry[3] if len(_entry) > 3 else []
    holds = _proof_holds(proof_path, proof_needle)
    check(f"the proof for '{label}' is present ({proof_path})", holds,
          "without it this claim cannot be gated at all")
    if not holds:
        continue
    offenders = []
    for rel in list(CURRENT_DOCS) + list(extra):
        doc = ROOT / rel
        if not doc.is_file():
            continue
        for lineno, text in _denials(doc.read_text(encoding="utf-8"), patterns):
            offenders.append(f"{rel}:{lineno} {text!r}")
    _claim_failures += len(offenders)
    _where = "doc" if not extra else "doc or source file"
    check(f"no current {_where} says '{label}' is unshipped", not offenders,
          " | ".join(offenders[:3]) + (f" (+{len(offenders)-3} more)"
                                       if len(offenders) > 3 else ""))

# The gate has to be able to FAIL, or it is decoration. Feed the matcher the
# exact sentence that shipped in v224 and require a hit; then mark it historical
# the way a real document would and require the hit to disappear.
_probe = "Pad's autosave holds strokes but not media bytes, so drafts are lossy."
check("MUTATION: the matcher catches the sentence that actually shipped",
      len(_denials(_probe, CLAIMS[0][2])) == 1, _probe)
# The regression for the hole above: the same sentence, wrapped the way a
# markdown document wraps it. A line-scoped matcher scores zero here.
_wrapped = ("Pad's autosave holds strokes but not\nmedia bytes, so drafts are "
            "lossy.")
check("MUTATION: ...and catches it WRAPPED across lines, which is how prose is",
      len(_denials(_wrapped, CLAIMS[0][2])) == 1,
      "markdown wraps at 80 columns; a line-scoped matcher misses most claims")
check("MUTATION: a denial split across a blank line is NOT one paragraph",
      not _denials("Pad's autosave holds strokes but not\n\nmedia bytes.",
                   CLAIMS[0][2]),
      "paragraphs are the unit, so unrelated neighbours cannot be glued together")
check("...and an explicitly superseded line is exempt, so history stays sayable",
      not _denials("This is SUPERSEDED:\n" + _probe, CLAIMS[0][2]),
      "a changelog must be able to state what used to be true")
check("...and an unrelated sentence is not a false positive",
      not _denials("Pad's autosave stores strokes and media bytes durably.",
                   CLAIMS[0][2]))


bad = [r for r in results if not r[0]]
print(f"\n{'='*62}\n{len(results)-len(bad)}/{len(results)} passed" +
      ("" if not bad else "  FAILURES: " + ", ".join(r[1] for r in bad)))
# This suite printed its failures and then exited 0, so run_harness.sh — which
# takes ok/FAIL from the exit code — reported it as "ok — 32/33 passed" and the
# aggregate counted the run as PASS with a failed assertion in it. A suite that
# fails must SAY so in the only channel the runner reads.
import sys
sys.exit(1 if bad else 0)
