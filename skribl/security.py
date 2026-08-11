"""Embed-origin parsing and the Content-Security-Policy.

The policy body is unchanged from v131. What changed is its SCOPE: it was an
app-wide after_request, which in a host application would either clobber the
platform's policy or be clobbered by it. It is now attached to the blueprint, so
it covers Skribl's own routes and Skribl's own static files and nothing else.
"""
import hmac
import ipaddress
import os
import secrets
from urllib.parse import urlsplit

from flask import g, request, url_for

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
def register_security(bp, skribl_version):
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
                "skribl_player_base": url_for(".skribl_player", public_id="").rstrip("/")}

    @bp.before_request
    def _prepare_csrf():
        if bp.skribl_csrf:
            bp.skribl_csrf[0]()

    @bp.after_request
    def _issue_csrf(resp):
        if bp.skribl_csrf:
            resp = bp.skribl_csrf[1](resp)
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
