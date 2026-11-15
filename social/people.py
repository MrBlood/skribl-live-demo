"""Finding people (the map, part two, item 5; docs/SOCIAL-SITE.md section 17),
from the finding-people mock and the owner's "All yes" (Nov 15, about 1:45 AM
Mountain): the Gallery's search box finds people too.

    /explore?q=pa       the Gallery (gallery.py), with a People section on
                        top: up to three people, then "See all" when there
                        are more; then Drawings, the tiles as before
    /explore?q=pa&who=people
                        See all: the people alone, twenty a page
    /explore/more?q=pa&who=people&before=<cursor>
                        Load more of them (JSON {html, next}), as the
                        Gallery's own Load more brings its tiles

WHO IS FOUND (find()): anybody whose name, by ANY word of it, or whose
@handle starts with what was typed; "pa" finds Theo Park, and "ar" finds
nobody by the middle of his name. Case, accents and a leading @ are put
aside, and so is anything else that is not a letter or a digit (fold()):
"theo-pa" and "Theo Pa" are typed alike. THE PEOPLE YOU FOLLOW FIRST, then
everybody else; within each, by the earliest of their ways that starts with
it (a word of their name from it on, or their handle), then who joined
first. Nobody a block hides either way, nobody taken down, signed out too.
You are found as anybody is, and your own row has no Follow, as your own
page has none. A mute changes nothing: their page stays open to you (what
you go to stays), so they are found.

A WAY OF FINDING SOMEBODY IS A ROW (models.PersonWord, social_people_words):
their name from each of its words on ("theo park", "park") and their handle,
folded, written in code whenever a name is set (write_words: joining, Edit
profile), in the same transaction, the old ones taken away first; so a name
changed is found by its new words and never by its old. A search reads the
keys from what was typed up to the next letter after it, which on both
engines is exactly the keys that start with it (models.WordKey): one read
of the people you follow (through your follows, then their keys), and one of
everybody else (the keys' own index, in order, a page and a little more),
each on an index, whatever the number of people.

THE PEOPLE WHO WERE HERE FIRST (fill(), `flask social words`): their keys
are written in code, never by a migration (the house lesson, v309): a batch
at a time, each batch committed, asking only after the people who have none,
so it can stop and start again, and a person who joined meanwhile is left as
joining wrote them. gunicorn.conf.py runs it once each start, right after
the site's chain, before any worker takes a visitor; anybody may run it by
hand. A person with no keys is found by nobody's search until it has run.

THE @ LIST (mentions.suggest) reads the same ways, the same way: the people
you follow, then anybody else, by these keys (and for an @ alone, the names'
own index, by name).

Reads only, but for write_words and fill. Nothing here commits but fill, a
command (cli.py).
"""
import base64
import re
import unicodedata

import sqlalchemy as sa

from .models import WORD_MAX, Follow, Person, PersonWord
from .safety import blocked_ids
from .security import site

#: The People section's rows on the Gallery, before "See all".
SECTION = 3

#: A page of See all.
PAGE = 20

#: The most reads of everybody else's keys one page makes: each brings a
#: page and a little more, so one is nearly always enough (a person whose
#: name has two words that both start with what was typed comes twice, and
#: is shown once).
READS = 4

#: People a fill writes before it commits.
FILL_BATCH = 200

#: How long a cursor may be (its name's key and a handle, base64).
CURSOR_MAX = 400

_HANDLE_KEY = re.compile(r"[a-z][a-z0-9_]{2,19}")


# ---- the ways somebody is found ------------------------------------------------------

def fold(text):
    """`text` as finding people compares it: its accents put aside (é is e),
    in small letters (casefold: ß is ss), and every run of anything that is
    not a letter or a digit (a space, a dash, an @, an _, an emoji) one space,
    none at either end."""
    t = unicodedata.normalize("NFD", str(text or ""))
    t = unicodedata.normalize("NFC", "".join(c for c in t if not unicodedata.combining(c))).casefold()
    out, gap = [], False
    for c in t:
        if c.isalnum():
            if gap and out:
                out.append(" ")
            out.append(c)
            gap = False
        else:
            gap = True
    return "".join(out)


def keys_of(name, handle):
    """Every way `name` and `handle` are found, each once: the name from each
    of its words on, and the handle, folded and cut to WORD_MAX."""
    words = fold(name).split()
    keys = {" ".join(words[i:])[:WORD_MAX] for i in range(len(words))}
    h = fold(handle)
    if h:
        keys.add(h[:WORD_MAX])
    return keys


