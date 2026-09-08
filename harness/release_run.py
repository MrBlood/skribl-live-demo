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
import json
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
HARNESS = ROOT / "harness"

# Excluded from the tree hash for the same reason run_harness.sh excludes them:
# they are written AFTER a run, so including them means recording a result
# changes the tree whose hash was just recorded. Kept in step by verify_docs.
ATTESTATION = "harness/MP4-ATTESTATION.txt"

GENERATED = {"harness/LAST-RUN.txt", "SHA256SUMS", "README.md",
             "harness/README.md", "docs/HANDOFF.md", "START-HERE.md",
             "harness/RELEASE.md",
             # v211: verify_postgres writes gunicorn logs beside itself; they
             # are run artefacts, not tree, and must not move the frozen hash
             # between batches (the F3 host log did exactly that once).
             "harness/.pg_gunicorn.log", "harness/.pg_f3_gunicorn.log",
             # The MP4 attestation NAMES a tree hash, so including it in that
             # hash would be circular: writing the evidence would change the
             # thing the evidence is about, and the file could never match.
             # Same argument as RELEASE.md above, which states the hash it is
             # excluded from. run_harness.sh's _tree_files must exclude it too
             # or the banner and this file print different hashes for one tree
             # — the v221 defect, which is why both lists carry the same names.
             # SPELLED OUT rather than written as the ATTESTATION constant: the
             # parity check in verify_docs.py compares the two lists as LITERAL
             # strings, so a name that reaches this set through a variable is
             # invisible to it. Caught by that check on the first run.
             "harness/MP4-ATTESTATION.txt"}

