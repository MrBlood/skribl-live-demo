"""A worked host application. Run it, post a Skribl, read the code.

    python examples/host_app/app.py          then open http://127.0.0.1:5055/

WHY THIS EXISTS. Every other document in this tree DESCRIBES the integration.
This one is the integration, in a file small enough to read in one sitting, and
`harness/verify_example.py` drives it end to end — so if the drop-in stops
working, something goes red rather than a paragraph quietly going stale.

WHAT IT IS MODELLED ON. A social site whose composer is a SERVER-SIDE FORM: the
author types some words, attaches things, and their browser sends one ordinary
POST to the host's own view. That is the harder of the two shapes and the one
least covered by the JSON endpoint, so it is the one worked here. A host whose
composer posts JSON from the browser has less to do, not more — see
`GET /feed` in the Skribl blueprint for that shape.

THE FIVE THINGS A HOST DOES, all visible below:

    1. own the app, the database and the session          create_app()
    2. mount the blueprint                                init_skribl(...)
    3. put the Skribl in the SAME transaction as its own  compose()
       row, with one commit
    4. render the player inside its own post              templates/feed.html
    5. drive the pad button from its own composer         templates/feed.html

MOUNTED UNDER A PREFIX ON PURPOSE. `url_prefix="/skribl"` is not the easy
setting — it is the one that catches route literals in client JavaScript and
relative endpoint names in templates, both of which have been real bugs here.
A host mounting at the root would work; this proves the harder case.

WHAT IS FAKE, and deliberately named as such: the login is a dropdown, because
authentication is the one thing every host already has and none of them have
the same. `current_user_id` is a callable — hand it whatever your real one
returns.
"""
import json
import os
import pathlib
import sys

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session as flask_session, url_for)
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import skribl
import skribl.models
import skribl.security
from skribl import SkriblRejected, create_post

db = SQLAlchemy()


class User(db.Model):
    """The host's users. Skribl never sees this table — it only ever gets an
    id back from the `current_user_id` callable, and stores it as an integer."""
    __tablename__ = "host_users"
    id = sa.Column(sa.Integer, primary_key=True)
    handle = sa.Column(sa.String(40), unique=True, nullable=False)


class Post(db.Model):
    """The host's posts. `skribl_id` is the whole of the coupling: a nullable
    string column holding the public id, because a post may have no Skribl and
    the host's schema should not care whether Skribl is installed."""
    __tablename__ = "host_posts"
    id = sa.Column(sa.Integer, primary_key=True)
    author_id = sa.Column(sa.Integer, sa.ForeignKey("host_users.id"),
                          nullable=False)
    body = sa.Column(sa.Text, nullable=False, default="")
    skribl_id = sa.Column(sa.String(32), nullable=True)
    created_at = sa.Column(sa.DateTime, server_default=sa.func.now())

    author = sa.orm.relationship("User")


def current_user():
    uid = flask_session.get("uid")
    return db.session.get(User, uid) if uid else None


