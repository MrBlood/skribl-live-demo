"""A host's brand on Skribl's own editors (docs/INTEGRATION.md, "Your brand
on Skribl's editors (`brand_resolver`)").

The Pad and Flip wear Skribl's mark at the top and say Skribl's hello the
first time they open. A host that serves them at an address of its own may
give them its own instead, PER REQUEST: the mark at the top (its own markup,
or a template it names), the label that names it, and a first-open hello of
its own with the key a browser remembers it by. The host decides by whatever
the request carries (the address it came to, say). Answering nothing is
Skribl as it is, byte for byte: the editors' templates take today's branch
whenever the answer is None.

    skribl.init_skribl(app, ..., brand_resolver=fn)    # or set_brand_resolver(fn, app=app)

`fn()` is called in the request, once for each editor page (the Pad, Flip,
and the Pad at "/" where the host asked for that route), and answers None or
a mapping of:

    mark           the host's own markup for the mark (an <svg>, or an <img>),
                   trusted as the host's own HTML; or
    mark_template  the name of a template the app's loader finds, rendered
                   in the request in its place;
    label          what names it, 1 to 40 characters: the lockup and the
                   page's heading read "<label> Pad" and "<label> Flip", the
                   hello is "<label>'s signature", and the words that name
                   the app the person is in say it (the tab, Post, the post
                   sheet, How it works, the menu's editors, the empty canvas;
                   the tool's own words stay Skribl's). Required with any of
                   the others;
    hello          the hello's drawing: a Skribl payload (a Flip, as
                   harness/tools/make_hello.py makes Skribl's), as a path on
                   this site, since Skribl's pages fetch from their own origin
                   only (connect-src 'self');
    hello_key      the key the browser remembers the host's hello as seen by:
                   letters, digits, ".", "_" and "-", up to 64, and not
                   Skribl's own, so somebody who met Skribl's hello still
                   meets the host's once. Given with `hello`, never without.

THE MARK IS DRAWN IN SKRIBL'S HAND and stands in the slot Skribl's own takes,
so nothing in the header moves: the hand is 30 units tall
(_skribl_brand_mark.html: the baseline at 23.4, a pen 2.3 wide), drawn at the
signature's scale (36px to 30 units, 26 on a phone); a box taller than the
hand hangs the rest below the line, read from the markup's own viewBox; and
the slot keeps the signature's 65 units of width, so the mode word beside it
stays where it was. It wears the signature's press, and its currentColor is
Skribl's purple; what the markup colours itself keeps its own colour
(styles.css and flip.css, A HOST'S OWN MARK).

FAILS LOUDLY. A wrong answer (an unknown key, a hello without its key, a key
or an address Skribl cannot put in the page safely, a box drawn at another
scale) raises at once, on the first page that asks, rather than half-applying
a brand. A resolver that raises is not caught either, as a feed filter's is
not.

Skribl knows nothing of any host: nothing here is named for one.
"""
import re
from collections.abc import Mapping

from flask import current_app, render_template
from markupsafe import Markup

#: The key Skribl's own hello is remembered as seen by. The page's head reads
#: it (_skribl_hello_boot.html) and lib/hello.js marks it, both by default.
HELLO_KEY = "skribl.hello.v2"

#: The height of the hand Skribl's mark is drawn in, in its own units.
HAND_UNITS = 30.0

#: A box this far from the hand (half to twice it) is a mark drawn at another
#: scale: in the header it would stand at a size nobody chose.
UNITS_RANGE = (15.0, 60.0)

_KEYS = ("mark", "mark_template", "label", "hello", "hello_key")
_HELLO_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_VIEWBOX = re.compile(r"<svg\b[^>]*?\bviewBox\s*=\s*([\"'])([^\"']*)\1", re.I | re.S)
_UNSET = object()
_RESOLVER = None


def set_brand_resolver(fn, app=None):
    """Install `fn() -> None | mapping` for the editors' brand (see the module
    docstring). With `app`, for that application alone; without, for every
    application in the process that has none of its own (one app per process
    only: another app's address would get this one's brand)."""
    if fn is not None and not callable(fn):
        raise TypeError("brand resolver must be callable or None")
    if app is not None:
        app.extensions.setdefault("skribl", {})["brand_resolver"] = fn
        return
    global _RESOLVER
    _RESOLVER = fn


