"""`python -m skribl.sweep` — run the orphan sweep as a scheduled job.

Outside review, finding #6. `storage.sweep_orphans` has existed since v180 and
reclaims real disk, but nothing shipped that could RUN it. Every deployment was
left to write its own entry point: resolve the app, find the store the host
passed to `init_skribl`, get a session, decide what "dry run" means, and hope it
got the argument order right on a function whose second positional argument is
seconds and whose third deletes user data. That is a lot of loaded footgun to
leave as an exercise, and the docs described the sweep as if it were operable.

WHAT THIS IS NOT. It is not a daemon and it does not schedule itself. It runs
once and exits, because the thing that should decide cadence is the deployment's
cron/systemd timer/scheduled job, not a library.

DRY RUN IS THE DEFAULT AND DELETION IS A FLAG. Running this with no arguments
reports what WOULD go and touches nothing. `--delete` is the wet flag, spelled
out rather than a `-d`, because the failure mode of getting it wrong is gone
user media. This mirrors `sweep_orphans(dry_run=True)`, which defaults the same
way for the same reason — the flag exists so the default can stay safe.

THE GRACE PERIOD IS THE OTHER SAFETY, and it is the one that is easy to shoot
off. Media is written BEFORE the transaction recording it commits, so an object
minutes old may belong to a post being created right now. `--older-than` below
one hour combined with `--delete` therefore needs `--i-know-the-grace-period-is-
short` as well: not to be tiresome, but because "just sweep everything" typed at
2am is exactly how a deployment deletes the media of every post in flight.

USAGE

    python -m skribl.sweep --app app:create_app                  # rehearse
    python -m skribl.sweep --app app:create_app --json           # for metrics
    python -m skribl.sweep --app app:create_app --delete         # reclaim
    python -m skribl.sweep --app app:create_app --older-than 604800 --delete

`--app` takes `module:attribute` like FLASK_APP does. A callable attribute is
treated as an app factory and called with no arguments; anything else is used as
the application object. Default `app:create_app`, which is this repository's own
factory — a host application passes its own.

EXIT CODES, because a scheduled job is read by its exit status:
    0  the sweep ran (including "found nothing", including a dry run)
    1  the sweep ran and at least one delete failed
    2  it could not run at all — bad --app, no store, no session, bad flags
"""
import argparse
import importlib
import json
import sys

from .storage import sweep_orphans_report

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_CANNOT_RUN = 2

#: Below this, --delete needs the extra acknowledgement. One hour is well under
#: the 24-hour default and still far longer than any commit this app performs.
SHORT_GRACE_SECONDS = 3600


def _die(message):
    """Exit 2 with a one-line reason on stderr.

    Not `raise SystemExit(message)`: that prints the message but exits 1, and 1
    is the code this tool reserves for "the sweep ran and some deletes failed".
    A scheduled job that cannot tell those apart cannot be alerted on.
    """
    print(f"skribl.sweep: {message}", file=sys.stderr)
    raise SystemExit(EXIT_CANNOT_RUN)


def _load_app(spec):
    """Resolve `module:attribute` to a Flask application. Exits 2 on failure."""
    if ":" not in spec:
        _die(f"--app must be module:attribute (got {spec!r}).")
    module_name, attr = spec.split(":", 1)
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        _die(f"--app: could not import {module_name!r}: "
             f"{type(exc).__name__}: {exc}")
    try:
        target = getattr(module, attr)
    except AttributeError:
        _die(f"--app: {module_name!r} has no attribute {attr!r}.")
    if callable(target):
        try:
            target = target()
        except Exception as exc:
            _die(f"--app: calling {spec} raised "
                 f"{type(exc).__name__}: {exc}")
    if not hasattr(target, "app_context"):
        _die(f"--app: {spec} is not a Flask application "
             f"(got {type(target).__name__}).")
    return target


def _find_store(app):
    """The media store the HOST passed to init_skribl, not one built here.

    Building a store from the environment would be the obvious shortcut and the
    wrong one: the sweep would then delete against whatever root the environment
    happens to name, which need not be the root the running app writes to. The
    only trustworthy answer is the object the app is actually using.
    """
    bp = app.blueprints.get("skribl")
    if bp is None:
        # A host may register the blueprint under another name.
        bp = next((b for b in app.blueprints.values()
                   if hasattr(b, "skribl_media_store")), None)
    if bp is None:
        _die("--app: that application has no Skribl blueprint registered, "
             "so there is no media store to sweep.")
    store = getattr(bp, "skribl_media_store", None)
    if store is None:
        _die("The Skribl blueprint has no media store.")
    return store