def first_key(person, nq):
    """The earliest of `person`'s ways that starts with `nq` (folded), as
    their name and handle are NOW, or None: where a search shows them. A key
    kept from an old name is no way of theirs, so it finds nobody."""
    hits = [k for k in keys_of(person.display_name, person.handle) if k.startswith(nq)]
    return min(hits) if hits else None


def _above(nq):
    """The first text after every key that starts with `nq`: its last letter
    one up (None past the last there is). In byte order, so on both engines
    (models.WordKey)."""
    n = ord(nq[-1]) + 1
    if 0xD800 <= n <= 0xDFFF:
        n = 0xE000
    return nq[:-1] + chr(n) if n <= 0x10FFFF else None


def write_words(person):
    """`person`'s ways of being found, written again from their name and
    handle as they are now, the old ones taken away (joining, and Edit
    profile, in the same transaction as the name). Flushes nothing."""
    sess = site().session()
    sess.execute(sa.delete(PersonWord).where(PersonWord.person_id == person.id)
                 .execution_options(synchronize_session=False))
    sess.execute(sa.insert(PersonWord), [{"person_id": person.id, "word_key": k}
                                         for k in sorted(keys_of(person.display_name, person.handle))])


def drop_person_words(person_id):
    """An account's ways of being found (accounts.delete_person)."""
    site().session().execute(sa.delete(PersonWord).where(PersonWord.person_id == person_id)
                             .execution_options(synchronize_session=False))


# ---- the two reads ----------------------------------------------------------------

def _shown(sel, blocked, exclude=None):
    sel = sel.where(Person.taken_down_at.is_(None))
    if blocked:
        sel = sel.where(Person.id.notin_(sorted(blocked)))
    if exclude is not None:
        sel = sel.where(Person.id != exclude)
    return sel


def _in_range(nq):
    hi = _above(nq)
    return sa.and_(PersonWord.word_key >= nq, PersonWord.word_key < hi) if hi else PersonWord.word_key >= nq


def followed(viewer, nq):
    """The people `viewer` follows whom `nq` finds: [(their first key,
    them)], earliest key first, then who joined first. ONE READ, through
    their follows' own index and then each one's keys (its own index): a
    few rows a person followed."""
    if viewer is None or not nq:
        return []
    from .follows import _on
    sel = (sa.select(PersonWord.word_key, Person).select_from(Follow)
           .join(Person, Person.id == Follow.followed_id)
           .join(PersonWord, PersonWord.person_id == Person.id)
           .where(Follow.follower_id == viewer.id, _on(), _in_range(nq)))
    best = {}
    for key, p in site().session().execute(_shown(sel, blocked_ids(viewer))).all():
        k = first_key(p, nq)
        if k is not None and k == key:
            best[p.id] = (k, p)
    return sorted(best.values(), key=lambda kp: (kp[0], kp[1].id))


def others(viewer, nq, after=None, most=PAGE + 1, exclude=None):
    """Everybody else `nq` finds for `viewer` (None: nobody signed in), in
    order (their first key, then who joined first), from just after `after`
    ((key, a person's id), or None for the start): [(key, them)], `most` at
    most. Never the people `viewer` follows (they come first, followed()),
    nobody a block hides either way, nobody taken down, never `exclude`.
    Read on the keys' own index, in its order, a little more than is wanted,
    READS times at most."""
    if not nq:
        return []
    sess = site().session()
    blocked = blocked_ids(viewer)
    out, at = [], after
    for _ in range(READS):
        sel = sa.select(PersonWord.word_key, PersonWord.person_id, Person).join(Person, Person.id == PersonWord.person_id)
        sel = _shown(sel.where(_in_range(nq)), blocked, exclude)
        if at is not None:
            sel = sel.where(PersonWord.word_key >= at[0],
                            sa.or_(PersonWord.word_key > at[0], PersonWord.person_id > at[1]))
        if viewer is not None:
            from .follows import _on
            sel = sel.where(~sa.exists().where(Follow.follower_id == viewer.id, Follow.followed_id == Person.id, _on()))
        want = most - len(out)
        chunk = max(2 * want, 8)
        rows = sess.execute(sel.order_by(PersonWord.word_key, PersonWord.person_id).limit(chunk)).all()
        for key, pid, p in rows:
            at = (key, pid)
            # Shown once, where their earliest key is: a second key of theirs
            # that starts with it, or one kept from an old name, finds nobody.
            if first_key(p, nq) == key:
                out.append((key, p))
                if len(out) >= most:
                    return out
        if len(rows) < chunk:
            break
    return out


