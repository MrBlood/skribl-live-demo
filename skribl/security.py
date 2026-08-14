"""Embed-origin parsing and the Content-Security-Policy.

The policy body is unchanged from v131. What changed is its SCOPE: it was an
app-wide after_request, which in a host application would either clobber the
platform's policy or be clobbered by it. It is now attached to the blueprint, so
it covers Skribl's own routes and Skribl's own static files and nothing else.
"""
import gzip
import hmac
import io
import ipaddress
import re as _re
import os
import secrets
import zlib
from urllib.parse import urlsplit

from flask import current_app, g, jsonify, request, url_for

from .jsstrip import strip_bytes

# Text-ish types only. Images, audio and video are already compressed;
# re-gzipping them spends CPU to make them marginally larger.
_GZIP_CACHE = {}          # (path, ?v=) -> gzipped bytes
_GZIP_CACHE_MAX = 128     # editor pulls 25; this is slack, not a budget

# Comment-stripped JavaScript, cached on exactly the same key and for exactly
# the same reason: a busted URL names one immutable byte sequence, so its
# stripped form is immutable too. Lexing app.js costs ~90 ms, which is a
# non-starter per request and a rounding error once per file version — the same
# arithmetic that decided gzip level 6 for busted assets and level 1 otherwise.
_STRIP_CACHE = {}         # (path, ?v=) -> comment-stripped bytes
_STRIP_CACHE_MAX = 128
_GZIP_MIN = 1024          # below this the header costs more than the saving
_COMPRESSIBLE = _re.compile(
    r'^(?:text/|application/(?:javascript|json|xml|manifest\+json)$|image/svg)')

_CSP_KEYWORD_SOURCES = {"'self'", "'none'"}
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}



_FORCE_SECURE = os.environ.get("SKRIBL_FORCE_SECURE_COOKIES", "").strip().lower() \
    in ("1", "true", "yes", "on")

def _normalise_origin(token):
    parsed = urlsplit(token)
    host = parsed.hostname or ""
    if ":" in host:                      # IPv6 literals need their brackets back
        host = f"[{host}]"
    port = f":{parsed.port}" if parsed.port is not None else ""
    return f"{parsed.scheme}://{host}{port}"


def _is_bare_origin(token):
    """True for scheme://host[:port] and nothing else.

    Round 2 checked a prefix and looked for '/' in the remainder, which let
    ?query, #fragment, user@host and :not-a-port through — several of which
    produce an invalid CSP source expression rather than a safe startup failure.
    Parsed structurally now. Wildcard hosts (https://*.example.com) are valid CSP
    source expressions but are NOT origins, and the variable is named
    EMBED_ORIGINS, so they are rejected as the less surprising policy.
    (Review round 3, #3)
    """
    parsed = urlsplit(token)
    if parsed.scheme not in ("https", "http"):
        return False
    try:
        host = parsed.hostname
        parsed.port                      # raises ValueError on a bad port
    except ValueError:
        return False
    if not host:
        return False
    if parsed.scheme == "http" and host not in _LOCAL_HOSTS:
        return False
    if parsed.username is not None or parsed.password is not None:
        return False
    if parsed.path not in ("", "/"):
        return False
    if parsed.query or parsed.fragment:
        return False
    if "*" in host:
        return False
    return True


def _validate_embed_origins(raw):
    """Whitespace-separated CSP source list for frame-ancestors, or ''.

    Administrator-controlled rather than user-controlled, so this is not a remote
    injection path — but a stray semicolon or comma silently produces an invalid
    or unexpectedly permissive header, which is worse than a startup failure.
    (Review round 2, #5)
    """
    raw = (raw or "").strip()
    if not raw:
        return ""
    if any(ch in raw for ch in (";", ",", "\n", "\r")):
        raise RuntimeError(
            "SKRIBL_EMBED_ORIGINS must be a space-separated list with no "
            f"semicolons, commas or newlines. Got: {raw!r}"
        )
    tokens = raw.split()
    # 'none' is a standalone source expression; combining it with origins yields a
    # policy that does not mean what the administrator intended. (Round 4, #4)
    if "'none'" in tokens and len(tokens) != 1:
        raise RuntimeError("SKRIBL_EMBED_ORIGINS value 'none' must be used alone.")
    if len(tokens) != len(set(tokens)):
        raise RuntimeError("SKRIBL_EMBED_ORIGINS contains duplicate entries.")
    normalised = []
    for token in tokens:
        if token in _CSP_KEYWORD_SOURCES:
            normalised.append(token)
            continue
        if not _is_bare_origin(token):
            raise RuntimeError(
                f"SKRIBL_EMBED_ORIGINS entry {token!r} must be 'self', 'none', or a "
                "bare origin scheme://host[:port] — https, or http only for "
                "localhost/127.0.0.1/[::1]. No path, query, fragment, userinfo or "
                "wildcard host."
            )
        normalised.append(_normalise_origin(token))
    # Canonical form is emitted, not the raw token: one representation for
    # capitalisation, IPv6 brackets, default ports and trailing slashes, so what
    # lands in the header is always a bare origin. (Round 4, #5)
    if len(normalised) != len(set(normalised)):
        raise RuntimeError("SKRIBL_EMBED_ORIGINS contains duplicate origins.")
    return " ".join(normalised)


