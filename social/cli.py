"""`flask social ...`: invite links from a shell (a laptop, or Render's shell).

    flask --app app social invite [--base https://your-site]
    flask --app app social recover HANDLE [--base https://your-site]

`invite` prints a join link (works once, for 14 days); `recover` prints a
recovery link for HANDLE (works once, for an hour, and adds a passkey to
their account): the way back in for the one admin who lost every passkey.
Without --base it prints the link's path, to put after the site's address
(nothing here knows the address: it is whatever the site is served on).

The link goes to the terminal and nowhere else: never to a log. The code is
kept only as a hash, so this is the one time it can be seen, and it sits after
the link's #, which a browser never sends to a server.
"""
import click
from flask import current_app
from flask.cli import AppGroup

group = AppGroup("social", help="The site at /social: invite links.")


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
