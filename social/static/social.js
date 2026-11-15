/* The site's sheets: MAKE'S (social/templates/social/_make.html), the ☰'S
 * on a phone's Home and Gallery (_menu.html, below), and every other sheet
 * the site raises the same way (Your face, on your own profile: profile.js,
 * through window.SocialSheet below).
 *
 * Make is a choice, not a page: a small sheet with two doors, Draw (Skribl's
 * Pad) and Flip (Skribl's Flip), raised by the bar's Make on a phone, the
 * rail's on a desk, and Home's "Make a skribl". The owner's yes, Nov 10.
 * That is Make for somebody signed out (and on a site without accounts);
 * signed in, Make is the composer since Nov 14 (compose.js, _compose.html),
 * which is this same sheet made tall, and its two doors are its tools.
 *
 * KIND, NEVER JUMPY. The sheet glides up from the bottom of a phone and back
 * down when it goes (social.css; a desk's card rises a little and fades);
 * under Reduce Motion it fades where it sits. Nothing here sets a position
 * on a timer: the stylesheet moves it, this only says open or closed, and
 * hides the sheet once the last of it has faded (the scrim, the slowest).
 *
 * IT GOES AWAY EASILY: a door picked (the door's own link then opens its
 * editor), Cancel where a sheet has one (Make's; a ⋯'s has none), a tap
 * outside it, a tap on its grip, Esc, and on a phone a
 * swipe down from anywhere on it, which follows the finger (the owner, v317:
 * "menus should always go down or away easily"). Nothing behind it scrolls
 * meanwhile: the stylesheet gives it touch-action: none, which also stops a
 * pull to refresh, so no touch handler here needs to cancel anything. A part
 * of a sheet with a gesture of its own (a list that scrolls, a drawing to
 * drag) is named to it (`ownTouch`) and keeps its gesture.
 *
 * FOCUS, AS A DIALOG'S. Opening moves focus to the first door and makes the
 * page behind it inert; Tab stays inside; closing gives focus back to the
 * button that opened it. The words are all in the template: nothing here
 * says anything (docs/SOCIAL-SITE.md, words in one place per page).
 *
 * AND THE EDITOR OVER THE PAGE (window.SocialPadOverlay, below): the Pad or
 * Flip in compose mode for your face (profile.js) and for a post (posts.js).
 * AND A PHONE'S KEYBOARD (window.SocialKeyboard, below): a sheet whose words
 * take one rides above it (the composer, a comment's sheet).
 *
 * ONE CONTROLLER, EVERY SHEET: window.SocialSheet(wrap, options) gives a
 * `.make`-shaped sheet these moving parts and returns { open, close, isOpen }.
 * Options: openers (marked aria-expanded), first (what takes focus on open),
 * doorCloses (a .make-door closes the sheet, as Make's links do; Your face's
 * doors lead on inside it), ownTouch (a selector for the parts above),
 * onOpen (called as it begins to rise), onSettled (called once it has gone).
 */
