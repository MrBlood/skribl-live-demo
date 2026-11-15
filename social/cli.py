"""`flask social ...`: invite links from a shell (a laptop, or Render's shell),
and the ways of finding the people who were here first.

    flask --app app social invite [--base https://your-site]
    flask --app app social recover HANDLE [--base https://your-site]
    flask --app app social words [--write] [--batch N] [--limit N]

`invite` prints a join link (works once, for 14 days); `recover` prints a
recovery link for HANDLE (works once, for an hour, and adds a passkey to
their account): the way back in for the one admin who lost every passkey.
Without --base it prints the link's path, to put after the site's address
(nothing here knows the address: it is whatever the site is served on).

The link goes to the terminal and nowhere else: never to a log. The code is
kept only as a hash, so this is the one time it can be seen, and it sits after
the link's #, which a browser never sends to a server.

`words` (finding people, people.fill): the people who joined before finding
people have no ways of being found yet; this writes theirs, a batch at a time,
each batch committed, so it can stop and start again. Without --write it only
says how many have none. gunicorn.conf.py runs it with --write once each
start, after the site's chain. Exit codes, as Skribl's backfills: 0 it ran
(nothing to do too), 1 it stopped part way (what it wrote is kept), 2 it could
not run.
"""
import click
from flask import current_app
from flask.cli import AppGroup

group = AppGroup("social", help="The site at /social: invite links, and the ways of finding its people.")


def _print_link(path, base):
    if base:
        click.echo(base.rstrip("/") + path)
    else:
        click.echo(path)
        click.echo("(put the site's address in front of it, or pass --base https://...)", err=True)


@group.command("invite")
@click.option("--base", default=None, help="The site's address, e.g. https://example.onrender.com")
def invite(base):
    """Print a join link: works once, for 14 days."""
    from .accounts import make_invite
    site = current_app.extensions["social"]
    sess = site.session()
    code, _inv = make_invite(sess, "join")
    sess.commit()
    _print_link(f"{site.url_prefix}/join#{code}", base)


@group.command("recover")
@click.argument("handle")
@click.option("--base", default=None, help="The site's address, e.g. https://example.onrender.com")
def recover(handle, base):
    """Print a recovery link for HANDLE: works once, for an hour."""
    import sqlalchemy as sa

    from .accounts import make_invite
    from .models import Person
    site = current_app.extensions["social"]
    sess = site.session()
    who = sess.execute(sa.select(Person).where(Person.handle_key == handle.lstrip("@").lower())
                       ).scalar_one_or_none()
    if who is None:
        raise click.ClickException(f"nobody has the handle @{handle.lstrip('@')}")
    code, _inv = make_invite(sess, "recover", for_person_id=who.id)
    sess.commit()
    _print_link(f"{site.url_prefix}/recover#{code}", base)


@group.command("words")
@click.option("--write", is_flag=True, help="Write them (without it, only say how many people have none).")
@click.option("--batch", default=200, show_default=True, type=click.IntRange(1, 5000),
              help="People written before each commit.")
@click.option("--limit", default=None, type=click.IntRange(1), help="Write at most this many people.")
def words(write, batch, limit):
    """Give the people who have no ways of being found yet theirs."""
    import sqlalchemy as sa

    from .people import fill
    site = current_app.extensions["social"]
    sess = site.session()
    try:
        done, left = fill(sess, batch=batch, limit=limit, write=write)
    except sa.exc.OperationalError as exc:
        # No table yet (the site's chain has not run), or no database.
        sess.rollback()
        click.echo(f"could not run: {str(exc).splitlines()[0][:160]}", err=True)
        raise SystemExit(2)
    except sa.exc.SQLAlchemyError as exc:
        sess.rollback()
        click.echo(f"stopped part way, what was written is kept: {str(exc).splitlines()[0][:160]}", err=True)
        raise SystemExit(1)
    if write:
        click.echo(f"words: {done} {'person' if done == 1 else 'people'} given their ways of being found; {left} left")
    else:
        click.echo(f"words: {left} {'person has' if left == 1 else 'people have'} no ways of being found yet"
                   + (" (run it with --write to give them theirs)" if left else ""))