# WHY A SUITE IS ALONE IN A BATCH — the whole decision, stated once.
#
# Batches exist because a bare run hangs. A suite SHARES a batch unless one of
# three things is true of it, and every solo batch below is tagged with which:
#
#   measures  It reads rendered geometry, canvas pixels or frame pacing. A
#             second Chromium in the same batch competes for the same CPU, and
#             a contention spike then reads as a moved pixel or a pacing
#             failure rather than as load. This is the common case, and it is
#             not theoretical: verify_hold flaked exactly this way in the v264
#             run, and its assertion carries a contention tolerance because of
#             it (see the note at that tolerance in verify_hold.py).
#   size      It will not finish inside one sandbox invocation. A batch that
#             never finishes never checkpoints, so a killed run restarts from
#             the top instead of resuming where it stopped.
#   store     It mutates state a neighbour can SEE — a media root, the shared
#             server's posts, a database. This is CORRECTNESS rather than
#             speed, and it is the only reason that names specific neighbours,
#             so those batches keep a note saying which and why. Nothing else
#             below needs one.
#
#   unrecorded  Marks a solo batch that meets none of the three. The suite
#             neither measures nor mutates, and sits alone only because that is
#             how this list grew. The tag records that no reason is on file —
#             NOT that merging it is safe, which nobody has measured.
#
# ADDING A SUITE MEANS ADDING A LINE HERE. The run refuses to start while any
# suite on disk is in no batch; that refusal has caught an unplaced suite three
# times, and it is the only thing that does.
BATCHES = [
    ["verify_ux.py"],                      # size
    ["verify_a11y.py"],                    # measures — keys against a playing scrubber
    ["verify_tools.py"],                   # size
    ["verify_move.py", "verify_pages.py"],
    ["verify_hold.py"],                    # measures — frame pacing
    ["verify_review.py", "verify_help.py", "verify_tips.py"],
    ["verify_exportui.py", "verify_exopts.py", "verify_dots.py", "verify_fix.py"],
    ["verify_amber.py", "verify_posted.py", "verify_report.py", "verify_canvas.py"],
    ["verify_padcanvas.py", "verify_pressure.py", "verify_lib.py", "verify_docs.py",
     "verify_integration.py", "verify_scrub.py"],
    ["verify_player_isolation.py"],        # measures, size
    ["verify_inline.py"],                  # measures
    ["verify_compose.py"],                 # measures
    # store: server-side creation and server-side DELETION, the two host-facing
    # Python entry points. Each builds its own Flask apps over its own temporary
    # SQLite file, so neither counts somebody else's posts and neither can be
    # counted. They keep this batch to themselves for that reason, not for
    # isolation from each other.
    #
    # verify_deletion sits here rather than beside verify_deletion_foundation
    # despite the name: that suite sweeps orphans FOR REAL against a live media
    # root. This one never touches a store.
    ["verify_createpost.py", "verify_deletion.py"],
    ["verify_example.py"],                 # measures — records a real drawing
    ["verify_audiosession.py"],            # measures — audio off an analyser tap
    ["verify_library.py"],                 # unrecorded
    ["verify_player_photo.py", "verify_sharecard.py"],
    ["verify_visual.py"],                  # measures
    ["verify_flipmotion.py"],              # measures
    ["verify_framecache.py"],              # measures
    ["verify_parity.py"],                  # measures
    ["verify_audio.py", "verify_seam.py", "verify_loopcap.py", "verify_audiostate.py"],
    ["verify_gifenc.py", "verify_muxer.py", "verify_mp4.py", "verify_flipmeta.py"],
    ["verify_feed.py", "verify_media.py", "verify_storage.py", "verify_privacy.py",
     # store: verify_deletion_foundation runs LAST here and brings its own
     # local-media server, on its own port with an isolated media root, because
     # it calls sweep_orphans with dry_run=False. Pointed at a shared root it
     # deletes other suites' media — observed doing exactly that. It must never
     # share a store with verify_media or verify_storage, which is also why it
     # cannot just take the ambient backend: verify_storage asserts the default
     # instance stores media INLINE.
     "verify_deletion_foundation.py"],
    ["verify_csp.py", "verify_csrf.py", "verify_race.py", "verify_prefix.py",
     "verify_delivery.py", "verify_surfaces.py"],
    ["verify_version.py", "verify_migrations.py", "verify_postgres.py"],
    # store: externalised and backfill each boot TWO instances and post through
    # them, so they are kept out of verify_deletion_foundation's batch.
    ["verify_externalised.py", "verify_backfill.py", "verify_mediaauthz.py"],
    ["verify_cssplit.py"],                 # measures
    ["verify_keys.py", "verify_strokegroups.py", "verify_sheetfit.py",
     "verify_apiedges.py", "verify_txcontract.py", "verify_assetcache.py",
     "verify_mimeparity.py"],
    ["verify_jsstrip.py"],                 # unrecorded
    ["verify_s3.py"],                      # unrecorded
    ["verify_layout.py"],                  # measures — geometry at eight widths
    ["verify_drafts.py"],                  # measures — multi-second settles
    ["verify_tween.py"],                   # measures
    ["verify_liquify.py"],                 # measures
    ["verify_sharedrules.py", "verify_theme.py", "verify_boot.py"],
    ["verify_nametab.py"],                 # unrecorded
    ["verify_tray.py", "verify_select.py", "verify_pillfit.py",
     "verify_flipdraft.py", "verify_fuzz.py"],
    # store: posts four rejected payloads and one accepted one to the shared
    # server, so it stays out of verify_deletion_foundation's batch.
    ["verify_medialimits.py"],
    ["verify_sweepjob.py"],                # unrecorded
    # store: drives a CLI as a subprocess against its own temp database, so it
    # wants no neighbour's server or schema in the way.
    ["verify_takedown.py"],
    ["verify_hostseams.py"],               # unrecorded
    ["verify_hostconfig.py"],              # unrecorded
    ["verify_beading.py"],                 # measures — alpha profiles
    ["verify_pagespan.py"],                # unrecorded
    ["verify_sizeclass.py"],               # measures
    ["verify_compactops.py"],              # measures
    ["verify_fill.py"],                    # measures
    ["verify_input.py"],                   # unrecorded
    ["verify_smudgeblur.py"],              # measures
    ["verify_stamps.py"],                  # measures
    ["verify_icons.py"],                   # measures — rasterised ink boxes
]


#: A skip that some OTHER lane proves. Keyed by suite, valued by the CI job in
#: .github/workflows/harness.yml that runs it in an environment where it cannot
#: skip. Adding a suite here is a claim that the job exists and gates on it —
#: verify_docs.py checks the job name is really in the workflow.
SKIP_COVERAGE = {
    "verify_mp4.py": "mp4",
    "verify_postgres.py": "postgres",
}


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


