/* lib/autosavepill.js — the autosave pill: one owner for its five states and,
 * when media is missing, the way out.
 *
 * Pad and Flip each had a showAutosaveStatus() — Flip's "ported from the
 * Pad" — and they had drifted (v294): Flip's amber named the action ("Media
 * missing — tap to re-add") and was a control that opened the drawer holding
 * the re-add card; the Pad's said "Saved without media", did nothing when
 * tapped, and with a pending record and no bytes reported plain GREEN. The
 * owner, from a phone: "the re-add media button doesn't go away unless I
 * click it or go to the drawer and x out ... shouldn't they be unified?"
 *
 * One module now, driven by three callbacks the editor supplies:
 *   pending()  is there media the session has LOST — a pending record with
 *              no bytes behind it? (As opposed to media it merely could not
 *              make durable, which is amber with nothing to re-add.)
 *   open()     open the drawer holding the missing file's re-add card.
 *   dismiss()  do what that card's Dismiss does: clear the record and save.
 *
 * THE CONTROL IS THE PILL'S TEXT, NOT THE PILL. Beside it sits a × of its own
 * (created here, so the player's copy of the markup — which never has media
 * to lose — carries nothing extra), and a button inside a role=button is
 * invalid nesting. The status stays a status and holds two controls, each
 * announced only while it does something: role and tabindex are added exactly
 * while there is somewhere to go and removed the moment there is not.
 *
 * 'failed', 'full' and 'saved-no-media' STAY UP — each describes an ongoing
 * durability problem, and a warning that fades claims it was resolved. A
 * later successful save replaces them with 'saved', which fades.
 *
 * THE AMBER WITH NOTHING TO RE-ADD CAN BE ACKNOWLEDGED (v294). "Saved without
 * media" is true — the bytes did not reach the store — and it had no exit:
 * owner, from a phone, "it never leaves". The same × acknowledges it for the
 * session and the pill goes quiet; it is not a lie hidden, because the leave
 * guard the editors arm on that state is untouched. Any OTHER state speaks
 * again — a later save that lands the bytes shows green, a new loss shows the
 * route — so an acknowledgement is of this warning, not of warnings. */
(function () {
  'use strict';
  var cfg = { pending: function () { return false; }, open: null, dismiss: null };
  var bound = false;
  var acknowledged = false;   // the no-route amber, quiet until the state changes

  function ensureDismiss(pill) {
    var x = document.getElementById('autosaveStatusDismiss');
    if (x) return x;
    x = document.createElement('button');
    x.type = 'button';
    x.id = 'autosaveStatusDismiss';
    x.className = 'autosave-dismiss';
    x.textContent = '✕';
    x.hidden = true;
    pill.appendChild(x);
    return x;
  }

  // The 'show' class is added on the NEXT frame, and a save reports 'saving'
  // and its outcome in the same tick: a hide that only removed the class lost
  // the race to the frame still queued by 'saving', and an acknowledged pill
  // came back reading "Saving…" for good (found by the pin, first cut). The
  // queued frame is cancelled here, and the hide timer is the pill's one.
  function hide(pill) {
    cancelAnimationFrame(pill._showRaf);
    pill.classList.remove('show');
    clearTimeout(pill._hideTimer);
    pill._hideTimer = setTimeout(function () { pill.hidden = true; }, 300);
  }

  // `on`: the pill is a route (pending record). `amber`: either amber wording,
  // which is when the × is offered — as Dismiss for a route, as acknowledge
  // for the warning with nowhere to go.
  function setActionable(pill, txt, on, amber) {
    pill.classList.toggle('actionable', !!on);
    var x = ensureDismiss(pill);
    if (on) {
      txt.setAttribute('role', 'button');
      txt.setAttribute('tabindex', '0');
      txt.setAttribute('title', 'Open the drawer holding the missing file');
    } else {
      txt.removeAttribute('role');
      txt.removeAttribute('tabindex');
      txt.removeAttribute('title');
    }
    x.hidden = !amber;
    if (amber) {
      x.setAttribute('aria-label', on ? 'Dismiss — keep the drawing without its media'
                                      : 'Dismiss this warning for now');
      x.title = on ? 'Keep the drawing without its media' : 'Hide this warning for now';
    }
    if (bound) return;
    bound = true;
    // stopPropagation: both editors close any open drawer on a click outside
    // it, at the document. Without this the drawer would open and shut in the
    // same event — opened here, closed by the same click still travelling up.
    var go = function (e) {
      if (!pill.classList.contains('actionable')) return;
      e.stopPropagation(); e.preventDefault();
      if (cfg.open) cfg.open();
    };
    txt.addEventListener('click', go);
    txt.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') go(e);
    });
    x.addEventListener('click', function (e) {
      e.stopPropagation(); e.preventDefault();
      if (pill.classList.contains('actionable')) { if (cfg.dismiss) cfg.dismiss(); return; }
      acknowledged = true;
      hide(pill);
    });
  }

  function show(state) {
    var pill = document.getElementById('autosaveStatus');
    var txt = document.getElementById('autosaveStatusText');
    if (!pill || !txt) return;
    clearTimeout(pill._hideTimer);
    var pending = state === 'saved-no-media' && !!(cfg.pending && cfg.pending());
    // The acknowledged warning stays quiet; 'saving' passes through it (every
    // save says so first) without resetting it; anything else is a new fact.
    if (state === 'saved-no-media' && !pending && acknowledged) { hide(pill); return; }
    if (state !== 'saving') acknowledged = false;
    pill.hidden = false;
    pill.classList.remove('saving', 'failed', 'partial');
    if (state === 'saving') { pill.classList.add('saving'); txt.textContent = 'Saving…'; }
    // 'failed' and 'full' are both red, and the difference matters: 'full'
    // means the browser's storage for this origin is out of room and the
    // drawing is NOT saved, which the user can act on; 'failed' is anything
    // else and they cannot.
    else if (state === 'failed') { pill.classList.add('failed'); txt.textContent = 'Autosave failed'; }
    else if (state === 'full') { pill.classList.add('failed'); txt.textContent = 'Storage full — not saved'; }
    // TWO WORDINGS for amber, because only one of them is something the user
    // can act on. With a pending record the file is GONE from the session and
    // the re-add card can put it back, so the pill names the action. Without
    // one the media is still loaded and in front of them; nothing needs
    // re-adding, it simply will not survive a reload, and "tap to re-add"
    // would send them to an empty drawer.
    else if (state === 'saved-no-media') {
      pill.classList.add('partial');
      txt.textContent = pending ? 'Media missing — tap to re-add' : 'Saved without media';
    }
    else { txt.textContent = 'Saved'; }
    setActionable(pill, txt, pending, state === 'saved-no-media');
    cancelAnimationFrame(pill._showRaf);
    pill._showRaf = requestAnimationFrame(function () { pill.classList.add('show'); });
    if (state !== 'saving' && state !== 'failed' && state !== 'full' && state !== 'saved-no-media') {
      pill._hideTimer = setTimeout(function () {
        pill.classList.remove('show');
        setTimeout(function () { pill.hidden = true; }, 300);
      }, 1600);
    }
  }

  window.SkriblAutosavePill = {
    configure: function (c) { cfg = Object.assign(cfg, c || {}); },
    show: show
  };
})();
