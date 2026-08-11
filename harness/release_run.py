#!/usr/bin/env python3
"""Aggregate release evidence across every suite, on one frozen tree.

WHY THIS EXISTS. `harness/LAST-RUN.txt` records ONE invocation. A full
single-invocation run hangs, so suites are named in batches — which means the
last batch overwrites the record of every earlier one, and `stamp_docs.py`
stamps whichever invocation happened last. The archive could therefore say
"421 assertions, 8 suites, all green" while saying nothing at all about the
29 suites that were also run and also passed. An external review read that
statement exactly as written and concluded, correctly, that it was evidence
for the latest feature batch and not for the release.

WHAT IT GUARANTEES. The tree hash is computed BEFORE the first batch and
re-verified before every subsequent one, so a source edit between batches is
caught rather than averaged away. Every suite in harness/ must appear in
exactly one batch or the run fails: a suite cannot be quietly dropped by being
left out of the list. Skips are counted separately from passes, because a skip
is not coverage.

    python3 harness/release_run.py                 # every suite, default batches
    python3 harness/release_run.py --dry-run       # check batch coverage only

Writes harness/RELEASE.md — the one document other docs should point at for
volatile release facts, so they stop being hand-typed.
"""
import argparse
import datetime
import hashlib
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
HARNESS = ROOT / "harness"

# Excluded from the tree hash for the same reason run_harness.sh excludes them:
# they are written AFTER a run, so including them means recording a result
# changes the tree whose hash was just recorded. Kept in step by verify_docs.
GENERATED = {"harness/LAST-RUN.txt", "SHA256SUMS", "README.md",
             "harness/README.md", "docs/HANDOFF.md", "START-HERE.md",
             "harness/RELEASE.md"}

# Batches exist because a bare run hangs. Grouped so a browser batch stays
# small enough to finish, and so the server/security suites — which do not
# drive Chromium — are not held hostage to a browser batch timing out.
BATCHES = [
    ["verify_move.py", "verify_ux.py", "verify_pages.py", "verify_hold.py"],
    ["verify_review.py", "verify_help.py", "verify_tips.py"],
    ["verify_exportui.py", "verify_exopts.py", "verify_dots.py", "verify_fix.py"],
    ["verify_amber.py", "verify_posted.py", "verify_report.py", "verify_canvas.py"],
    ["verify_padcanvas.py", "verify_pressure.py", "verify_lib.py", "verify_docs.py",
     "verify_integration.py"],
    ["verify_parity.py"],
    ["verify_audio.py", "verify_seam.py", "verify_loopcap.py"],
    ["verify_gifenc.py", "verify_muxer.py", "verify_mp4.py", "verify_flipmeta.py"],
    ["verify_feed.py", "verify_media.py", "verify_storage.py", "verify_privacy.py"],
    ["verify_csp.py", "verify_csrf.py", "verify_race.py", "verify_prefix.py"],
    ["verify_version.py", "verify_migrations.py", "verify_postgres.py"],
]