def mp4_attestation(frozen):
    """What the seal can honestly say about H.264, for THIS tree.

    verify_mp4.py SKIPS wherever Chromium is the browser: Playwright ships the
    open-source build, which has WebCodecs but no H.264 encoder. The CI job
    `mp4 (real Chrome)` exists to cover it and does — and an audit of v278
    pointed out that its result never reached the sealed archive, so the seal
    said "skipped 1" and nothing about whether the gap had been closed
    elsewhere. A reader could not tell "not covered" from "covered somewhere
    you cannot see".

    The attestation is that job's answer, written as a file it produces. THE
    TREE HASH IN IT MUST MATCH THE ONE THIS RUN FROZE — an attestation for a
    different tree is evidence about different code, and accepting one would be
    worse than having none, because the seal would then assert coverage it does
    not have.

    Returns a single line for RELEASE.md. It never raises and never blocks a
    release: whether an unverified MP4 path is shippable is a product decision,
    and the seal's job is to state the fact, not to make it.
    """
    f = ROOT / ATTESTATION
    if not f.is_file():
        return ("NOT VERIFIED for this tree — no attestation. Run the "
                "'mp4 (real Chrome)' CI job, or "
                "SKRIBL_BROWSER_CHANNEL=chrome ./harness/run_harness.sh "
                "verify_mp4.py on a machine with Google Chrome.")
    fields = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fields[k.strip().lower()] = v.strip()
    got = fields.get("tree", "")
    if got != frozen:
        return (f"STALE — the attestation describes tree {got[:12] or '?'}, "
                f"this release is {frozen[:12]}. Evidence about different code.")
    if fields.get("result", "").upper() != "PASS":
        return f"FAILED on {fields.get('channel', '?')} — {fields.get('result')}"
    return (f"verified on {fields.get('channel', '?')}, "
            f"{fields.get('assertions', '?')} assertions, "
            f"{fields.get('generated', 'time unknown')}")


def external_coverage(frozen, skipped):
    """Which mandatory EXTERNAL lanes have tree-bound evidence in hand.

    The local run proves what ran locally. Two kinds of coverage live outside it
    and they are NOT the same kind of thing, so they are never summed:

      ATTESTED — the `mp4` lane writes harness/MP4-ATTESTATION.txt, which names
      the tree it describes. mp4_attestation() refuses one for a different tree,
      so a local run can actually CHECK this.

      CLAIMED — SKIP_COVERAGE says some CI job runs a suite this environment
      skipped. Nothing a local run can read says that job was green on this
      tree. verify_docs.py checks the job EXISTS in the workflow; existence is
      not a result.

    Returns (attested, pending) as display strings. Anything in `pending` means
    the local record cannot speak for that lane.
    """
    attested, pending = [], []
    for name in skipped:
        lane = SKIP_COVERAGE.get(name)
        if lane is None:
            pending.append(f"`{name}` — NOT covered anywhere")
        elif name == "verify_mp4.py":
            line = mp4_attestation(frozen)
            (attested if line.startswith("verified") else pending).append(
                f"`{name}` — {line.split(',')[0]}")
        else:
            pending.append(f"`{name}` — claimed by the `{lane}` CI job, "
                           "no tree-bound attestation reaches this run")
    return attested, pending


def release_status(ok, pending):
    """The headline, which must never outrun the evidence under it.

    A bare `PASS` was read — correctly, by an outside review — as a claim about
    the whole release when the predicate behind it only ever covered the local
    suite ledger: a skip lands in `skipped`, never in `failed`, and the MP4
    attestation is rendered beside the result rather than gating it. That is a
    deliberate design (the seal states the fact, it does not make the shipping
    decision) and the defect was the WORD, not the gate. So the gate is
    unchanged and the label is split.
    """
    if not ok:
        return "FAIL"
    if pending:
        return "LOCAL PASS — EXTERNAL COVERAGE PENDING"
    return "FULL RELEASE PASS"


def source_state():
    """('clean' | 'generated-only dirty' | 'dirty', [paths]) for the working tree.

    "Dirty" means two opposite things here and a bare -dirty suffix reported
    them identically — the v282 seal recorded `0d88605-dirty` and an outside
    audit could not tell which it was.

      GENERATED files are written into the tree BY the release itself.
      harness/MP4-ATTESTATION.txt is dropped in DURING the run so RELEASE.md can
      report the H.264 result on the tree it describes, and RELEASE.md and
      LAST-RUN.txt are written at the end. Dirt there is the process working.

      Everything else is source no commit records, which is the reproducibility
      hole the audit was actually pointing at.

    The audit's original wording — "require a clean working tree" — would have
    forbidden the mid-run attestation write that v282's own process fix requires,
    so the rule is narrowed to the second case and the first is enumerated rather
    than trusted.
    """
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", "HEAD"],
                             capture_output=True, text=True, timeout=30)
    except Exception:
        return "unknown", []
    if out.returncode != 0:
        return "unknown", []
    dirty = sorted(p for p in out.stdout.split("\n") if p.strip())
    if not dirty:
        return "clean", []
    source = [p for p in dirty if p not in GENERATED]
    return ("dirty", source) if source else ("generated-only dirty", dirty)