# ---- a page of them -----------------------------------------------------------------

def _cursor(group, key, handle):
    """Where a page ended: which part (the people you follow, "f", or everybody
    else, "e"), the key it ended on, and whose (by handle: no internal id
    leaves the server)."""
    return base64.urlsafe_b64encode(f"{group}|{handle}|{key}".encode()).rstrip(b"=").decode()


def _uncursor(text):
    """(part, key, handle), or None."""
    try:
        raw = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4)).decode()
        group, handle, key = raw.split("|", 2)
    except (ValueError, TypeError, UnicodeDecodeError):
        return None
    # A key is folded (a key cut at WORD_MAX may end with its space).
    if group not in ("f", "e") or not _HANDLE_KEY.fullmatch(handle) or not key or fold(key) != key.rstrip(" "):
        return None
    return group, key, handle


def find(viewer, q, limit=SECTION, before=None):
    """A page of the people `q` finds for `viewer` (None: nobody signed in),
    from just after a cursor of this function's: ([{"who", "following",
    "mine"}], next cursor or None). The people you follow first, then
    everybody else (followed() and others()). A cursor that cannot be read
    ends the list rather than starting it again."""
    nq = fold(q)[:WORD_MAX]
    if not nq:
        return [], None
    at = None
    if before:
        at = _uncursor(before) if len(before) <= CURSOR_MAX else None
        if at is None:
            return [], None
    found = []
    if at is None or at[0] == "f":
        mine = followed(viewer, nq)
        if at is not None:
            # Just after where the last page ended: whose it was, if they are
            # still found here, else every key past the one it ended on.
            place = next((i for i, (k, p) in enumerate(mine) if k == at[1] and p.handle_key == at[2]), None)
            mine = mine[place + 1:] if place is not None else [(k, p) for k, p in mine if k > at[1]]
        found = [("f", k, p) for k, p in mine[:limit + 1]]
    if len(found) <= limit:
        after = None
        if at is not None and at[0] == "e":
            pid = site().session().execute(sa.select(Person.id).where(Person.handle_key == at[2])).scalar()
            # Gone, or a new handle: the rest of that key's people from its start.
            after = (at[1], pid if pid is not None else 0)
        found += [("e", k, p) for k, p in others(viewer, nq, after, most=limit + 1 - len(found))]
    page = found[:limit]
    nxt = _cursor(*page[-1][:2], page[-1][2].handle_key) if len(found) > limit and page else None
    me = viewer.id if viewer is not None else None
    return [{"who": p, "following": g == "f", "mine": p.id == me} for g, k, p in page], nxt


# ---- the people who were here first ------------------------------------------------

def fill(sess, batch=FILL_BATCH, limit=None, write=False):
    """THE PEOPLE WHO HAVE NO WAYS OF BEING FOUND YET (they joined before
    finding people), given theirs: `batch` at a time by id, each batch
    committed, so a run stopped part way keeps what it wrote and the next
    carries on. Each person in a savepoint of their own: one who joined, or
    whose keys a run beside this one wrote, meanwhile is left as they are.
    Without `write`, it only counts. (written, still without) -- a command's
    work (cli.py, `flask social words`), never a request's."""
    wordless = ~sa.exists().where(PersonWord.person_id == Person.id)

    def left():
        return int(sess.execute(sa.select(sa.func.count()).select_from(Person).where(wordless)).scalar() or 0)
    if not write:
        return 0, left()
    done, last = 0, 0
    while limit is None or done < limit:
        n = batch if limit is None else min(batch, limit - done)
        rows = sess.execute(sa.select(Person.id, Person.display_name, Person.handle)
                            .where(wordless, Person.id > last).order_by(Person.id).limit(n)).all()
        if not rows:
            break
        for pid, name, handle in rows:
            try:
                with sess.begin_nested():
                    sess.execute(sa.insert(PersonWord), [{"person_id": pid, "word_key": k}
                                                         for k in sorted(keys_of(name, handle))])
            except sa.exc.IntegrityError:
                continue            # written meanwhile, by joining or another run
            done += 1
        last = rows[-1][0]
        sess.commit()
    return done, left()