(function () {
  'use strict';
  var doc = document;
  var desk = window.matchMedia ? window.matchMedia('(min-width: 900px)') : null;
  /* Longer than the slowest fade (the scrim's), in case its transitionend
     never comes: a tab put in the background mid-glide, say. */
  var SETTLE_MS = 450;

  function shown(el) { return !!el && el.getClientRects().length > 0; }

  /* ONE SHEET OVER ANOTHER (the owner's "A", Nov 15: "Unfollow Theo?" over
     your follows sheet): the sheets open, in the order they rose. Esc and Tab
     are the top one's alone, and the page behind stays out of reach until
     the last one has gone. */
  var OPEN = [];

  function sheetFor(wrap, o) {
    o = o || {};
    var sheet = wrap.querySelector('.make-sheet');
    var scrim = wrap.querySelector('.make-scrim');
    var openers = o.openers || [];
    var behind = [doc.querySelector('body > .top'), doc.querySelector('body > .nav'), doc.getElementById('main')];
    var isOpen = false, from = null, timer = 0, drag = null;
    var self = {};

    function mark(on) {
      for (var i = 0; i < openers.length; i++) {
        if (openers[i].tagName !== 'SPAN') openers[i].setAttribute('aria-expanded', on ? 'true' : 'false');
      }
      for (var j = 0; j < behind.length; j++) {
        if (!behind[j]) continue;
        if (on) behind[j].setAttribute('inert', ''); else if (!OPEN.length) behind[j].removeAttribute('inert');
      }
    }

    function open(opener) {
      if (isOpen) return;
      isOpen = true;
      OPEN.push(self);
      from = opener || null;
      clearTimeout(timer);
      wrap.classList.remove('is-closing', 'is-dragging');
      sheet.style.transform = '';
      wrap.hidden = false;
      /* Read a size, so the glide starts from where the sheet rests closed
         (below the screen) rather than appearing where it ends. */
      void sheet.offsetHeight;
      wrap.classList.add('is-open');
      mark(true);
      if (o.onOpen) o.onOpen();
      var first = o.first ? o.first() : sheet.querySelector('.make-door');
      if (first) first.focus({ preventScroll: true });
    }

    function settle() {
      if (isOpen) return;
      clearTimeout(timer);
      var was = !wrap.hidden;
      wrap.hidden = true;
      wrap.classList.remove('is-closing', 'is-dragging');
      sheet.style.transform = '';
      if (was && o.onSettled) o.onSettled();
    }

    /* `quiet`: something else takes focus next (a door that opens the Pad
       over the page), so focus is not handed back here. */
    function close(quiet) {
      if (!isOpen) return;
      isOpen = false;
      if (OPEN.indexOf(self) >= 0) OPEN.splice(OPEN.indexOf(self), 1);
      drag = null;
      wrap.classList.add('is-closing');
      wrap.classList.remove('is-open', 'is-dragging');
      sheet.style.transform = '';
      mark(false);
      var back = !quiet && shown(from) ? from : null;
      from = null;
      if (back) back.focus({ preventScroll: true });
      clearTimeout(timer);
      timer = setTimeout(settle, SETTLE_MS);
    }

    scrim.addEventListener('transitionend', function (e) {
      if (e.target === scrim && !isOpen) settle();
    });

    wrap.addEventListener('click', function (e) {
      if (e.target.closest('[data-make-close]')) { close(); return; }
      /* A door: its link opens the editor; the sheet goes down as it does, so
         the page the back button returns to has it closed. */
      if (o.doorCloses !== false && e.target.closest('.make-door')) close();
    });

    doc.addEventListener('keydown', function (e) {
      if (!isOpen || OPEN[OPEN.length - 1] !== self) return;
      if (e.key === 'Escape') { e.preventDefault(); close(); return; }
      if (e.key !== 'Tab') return;
      var stops = Array.prototype.filter.call(
        sheet.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]):not([type=hidden]), [tabindex="0"]'), shown);
      if (!stops.length) return;
      var first = stops[0], last = stops[stops.length - 1], at = doc.activeElement;
      if (e.shiftKey && (at === first || !sheet.contains(at))) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && (at === last || !sheet.contains(at))) { e.preventDefault(); first.focus(); }
    });

    /* A page the back button brings back whole (the bfcache) comes back as it
       was left: if a door was picked, closed. */
    window.addEventListener('pageshow', function (e) { if (e.persisted && !isOpen) settle(); });

    /* THE SWIPE DOWN, a phone's bottom sheet only (a desk's card has no
       bottom to go to). It follows the finger once it has moved a little, so a
       tap on a door stays a tap, and lets go past a quarter of the sheet or on
       a quick flick; less, and it glides back up. */
    sheet.addEventListener('touchstart', function (e) {
      if (!isOpen || (desk && desk.matches) || e.touches.length !== 1 ||
          (o.ownTouch && e.target.closest && e.target.closest(o.ownTouch))) { drag = null; return; }
      drag = { y: e.touches[0].clientY, t: e.timeStamp, dy: 0, h: sheet.offsetHeight, on: false };
    }, { passive: true });
    sheet.addEventListener('touchmove', function (e) {
      if (!drag) return;
      var dy = e.touches[0].clientY - drag.y;
      if (!drag.on && dy < 6) return;
      if (!drag.on) { drag.on = true; drag.y += 6; dy -= 6; wrap.classList.add('is-dragging'); }
      drag.dy = Math.max(0, dy);
      sheet.style.transform = 'translateY(' + drag.dy + 'px)';
    }, { passive: true });
    function letGo(e, cancelled) {
      var d = drag;
      drag = null;
      if (!d || !d.on) return;
      var flick = d.dy > 24 && e.timeStamp - d.t < 250;
      if (!cancelled && (d.dy > d.h / 4 || flick)) { close(); return; }
      wrap.classList.remove('is-dragging');
      sheet.style.transform = '';
    }
    sheet.addEventListener('touchend', function (e) { letGo(e, false); });
    sheet.addEventListener('touchcancel', function (e) { letGo(e, true); });

    self.open = open;
    self.close = close;
    self.isOpen = function () { return isOpen; };
    self.sheet = sheet;
    return self;
  }

  window.SocialSheet = sheetFor;

  /* A PHONE'S KEYBOARD (window.SocialKeyboard): a sheet whose words take a
   * keyboard rides above it, the composer (compose.js) and a comment's sheet
   * (comments.js) alike. The keyboard is what the visual viewport lost at
   * the bottom of the layout viewport the sheet is fixed to (iPhone's Safari
   * shrinks only the visual one), less any way the visual viewport has been
   * moved down; a pinch's zoom is not a keyboard, so only at a scale of 1.
   *
   * READ AGAIN UNTIL IT RESTS (the owner's iPhone, Nov 14: the composer
   * opened with its foot halfway up the screen and its words drawn over
   * Home, until a touch put it right). While a keyboard comes or goes, a
   * phone can report a size it is only passing through, then say nothing
   * more once it rests. So whenever anything could move it (the visual or
   * the layout viewport changing, a field in the sheet taking or losing
   * focus, the sheet opening), the keyboard is read on every frame for the
   * next second and a half, and by timers in case frames are held meanwhile,
   * and the sheet rides above what it rests at. NOT SEEN HERE: this box has
   * no phone keyboard; the suites stand one in for the visual viewport, and
   * a keyboard that says nothing once it rests is among them.
   *
   * When the page itself changes size with the keyboard (Chrome on an
   * iPhone), the sheet takes the new reading at once rather than gliding
   * to it, so it never hops above the keyboard on the way.
   *
   * SocialKeyboard(wrap, name, isOpen) keeps --<name> on wrap (the
   * keyboard, in px; none without one) and returns { watch, read }. */
  var REREAD_MS = 1500;
  function keyboardFor(wrap, name, isOpen) {
    var vv = window.visualViewport, raf = 0, until = 0, said = -1, late = [], page = window.innerHeight;
    function read() {
      var kb = 0, now = window.innerHeight, moved = now !== page;
      page = now;
      if (vv && isOpen() && Math.abs((vv.scale || 1) - 1) < 0.01) {
        kb = Math.max(0, Math.round(now - vv.height - vv.offsetTop));
      }
      if (kb === said) return;
      said = kb;
      /* THE PAGE ITSELF CHANGED SIZE (Chrome on an iPhone shrinks it for the
         keyboard): the sheet's fixed box has moved with it already, so the
         new reading is taken at once (.kb-now), not glided to, or the sheet
         would hop up above the keyboard and back down to it. Over a page
         that keeps its size, the sheet glides with the keyboard (social.css). */
      if (moved) wrap.classList.add('kb-now');
      if (kb) wrap.style.setProperty('--' + name, kb + 'px');
      else wrap.style.removeProperty('--' + name);
      if (moved) {
        void wrap.offsetHeight;
        var done = function () { wrap.classList.remove('kb-now'); };
        requestAnimationFrame(done);
        setTimeout(done, 100);
      }
    }
    function frame() {
      raf = 0;
      read();
      if (Date.now() < until) raf = requestAnimationFrame(frame);
    }
    function watch() {
      read();
      until = Date.now() + REREAD_MS;
      if (!raf) raf = requestAnimationFrame(frame);
      while (late.length) clearTimeout(late.pop());
      [250, 700, REREAD_MS + 500].forEach(function (ms) { late.push(setTimeout(read, ms)); });
    }
    if (vv) {
      vv.addEventListener('resize', watch);
      vv.addEventListener('scroll', watch);
    }
    window.addEventListener('resize', watch);
    wrap.addEventListener('focusin', watch);
    wrap.addEventListener('focusout', watch);
    return { watch: watch, read: read };
  }

  window.SocialKeyboard = keyboardFor;

  /* THE EDITOR, OVER THE PAGE: Skribl's Pad or Flip in compose mode, in a
   * frame over the page, for your face (profile.js) and for a post (posts.js).
   * Skribl's lib/composehost.js is the editor's side of it (the frame's
   * address set on the first open and never in the page, a drawing reopened
   * the one it handed back, messages checked by origin both ways); this is the
   * page's: it glides up over the page and back down (a desk's card rises a
   * little as it fades in), under Reduce Motion it fades where it sits
   * (social.css, .facepad), and nothing here sets a position on a timer.
   * While it is up the page behind is inert and still, and closing gives
   * focus back to where the person was. The editor brings its own ×; a tap
   * beside a desk's card puts it away, the drawing kept in it.
   *
   *   var over = SocialPadOverlay(wrap, { openers, onDone, onReady });
   *   over.open(back)          // back: what takes focus when it goes
   *   over.guide(file, back)   // a face's photo to trace (composehost guide)
   *   over.openDraft(id, back) // a saved draft on its canvas (the composer's
   *                            // Yours; composehost openDraft)
   *
   * `wrap` is the overlay (.facepad: its scrim, its sheet, its frame, and the
   * editor's address in data-compose); `openers` are marked aria-expanded. */
  function padOver(wrap, o) {
    o = o || {};
    if (!wrap || !window.SkriblComposeHost) return null;
    var frame = wrap.querySelector('.facepad-frame');
    var scrim = wrap.querySelector('.facepad-scrim');
    var openers = o.openers || [];
    var behind = [doc.querySelector('body > .top'), doc.querySelector('body > .nav'), doc.getElementById('main')];
    var from = null, timer = 0, open = false, was = [];

    /* The page behind goes inert while it is up, and comes back as it was:
       opened from a sheet (a phone's comment box), the page stays inert
       behind the sheet once the editor goes. */
    function mark(on) {
      for (var i = 0; i < openers.length; i++) {
        if (openers[i].hasAttribute('aria-expanded')) openers[i].setAttribute('aria-expanded', on ? 'true' : 'false');
      }
      for (var j = 0; j < behind.length; j++) {
        if (!behind[j]) continue;
        if (on) { was[j] = behind[j].hasAttribute('inert'); behind[j].setAttribute('inert', ''); }
        else if (!was[j]) behind[j].removeAttribute('inert');
      }
    }

    function settle() {
      if (open) return;
      clearTimeout(timer);
      wrap.hidden = true;
      wrap.classList.remove('is-closing');
      doc.body.classList.remove('facepad-open');
    }

    var pad = window.SkriblComposeHost.create({
      frame: frame,
      src: wrap.getAttribute('data-compose'),
      onOpen: function () {
        if (open) return;
        open = true;
        clearTimeout(timer);
        wrap.classList.remove('is-closing');
        wrap.hidden = false;
        doc.body.classList.add('facepad-open');
        /* Read a size, so the glide starts from where the sheet rests closed. */
        void wrap.offsetHeight;
        wrap.classList.add('is-open');
        mark(true);
        try { frame.focus({ preventScroll: true }); } catch (e) { /* not focusable yet */ }
      },
      onClose: function () {
        if (!open) return;
        open = false;
        wrap.classList.add('is-closing');
        wrap.classList.remove('is-open');
        mark(false);
        if (from && from.getClientRects().length && from.focus) from.focus({ preventScroll: true });
        from = null;
        clearTimeout(timer);
        timer = setTimeout(settle, SETTLE_MS);
      },
      onReady: function () { wrap.classList.add('is-ready'); if (o.onReady) o.onReady(); },
      onDone: function (payload, preview, hasAudio) { if (o.onDone) o.onDone(payload, preview, hasAudio); }
    });

    if (scrim) {
      scrim.addEventListener('transitionend', function (e) { if (e.target === scrim && !open) settle(); });
      scrim.addEventListener('click', function () { pad.close(); });
    }

    return {
      pad: pad,
      open: function (back) { from = back || null; pad.open(); },
      guide: function (file, back) { from = back || null; pad.guide(file); },
      openDraft: function (id, back) { from = back || null; wrap.classList.remove('is-ready'); pad.openDraft(id); },
      isOpen: function () { return open; }
    };
  }

  window.SocialPadOverlay = padOver;

  /* THE ONE PILL (window.SocialPill): the tint under the chosen option of
   * every .fo-seg on the site (Home's Following | Everyone, the Gallery's two,
   * your lists' Followers | Following, the composer's Drafts | Drawings).
   * Here since the composer, whose picker carries one on every page; it was
   * follows.js's, which reads it from here now, as explore.js and compose.js
   * do. Placed from the rendered boxes, to the hundredth of a pixel (as
   * Skribl's lib/segslider.js places the Gallery's): the first time, and
   * `now`, put there; after that it glides (social.css), and is put there
   * under Reduce Motion. Until it is placed, the chosen option wears the tint
   * itself. choose() presses an option and glides the tint to it. */
  function place(seg, now) {
    var pill = seg.querySelector('.fo-slider'), btn = seg.querySelector('button[aria-pressed="true"]');
    var g = seg.getBoundingClientRect(), b = btn ? btn.getBoundingClientRect() : null;
    if (!pill || !b || !b.width || !g.width) { seg.removeAttribute('data-pill'); return; }
    var x = Math.round((b.left - g.left - seg.clientLeft - (parseFloat(getComputedStyle(pill).left) || 0)) * 100) / 100;
    var w = Math.round(b.width * 100) / 100;
    var first = now || !seg.hasAttribute('data-pill');
    if (first) pill.style.transition = 'none';
    pill.style.transform = 'translateX(' + x + 'px)';
    pill.style.width = w + 'px';
    if (first) {
      seg.setAttribute('data-pill', '');
      void pill.offsetWidth;
      pill.style.transition = '';
    }
  }
  function choose(seg, btn) {
    Array.prototype.forEach.call(seg.querySelectorAll('button'), function (b) {
      b.setAttribute('aria-pressed', b === btn ? 'true' : 'false');
    });
    place(seg, false);
  }
  window.SocialPill = { choose: choose, place: place };
  /* Watched, so a pill in a sheet that ships hidden, a late font or a turned
     phone still has its tint where its option is. */
  Array.prototype.forEach.call(doc.querySelectorAll('.fo-seg'), function (seg) {
    var wide = 0;
    function again() {
      var w = seg.getBoundingClientRect().width;
      place(seg, !wide || !w);
      wide = w;
    }
    if (window.ResizeObserver) new ResizeObserver(again).observe(seg);
    again();
    if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(again);
  });

  /* TIMES, IN THE PERSON'S OWN (window.SocialWhen): every <time data-when>
   * under `root` said as the site says a time: "now", "35m", "2h", "3d", then
   * the day ("Nov 3"); data-when="at", the day and the hour ("Nov 10 at 8:20
   * PM"). Here, not in posts.js, so any page can say them (follows: your
   * own page's lists, where Skribl's Gallery leaves no room for posts.js).
   * The words are the page's ([data-word="now"], [data-word="at"]). */
  function word(key) {
    var w = doc.querySelector('[data-word="' + key + '"]');
    return w ? w.textContent : '';
  }
  window.SocialWhen = function (root) {
    var now = Date.now();
    Array.prototype.forEach.call((root || doc).querySelectorAll('time[data-when]'), function (t) {
      var d = new Date(t.getAttribute('datetime'));
      if (isNaN(d)) return;
      var sameYear = d.getFullYear() === new Date(now).getFullYear();
      var day = d.toLocaleDateString(undefined, sameYear ? { month: 'short', day: 'numeric' }
                                                         : { month: 'short', day: 'numeric', year: 'numeric' });
      if (t.getAttribute('data-when') === 'at') {
        t.textContent = word('at').split('{day}').join(day)
          .split('{time}').join(d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }));
        return;
      }
      var mins = Math.floor((now - d) / 60000);
      t.textContent = mins < 1 ? word('now') : mins < 60 ? mins + 'm' : mins < 1440 ? Math.floor(mins / 60) + 'h'
        : mins < 10080 ? Math.floor(mins / 1440) + 'd' : day;
    });
  };

  /* THE THEME, ON A PAGE THE BACK BUTTON BRINGS BACK WHOLE (the bfcache):
     a choice made while it was away (Settings, the Pad's or Flip's own menu,
     another tab) never reached it, so it takes the one chosen now, through
     Skribl's own theme code (lib/theme.js), as the page comes back. */
  window.addEventListener('pageshow', function (e) {
    var T = window.SkriblTheme;
    if (e.persisted && T) T.apply(T.get());
  });

  /* ACTIVITY'S DOT GOES AS YOU LOOK (notifications): a tap on the bell (a
     phone's top) or the rail's Activity lets the dot fade while Activity
     opens (social.css, .is-seen), so a page the back button brings back
     whole has it gone too. Opening Activity is what marks it seen. */
  doc.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[data-activity]') : null;
    if (a) a.classList.add('is-seen');
  });

  /* THE ☰ ON A PHONE (the quick-patterns mock; the owner's "Yes on
     everything", Nov 13): the site's own sheet (_menu.html), the ⋯'s, rising
     from the bottom, focus on its first row. A row picked (a link, or Sign
     out's form) goes, and the sheet goes down as it does, so the page the
     back button brings back has it closed. Esc, a tap outside it, its grip
     and a swipe down close it, giving the ☰ its focus back; it has no
     Cancel (the owner's "B, equal lines", Nov 14), as the Pad's menu has
     none. */
  var siteMenu = doc.getElementById('siteMenu');
  var menuBtn = doc.querySelector('[data-site-menu]');
  if (siteMenu && menuBtn) {
    var menuApi = sheetFor(siteMenu, {
      openers: [menuBtn], doorCloses: false,
      first: function () { return siteMenu.querySelector('.post-act'); }
    });
    menuBtn.addEventListener('click', function (e) {
      e.preventDefault();
      menuApi.open(menuBtn);
    });
    siteMenu.addEventListener('click', function (e) {
      if (e.target.closest('a.post-act, button.post-act[type="submit"]')) menuApi.close(true);
    });
    homeScreen(siteMenu, menuApi, menuBtn);
  }

  /* BLOOBY ON THE HOME SCREEN (the owner, Nov 15: "Let's do the home icon so
     I can get full screen on my iPhone"). The ☰'s two rows start hidden
     (_menu.html), and this says which one this phone gets, if either:
       - opened from the Home Screen (navigator.standalone, or the standalone
         display the site's manifest asks for): Reload, as there is no browser
         bar to reload with;
       - an iPhone or an iPad in a browser tab (iPadOS says it is a Mac, so a
         Mac with a touch screen counts): Add to Home Screen, which lets the ☰
         go down and the steps rise (_homescreen.html), giving the ☰ its
         focus back when they close;
       - anywhere Chrome offers its own install (beforeinstallprompt, as on
         Android): Add to Home Screen, which asks Chrome; gone once installed;
       - a desk, or a browser that offers nothing: neither. */
  function homeScreen(menu, menuApi, menuBtn) {
    var add = doc.getElementById('siteAddHome');
    var reload = doc.getElementById('siteReload');
    var steps = doc.getElementById('homeSteps');
    if (!add || !reload) return;
    var nav = window.navigator;
    var installed = nav.standalone === true;
    try { installed = installed || window.matchMedia('(display-mode: standalone)').matches; } catch (e) { /* none */ }
    if (installed) {
      reload.hidden = false;
      reload.addEventListener('click', function () {
        menuApi.close(true);
        window.location.reload();
      });
      return;
    }
    var apple = /iP(hone|od|ad)/.test(nav.userAgent || '') || (nav.platform === 'MacIntel' && nav.maxTouchPoints > 1);
    if (apple && steps) {
      var stepsApi = sheetFor(steps, { first: function () { return steps.querySelector('.btn-primary'); } });
      add.hidden = false;
      add.addEventListener('click', function () {
        menuApi.close(true);
        var icon = steps.querySelector('img');
        if (icon) icon.loading = 'eager';
        stepsApi.open(menuBtn);
      });
      return;
    }
    var offer = null;
    window.addEventListener('beforeinstallprompt', function (e) {
      e.preventDefault();
      offer = e;
      add.hidden = false;
    });
    window.addEventListener('appinstalled', function () { offer = null; add.hidden = true; });
    add.addEventListener('click', function () {
      if (!offer) return;
      menuApi.close(true);
      offer.prompt();
      offer = null;
      add.hidden = true;
    });
  }

  var make = doc.getElementById('makeSheet');
  if (!make) return;
  var openers = doc.querySelectorAll('[data-make]');
  var api = sheetFor(make, { openers: openers });
  for (var i = 0; i < openers.length; i++) {
    openers[i].addEventListener('click', function (e) {
      e.preventDefault();
      api.open(e.currentTarget);
    });
  }
})();