def tree_hash():
    inner = "".join(
        f"{hashlib.sha256((ROOT / f).read_bytes()).hexdigest()}  {f}\n"
        for f in tree_files())
    return hashlib.sha256(inner.encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    # RESUME. A full aggregate takes ~25 minutes of wall clock. Some execution
    # environments — including the sandbox this is usually run in — cap a single
    # invocation well below that and do not let a background process survive
    # between invocations, so the run is killed part-way and no evidence is
    # produced at all. The tempting workaround is to run batches by hand and add
    # the numbers up, which is precisely the hand-typed total this whole file
    # exists to abolish.
    #
    # Instead the run checkpoints after every batch and can be re-invoked until
    # it completes. The guarantees are unchanged, and the tree-hash one is
    # actually STRONGER: the frozen hash is stored in the checkpoint and
    # re-verified on every resume, so an edit made BETWEEN invocations aborts
    # the run exactly as an edit between batches does.
    #
    # The state file lives outside the tree by default. Putting it inside would
    # mean a file written during the run changing the hash of the tree the run
    # is about to describe — the defect GENERATED exists to prevent.
    ap.add_argument("--state", default="/tmp/skribl-release-state.json",
                    help="checkpoint path (outside the tree by design)")
    ap.add_argument("--budget", type=float, default=0.0,
                    help="seconds of wall clock before checkpointing and exiting "
                         "with 75 (incomplete); 0 means run to completion")
    ap.add_argument("--restart", action="store_true",
                    help="discard any existing checkpoint and start over")
    # A CHECKPOINT RUN DURING DEVELOPMENT IS LEGITIMATELY DIRTY; a final seal is
    # not. Both use this script, so the refusal has an escape rather than a
    # workflow that has to be abandoned — and RELEASE.md records which was used,
    # so "development run" cannot be mistaken for a seal after the fact.
    ap.add_argument("--allow-dirty", action="store_true",
                    help="proceed with uncommitted source changes (development "
                         "runs only; RELEASE.md records that it was used)")
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

    state, paths = source_state()
    if state == "dirty" and not args.allow_dirty:
        print("REFUSED: the working tree has uncommitted changes outside the")
        print("generated-evidence set, so the hash this run is about to freeze")
        print("would describe source that no commit records:")
        for f in paths:
            print(f"    {f}")
        print("\nCommit them, or pass --allow-dirty for a development run "
              "(which says so in RELEASE.md).")
        return 1
    if state == "generated-only dirty":
        print("source state   : generated-only dirty — " + ", ".join(paths))
    elif state == "dirty":
        print("source state   : DIRTY, --allow-dirty given — " + ", ".join(paths))

    frozen = tree_hash()
    state_path = pathlib.Path(args.state)
    rows, skipped, total, failed = [], [], 0, []
    diagnostics = []
    done = 0

    if args.restart and state_path.exists():
        state_path.unlink()
        print("checkpoint discarded (--restart)")

    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state.get("frozen") != frozen:
            # Refuse rather than silently starting over: a resumed run that
            # quietly restarts on a different tree would report batches from
            # two trees under one hash, which is the exact claim this file
            # exists to make impossible.
            print(f"ABORT: the tree changed since the checkpoint was written "
                  f"({tree_hash()[:12]} != {state['frozen'][:12]}).\n"
                  f"       Release evidence must describe ONE tree. Re-run with "
                  f"--restart to begin a fresh run on the current tree.")
            return 1
        if state.get("batches") != [list(b) for b in BATCHES]:
            print("ABORT: the batch layout changed since the checkpoint was "
                  "written. Re-run with --restart.")
            return 1
        rows = [tuple(r) for r in state["rows"]]
        skipped = state["skipped"]
        total = state["total"]
        failed = state["failed"]
        diagnostics = state["diagnostics"]
        done = state["done"]
        print(f"resuming: {done}/{len(BATCHES)} batches already recorded "
              f"on tree {frozen[:12]}")

    print(f"frozen tree    : {frozen}\n")
    started = time.monotonic()

    def save(done_count):
        state_path.write_text(json.dumps({
            "frozen": frozen,
            "batches": [list(b) for b in BATCHES],
            "rows": [list(r) for r in rows],
            "skipped": skipped, "total": total, "failed": failed,
            "diagnostics": diagnostics, "done": done_count,
        }))

    def tail(text, lines=25, chars=2500):
        # Bounded on purpose: a full Chromium batch log is thousands of lines,
        # and an unbounded dump in a release document is not a diagnostic, it is
        # a place diagnostics go to hide. The end is where the failure is.
        t = "\n".join(text.strip().splitlines()[-lines:])
        return t[-chars:] if len(t) > chars else t

    for n, batch in enumerate(BATCHES, 1):
        if n <= done:
            continue
        if args.budget and time.monotonic() - started > args.budget:
            save(n - 1)
            print(f"\nBUDGET REACHED — checkpointed after batch {n - 1}/"
                  f"{len(BATCHES)}. Re-invoke to continue; the frozen tree is "
                  f"re-verified on resume.")
            return 75
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
        save(n)

    seen = {r[0] for r in rows}
    never = [s for s in on_disk if s not in seen]
    ok = not failed and not never
    _attested, _pending = external_coverage(frozen, skipped)

    lines = [
        "# Release evidence", "",
        "Generated by `harness/release_run.py`. Every fact here is computed, "
        "not typed — see the note at the top of that file for why.", "",
        f"    release status   {release_status(ok, _pending)}",
        f"    local result     {'PASS' if ok else 'FAIL'}"
        f"   (every suite that ran here, on this tree)",
        f"    tested tree hash {frozen}",
        f"    source state     " + (
            "clean"
            if state == "clean" else
            f"{state} ({', '.join(paths)})"
            if state == "generated-only dirty" else
            f"DIRTY, --allow-dirty used ({', '.join(paths)}) — "
            f"NOT A SEALABLE RUN"
            if state == "dirty" else
            "unknown (not a git checkout)"),
        f"    SKRIBL_VERSION   " + re.search(
            r'SKRIBL_VERSION\s*=\s*"([^"]+)"',
            (ROOT / "skribl" / "core.py").read_text()).group(1),
        f"    python           {sys.version.split()[0]}",
        f"    suites on disk   {len(on_disk)}",
        f"    suites reported  {len(seen)}",
        f"    assertions       {total}",
        f"    skipped          {len(skipped)}" +
        (f"  ({', '.join(skipped)})" if skipped else ""),
        f"    mp4 (H.264)      {mp4_attestation(frozen)}",
        f"    external lanes   {len(_attested)} attested, {len(_pending)} pending",
        f"    generated        {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%dT%H:%M:%SZ}",
        "",
        "A skip is not coverage. Suites that skip are listed above by name so "
        "that an absence of failures is never read as an absence of gaps.", "",
        "THE HEADLINE IS SPLIT IN TWO BECAUSE THE PREDICATE ONLY EVER COVERED "
        "HALF OF IT. `local result` is computed from the suites that ran here: "
        "a skip lands in the skipped list, never in the failed one, and the MP4 "
        "attestation is stated beside the result rather than gating it — "
        "deliberately, because whether an unverified path is shippable is a "
        "product decision and the seal's job is to state the fact. So a single "
        "`PASS` could sit above a STALE attestation and a postgres lane nobody "
        "had run. `release status` is FULL RELEASE PASS only when the local run "
        "is green AND every external lane below has tree-bound evidence in "
        "hand; otherwise it says LOCAL PASS — EXTERNAL COVERAGE PENDING and "
        "names what is missing. The gate did not change. The word did. "
        "(Outside review of v285, P1-M-01.)", "",
        "THREE HASHES IN THIS PROJECT ARE NOT THE SAME HASH, and calling all of "
        "them \"the tree hash\" is how they get confused. The TESTED TREE HASH "
        "above is the one this run froze and the suites ran against; it "
        "deliberately EXCLUDES the docs that carry "
        "generated counts (README.md, START-HERE.md, docs/HANDOFF.md, "
        "harness/README.md), this file, harness/LAST-RUN.txt and SHA256SUMS: "
        "each is written AFTER the run, so a hash covering them would describe "
        "a tree that no longer exists once they are stamped. Their final bytes "
        "are covered instead by `SHA256SUMS`, which is regenerated last, and "
        "`verify_docs.py` fails if any stamped count disagrees with this run. "
        "(Outside review of v263, M6.)", "",
    ]
    # Where a skip IS covered, say where — generated from the table below, not
    # typed into prose. The v224 outside review filed the MP4 skip as a finding
    # and recommended a CI lane with real H.264, which .github/workflows has run
    # since v103 and which FAILS if the suite merely skips. The lane shipped
    # inside the reviewed archive; nothing in the evidence pointed at it, so a
    # reader of this file had no way to know the gap was already closed. An
    # uncovered skip still says so, loudly.
    for name in skipped:
        lane = SKIP_COVERAGE.get(name)
        lines += [f"  * `{name}` — " + (
            f"covered by the `{lane}` CI job in .github/workflows/harness.yml, "
            "which installs the environment this one lacks and fails if the "
            "suite skips there too."
            if lane else
            "NOT covered anywhere. This is a real gap in the release.")]
    if _pending:
        lines += ["**External lanes this record cannot speak for:**"]
        lines += [f"  * {d}" for d in _pending]
        lines += [""]
    if _attested:
        lines += ["**External lanes attested for THIS tree:**"]
        lines += [f"  * {d}" for d in _attested]
        lines += [""]
    if skipped:
        lines += [""]
    lines += [
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

    # LAST-RUN.txt is written by run_harness.sh, which this drives ONE BATCH AT
    # A TIME — so the record left behind described only the final batch, and
    # stamp_docs.py (invoked by the runner at the end of that batch) stamped the
    # docs from it. A completed 42-suite release therefore published README.md
    # saying "78 assertions across 2 suites" beside a RELEASE.md saying 1693
    # across 42. Both were machine-generated and they contradicted each other,
    # which is the exact defect the generated-not-typed rule exists to prevent —
    # it just moved from typed prose into a second generator.
    #
    # The whole run is the run. Rewrite the record to describe every batch, then
    # re-stamp from it so the docs agree with RELEASE.md.
    # The whole run is the run. Keep the RUN CONTEXT block the runner itself
    # wrote — every environment fact in it (Chromium build, SQLAlchemy version,
    # DATABASE_URL class) is machine-generated and would be invented if this
    # rewrote the header — and replace only the AGGREGATE with one covering
    # every batch. stamp_docs.py then reads the widened record.
    _lr = HARNESS / "LAST-RUN.txt"
    _prev = _lr.read_text(encoding="utf-8") if _lr.is_file() else ""
    _marker = "================ AGGREGATE"
    _header = _prev.split(_marker)[0] if _marker in _prev else ""
    _header = re.sub(r"^(Tree SHA-256\s+:\s*)\S+$", r"\g<1>" + frozen, _header,
                     flags=re.M)
    summary_lines = [f"  {n}: " + ("SKIPPED (0 assertions) — " + d
                                   if s == "skip" else
                                   ("ok — " if s == "pass" else "FAIL — ") + d)
                     for n, s, d in sorted(rows)]
    _lr.write_text(_header + "\n".join([
        "================ AGGREGATE (machine-generated) ================",
        f"# whole release run: {len(BATCHES)} batches recorded as one run",
        f"suites requested : {len(on_disk)}",
        *summary_lines,
        f"assertions passed: {total}   (skipped suites contribute 0)",
        f"suites skipped   : {len(skipped)}",
        f"suites with problems: {len(failed) + len(never)}",
        "",
    ]))
    # The final stamp is part of the release, not an afterthought: if it fails,
    # the docs keep the PREVIOUS run's counts while RELEASE.md carries this
    # one's, and nothing said so. (Outside review of v263, M7.) Surface it.
    _stamp = subprocess.run([sys.executable, str(HARNESS / "stamp_docs.py")],
                            cwd=str(ROOT), capture_output=True, text=True)
    if _stamp.returncode != 0:
        sys.exit("stamp_docs.py failed after the run — the docs were NOT "
                 "updated and the release is not sealed:\n"
                 + (_stamp.stderr or _stamp.stdout).strip())

    # The run is complete, so the checkpoint has served its purpose. Leaving it
    # behind would make the NEXT release silently resume a finished run and
    # report its batches again — a stale-state failure of exactly the kind that
    # has already cost this project a debugging cycle.
    if state_path.exists():
        state_path.unlink()

    print(f"\n{'PASS' if ok else 'FAIL'} — {total} assertions, "
          f"{len(seen)}/{len(on_disk)} suites reported, {len(skipped)} skipped")
    print(f"wrote {(HARNESS / 'RELEASE.md').relative_to(ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
