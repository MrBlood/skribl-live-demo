"""Passkeys: the WebAuthn ceremonies, through py_webauthn (not hand-rolled).

    begin(purpose, ...)   a fresh challenge, kept for this browser and this
                          purpose, five minutes, then the options the page
                          hands navigator.credentials
    take(purpose)         the challenge back, once: it is deleted as it is read

A REGISTRATION (join, recovery, adding another) asks for a DISCOVERABLE
credential (resident key required), so signing in needs no handle typed:
the passkey says whose it is. USER VERIFICATION IS REQUIRED both ways (Face
ID, Touch ID, Windows Hello, a key's PIN), not merely a tap. No attestation is
asked for: the site needs to know the key is the person's, not its maker.

THE ADDRESS IS THE REQUEST'S (rp()): the relying party is the host the page
was served from, and the origin its scheme and host, so passkeys made on the
demo's address work there and are made again after the move to a domain.
Each passkey keeps the address it was made on (rp_id) and only signs in there.
A host that is a bare IP address cannot hold a passkey at all (browsers refuse
it), so the site says so rather than letting the browser fail obscurely.

THE SITE'S OWN ADDRESSES (after v330; the review of piece 2, on the owner's
yes): when they are named, a passkey is made and used only there.
SKRIBL_SOCIAL_HOSTS names them (comma-separated: the demo's onrender name, and
the domain once there is one, set at the move to it). A request whose address
is not one of them begins no ceremony and is told kindly (`Elsewhere`).
Unnamed (a laptop, CI, the demo until it is set), it is each request's own
address, as it always was: a site reached by one name only loses nothing.

THE SIGN COUNT is checked by the library and stored after every sign-in: an
authenticator that counts must count up, or the sign-in is refused (a copied
key). Many passkeys (synced ones) always say 0, which the library allows.
"""
import ipaddress
import json
import os
import secrets
from datetime import timedelta

import sqlalchemy as sa
from flask import current_app, request

from .models import Challenge, as_utc, utcnow
from .security import browser_sid, is_https, sid_hash, site

#: How long a page has to finish a ceremony it began.
CHALLENGE_FOR = timedelta(minutes=5)
#: What the browser is told it has (it may give less).
TIMEOUT_MS = 120000
RP_NAME = "Blooby"


class NoName(Exception):
    """The page's address is a bare IP address: no passkey can belong to it."""


class Elsewhere(Exception):
    """The page's address is not one of the site's own (own_hosts())."""


class Refused(Exception):
    """The browser's answer did not check out. `key` names what to say."""

    def __init__(self, key):
        super().__init__(key)
        self.key = key


def own_hosts():
    """The site's own addresses, lower case, or None when nothing names them:
    the app's config or SKRIBL_SOCIAL_HOSTS (comma-separated)."""
    raw = current_app.config.get("SKRIBL_SOCIAL_HOSTS") or os.environ.get("SKRIBL_SOCIAL_HOSTS", "")
    hosts = {h.strip().lower().rstrip(".") for h in str(raw).split(",") if h.strip()}
    return hosts or None


def rp():
    """(rp_id, origin) for this request: its host, and the origin the browser is on."""
    host = request.host
    name = host.rsplit(":", 1)[0] if not host.startswith("[") else host.split("]", 1)[0] + "]"
    try:
        ipaddress.ip_address(name.strip("[]"))
        raise NoName(name)
    except ValueError:
        pass
    own = own_hosts()
    if own is not None and name.lower() not in own:
        raise Elsewhere(name)
    return name.lower(), ("https" if is_https() else request.scheme) + "://" + host


def begin(purpose, *, person_id=None, invite_id=None, data=None):
    """A new challenge for this browser and purpose, replacing any it had.
    Written through the request's session: it commits with the request."""
    sess = site().session()
    key = sid_hash(browser_sid())
    sess.execute(sa.delete(Challenge).where(Challenge.sid_hash == key, Challenge.purpose == purpose))
    # Old ceremonies nobody finished are swept as new ones begin, a few at a time.
    stale = sa.select(Challenge.id).where(Challenge.expires_at < utcnow()).limit(50)
    sess.execute(sa.delete(Challenge).where(Challenge.id.in_(stale.scalar_subquery())))
    challenge = secrets.token_bytes(32)
    sess.add(Challenge(sid_hash=key, purpose=purpose, challenge=challenge, person_id=person_id,
                       invite_id=invite_id, data=json.dumps(data) if data is not None else None,
                       created_at=utcnow(), expires_at=utcnow() + CHALLENGE_FOR))
    sess.flush()
    return challenge


