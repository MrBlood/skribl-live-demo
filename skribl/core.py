"""Version, Open Graph defaults, public-id validation, and env parsing.

Pure and import-light on purpose: nothing here touches Flask or the database, so
it stays unit-testable headless — the property the original module comments
already claimed for these helpers.
"""
import os
import re

# Open Graph title/description for a shared Skribl, with generic fallbacks.
# Kept pure and import-free (no DB, no Flask context) so it can be unit-tested
# headless — the route feeds it the post's fields (or None on a miss/error).
# The version string shown in the Pad's overflow menu. Single-sourced HERE and
# injected into the template, because the literal that used to live in
# skribl_editor.html drifted nine versions (it still read v96 at v105) — nothing
# forced anyone to touch it. Bump this one line per release; verify_version.py
# fails if a hardcoded version reappears in a template.
SKRIBL_VERSION = "v210"

OG_DEFAULT_TITLE = "Skribl Pad"
OG_DEFAULT_DESCRIPTION = "A drawing that replays in time with music."


def _og_meta(title, caption):
    og_title = (title or "").strip() or OG_DEFAULT_TITLE
    og_description = (caption or "").strip() or OG_DEFAULT_DESCRIPTION
    return og_title, og_description


# Decode a client-generated share-card thumbnail stored in the payload as an
# image data URL back into raw bytes for the card route. Accepts PNG or JPEG:
# the card was historically PNG and is JPEG now (opaque 1200x630, no alpha to
# lose — ~5x smaller), and old PNG posts must keep unfurling, so both are served.
# The subtype is captured so the route can send a matching Content-Type. Kept
# pure and import-light (base64 + re only, no DB/Flask) so it can be unit-tested
# headless. Returns None on anything malformed so the caller can fall back to the
# static branded card instead of erroring.
_DATA_URL_IMAGE_RE = re.compile(r"^data:image/(png|jpeg);base64,(.+)$", re.DOTALL)

# public_id slugs come from secrets.token_urlsafe(8) → 11 chars of [A-Za-z0-9_-].
# Checking the format up front (range is generous for future length changes)
# keeps junk out of DB lookups and template injection surface entirely. Routes
# keep their existing render-always / fallback contracts on a mismatch — this
# only short-circuits the lookup, it never changes what a URL renders.
_PUBLIC_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,64}$")


def _valid_public_id(public_id):
    return isinstance(public_id, str) and bool(_PUBLIC_ID_RE.match(public_id))


# Hard ceiling for the share-card image served by /s/<id>/card.png. A real
# 1200x630 thumbnail is a few hundred KB; anything much larger in the payload
# is malformed or hostile, and serving (and CDN-caching) it on every unfurl
# would be a cheap amplification. Oversize falls back to the static card.
MAX_CARD_BYTES = 2_000_000

# Naive in-memory per-IP rate limit for POST /api/skribls: N posts per rolling
# window, per process. Not distributed, resets on deploy — deliberately minimal.
# It exists to stop the trivial abuse case (one client looping max-size posts
# until free-tier Postgres fills), not to be real infrastructure; replace with
# proper limiting when auth lands (roadmap #5).
def _env_int(name, default, minimum=1, maximum=None):
    # Bare int(os.environ[...]) meant a typo in deployment config crashed the app
    # at import with a traceback naming neither the variable nor the value, and 0
    # or a negative produced a nonsensical limit that looked like a bug elsewhere.
    # Fail loudly, name the variable, clamp the range. (Review #12)
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        raise RuntimeError(f"{name} must be an integer, got {raw!r}. Fix the deployment config.")
    if value < minimum:
        raise RuntimeError(f"{name} must be >= {minimum}, got {value}.")
    if maximum is not None and value > maximum:
        raise RuntimeError(f"{name} must be <= {maximum}, got {value}.")
    return value


# Rate-limiter sizing. Lives here with the other env knobs rather than in
# validation, which is where the original single-file layout happened to put it.
RATE_CLEANUP_BATCH = _env_int("SKRIBL_RATE_CLEANUP_BATCH", 500, minimum=1)
# How long an unresolved reservation keeps occupying a slot. Long enough for a
# slow post to finish, short enough that a killed process costs seconds not hours.
RATE_PENDING_TTL = _env_int("SKRIBL_RATE_PENDING_TTL", 120, minimum=5)