# --- CSP + security headers, scoped to the blueprint ------------------------
def register_security(bp, skribl_version, player_target="_blank"):
    # --- Content Security Policy ---------------------------------------------
    # Deferred until v105 for a good reason: while gifenc/mp4-muxer came from
    # jsdelivr, any workable policy needed a third-party script-src, and the app
    # also had inline <script type="module"> loaders. Vendoring both libraries
    # (v103/v104) removed the last off-origin script AND the last inline module,
    # so a genuinely strict script-src is now possible.
    #
    # What made this cheap: the templates have ZERO inline event handlers
    # (onclick=...), zero javascript: URLs, and only two inline <script> blocks
    # (the SKRIBL_MODE config in the editor and player). Those two get a
    # per-request nonce. Note that a nonce DISABLES 'unsafe-inline' for scripts
    # in CSP2+ browsers, which is exactly what we want — but it also means any
    # inline handler added later will silently stop firing. verify_csp.py fails
    # loudly if one appears.
    #
    # Deliberate looseness, each load-bearing:
    #   style-src 'unsafe-inline'  — 51 style="..." attributes across the
    #       templates. Style ATTRIBUTES cannot be nonced (a nonce only covers
    #       <style> blocks), so this is required until they're refactored. Much
    #       lower risk than inline script, and there is no user-controlled style
    #       injection surface here.
    #   connect-src data:          — NOT optional. app.js fetches data: URLs
    #       directly (`fetch(data.music.data)`, `fetch(built.dataUrl)`) to get
    #       audio into an ArrayBuffer. Omitting this breaks music loading on the
    #       player and the WAV/MP4 build path, silently.
    #   img-src/media-src data: blob: — canvas toDataURL, new Audio(dataUrl),
    #       and createObjectURL for downloads and playback.
    #
    # NO frame-ancestors, on purpose. The roadmap embeds the player in an iframe
    # on skribls.net, and the previous note here warned that a blanket deny would
    # break that. Omitting the directive leaves framing unrestricted, matching the
    # existing (deliberate) absence of X-Frame-Options. Do not "harden" this
    # without checking the embed first.
    #
    # SKRIBL_CSP=off disables it; SKRIBL_CSP=report-only sends the policy as
    # Content-Security-Policy-Report-Only, so a deploy can watch for violations
    # before enforcing. Default is enforcing.
    csp_mode = os.environ.get("SKRIBL_CSP", "on").strip().lower()
    embed_origins = _validate_embed_origins(os.environ.get("SKRIBL_EMBED_ORIGINS", ""))

    @bp.before_request
    def _make_csp_nonce():
        # Per-request, per-response nonce. Generated for every request (not just
        # rendered ones) so the header and the template can never disagree.
        g.csp_nonce = secrets.token_urlsafe(16)

    # context_processor, NOT app_context_processor. The app_ variant runs for
    # templates rendered by EVERY view, and this one calls relative endpoints
    # (url_for(".create_skribl")) — which, outside a Skribl request, resolve
    # against the wrong blueprint or none at all and raise BuildError. It would
    # have broken unrelated host pages that never mention Skribl.
    @bp.context_processor
    def _expose_template_globals():
        # Route bases are derived, never literals. Templates hardcoded
        # "/api/skribls" and flip.js hardcoded both it and "/s/", so a url_prefix
        # would have broken posting on Flip while every harness suite stayed
        # green (the suites drive the root prefix too). Deriving them here means
        # the prefix move is a registration change, not a search-and-replace.
        return {"csp_nonce": getattr(g, "csp_nonce", ""),
                "skribl_version": skribl_version,
                "skribl_csrf_token": getattr(g, "skribl_csrf_token", ""),
                "skribl_api_base": url_for(".create_skribl"),
                "skribl_player_base": url_for(".skribl_player", public_id="").rstrip("/"),
                "skribl_player_target": player_target}

    @bp.before_request
    def _prepare_csrf():
        if bp.skribl_csrf:
            bp.skribl_csrf[0]()

    @bp.after_request
    def _issue_csrf(resp):
        if bp.skribl_csrf:
            resp = bp.skribl_csrf[1](resp)
        return resp

    @bp.before_request
    def _inflate_request():
        """Accept a gzipped request body.

        Response compression cannot touch the direction that actually hurts
        here. Measured on a photo-plus-music post: 2,382,255 B of request body
        against 33 ms of server processing. The seven seconds a user waits on
        Post is upload transfer, essentially all of it base64 media inside the
        JSON, and no amount of work on the response side moves it. Gzipped, the
        same body is about 40 KB.

        Optional and backwards compatible: a client that does not set the header
        is untouched, so an older cached editor keeps posting exactly as before.

        The cap is the point of the decompressobj: MAX_CONTENT_LENGTH bounds the
        COMPRESSED bytes Werkzeug will read, which is no bound at all on what
        they expand to. Decompression stops at the same limit and the request is
        refused, so a few KB cannot become a few GB of resident memory.
        """
        if (request.method not in ("POST", "PUT", "PATCH")
                or (request.headers.get("Content-Encoding") or "").lower() != "gzip"):
            return None
        limit = current_app.config.get("MAX_CONTENT_LENGTH") or 25_000_000
        try:
            dec = zlib.decompressobj(16 + zlib.MAX_WBITS)
            plain = dec.decompress(request.get_data(cache=False), limit)
            if dec.unconsumed_tail or not dec.eof:
                raise ValueError("body expands past MAX_CONTENT_LENGTH")
        except Exception:
            return jsonify({"error": "Malformed compressed request body."}), 400
        request._cached_data = plain
        request.environ["wsgi.input"] = io.BytesIO(plain)
        request.environ["CONTENT_LENGTH"] = str(len(plain))
        request.environ.pop("HTTP_CONTENT_ENCODING", None)
        return None

    @bp.after_request
    def _cache_and_compress(resp):
        """Long-cache the busted assets and gzip our own responses.

        SCOPE FIRST: this is `bp.after_request`, so it touches ONLY responses
        from this blueprint. A `flask_compress` on the application, or an
        app-wide after_request, would compress and cache the HOST'S pages too —
        the same reach-past-the-seam mistake the FK listener made.

        Measured before this: the editor pulled 25 files / 559,734 B and the
        player 5 files / 350,950 B, every one of them `Cache-Control: no-cache`
        and uncompressed. Flask's default max-age is no-cache, so every page
        load revalidated all 25 — on a phone that is seconds of round trips
        before anything renders, and it is what left a shared link sitting on an
        unsized 300x150 canvas while app.js (214 KB, uncompressed) arrived.

        The long cache is SAFE because asset_url() busts on content: a changed
        file gets a new ?v=, so nothing stale can be pinned. It is applied only
        when that bust is present — an un-busted request is not immutable and
        must not be treated as such. setdefault throughout, so a host or CDN
        that sets its own policy wins.
        """
        is_static = (request.endpoint == f"{bp.name}.static"
                     and resp.status_code == 200)
        bust = request.args.get("v") if is_static else None
        if bust:
            # Assignment, not setdefault: send_file already put "no-cache" here
            # from SEND_FILE_MAX_AGE_DEFAULT. Safe to overwrite ONLY because
            # asset_url() busts on content, so a changed file gets a new ?v=.
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        # STRIP BEFORE COMPRESSING, and inline here rather than in a second
        # after_request, because Flask runs those in reverse registration order:
        # a separate handler would have to be registered AFTER this one to run
        # BEFORE it, which is a correctness-critical ordering that reads as a
        # mistake. The sequence is explicit instead.
        #
        # Only busted requests are stripped. Without a ?v= there is no key to
        # cache under, and paying ~90 ms of lexing per request to save 32% of a
        # transfer is the same bad trade as gzip level 6 on a dynamic response.
        # An unbusted asset therefore serves its comments, which is correct
        # JavaScript either way — the file on disk is what it always was.
        if bust and request.path.endswith(".js"):
            key = (request.path, bust)
            lean = _STRIP_CACHE.get(key)
            if lean is None:
                resp.direct_passthrough = False
                lean = strip_bytes(resp.get_data(), request.path)
                if len(_STRIP_CACHE) >= _STRIP_CACHE_MAX:
                    _STRIP_CACHE.clear()          # bounded; refills on demand
                _STRIP_CACHE[key] = lean
            if len(lean) != resp.headers.get("Content-Length", type=int):
                resp.direct_passthrough = False
                resp.set_data(lean)
                # send_file's ETag is derived from the FILE on disk, and this is
                # no longer that byte sequence. Two entities under one tag is
                # the defect the -gzip suffix below already exists to fix.
                etag = resp.headers.get("ETag")
                if etag:
                    resp.headers["ETag"] = (etag[:-1] + '-strip"' if etag.endswith('"')
                                            else etag + "-strip")

        # Decide BEFORE touching the body. The first version of this turned off
        # direct_passthrough for every busted asset, which materialised fonts
        # and images into memory to then not compress them, and it recompressed
        # app.js on every single request: 10.4 ms against 0.6 ms unmodified, 37 ms
        # of CPU for one cold page load of 25 assets, serialised across two sync
        # workers. Compression that costs more than the transfer it saves is not
        # an optimisation.
        if not (resp.status_code == 200
                and "Content-Encoding" not in resp.headers
                and "gzip" in (request.headers.get("Accept-Encoding") or "")
                and _COMPRESSIBLE.match(resp.mimetype or "")):
            resp.vary.add("Accept-Encoding")
            return resp

        packed = None
        if bust:
            # A busted URL names one immutable byte sequence, so its compressed
            # form is equally immutable: compress once per file version and hand
            # out the bytes thereafter. The ?v= IS the content key; no stat call
            # is needed to know the entry is still valid.
            key = (request.path, bust)
            packed = _GZIP_CACHE.get(key)
            if packed is None:
                resp.direct_passthrough = False
                body = resp.get_data()
                if len(body) < _GZIP_MIN:
                    resp.vary.add("Accept-Encoding")
                    return resp
                packed = gzip.compress(body, 6)   # paid once, so buy the ratio
                if len(packed) >= len(body):
                    packed = None
                if packed is not None:
                    if len(_GZIP_CACHE) >= _GZIP_CACHE_MAX:
                        _GZIP_CACHE.clear()        # bounded; refills on demand
                    _GZIP_CACHE[key] = packed
        else:
            # Dynamic, or an unbusted asset: the result cannot be reused, so buy
            # speed instead of ratio. On app.js level 1 is 2.9 ms for 77 KB where
            # level 6 is 9.0 ms for 64 KB — six milliseconds of a worker for
            # thirteen kilobytes, on a response nobody will ask for twice.
            resp.direct_passthrough = False
            body = resp.get_data()
            if len(body) >= _GZIP_MIN:
                cand = gzip.compress(body, 1)
                packed = cand if len(cand) < len(body) else None

        if packed is not None:
            resp.direct_passthrough = False
            resp.set_data(packed)
            resp.headers["Content-Encoding"] = "gzip"
            resp.headers["Content-Length"] = str(len(packed))
            # A gzipped body is not the same entity as the plain one. send_file's
            # ETag is derived from the FILE, so both variants were going out
            # under one tag — Vary saves a compliant cache, but a tag that
            # identifies two different byte sequences is simply wrong. nginx
            # suffixes it; so do we.
            etag = resp.headers.get("ETag")
            if etag:
                resp.headers["ETag"] = etag[:-1] + '-gzip"' if etag.endswith('"') \
                    else etag + "-gzip"
        resp.headers.add("Vary", "Accept-Encoding")
        return resp

    @bp.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if csp_mode != "off":
            nonce = getattr(g, "csp_nonce", "")
            policy = "; ".join([
                "default-src 'self'",
                f"script-src 'self' 'nonce-{nonce}'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: blob:",
                "media-src 'self' data: blob:",
                "connect-src 'self' data: blob:",
                "font-src 'self'",
                "worker-src 'self' blob:",
                "base-uri 'self'",
                "form-action 'self'",
                "object-src 'none'",
            ])
            # Review #11 / round 2 #4: this used to test `path.startswith("/s/")`,
            # which also matched /s/<id>/card.png and every 404 under that prefix,
            # so error responses were left framable. Key off the matched endpoint
            # instead — only the HTML player gets the permissive treatment, and
            # only while SKRIBL_EMBED_ORIGINS is unset so an existing embed cannot
            # break on deploy. Card images and errors take the restrictive default.
            # A 404 raised INSIDE skribl_player still carries that endpoint, so the
            # endpoint alone is not enough: only a successful HTML render is the
            # embeddable thing. Errors under /s/ take the restrictive default.
            is_player = (request.endpoint or "").rsplit(".", 1)[-1] == "skribl_player" and resp.status_code == 200
            if is_player:
                if embed_origins:
                    policy += "; frame-ancestors " + embed_origins
            else:
                policy += "; frame-ancestors 'self'"
            header = ("Content-Security-Policy-Report-Only"
                      if csp_mode == "report-only" else "Content-Security-Policy")
            resp.headers.setdefault(header, policy)
        return resp