def _resolver():
    fn = _RESOLVER
    try:
        local = current_app.extensions.get("skribl", {}).get("brand_resolver", _UNSET)
        if local is not _UNSET:
            fn = local
    except RuntimeError:          # no application here: the process-wide one
        pass
    return fn


def _units(markup):
    """The mark's box height in the hand's units: its own viewBox's, or the
    hand's when it has none (an <img>, say)."""
    m = _VIEWBOX.search(markup)
    if not m:
        return HAND_UNITS
    nums = re.split(r"[\s,]+", m.group(2).strip())
    try:
        h = float(nums[3])
    except (IndexError, ValueError):
        raise ValueError(f"brand mark: its viewBox {m.group(2)!r} is not four numbers") from None
    if not UNITS_RANGE[0] <= h <= UNITS_RANGE[1]:
        raise ValueError(
            f"brand mark: its viewBox is {h:g} units tall; draw it in Skribl's hand, "
            f"{HAND_UNITS:g} units tall (a box between {UNITS_RANGE[0]:g} and "
            f"{UNITS_RANGE[1]:g}, the part past {HAND_UNITS:g} hanging below the line)")
    return h


def _path(url):
    """The hello's address as given, if it is a path on this site Skribl can
    put in the page and fetch; else ValueError."""
    u = url.strip() if isinstance(url, str) else ""
    if (not u.startswith("/") or u.startswith("//") or len(u) > 2048
            or any(c in u for c in " \\\"'<>`") or any(ord(c) < 32 or ord(c) == 127 for c in u)):
        raise ValueError(
            "brand hello: a path on this site, starting with '/' (Skribl's pages fetch "
            f"from their own origin only). Got {url!r}.")
    return u


def page_brand():
    """The host's brand for this request's editor page, checked; or None for
    Skribl's own. Called by the editors' routes, once a page."""
    fn = _resolver()
    if fn is None:
        return None
    got = fn()
    if got is None:
        return None
    if not isinstance(got, Mapping):
        raise TypeError(f"brand resolver: answer None or a mapping, not {type(got).__name__}")
    if not got:
        return None
    stray = sorted(set(got) - set(_KEYS))
    if stray:
        raise ValueError(f"brand resolver: unknown key(s) {stray}; the keys are {list(_KEYS)}")
    if "mark" in got and "mark_template" in got:
        raise ValueError("brand resolver: give `mark` or `mark_template`, not both")
    if ("hello" in got) != ("hello_key" in got):
        raise ValueError("brand resolver: `hello` and `hello_key` go together (a hello of "
                         "the host's own is remembered by a key of its own)")
    label = got.get("label")
    if not isinstance(label, str) or not 1 <= len(label.strip()) <= 40:
        raise ValueError(f"brand resolver: `label` names the brand, 1 to 40 characters. Got {label!r}.")
    if not ({"mark", "mark_template", "hello"} & set(got)):
        raise ValueError("brand resolver: a `label` names a mark or a hello; give one")
    out = {"label": label.strip(), "mark": None, "units": HAND_UNITS, "hello": None, "hello_key": None}
    if "mark_template" in got:
        name = got["mark_template"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"brand resolver: `mark_template` is a template's name. Got {name!r}.")
        out["mark"] = Markup(render_template(name))
    elif "mark" in got:
        if not isinstance(got["mark"], str) or not got["mark"].strip():
            raise ValueError("brand resolver: `mark` is the host's markup, a non-empty string")
        out["mark"] = Markup(got["mark"])
    if out["mark"] is not None:
        out["units"] = _units(str(out["mark"]))
    if "hello" in got:
        key = got["hello_key"]
        if not isinstance(key, str) or not _HELLO_KEY.match(key):
            raise ValueError(
                "brand resolver: `hello_key` is letters, digits, '.', '_' and '-', up to 64 "
                f"(it is written into the page's head). Got {key!r}.")
        if key == HELLO_KEY:
            raise ValueError(
                f"brand resolver: `hello_key` {key!r} is Skribl's own; somebody who met "
                "Skribl's hello would never meet the host's")
        out["hello"], out["hello_key"] = _path(got["hello"]), key
    return out