def take(purpose):
    """This browser's challenge for `purpose`, deleted as it is read, or None
    if there is none or it is too old. Used once whatever happens next."""
    sess = site().session()
    row = sess.execute(sa.select(Challenge).where(Challenge.sid_hash == sid_hash(browser_sid()),
                                                  Challenge.purpose == purpose)).scalar_one_or_none()
    if row is None:
        return None
    sess.delete(row)
    sess.flush()
    if as_utc(row.expires_at) < utcnow():
        return None
    return row


def registration_options(challenge, *, rp_id, user_handle, handle, display_name, exclude=()):
    from webauthn import generate_registration_options, options_to_json
    from webauthn.helpers.structs import (AttestationConveyancePreference,
                                          AuthenticatorSelectionCriteria,
                                          PublicKeyCredentialDescriptor,
                                          ResidentKeyRequirement,
                                          UserVerificationRequirement)
    options = generate_registration_options(
        rp_id=rp_id, rp_name=RP_NAME, user_id=user_handle, user_name=handle,
        user_display_name=display_name, challenge=challenge, timeout=TIMEOUT_MS,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=c) for c in exclude])
    return json.loads(options_to_json(options))


#: Everything a browser's answer can make the library raise. A body can say
#: anything; it is refused, never a 500.
_BAD_ANSWER = (ValueError, TypeError, KeyError, AttributeError, IndexError)


def verify_registration(credential, challenge, *, rp_id, origin):
    """The new passkey, checked: the challenge, the origin, the address, a
    user who was verified. Raises Refused('failed') otherwise, and for
    anything that is not an answer at all (only a JSON object can be one)."""
    from webauthn import verify_registration_response
    from webauthn.helpers.exceptions import WebAuthnException
    if not isinstance(credential, dict):
        raise Refused("failed")
    try:
        return verify_registration_response(credential=credential, expected_challenge=challenge,
                                            expected_rp_id=rp_id, expected_origin=origin,
                                            require_user_verification=True)
    except (WebAuthnException,) + _BAD_ANSWER as exc:
        raise Refused("failed") from exc


def authentication_options(challenge, *, rp_id):
    from webauthn import generate_authentication_options, options_to_json
    from webauthn.helpers.structs import UserVerificationRequirement
    options = generate_authentication_options(rp_id=rp_id, challenge=challenge, timeout=TIMEOUT_MS,
                                              allow_credentials=[],
                                              user_verification=UserVerificationRequirement.REQUIRED)
    return json.loads(options_to_json(options))


def read_assertion(credential):
    """The parts of a sign-in answer read before it is checked: which
    credential, and which account it says it is for."""
    from webauthn.helpers import parse_authentication_credential_json
    from webauthn.helpers.exceptions import WebAuthnException
    if not isinstance(credential, dict):
        raise Refused("failed")
    try:
        return parse_authentication_credential_json(credential)
    except (WebAuthnException,) + _BAD_ANSWER as exc:
        raise Refused("failed") from exc


def verify_assertion(parsed, challenge, *, rp_id, origin, public_key, sign_count):
    from webauthn import verify_authentication_response
    from webauthn.helpers.exceptions import WebAuthnException
    try:
        return verify_authentication_response(credential=parsed, expected_challenge=challenge,
                                              expected_rp_id=rp_id, expected_origin=origin,
                                              credential_public_key=public_key,
                                              credential_current_sign_count=sign_count,
                                              require_user_verification=True)
    except (WebAuthnException,) + _BAD_ANSWER as exc:
        raise Refused("failed") from exc


def transports_of(credential):
    """The transports the browser said the new passkey has, as stored."""
    try:
        got = credential.get("response", {}).get("transports") or []
    except AttributeError:
        return None
    known = {"usb", "nfc", "ble", "smart-card", "internal", "cable", "hybrid"}
    kept = [t for t in got if isinstance(t, str) and t in known]
    return ",".join(kept)[:120] or None


def default_nickname(user_agent, taken):
    """A first name for a new passkey, from the device it was made on; the
    person can rename it. "iPhone", then "iPhone 2" if that is taken."""
    ua = user_agent or ""
    for needle, name in (("iPhone", "iPhone"), ("iPad", "iPad"), ("Android", "Android"),
                         ("CrOS", "Chromebook"), ("Windows", "Windows"), ("Macintosh", "Mac"),
                         ("Mac OS X", "Mac"), ("Linux", "Linux")):
        if needle in ua:
            break
    else:
        name = "Passkey"
    taken = {t.lower() for t in taken}
    if name.lower() not in taken:
        return name
    n = 2
    while f"{name} {n}".lower() in taken:
        n += 1
    return f"{name} {n}"