def install_standalone_security(app):
    """Apply Skribl's baseline headers to responses no blueprint handled.

    Only for the STANDALONE app, where Skribl is the whole site and a 404 on an
    unrouted path is still Skribl's 404 — it must not be left framable. A host
    application must NOT call this: its own 404s, its own error pages and its own
    pages are its own to police, and Skribl silently stamping a policy on them is
    exactly the app-wide clobbering that scoping to the blueprint fixed.

    Uses setdefault, and the blueprint's own after_request runs first for Skribl
    endpoints, so this never overrides the per-route policy above.
    """
    csp_mode = os.environ.get("SKRIBL_CSP", "on").strip().lower()

    @app.after_request
    def _baseline_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if csp_mode != "off":
            nonce = getattr(g, "csp_nonce", "")
            policy = "; ".join([
                "default-src 'self'",
                f"script-src 'self' 'nonce-{nonce}'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: blob:",
                "media-src 'self' data: blob:",
                "connect-src 'self' data: blob:",
                "font-src 'self'",
                "worker-src 'self' blob:",
                "base-uri 'self'",
                "form-action 'self'",
                "object-src 'none'",
                "frame-ancestors 'self'",
            ])
            header = ("Content-Security-Policy-Report-Only"
                      if csp_mode == "report-only" else "Content-Security-Policy")
            resp.headers.setdefault(header, policy)
        return resp


