"""Withdraw a Skribl nobody else can: the operational path for a lost key.

    python -m skribl.takedown --list-orphans
    python -m skribl.takedown --reports
    python -m skribl.takedown <public-id> --delete
    python -m skribl.takedown <public-id> --visibility private
    python -m skribl.takedown <public-id> --resolve

WHY THIS EXISTS. v279 gave anonymous posts a revocation capability, and an
audit of it asked the question the migration had answered honestly and the
product had not: what about the posts that came BEFORE? The migration adds a
nullable column, so every pre-v279 row holds NULL, and `_token_matches()`
refuses NULL deliberately — an empty token matching an empty hash would make
the entire anonymous back-catalogue deletable by anybody. Correct, and it
leaves those authors with no self-service route at all.

THERE IS NO CRYPTOGRAPHIC FIX AND CLAIMING OTHERWISE WOULD BE WORSE. The server
never held a secret proving which browser created those rows, so nothing can
reconstruct that authorship after the fact. The tempting shortcut — treat
possession of the share URL as proof — is exactly wrong: the URL is the thing
the author GAVE AWAY, so it proves the opposite of ownership. The audit named
that trap explicitly and it is not taken here.

What is left is an operator doing it on request, and that is a real answer as
long as it exists, is documented, and is reachable. Before v280 `require_author
=False` existed in the Python API with nothing to invoke it: a capability with
no operational path is a capability the person answering the support mail does
not have.

THE REPORT QUEUE LANDS HERE TOO (v304). The public gallery puts Report on
every tile, and a report is a row in skribl_reports, not an action. --reports
lists the open ones grouped by post, most-reported first, with the two wet
flags above as the next step; <public-id> --resolve closes that post's rows
without touching the post, for the reports that turn out to be nothing.
Deleting a post takes its reports with it.

IT IS NOT ONLY FOR LEGACY ROWS. The same door is the one for a post-v279 author
who cleared their site data, a moderation decision, and a legal takedown. Those
are permanent needs; the legacy back-catalogue is the one that goes away.

REFUSING TO GUESS is the whole safety model here. This tool takes a public id
and acts on exactly that post. It has no search-by-title, no wildcard and no
--all, because the failure mode of an operator tool is deleting more than was
asked and every one of those would make it easier.

DRY RUN BY DEFAULT, like skribl.sweep. --delete and --visibility are the wet
flags, and neither does anything without one.

TRANSACTIONS: this owns its own, unlike everything in deletion.py. It is a
command, not a request inside a host's unit of work, so there is no outer
transaction to belong to and nobody else to commit for it.

EXIT CODES, because an operator runs this from a runbook:
    0  it did what was asked (including a dry run, including --list-orphans)
    1  the post does not exist
    2  it could not run at all — bad --app, no session, bad flags
"""
import argparse
import sys

from .deletion import delete_post, set_post_visibility
from .models import (SkriblPost, SkriblReport, session as resolve_session,
                     visibility_values)
from .sweep import _load_app, EXIT_CANNOT_RUN

EXIT_OK = 0
EXIT_NO_SUCH_POST = 1


def _die(message):
    print(f"skribl.takedown: {message}", file=sys.stderr)
    raise SystemExit(EXIT_CANNOT_RUN)


def orphans(limit=None):
    """Posts nobody can revoke: no owner, and no capability.

    This is the query an audit asked to be run against production before v279
    could be called shipped, because whether the gap has victims is a fact
    about deployed data and not about source. Exposed as a command so the
    answer is reproducible rather than a number somebody once pasted.
    """
    q = (resolve_session().query(SkriblPost)
         .filter(SkriblPost.user_id.is_(None))
         .filter(SkriblPost.delete_token_hash.is_(None))
         .order_by(SkriblPost.id))
    if limit:
        q = q.limit(limit)
    return q.all()


def build_parser():
    p = argparse.ArgumentParser(
        prog="python -m skribl.takedown",
        description="Withdraw or hide one Skribl by public id, as an operator.",
        epilog="Dry run by default. --delete and --visibility are the wet flags.")
    p.add_argument("public_id", nargs="?",
                   help="the public id of the post to act on")
    p.add_argument("--app", default="app:create_app",
                   help="module:attribute of the Flask app or app factory "
                        "(default: app:create_app)")
    p.add_argument("--list-orphans", action="store_true",
                   help="count and list posts with no owner and no revocation "
                        "capability — the pre-v279 anonymous back-catalogue. "
                        "Read-only; ignores every other flag.")
    p.add_argument("--reports", action="store_true",
                   help="list open reports from the public gallery, grouped "
                        "by post, most-reported first. Read-only; ignores "
                        "every other flag.")
    p.add_argument("--resolve", action="store_true",
                   help="close every open report on the post without "
                        "touching the post -- for reports that were nothing")
    p.add_argument("--delete", action="store_true",
                   help="actually delete the post. Bytes are left to "
                        "skribl.sweep, which is the only thing that can tell "
                        "whether another post shares them.")
    p.add_argument("--visibility", choices=sorted(visibility_values()),
                   help="change who may read it instead of deleting it")
    return p