def create_app(database_url=None):
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        database_url or os.environ.get("EXAMPLE_DATABASE_URL")
        or "sqlite:///" + str(pathlib.Path(__file__).with_name("example.db")))
    # A real host has a real secret. This one is fine because the whole app is
    # a demonstration that gets thrown away.
    app.config["SECRET_KEY"] = os.environ.get("EXAMPLE_SECRET", "example-host-key")
    db.init_app(app)

    # ---- 2. MOUNT SKRIBL ---------------------------------------------------
    # `current_user_id` is BOTH the author stamp on a new Skribl and the viewer
    # identity for authorisation, so it has to be the truth. Skribl never
    # imports the host's auth; it calls this.
    #
    # `csrf` is not optional once current_user_id is set, and the blueprint
    # refuses to start without the choice being made: cookie-based auth plus no
    # CSRF validator means any third-party page can post as the signed-in user.
    # This host's own forms carry their own token; this triple is for Skribl's
    # JSON endpoint.
    skribl.init_skribl(
        app,
        session=lambda: db.session,
        url_prefix="/skribl",
        current_user_id=lambda: flask_session.get("uid"),
        csrf=skribl.security.double_submit_csrf(),
    )
    # One db.create_all() then covers Skribl's five tables as well as the two
    # above. An Alembic host migrates skribl.models.SkriblBase.metadata instead.
    skribl.models.attach_to_metadata(db.metadata)

    # ---- TRANSACTION OWNERSHIP --------------------------------------------
    # The HOST commits, once per request. Skribl's routes flush and use
    # savepoints and never commit or roll back this session, which is what lets
    # compose() below put a Skribl and a host row in one transaction.
    @app.after_request
    def _commit(response):
        if response.status_code < 500:
            db.session.commit()
        return response

    @app.teardown_request
    def _rollback(exc):
        db.session.rollback()

    @app.get("/")
    def feed():
        posts = (db.session.query(Post)
                 .order_by(Post.created_at.desc(), Post.id.desc())
                 .limit(30).all())
        return render_template("feed.html", posts=posts, me=current_user(),
                               users=db.session.query(User).all())

    @app.post("/login")
    def login():
        flask_session["uid"] = int(request.form["uid"])
        return redirect(url_for("feed"))

    @app.post("/logout")
    def logout():
        flask_session.pop("uid", None)
        return redirect(url_for("feed"))

    # ---- 3. THE COMPOSER'S VIEW -------------------------------------------
    @app.post("/compose")
    def compose():
        """One ordinary form POST, one transaction, one commit.

        THIS IS THE PART WORTH COPYING. The browser sent a normal form: some
        words, and a hidden field carrying the Skribl payload as JSON. Nothing
        has been posted to Skribl's API and nothing needs to be — `create_post`
        runs in THIS request, on THIS session, so the Skribl and the host's own
        row are made durable by the same commit or by neither.

        The alternative — having this view POST to /skribl/api/skribls over
        HTTP — costs a second request, a second authentication, a second CSRF
        exchange, and a SEPARATE TRANSACTION. A failure between the two leaves
        a Skribl nothing points at, or a post pointing at a Skribl that was
        never stored.
        """
        me = current_user()
        if me is None:
            abort(403)

        body = (request.form.get("body") or "").strip()
        raw = (request.form.get("skribl_payload") or "").strip()

        skribl_id = None
        if raw:
            try:
                drawing = json.loads(raw)
            except ValueError:
                flash("That drawing did not arrive intact. Try again.")
                return redirect(url_for("feed"))

            # The host decides these three, not Skribl:
            #   visibility  the API defaults to "unlisted" (reachable by link,
            #               listed nowhere) because that is right for a
            #               link-sharing product. A feed means otherwise.
            #   title       what /s/<id> unfurls with.
            #   caption     the words, so the Skribl carries its own context.
            drawing["visibility"] = "public"
            drawing["title"] = body[:80] or "Untitled Skribl"
            drawing["caption"] = body

            try:
                made = create_post(drawing, author_id=me.id)
            except SkriblRejected as exc:
                # .message is the same wording Skribl's own composer shows.
                flash(exc.message)
                return redirect(url_for("feed"))
            skribl_id = made.public_id

        if not body and skribl_id is None:
            flash("A post needs words, a drawing, or both.")
            return redirect(url_for("feed"))

        db.session.add(Post(author_id=me.id, body=body, skribl_id=skribl_id))
        # NO COMMIT HERE. _commit above does it, once, for the whole request —
        # so the Skribl created a few lines up and this row land together.
        return redirect(url_for("feed"))

    @app.cli.command("seed")
    def seed():
        db.create_all()
        if not db.session.query(User).count():
            db.session.add_all([User(handle="ada"), User(handle="grace")])
            db.session.commit()
        print("Seeded.")

    return app


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if not db.session.query(User).count():
            db.session.add_all([User(handle="ada"), User(handle="grace")])
            db.session.commit()
    app.run(port=int(os.environ.get("PORT", 5055)), debug=False)
