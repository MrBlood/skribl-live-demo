"""Withdraw a Skribl nobody else can: the operational path for a lost key.

    python -m skribl.takedown --list-orphans
    python -m skribl.takedown <public-id> --delete
    python -m skribl.takedown <public-id> --visibility private

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
from .models import SkriblPost, session as resolve_session, visibility_values
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
    p.add_argument("--delete", action="store_true",
                   help="actually delete the post. Bytes are left to "
                        "skribl.sweep, which is the only thing that can tell "
                        "whether another post shares them.")
    p.add_argument("--visibility", choices=sorted(visibility_values()),
                   help="change who may read it instead of deleting it")
    return p


def main(argv=None, out=sys.stdout):
    args = build_parser().parse_args(argv)
    if args.delete and args.visibility:
        _die("--delete and --visibility ask for different outcomes; pick one.")
    if not args.list_orphans and not args.public_id:
        _die("a public id is required unless you passed --list-orphans.")

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

        if not args.delete and not args.visibility:
            print("\nDRY RUN — nothing changed. Add --delete, or "
                  "--visibility private, to act.", file=out)
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
