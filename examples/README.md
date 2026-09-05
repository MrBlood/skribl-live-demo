# Worked examples

## `host_app/` — a Flask site that mounts Skribl

    python examples/host_app/app.py

Then open <http://127.0.0.1:5055/>, sign in as `ada`, press the ✎ button,
draw something, and post it.

It is about 200 lines of application and one template. Read `app.py` first —
its docstring lists the five things a host does and points at the line where
each one happens.

**What it demonstrates that the standalone `app.py` at the repo root does not:**

* **Skribl is mounted under a prefix** (`/skribl`), which is what a real host
  does and what catches route literals in client JavaScript and relative
  endpoint names in templates. Both have been real bugs in this tree.
* **The host has its own users and its own posts.** `host_posts.skribl_id` is
  the entire coupling — one nullable string column holding the public id.
* **The composer is a SERVER-SIDE FORM.** The drawing rides in a hidden field
  and the host's view calls `skribl.create_post()`, so the Skribl and the
  host's own row are made durable by ONE commit. The browser never talks to
  `POST /api/skribls` at all.

That last point is the shape skribls.net has, and it is the one the JSON
endpoint alone does not serve. A host whose composer posts JSON from the
browser has less to do, not more — `GET /skribl/feed` in the blueprint is that
shape, and `skribl/static/feed.js` is its recipe.

**It is tested.** `harness/verify_example.py` boots this app as a real server
on its own port, drives a real browser through drawing and posting, and then
checks on a fresh database connection that the host's post row and the Skribl
were committed together. An example nothing runs is a document that goes stale
silently, which this project has been bitten by more than once.

**What is deliberately fake:** the login is a dropdown. Authentication is the
one thing every host already has and no two have the same, so `current_user_id`
is a callable — hand it whatever yours returns.

For the full contract, read `docs/INTEGRATION.md`.