def open_reports():
    """Every post with open reports, most-reported first, newest report first
    within each: [(post, [reports...]), ...]."""
    s = resolve_session()
    rows = (s.query(SkriblReport)
            .filter(SkriblReport.state == "open")
            .order_by(SkriblReport.created_at.desc(), SkriblReport.id.desc())
            .all())
    by_post = {}
    for r in rows:
        by_post.setdefault(r.post_id, []).append(r)
    posts = {p.id: p for p in s.query(SkriblPost)
             .filter(SkriblPost.id.in_(list(by_post))).all()} if by_post else {}
    groups = [(posts[pid], rs) for pid, rs in by_post.items() if pid in posts]
    groups.sort(key=lambda g: (-len(g[1]), g[0].public_id))
    return groups


def main(argv=None, out=sys.stdout):
    args = build_parser().parse_args(argv)
    if sum(bool(f) for f in (args.delete, args.visibility, args.resolve)) > 1:
        _die("--delete, --visibility and --resolve ask for different outcomes; pick one.")
    if not args.list_orphans and not args.reports and not args.public_id:
        _die("a public id is required unless you passed --list-orphans or --reports.")

    app = _load_app(args.app)
    with app.app_context():
        try:
            resolve_session()
        except Exception as exc:
            _die(f"no database session: {type(exc).__name__}: {exc}")

        if args.list_orphans:
            rows = orphans()
            print(f"{len(rows)} post(s) with no owner and no revocation key.",
                  file=out)
            # WHY THE COUNT LEADS AND THE LIST FOLLOWS: zero is the answer that
            # closes the finding, and it should be readable without scrolling.
            for post in rows:
                print(f"  {post.public_id}  {post.visibility}  "
                      f"{post.created_at}", file=out)
            if rows:
                print("\nThese cannot be withdrawn by their authors. Handle "
                      "them on request with:\n"
                      "  python -m skribl.takedown <public-id> --delete",
                      file=out)
            return EXIT_OK

        if args.reports:
            groups = open_reports()
            print(f"{len(groups)} post(s) with open reports.", file=out)
            for post, rows in groups:
                reasons = {}
                for r in rows:
                    reasons[r.reason] = reasons.get(r.reason, 0) + 1
                why = ", ".join(f"{k} x{v}" for k, v in sorted(reasons.items()))
                print(f"  {post.public_id}  {post.visibility}  "
                      f"{len(rows)} report(s)  {why}  latest {rows[0].created_at}\n"
                      f"    title : {post.title or '(untitled)'}", file=out)
                for r in rows:
                    if r.note:
                        print(f"    note  : {r.note}", file=out)
            if groups:
                print("\nAct on one with:\n"
                      "  python -m skribl.takedown <public-id> --visibility private\n"
                      "  python -m skribl.takedown <public-id> --delete\n"
                      "  python -m skribl.takedown <public-id> --resolve   (it was nothing)",
                      file=out)
            return EXIT_OK

        post = (resolve_session().query(SkriblPost)
                .filter(SkriblPost.public_id == args.public_id)
                .one_or_none())
        if post is None:
            print(f"skribl.takedown: no post with public id "
                  f"{args.public_id!r}.", file=sys.stderr)
            return EXIT_NO_SUCH_POST

        # SAY WHAT IT IS BEFORE TOUCHING IT. An operator acting on a support
        # mail has a public id and no other way to confirm they have the right
        # post; printing the title and date is the confirmation step, and it
        # is the only one a dry run can offer.
        print(f"{post.public_id}  {post.visibility}  {post.created_at}\n"
              f"  title  : {post.title or '(untitled)'}\n"
              f"  author : {post.user_id if post.user_id is not None else '(anonymous)'}\n"
              f"  key    : {'held by its author' if post.delete_token_hash else 'none — this post is why this tool exists'}",
              file=out)

        n_open = (resolve_session().query(SkriblReport)
                  .filter(SkriblReport.post_id == post.id,
                          SkriblReport.state == "open").count())
        print(f"  reports: {n_open} open", file=out)

        if not args.delete and not args.visibility and not args.resolve:
            print("\nDRY RUN — nothing changed. Add --delete, "
                  "--visibility private, or --resolve, to act.", file=out)
            return EXIT_OK

        if args.resolve:
            (resolve_session().query(SkriblReport)
             .filter(SkriblReport.post_id == post.id,
                     SkriblReport.state == "open")
             .update({"state": "closed"}, synchronize_session=False))
            resolve_session().commit()
            print(f"\n{n_open} report(s) closed. The post is untouched.", file=out)
            return EXIT_OK

        if args.visibility:
            set_post_visibility(args.public_id, args.visibility,
                                require_author=False)
            resolve_session().commit()
            print(f"\nvisibility is now {args.visibility}.", file=out)
            return EXIT_OK

        delete_post(args.public_id, require_author=False)
        resolve_session().commit()
        print("\ndeleted. The media bytes are NOT gone: run skribl.sweep, "
              "which is the only thing that can tell whether another post "
              "shares them.", file=out)
        return EXIT_OK


if __name__ == "__main__":       # pragma: no cover
    raise SystemExit(main())
