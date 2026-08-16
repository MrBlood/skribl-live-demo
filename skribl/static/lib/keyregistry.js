/* lib/keyregistry.js — what is bound to which key, and whether two things
   answer at once.

   NOT A COMMAND ROUTER. It does not dispatch, does not preventDefault, does not
   stopPropagation and does not decide who wins. Every existing handler keeps
   its own listener and its own behaviour; this only records what each one
   CLAIMS to bind and reports when more than one claim is live for the key that
   was actually pressed. Routing would mean rewriting eight working handlers and
   inheriting the ordering bugs that come with a single dispatch point — the
   opposite of what this is for.

   WHY IT EXISTS, from the tree rather than from principle. flip.js already
   carries this comment:

     "ArrowLeft/ArrowRight are handled by the flip-scrub block above, which adds
      hold-to-riffle. Leaving the single-step versions here as well meant BOTH
      fired on one press and the page advanced twice."

   Two listeners, one key, both live, found by someone noticing a page advance
   twice. The fix was to delete one and leave a comment where the collision had
   been — which is a guard only for as long as the next person reads it. There
   are five separate global Escape listeners in that file and two on Space.
   Nothing anywhere states the whole set, so the only way to know whether a new
   binding is free is to grep and hope.

   WHAT "UNIQUE" HAS TO MEAN HERE. Not one binding per key: the five Escapes are
   correct, because each is scoped to a different surface being open. So a
   registration may declare a `scope` predicate, and the check is that AT MOST
   ONE scope is true at the moment the key fires. That is a runtime fact, not a
   static one, and it is the fact that was actually wrong in the arrow-key bug —
   both handlers were unscoped, so both were always live.

   Two things are therefore detectable, and they are different:

     unconditional()  two registrations share a key and neither declares a
                      scope. Reportable without pressing anything.
     collisions()     two scopes were true when the key was pressed. Needs the
                      key pressed in that state, which is what the suite drives.
*/
(function (global) {
  'use strict';

  var registered = [];
  var seen = [];
  var attached = false;

  // "Mod" is Ctrl or Cmd, deliberately one token: every existing handler here
  // writes (e.ctrlKey||e.metaKey), and splitting them would make the registry
  // disagree with the code it describes.
  function parse(token) {
    var parts = String(token).split('+');
    var key = parts.pop();
    var spec = {key: key, mod: false, shift: false, alt: false};
    for (var i = 0; i < parts.length; i++) {
      var p = parts[i].toLowerCase();
      if (p === 'mod') spec.mod = true;
      else if (p === 'shift') spec.shift = true;
      else if (p === 'alt') spec.alt = true;
    }
    return spec;
  }

  function keyMatches(spec, e) {
    if (spec.key === 'Space') return e.code === 'Space' || e.key === ' ';
    if (spec.key.length === 1) {
      return String(e.key).toLowerCase() === spec.key.toLowerCase();
    }
    return e.key === spec.key;
  }

  function matches(spec, e) {
    if (!keyMatches(spec, e)) return false;
    if (spec.mod !== !!(e.ctrlKey || e.metaKey)) return false;
    if (spec.shift !== !!e.shiftKey) return false;
    if (spec.alt !== !!e.altKey) return false;
    return true;
  }

  function attach() {
    if (attached) return;
    attached = true;
    // CAPTURE phase, so the record is taken before any handler can stopPropagation
    // and hide the collision from the very mechanism that exists to find it.
    global.addEventListener('keydown', function (e) {
      var live = [];
      for (var i = 0; i < registered.length; i++) {
        var r = registered[i];
        var hit = false;
        for (var j = 0; j < r.specs.length; j++) {
          if (matches(r.specs[j], e)) { hit = true; break; }
        }
        if (!hit) continue;
        var active = true;
        if (r.scope) {
          // A scope that throws is not evidence of anything, so it is recorded
          // as such rather than counted as active or silently swallowed.
          try { active = !!r.scope(); }
          catch (err) { active = false; r.scopeError = String(err); }
        }
        if (active) live.push(r);
      }
      if (live.length > 1) {
        seen.push({
          key: (e.ctrlKey || e.metaKey ? 'Mod+' : '') + (e.shiftKey ? 'Shift+' : '')
               + (e.code === 'Space' ? 'Space' : e.key),
          claims: live.map(function (r) { return r.surface + ':' + r.label; })
        });
      }
    }, true);
  }

  var KeyRegistry = {
    /* register({surface, label, keys, scope})
       keys   array of tokens: 'Escape', 'Space', 'Mod+z', 'Mod+Shift+z', 'p'
       scope  optional () -> boolean. OMITTING IT IS A CLAIM: it says this
              binding is live whenever the surface is, which is what makes two
              unscoped registrations on one key a reportable duplicate. */
    register: function (entry) {
      attach();
      var r = {
        surface: entry.surface || '?',
        label: entry.label || '?',
        keys: entry.keys || [],
        specs: (entry.keys || []).map(parse),
        scope: entry.scope || null,
        scopeError: null
      };
      registered.push(r);
      return r;
    },

    /* Registrations sharing a key where two or more declare no scope. Static —
       no key needs to be pressed, so a suite can assert it on load. */
    unconditional: function () {
      var byKey = {}, out = [];
      registered.forEach(function (r) {
        if (r.scope) return;
        r.keys.forEach(function (k) {
          (byKey[k] = byKey[k] || []).push(r.surface + ':' + r.label);
        });
      });
      Object.keys(byKey).forEach(function (k) {
        if (byKey[k].length > 1) out.push({key: k, claims: byKey[k]});
      });
      return out;
    },

    /* Collisions actually observed: two scopes true for one press. */
    collisions: function () { return seen.slice(); },

    /* Every key any surface claims, for the suite and for a human. */
    list: function () {
      return registered.map(function (r) {
        return {surface: r.surface, label: r.label, keys: r.keys.slice(),
                scoped: !!r.scope, scopeError: r.scopeError};
      });
    },

    count: function () { return registered.length; },
    reset: function () { seen = []; }
  };

  global.KeyRegistry = KeyRegistry;
})(window);