# --- CSRF -------------------------------------------------------------------
# Skribl has no CSRF protection in v131, and that is CORRECT there: the API is
# unauthenticated, so there is no session for a cross-origin form to ride and
# nothing an attacker gains by making a victim's browser post a drawing.
#
# The moment a host authenticates POST /api/skribls with a cookie, that changes
# completely: any page on the internet can then post as the logged-in user. The
# vulnerability is CREATED BY the integration, which is why the seam belongs
# here rather than in the host's backlog.
#
# Two ways to satisfy it, because hosts differ:
#   * The host owns CSRF already (Flask-WTF, Django-style middleware). It passes
#     its own validator and its own token source; Skribl just calls them.
#   * The host has nothing. `double_submit_csrf()` below is a complete,
#     dependency-free implementation it can use as-is.
CSRF_HEADER = "X-Skribl-CSRF"
CSRF_COOKIE = "skribl_csrf"


def double_submit_csrf(cookie_name=CSRF_COOKIE, header_name=CSRF_HEADER):
    """A double-submit CSRF triple: (prepare, issue, validate).

    Double-submit rather than server-side session state, so it works for a host
    that keeps no server-side session and adds no storage requirement. The token
    goes in a cookie AND in a header; an attacker's page can cause the cookie to
    be sent, but same-origin policy stops it READING the cookie to set the
    matching header.

    Requires SameSite=Lax at minimum, which `issue` sets. Compared with
    hmac.compare_digest so a wrong token cannot be discovered a character at a
    time by timing the response.
    """
    def prepare():
        """Resolve the token BEFORE the view runs.

        This has to happen in before_request, not after: the template renders
        during the view, so a token established in after_request arrives too late
        and the page ships an empty `window.SKRIBL_CSRF_TOKEN` — the client then
        sends no header and every post is refused. (Caught by verify_csrf.py on
        its first run, which is exactly the "created by the integration" failure
        this seam exists to prevent.)
        """
        token = request.cookies.get(cookie_name)
        g.skribl_csrf_token = token or secrets.token_urlsafe(32)
        g.skribl_csrf_is_new = not token

    def issue(response):
        if getattr(g, "skribl_csrf_is_new", False):
            response.set_cookie(
                cookie_name, g.skribl_csrf_token,
                httponly=False,      # the client script must read it to echo it
                samesite="Lax",
                # request.is_secure is only true if Flask can SEE the original
                # scheme. Behind a TLS-terminating proxy that is a deployment
                # setting (ProxyFix / X-Forwarded-Proto), not something this
                # package can know, so an HTTPS site whose proxy headers are not
                # trusted would ship this cookie WITHOUT Secure. Set
                # SKRIBL_FORCE_SECURE_COOKIES=1 to state that the public origin
                # is HTTPS regardless of what the request object believes.
                secure=_FORCE_SECURE or request.is_secure,
                max_age=60 * 60 * 12,
            )
        return response

    def validate(req):
        sent = req.headers.get(header_name, "")
        known = req.cookies.get(cookie_name, "")
        if not sent or not known:
            return False
        return hmac.compare_digest(sent, known)

    return prepare, issue, validate