def tree_files():
    out = subprocess.run(["find", ".", "-type", "f"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.split("\n")
    keep = []
    for line in out:
        if not line:
            continue
        rel = line[2:] if line.startswith("./") else line
        if rel.startswith(".git/") or rel.startswith("instance/"):
            continue
        if "__pycache__" in rel or rel.endswith(".pyc"):
            continue
        if rel in GENERATED:
            continue
        keep.append(rel)
    return sorted(keep)


def tree_hash():
    inner = "".join(
        f"{hashlib.sha256((ROOT / f).read_bytes()).hexdigest()}  {f}\n"
        for f in tree_files())
    return hashlib.sha256(inner.encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    on_disk = sorted(p.name for p in HARNESS.glob("verify_*.py"))
    listed = [s for b in BATCHES for s in b]
    missing = [s for s in on_disk if s not in listed]
    unknown = [s for s in listed if s not in on_disk]
    dupes = sorted({s for s in listed if listed.count(s) > 1})
    if missing or unknown or dupes:
        print("BATCH COVERAGE IS WRONG — a release cannot proceed:")
        if missing:
            print("  in harness/ but in no batch :", ", ".join(missing))
        if unknown:
            print("  batched but not on disk     :", ", ".join(unknown))
        if dupes:
            print("  listed more than once       :", ", ".join(dupes))
        return 1
    print(f"batch coverage: all {len(on_disk)} suites appear exactly once")
    if args.dry_run:
        return 0

    frozen = tree_hash()
    print(f"frozen tree    : {frozen}\n")
    rows, skipped, total, failed = [], [], 0, []
    diagnostics = []

    def tail(text, lines=25, chars=2500):
        # Bounded on purpose: a full Chromium batch log is thousands of lines,
        # and an unbounded dump in a release document is not a diagnostic, it is
        # a place diagnostics go to hide. The end is where the failure is.
        t = "\n".join(text.strip().splitlines()[-lines:])
        return t[-chars:] if len(t) > chars else t

    for n, batch in enumerate(BATCHES, 1):
        now = tree_hash()
        if now != frozen:
            print(f"ABORT: the tree changed before batch {n} ({now[:12]} != "
                  f"{frozen[:12]}). Release evidence must describe ONE tree.")
            return 1
        print(f"--- batch {n}/{len(BATCHES)}: {' '.join(batch)}")
        r = subprocess.run([str(HARNESS / "run_harness.sh")] + batch,
                           cwd=ROOT, capture_output=True, text=True)
        out = r.stdout
        reported_here = set()
        # `(\w+) — ` used to be the status pattern, which silently failed to
        # match run_harness.sh's own skip line:
        #   verify_mp4.py: SKIPPED (0 assertions) — no H.264 profile supported
        # The parenthetical breaks \w+, so a DECLARED skip with a stated reason
        # was recorded as "reported nothing" — turning the one thing the runner
        # explained into the one thing the report could not.
        for m in re.finditer(r"^  (verify_\S+): (.+?) — (.*)$", out, re.M):
            name, status, detail = m.group(1), m.group(2).strip(), m.group(3).strip()
            got = re.match(r"(\d+)/(\d+) passed", detail)
            if status.upper().startswith("SKIP"):
                skipped.append(name)
                rows.append((name, "skip", detail))
            elif status == "ok" and got:
                total += int(got.group(1))
                rows.append((name, "pass", detail))
            else:
                failed.append(name)
                rows.append((name, "FAIL", detail))
            reported_here.add(name)
            print(f"    {name:26} {status:6} {detail}")

        # A batch that dies before run_harness.sh emits its aggregate stanza
        # produces no rows at all, and the report would then say only that
        # these suites "reported nothing" — true, and useless. The exit code
        # and the tail of the child's output are what distinguish a missing
        # dependency from a hung browser from a genuine assertion failure.
        silent = [s for s in batch if s not in reported_here]
        if r.returncode != 0 or silent:
            diagnostics.append({
                "batch": n, "suites": batch, "silent": silent,
                "returncode": r.returncode,
                "stdout": tail(out), "stderr": tail(r.stderr),
            })
            print(f"    !! batch {n} exited {r.returncode}"
                  + (f"; no output from: {', '.join(silent)}" if silent else ""))
            if r.stderr.strip():
                print("    !! stderr tail: "
                      + r.stderr.strip().splitlines()[-1][:160])

    seen = {r[0] for r in rows}
    never = [s for s in on_disk if s not in seen]
    ok = not failed and not never

    lines = [
        "# Release evidence", "",
        "Generated by `harness/release_run.py`. Every fact here is computed, "
        "not typed — see the note at the top of that file for why.", "",
        f"    result           {'PASS' if ok else 'FAIL'}",
        f"    tree hash        {frozen}",
        f"    SKRIBL_VERSION   " + re.search(
            r'SKRIBL_VERSION\s*=\s*"([^"]+)"',
            (ROOT / "skribl" / "core.py").read_text()).group(1),
        f"    python           {sys.version.split()[0]}",
        f"    suites on disk   {len(on_disk)}",
        f"    suites reported  {len(seen)}",
        f"    assertions       {total}",
        f"    skipped          {len(skipped)}" +
        (f"  ({', '.join(skipped)})" if skipped else ""),
        f"    generated        {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%dT%H:%M:%SZ}",
        "",
        "A skip is not coverage. Suites that skip are listed above by name so "
        "that an absence of failures is never read as an absence of gaps.", "",
        "| suite | result | detail |", "| --- | --- | --- |",
    ]
    lines += [f"| `{n}` | {s} | {d} |" for n, s, d in sorted(rows)]
    if never:
        lines += ["", "**Suites that reported nothing:** " +
                  ", ".join(f"`{s}`" for s in never)]
    if diagnostics:
        lines += ["", "## Batch diagnostics", "",
                  "Exit codes and bounded output tails for every batch that "
                  "failed or went silent. A suite that reported nothing is not "
                  "evidence of anything until you can see why."]
        for d in diagnostics:
            lines += ["", f"### Batch {d['batch']} — exit {d['returncode']}", "",
                      f"Suites: {', '.join('`' + s + '`' for s in d['suites'])}"]
            if d["silent"]:
                lines.append("No output from: "
                             + ", ".join(f"`{s}`" for s in d["silent"]))
            if d["stderr"]:
                lines += ["", "stderr (tail):", "", "```", d["stderr"], "```"]
            if d["stdout"]:
                lines += ["", "stdout (tail):", "", "```", d["stdout"], "```"]
    (HARNESS / "RELEASE.md").write_text("\n".join(lines) + "\n")

    print(f"\n{'PASS' if ok else 'FAIL'} — {total} assertions, "
          f"{len(seen)}/{len(on_disk)} suites reported, {len(skipped)} skipped")
    print(f"wrote {(HARNESS / 'RELEASE.md').relative_to(ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