def build_parser():
    p = argparse.ArgumentParser(
        prog="python -m skribl.sweep",
        description="Reclaim stored media that no Skribl post references.",
        epilog="Dry run by default. --delete is the wet flag.")
    p.add_argument("--app", default="app:create_app",
                   help="module:attribute of the Flask app or app factory "
                        "(default: app:create_app)")
    p.add_argument("--older-than", type=int, default=86400, metavar="SECONDS",
                   help="grace period; objects younger than this are never "
                        "touched (default: 86400, one day)")
    p.add_argument("--delete", action="store_true",
                   help="actually delete. Without this nothing is removed.")
    p.add_argument("--i-know-the-grace-period-is-short", action="store_true",
                   dest="short_grace_ok",
                   help=f"required to combine --delete with --older-than under "
                        f"{SHORT_GRACE_SECONDS}s; media is written before the "
                        f"transaction recording it commits, so a short grace "
                        f"period deletes posts that are still being created")
    p.add_argument("--json", action="store_true",
                   help="print the report as one JSON object and nothing else")
    p.add_argument("--list-keys", action="store_true",
                   help="also print every key (the JSON report always has them)")
    return p


def _human(report, list_keys, out):
    verb = "would remove" if report["dry_run"] else "removed"
    print(f"{'DRY RUN — ' if report['dry_run'] else ''}"
          f"{verb} {report['removed_count']} object(s) "
          f"in {report['duration_seconds']}s", file=out)
    print(f"  listed by the store   : {report['listed']}", file=out)
    # Each line below is a reason the sweep DECLINED to delete something. A run
    # that reclaims nothing is explained by whichever of these is large, which
    # is the whole point of counting them separately.
    print(f"  not ours (namespace)  : {report['skipped_foreign']}", file=out)
    print(f"  inside grace period   : {report['skipped_young']}", file=out)
    print(f"  referenced by a post  : {report['skipped_referenced']}", file=out)
    print(f"  reused mid-sweep      : {report['skipped_reused']}", file=out)
    print(f"  candidates checked    : {report['candidates']} "
          f"in {report['chunks']} chunk(s)", file=out)
    if report["delete_error_count"]:
        print(f"  DELETES THAT FAILED   : {report['delete_error_count']}", file=out)
        for e in report["delete_errors"][:20]:
            print(f"    {e['key']}: {e['error']}", file=out)
        if report["delete_error_count"] > 20:
            print(f"    …and {report['delete_error_count'] - 20} more", file=out)
    if list_keys:
        for key in report["removed"]:
            print(f"  {verb}: {key}", file=out)
    if report["dry_run"] and report["removed_count"]:
        print("\nNothing was deleted. Re-run with --delete to reclaim these.",
              file=out)


def main(argv=None, out=None):
    out = out or sys.stdout
    args = build_parser().parse_args(argv)

    if args.older_than < 0:
        _die("--older-than cannot be negative.")
    if args.delete and args.older_than < SHORT_GRACE_SECONDS \
            and not args.short_grace_ok:
        _die(
            f"Refusing to delete with a grace period of {args.older_than}s. "
            f"Media is written before the transaction that records it commits, "
            f"so anything younger than a few minutes may belong to a post being "
            f"created right now. Raise --older-than above {SHORT_GRACE_SECONDS}, "
            f"or pass --i-know-the-grace-period-is-short if you mean it.")

    app = _load_app(args.app)
    store = _find_store(app)
    if not getattr(store, "externalises", True):
        # An inline store keeps media inside payload_json; there are no objects
        # to reclaim and iter_keys is not implemented. Say so rather than crash
        # on NotImplementedError, and exit 0 — nothing is wrong.
        print(f"{type(store).__name__} keeps media inside payload_json, so "
              f"there are no stored objects to sweep.", file=out)
        return EXIT_OK

    with app.app_context():
        from .models import session as _session
        try:
            sess = _session()
        except RuntimeError as exc:
            _die(f"No database session: {exc}")
        try:
            report = sweep_orphans_report(store, sess,
                                          older_than_seconds=args.older_than,
                                          dry_run=not args.delete)
        except Exception as exc:
            # Broad on purpose. Everything that reaches here — an unmigrated
            # database, a bucket the credentials cannot list, a host store
            # raising its own type — means the same thing operationally: the
            # sweep did not run. A scheduled job needs that as one line and
            # exit 2, not as forty lines of SQLAlchemy traceback in cron mail.
            # Per-key DELETE failures do NOT come through here; those are
            # collected in the report and are what exit 1 means.
            _die(f"the sweep could not run: {type(exc).__name__}: {exc}")

    if args.json:
        print(json.dumps(report, sort_keys=True), file=out)
    else:
        _human(report, args.list_keys, out)
    return EXIT_PARTIAL if report["delete_error_count"] else EXIT_OK


if __name__ == "__main__":       # pragma: no cover
    sys.exit(main())
