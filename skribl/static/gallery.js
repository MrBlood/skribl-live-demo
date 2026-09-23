/* The public gallery's own script: fetch the real listing, clone the real macro.
 *
 * This file is NOT the in-post player — inlineplayer.js is. What this does is
 * the job a host page does (feed.js is the recipe, and this is the same recipe
 * without a composer): get a page of public posts from GET /api/skribls, put a
 * skribl_inline() block in the DOM for each one, call SkriblInline.mount(), and
 * offer the next page through the listing's own keyset cursor.
 *
 * NOTHING HERE DECIDES WHAT IS PUBLIC. The author did, with one tick on the
 * post sheet (editor_post.js buildPostPayload, flip.js buildSharePayload), and
 * the server's visibility rules are the only filter. The listing is asked for
 * with a limit and a cursor and nothing else: no client-side filtering, no
 * fallback to invented tiles. An empty gallery renders as an empty gallery.
 */
(function () {
  'use strict';

  var list = document.getElementById('galleryList');
  var empty = document.getElementById('galleryEmpty');
  var errEl = document.getElementById('galleryError');
  var more = document.getElementById('galleryMore');
  var tpl = document.getElementById('skriblTileTpl');
  var api = document.body.getAttribute('data-skribl-api');
  var PAGE = 24;
  var cursor = null;       /* the keyset cursor for the next page, or null */
  var loading = false;
  var sort = 'new';        /* new | hot -- the server's orders */
  var query = '';          /* the search box's words, sent as q */
  var noneEl = document.getElementById('galleryNone');
  var subEl = document.getElementById('gallerySub');
  /* WHICH REQUEST IS STILL WANTED. Bumped by every load; a response may only
     touch the page while its own number is still the current one. See load(). */
  var gen = 0;

  /* A LINK THE HOST SUPPLIED IS STILL SOMEBODY ELSE'S STRING. `author.url`
     comes from the host's resolver, which a host may well build from a
     database column, so it is not trusted to be a web address: an
     `href="javascript:..."` runs on click, and a tile is a thing people click.
     Only http and https, and only after the URL parser agrees -- a scheme
     check on the raw text is the substring search this tree keeps learning
     not to write. A relative path is allowed by resolving it against this
     document first, which is what makes a host's `/u/name` work.
     Anything else yields null and the name renders as plain text. */
  function safeHref(raw) {
    if (!raw || typeof raw !== 'string') return null;
    var u;
    try { u = new URL(raw, document.baseURI); } catch (e) { return null; }
    return (u.protocol === 'http:' || u.protocol === 'https:') ? u.href : null;
  }

  /* WHO MADE IT, under the title (owner: "at the top under the title which
     probably makes more sense").

     SKRIBL HAS NO USER TABLE and this does not invent one. Everything here is
     what the host's resolver returned for the post's user_id
     (models.set_author_resolver, docs/INTEGRATION.md) -- display_name,
     username, avatar_url, url, verified -- and the field names are the ones
     skribls.net already renders in its own post head. No author, no block:
     an anonymous post has no name to print, and a placeholder would be a
     claim about who drew it.

     The avatar falls back to an initial on a tinted disc rather than to a
     broken image or a silhouette, which is what the host does for a user with
     no photo; `onerror` covers a URL that resolves and then 404s, because a
     cracked-image glyph in a grid of drawings reads as a broken page.

     AND AN UNNAMED POST SAYS SO OUT LOUD. This function used to return null
     and the card drew no author at all, on the reasoning that "a placeholder
     would be a claim about who drew it". Half of that is right and the
     conclusion was not: a card with a hole where every neighbour has a face
     reads as BROKEN, not as anonymous, and the owner read it that way the
     first time they saw a grid of them. The answer is to name the STATE --
     "Anonymous" on a plain disc -- which invents no person and is the same
     move as a null canvas size falling back to the band crop rather than
     guessing 4:3. Say unknown out loud; never guess.

     `isAnon` is what keeps that honest. It carries no handle, no link, no
     tick and no initial, so nothing on it can be mistaken for somebody's
     identity, and `.tanon` is what the suite asserts on. */
  /* THE UNATTRIBUTED CARD, given a shape instead of a gap. No handle, no
     link, no tick, no initial -- an initial would be a letter of a name that
     does not exist. A neutral disc and one word. */
  var ICON_MORE =
    '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
    '<circle cx="5" cy="12" r="1.9" fill="currentColor"/>' +
    '<circle cx="12" cy="12" r="1.9" fill="currentColor"/>' +
    '<circle cx="19" cy="12" r="1.9" fill="currentColor"/></svg>';

  /* LINES OF TEXT, NOT A SPEECH BUBBLE. A bubble is the shape every product
     on a phone uses for a CONVERSATION -- a reply, a comment, a thread -- and
     what this control opens is the author's own description, which nobody can
     answer (there are no comments on a Skribl and the post is immutable once
     made). The owner read the bubble as the wrong promise before reading it as
     the wrong size: "not sure that's the best icon for caption/description".

     Three ranged lines is the settled glyph for a body of text, and it is
     already the shape of the description the card is hiding. */
  var ICON_CAP =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"' +
    ' stroke-linecap="round" aria-hidden="true" focusable="false">' +
    '<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h9"/></svg>';

  /* U+1F7CD, SIX POINTED PINWHEEL STAR. Six, and the first draft had EIGHT --
     the owner asked for the skribls.net star and got a generic sparkle, "too
     fat" and a different shape entirely.

     The geometry: outer vertices every 60 degrees, inner vertices offset from
     the midpoint by a SKEW of 16 degrees. That offset is the whole pinwheel --
     at zero it is a plain symmetric hexagram, and the lean is what makes each
     point read as turning rather than sitting. The inner radius is 3.15 to the
     outer's 10.6; a hexagram's would be 6.1, which is the fat the owner saw.

     Generated rather than hand-drawn, because twelve vertices placed by eye
     are twelve chances to make an asymmetric shape asymmetric in the wrong
     place. */
  var ICON_STAR =
    '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
    '<path fill="currentColor" d="M12 1.4L14.27 9.81L21.18 6.7L15.03 12.87' +
    'L21.18 17.3L12.76 15.06L12 22.6L9.73 14.19L2.82 17.3L8.97 11.13L2.82 6.7' +
    'L11.24 8.94Z"/></svg>';

  function anonBlock() {
    var wrap = document.createElement('div');
    wrap.className = 'tauth tanon';
    var av = document.createElement('span');
    av.className = 'tavatar tavatar-anon';
    av.setAttribute('aria-hidden', 'true');
    /* THE SKRIBL STAR, drawn rather than typed. U+1F7CD names the shape the
       owner means (six-pointed pinwheel) and almost no system font carries
       it, so a codepoint would render as a tofu box on most of the phones
       this page is read on -- which is the same class of mistake as the
       cracked-image glyph the avatar's onerror exists to avoid. Inline SVG
       renders identically everywhere and inherits currentColor. */
    av.innerHTML = ICON_STAR;
    var names = document.createElement('div');
    names.className = 'tnames';
    var line = document.createElement('div');
    line.className = 'tline';
    var dn = document.createElement('span');
    dn.className = 'tdn tdn-anon';
    dn.textContent = 'Anonymous';
    line.appendChild(dn);
    names.appendChild(line);
    wrap.appendChild(av);
    wrap.appendChild(names);
    return wrap;
  }

  function authorBlock(a) {
    var name = (a && (a.display_name || a.username)) || '';
    var isAnon = !name;
    if (isAnon) return anonBlock();
    var handle = a.username ? '@' + a.username : '';
    var wrap = document.createElement(safeHref(a.url) ? 'a' : 'div');
    wrap.className = 'tauth';
    if (wrap.tagName === 'A') {
      wrap.href = safeHref(a.url);
      /* The tile is not a link, so this one does not need to escape a click
         handler -- but the stage below IS interactive, and a bubbled click
         that both navigates and plays is neither. */
      wrap.addEventListener('click', function (e) { e.stopPropagation(); });
    }

    var av = document.createElement('span');
    av.className = 'tavatar';
    av.setAttribute('aria-hidden', 'true');
    var src = safeHref(a.avatar_url);
    if (src) {
      var img = document.createElement('img');
      img.src = src;
      img.alt = '';
      img.loading = 'lazy';
      img.decoding = 'async';
      img.addEventListener('error', function () {
        img.remove();
        av.textContent = name.charAt(0).toUpperCase();
      });
      av.appendChild(img);
    } else {
      av.textContent = name.charAt(0).toUpperCase();
    }
    wrap.appendChild(av);

    /* The names go in their own box so the TITLE can sit under them (direction
       B): avatar on the left, then name / handle / title stacked beside it,
       which is the post head skribls.net already renders. */
    var names = document.createElement('div');
    names.className = 'tnames';
    wrap.appendChild(names);
    var line = document.createElement('div');
    line.className = 'tline';
    names.appendChild(line);

    var dn = document.createElement('span');
    dn.className = 'tdn';
    dn.textContent = name;
    line.appendChild(dn);
    /* The tick is the HOST'S claim, not Skribl's -- Skribl has nothing to
       verify with. Titled so it says whose claim it is. */
    if (a.verified) {
      var vf = document.createElement('span');
      vf.className = 'tverified';
      vf.textContent = '\u2713';
      vf.title = 'Verified by the site this Skribl was posted from';
      line.appendChild(vf);
    }
    if (handle) {
      var un = document.createElement('span');
      un.className = 'tun';
      un.textContent = handle;
      line.appendChild(un);
    }
    return wrap;
  }

  function when(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d)) return '';
    var mins = Math.round((Date.now() - d.getTime()) / 60000);
    if (mins < 1) return 'now';
    if (mins < 60) return mins + 'm';
    if (mins < 1440) return Math.round(mins / 60) + 'h';
    return Math.round(mins / 1440) + 'd';
  }

  /* The two marks a tile can carry, in the app's own shapes: lib/postedui.js
     draws the same pen and the same book on the profile's rows, and a Flip is
     marked with a book everywhere in this product. Copied rather than shared
     because postedui.js is the profile's module and this page does not load
     it -- three lines of path data against a dependency on a module built for
     a different surface. */
  var ICON_FLIP =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"'
    + ' stroke-linecap="round" stroke-linejoin="round">'
    + '<path d="M12 6.5C9.5 4.9 6.4 4.6 3 5.2v13c3.4-.6 6.5-.3 9 1.3 2.5-1.6 5.6-1.9 9-1.3v-13c-3.4-.6-6.5-.3-9 1.3z"/>'
    + '<path d="M12 6.5v13.3"/></svg>';
  var ICON_PAD =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"'
    + ' stroke-linecap="round" stroke-linejoin="round">'
    + '<path d="M17 3.5a2.1 2.1 0 0 1 3 3L8.5 18 4 20l2-4.5z"/></svg>';

  /* The module is loaded by the page and started here; it suppresses itself
     on coarse pointers, so on a phone this call does nothing by design. */
  if (window.SkriblTooltip) window.SkriblTooltip.init();

  /* capToggles() WAS HERE AND IS NOT NEEDED ANY MORE. It measured, for every
     captioned card, whether a two-line clamp was actually cutting the text --
     because an expander that expands nothing is worse than no expander -- and
     re-ran on resize, since the same caption clips at 390 and does not at
     1280.

     None of that question exists now. The caption is CLOSED at rest and
     contributes no height, so the mark that opens it is warranted by the
     caption existing rather than by the clamp biting, which is a fact the
     listing already carries and no layout read can disagree with. One fewer
     forced layout per card per resize, and one fewer thing to be wrong.

     The measure is gone; what it was protecting is not. verify_gallery still
     asserts that a card with no caption draws no mark. */


  function tile(item) {
    var art = document.createElement('article');
    art.className = 'tile';
    art.setAttribute('data-id', item.id);

    /* DIRECTION B, the post-like card (owner picked it from three). The head
       is the shape skribls.net already renders in its own post head: who, then
       what. The title sits UNDER the name the way a post's body does, rather
       than sharing a flex row with the time, the play count and two buttons. */
    var head = document.createElement('div');
    head.className = 'thead';
    /* EVERY CARD GETS A BLOCK, named or not -- authorBlock() answers for both
       and `.tanon` is how the suite tells them apart. The old shape here was a
       null check with a `.tsolo` fallback that drew the title alone, which is
       the gap this change is about. */
    var who = authorBlock(item.author);
    var tt = document.createElement('div');
    tt.className = 'tt';
    tt.textContent = item.title || 'Untitled Skribl';
    who.querySelector('.tnames').appendChild(tt);
    head.appendChild(who);
    var tm = document.createElement('span');
    tm.className = 'tm';
    tm.textContent = when(item.created_at);
    /* THE TWO FACTS TRAVEL TOGETHER, and Report does not. They were three
       siblings of `.thead` separated by one gap, which is why the row read as
       "3d 2 plays Report" with nothing telling the eye where one ended. Age
       and plays are both things the post IS; Report is a thing you DO to it. */
    var meta = document.createElement('div');
    meta.className = 'tmeta';
    meta.appendChild(tm);
    /* PLAYS, as counted (v304): the seven-day count under Hot, the total
       otherwise. Zero says nothing rather than "0 plays". */
    var n = sort === 'hot' ? (item.views_recent || 0) : (item.views || 0);
    if (n > 0) {
      var pl = document.createElement('span');
      pl.className = 'plays';
      pl.textContent = n + (n === 1 ? ' play' : ' plays');
      meta.appendChild(pl);
    }
    head.appendChild(meta);
    /* THE OVERFLOW, ON EVERY TILE. Report used to be a word here, permanently,
       beside two facts -- which is how the head came to read as one run-on
       string, and why the owner's auditor asked for it to move: "reduce or
       remove permanently visible secondary controls."

       Report is the rarest thing anybody does to a card and it had the
       loudest slot in the head. Behind the menu it is still one tap from every
       tile, and the head is down to who, what and when.

       ONE MENU, SHARED, like the report sheet it opens. Twenty-four menus in
       the DOM is twenty-four sets of listeners for a thing only ever open
       once. */
    var rep = document.createElement('button');
    rep.type = 'button';
    /* NOT `tileMark`. It sat in the head beside the kind glyph and borrowed
       that class for its colour, and `.tile .tileMark` fixes width and height
       at 16 -- equal specificity, later in the sheet, so the control's own 34px
       lost and verify_layout's visible touch floor failed at 360, 390 and 430.
       
       Source order has now decided three things in this change that were meant
       to be decided by intent. The fix is not another selector: a control is
       not a mark, so it does not carry the mark's class. */
    rep.className = 'tileMore';
    rep.setAttribute('data-more', item.id);
    rep.setAttribute('aria-haspopup', 'menu');
    rep.setAttribute('aria-expanded', 'false');
    rep.setAttribute('aria-label', 'More for ' + (item.title || 'this Skribl'));
    rep.title = 'More';
    rep.innerHTML = ICON_MORE;
    rep.addEventListener('click', function (e) {
      e.stopPropagation();
      openMenu(item, rep);
    });
    /* A SIBLING OF THE FACT RUN, NOT A MEMBER OF IT. It was appended to
       `.tmeta` first and the suite caught it: age and plays are things the
       post IS, and this opens the things you can DO to it, so it sits outside
       the group with its own air -- the same place, and the same reasoning, as
       the Report word it replaces. Visually it is still the row's last item. */
    head.appendChild(rep);
    art.appendChild(head);



    /* The macro rendered the poster URL with the placeholder in it, so the
       real one is that same server-built path with the id substituted — no
       path is assembled here, which keeps this correct under a url_prefix. */
    /* FULL SCREEN, PER TILE (owner: "since the controls stay on the screen
       when playing, there should be a way to watch full size"). The gallery
       had no way to watch a drawing big: the profile stage has one, /s/<id>
       has one, and the page where the drawings actually are had none.

       THE WRAPPER IS FULLSCREENED, NOT THE PLAYER. This page's own comment
       says "Not one rule touches .skribl-inline: the component is the
       component", and a `:fullscreen` rule on it would be exactly that. The
       wrapper takes the display and the component sizes itself inside it,
       which is the same shape the profile's .stageCanvasWrap uses.

       The button exists only where the API does. iPhone Safari has fullscreen
       for <video> alone, and a control that did nothing there would be worse
       than not having one — the same rule library.js states at its own. */
    var stage = document.createElement('div');
    stage.className = 'tileStage';
    /* THE CONTROL IS UNCONDITIONAL NOW, and that is the whole change. It used
       to appear only where `document.fullscreenEnabled` said yes, on the sound
       rule that a button which cannot work should not be on screen -- which on
       an iPhone meant no way to enlarge a drawing on the one device where it
       is smallest (owner, twice). lib/immersive.js takes the real API where
       there is one and pins the stage over the viewport where there is not, so
       there is always something for the button to do. */
    var imm = null;      /* set below, once, with its onChange in hand */
    var foot = null;     /* the card's transport row, built after the stage */
    if (window.SkriblImmersive) {
      /* THE CONTROL IS IN THE FOOTER AND NOWHERE ELSE. This block used to build
         a second one, `.tileFull`, in the card's head -- correct while the head
         was the only place a tile had for a button, and a duplicate the moment
         direction B gave the card a transport row that already carries full
         screen. The first screenshot of the new card showed both, on all 24
         tiles: same glyph, same action, eight pixels apart. One control per
         thing a person can do. */
      /* A WAY OUT, INSIDE THE THING (owner: "also no x (which is fine) on full
         screen" -- fine on the real API, where Escape and the system gesture
         both work, and not fine at all in the fallback, where the page is
         still the page and nothing else exits it). The profile's stage has
         had this since v304 and the gallery did not, which is the same
         two-surfaces-one-product problem as the full screen control itself. */
      var exit = document.createElement('button');
      exit.type = 'button';
      exit.className = 'tileExit';
      exit.title = 'Leave full screen';
      exit.setAttribute('aria-label', 'Leave full screen');
      exit.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"'
        + ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        + '<path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>';
      exit.addEventListener('click', function (e) { e.stopPropagation(); imm.close(); });
      stage.appendChild(exit);
      /* WHAT A FULL SCREEN SHOWS. Idle, a tile shows the POSTER -- the share
         card, cropped to keep its wordmark band out of frame -- and the canvas
         sits at time zero underneath it, which for a replay is blank. That
         crop is right at tile size and wrong at screen size: it just cuts the
         picture off (the owner's screenshot, then the measurement: the poster
         ran 151->1249 across a box of 300->1100).
         So the card is hidden while the stage is up (the sheet does that) and
         the drawing takes its place: FULL SCREEN PLAYS IT, which is what that
         control means everywhere else.

         PLAY, not seek-to-the-end, and the measurement is why. A tile does not
         fetch its payload until somebody presses play -- a feed of fifty must
         not pull fifty payloads -- so `loaded` is false on a tile you have
         only looked at, and seeking a player with nothing in it paints
         nothing. Hiding the card would then have traded a cropped picture for
         a black screen. play() is the one call that loads AND shows, and it
         costs the embed nothing: this is the gallery's code driving the
         transport the profile's stage already drives.

         Reset on the way out so the tile goes back to being a tile. */
      /* THE BAR IS THE SAME OBJECT THE PROFILE'S STAGE USES (lib/fullbar.js).
         The two full screens diverged because each page built its own; neither
         builds one now. It lives INSIDE the wrapper because only the
         fullscreened subtree renders. */
      var bar = window.SkriblFullBar ? window.SkriblFullBar.attach(stage, {
        player: function () {
          var b = stage.querySelector('.skribl-inline');
          return (b && b._skriblInline) || null;
        },
        meta: function () {
          var a = item.author || {};
          return { title: item.title,
                   name: a.display_name || a.username || '',
                   handle: a.username ? '@' + a.username : '',
                   avatar: safeHref(a.avatar_url) };
        },
        onExit: function () { if (imm) imm.close(); }
      }) : null;

      var onFs = function (big) {
        var box = stage.querySelector('.skribl-inline');
        var pl = box && box._skriblInline;
        /* The bar follows the clock on a frame loop, so it runs only while it
           is on screen: a rAF per hidden bar per tile is a feed burning
           battery on nothing. */
        if (bar) bar.running(!!big);
        /* AND THE CARD'S ROW STOPS WHILE THE STAGE IS UP. Two bars over one
           drawing, one of them behind a pinned overlay, is two clocks read
           from the same player to paint one of them into a viewport nobody
           can see. The sync on the way back out is what repaints the footer's
           play glyph after full screen paused it. */
        if (foot) { foot.running(!big); foot.sync(); }
        /* BARE IS PERMANENT ON A CARD, so nothing here touches it. This line
           used to be `toggle('is-bare', !!big)`, written when full screen was
           the only thing on this page that supplied a transport -- so leaving
           full screen STRIPPED the class the card had added at build time and
           the component's own mute/loop cluster came back on the stage, under
           a footer that already has both. One round trip through full screen
           and the tile kept a second loop button for good (owner: "when you
           hover on the card the button in bottom right (recycle/loop) shows
           and it's redundant because it is on the player").

           The card sets `is-bare` once, in build(), because the footer is
           there from the first paint to the last. A toggle keyed to full
           screen is answering a question nobody on this page asks. */
        if (!box) return;
        /* THE PAGE SAYS WHEN, THE COMPONENT SAYS WHAT. `is-immersive` is the
           component's own state (inlineplayer.css): it hides the share card and
           lets the drawing scale to whatever contains it. Those rules used to
           live in this page's sheet, reaching into the player's internals —
           which is the copy verify_inline's gate exists to stop, and it caught
           it on main. */
        box.classList.toggle('is-immersive', !!big);
        if (!pl) return;
        if (big) { pl.play(); return; }
        pl.pause();
        if (pl.state().loaded) pl.seek(0);
      };
      imm = window.SkriblImmersive.attach(stage, { onChange: onFs });
    }

    var frag = tpl.content.cloneNode(true);
    var box = frag.querySelector('[data-skribl-inline]');
    box.setAttribute('data-skribl-id', item.id);
    /* THE DRAWING'S SHAPE, so the component can frame the idle poster where the
       canvas will be rather than showing the share card's ground either side of
       it (v309). Null on a row written before the column, and the component
       then keeps the band crop -- so this is written only when the listing
       actually answered, never as a default. */
    if (item.canvas_w && item.canvas_h) {
      box.setAttribute('data-skribl-w', item.canvas_w);
      box.setAttribute('data-skribl-h', item.canvas_h);
    }
    var poster = box.querySelector('.skribl-inline-poster');
    if (poster) {
      poster.setAttribute('src', poster.getAttribute('src').replace('__ID__', encodeURIComponent(item.id)));
      poster.setAttribute('alt', item.title || 'A Skribl');
    }
    /* WHAT IT IS, ON THE TILE (owner: "on public gallery it doesn't show a
       pen, book - no way to tell which"). The listing could not say until
       v307 put `kind` and `pages` on the post; it still defers the payload.

       NOT OVER THE DRAWING ANY MORE. They sat in two corners of the stage and
       the owner asked for the canvas back: "no need to show speaker in upper
       right corner - in fact, the canvas needs to be clean, nothing but
       drawing. maybe the pen/book can go up in the top line with 3d 2play
       report?" So they join the head's meta run, which is already where the
       post's other facts are -- kind leads it, sound closes it, and the
       drawing is left alone.

       What stays on the stage is the idle veil and its play triangle, which
       are not decoration: they are the affordance that says this moves, and a
       card without them reads as a black rectangle (v309, the same owner, the
       same page). Both are aria-hidden and the WORDS go in one visually
       hidden line -- a screen reader gets "Flip, 6 pages, with sound" as
       text, not two unlabelled glyphs.

       A NULL DRAWS NOTHING. `kind` is null on a row written before the
       column existed and not yet backfilled, and `has_audio` is null when
       nothing answered; a badge over either would be a guess printed as a
       fact, which is the bug this tree just fixed on the profile. */
    var marks = document.createElement('div');
    marks.className = 'tileMarks';
    marks.setAttribute('aria-hidden', 'true');
    if (item.kind === 'flip' || item.kind === 'pad') {
      marks.insertAdjacentHTML('beforeend',
        '<span class="tileMark tileKind">' + (item.kind === 'flip' ? ICON_FLIP : ICON_PAD) + '</span>');
    }
    /* NO SOUND BADGE. It was a green speaker beside the kind glyph and the
       owner took it off: "lose the green speaker icon. not necessary if there
       is music it will play." Which is right -- the badge announced a fact
       that announces itself one tap later, and it was the only coloured thing
       in a row that is otherwise quiet.

       The WORDS stay in the visually hidden line below. That line describes
       the post to a screen reader, not the badges, and "with sound" is worth
       knowing before you commit to playing something. */
    /* Appended to the head's fact run, not to the stage. `marks` is built
       above and placed here because the head is assembled before the stage
       exists; the meta element is the one that has been carrying age and
       plays since the run was grouped. */
    if (marks.firstChild) meta.insertBefore(marks, meta.firstChild);

    var says = [];
    if (item.kind === 'flip') says.push(item.pages > 1 ? item.pages + ' pages' : 'a flip');
    else if (item.kind === 'pad') says.push('a replay');
    if (item.has_audio === true) says.push('with sound');
    else if (item.has_audio === false) says.push('silent');
    if (says.length) {
      var sr = document.createElement('span');
      sr.className = 'tileSr';
      sr.textContent = says.join(', ');
      head.appendChild(sr);
    }

    stage.appendChild(frag);
    art.appendChild(stage);

    /* THE CAPTION CAME OFF THE ART. It was a scrim over the drawing because a
       poster-first card had nowhere else to put it; a post-like card has room
       for words, so it is text under the title, clamped to two lines, and the
       toggle EXPANDS it rather than revealing it. Nothing needs to sit on the
       picture. */
    /* EVERY CARD IS THE SAME HEIGHT, AND THE CAPTION IS WHY IT WAS NOT.
       The text sat between the head and the stage, so a card with a caption
       was two lines taller than one without -- and in a grid the short card's
       ROW stretches to match, which is the dead space at the bottom the owner
       photographed: "the message takes up space which, when next to a card
       with no caption, makes the card next to it have that empty space at the
       bottom. there has to be a way for the cards to be the same size."

       So the caption no longer contributes height at rest. It is collapsed to
       zero and opened by a mark in the HEAD's fact run, where there is already
       a row and no vertical cost -- the owner's own suggestion ("a button /
       toggle to show msg... if one is it accordions out to show it"), with one
       departure: a card with nothing to say draws NO mark rather than the
       words "no msg". A label announcing an absence is still furniture on
       every silent card, and the ask was simplicity. Absence says it.

       The accordion opens BELOW the drawing, not above it: opening it above
       would push the picture down the page under the reader's cursor. */
    if (item.caption) {
      /* The wrapper is the accordion (a 0fr/1fr grid row) and the paragraph is
         what it collapses; one element cannot be both, because the track that
         animates has to sit outside the content whose height it is hiding. */
      var cw = document.createElement('div');
      cw.className = 'tcapWrap';
      var tc = document.createElement('p');
      tc.className = 'tcap';
      tc.textContent = item.caption;
      cw.appendChild(tc);
      art.appendChild(cw);

      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'tileCapBtn';
      btn.setAttribute('aria-pressed', 'false');
      btn.setAttribute('aria-expanded', 'false');
      btn.innerHTML = ICON_CAP;
      meta.appendChild(btn);
      var label = function (on) {
        btn.setAttribute('aria-label', on ? 'Hide the description'
                                          : 'Read the description');
        btn.title = btn.getAttribute('aria-label');
      };
      btn.addEventListener('click', function () {
        var on = art.classList.toggle('cap-open');
        btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        btn.setAttribute('aria-expanded', on ? 'true' : 'false');
        label(on);
      });
      label(false);
    }

    /* THE FOOTER IS THE FULL-SCREEN BAR AT CARD SIZE, from the same builder
       (lib/fullbar.js) with a different control list. A second transport
       written here would contradict the reason that module exists inside a day
       of it landing. */
    if (window.SkriblFullBar) {
      /* ATTACHED TO THE STAGE, NOT THE CARD, and that is the whole change.
         The bar used to sit BELOW the drawing as a permanent row -- which is
         the "full media-player toolbar at all times" the owner's auditor asked
         to be rid of, and which the owner then read as clutter across a grid
         of twenty-four cards.

         Overlaid on the artwork's bottom edge instead, it costs the card no
         height at all: the drawing grows by the row's worth, which is the same
         brief's "make the artwork area larger relative to the surrounding
         controls". And because the element is always in the DOM and only ever
         changes opacity, nothing reflows when it appears and a screen reader
         can reach every control at any moment -- a bar BUILT on first play
         cannot be announced before that play.

         SAME MODULE, SAME CONTROLS. What changed is when they are visible;
         building a second transport inside the byte-budgeted component would
         contradict the reason lib/fullbar.js exists. */
      foot = window.SkriblFullBar.attach(stage, {
        variant: 'skfull-card',
        controls: ['play', 'loop', 'mute', 'full'],
        who: false,
        scrubRow: false,
        player: function () {
          var b = stage.querySelector('.skribl-inline');
          return (b && b._skriblInline) || null;
        },
        onFull: function () { if (imm) imm.toggle(); },
        isFull: function () { return !!(imm && imm.isOn()); }
      });
      /* The component's own cluster and duration chip yield on the card for
         the same reason they do in full screen: the page took the transport
         over, and two of them on one drawing is the defect. */
      var box0 = stage.querySelector('.skribl-inline');
      if (box0) box0.classList.add('is-bare');
      foot.running(true);

      /* WHEN THE CONTROLS ARE THERE. At rest the card offers one thing to do,
         which is the honest count: at 0:00 there is nothing to scrub, nothing
         to mute (nothing is making a sound yet) and the loop has not come
         round. They are not withheld, they have nothing to act on.

         Hover and focus-within are CSS. Playing and the touch reveal are
         state, because a phone has no hover: a tap on the artwork that is not
         on a control summons them, and they recede after a quiet interval so
         the drawing gets the card back. Keyboard focus never starts that
         timer -- a bar that vanishes from under a tab key is a bar a keyboard
         cannot use. */
      var hideT = null;
      function peek(sticky) {
        art.classList.add('ctl-on');
        clearTimeout(hideT);
        if (sticky) return;
        hideT = setTimeout(function () {
          /* The stage for the same reason the listeners above use it: focus
             parked on the description toggle is not somebody using the bar. */
          if (stage.contains(document.activeElement)) return;
          art.classList.remove('ctl-on');
        }, 2600);
      }
      /* THE STAGE, NOT THE CARD, and that is the whole of the bug the owner
         found: "when I reclicked the bubble, it closed - but it left the
         controls still on screen".

         These two listeners were on the card. The description toggle and the
         overflow button live in the card's HEAD, and a button keeps focus
         after a click, so pressing either one raised `focusin` on the card,
         which summoned the transport and -- because that peek is the STICKY
         kind, the one a keyboard gets so a bar cannot vanish from under a tab
         key -- left it up with no timer to take it down again. Reading the
         description turned the transport on, and closing the description
         could not turn it off, because nothing about the description had
         anything to do with the transport.

         Scoped to the stage, focus means what it is supposed to mean here:
         somebody has tabbed into the transport itself. The head's buttons no
         longer say anything about the drawing. */
      stage.addEventListener('pointerdown', function (e) {
        if (e.target.closest('.skfull')) return;
        peek(false);
      });
      stage.addEventListener('focusin', function () { peek(true); });
      stage.addEventListener('focusout', function () {
        if (!stage.contains(document.activeElement)) peek(false);
      });
      if (box0 && box0._skriblInline) {
        /* The player does not emit events, so the card watches the state it
           already polls for the bar's own sync. Cheap: this is the same
           quarter-second tick the footer runs while stopped. */
        setInterval(function () {
          var st = box0._skriblInline.state();
          if (st.state === 'playing') peek(true);
          else if (art.classList.contains('ctl-on')) peek(false);
        }, 400);
      }
    }
    return art;
  }

  /* One page of the listing. `reset` starts from the top with a clean grid —
     a retry after a response that failed mid-way must not double every row —
     and otherwise the page is appended after the cursor the last one gave. */
  function load(reset) {
    /* A RESET IS THE PERSON'S LATEST INTENT AND IS NEVER DROPPED.
     *
     * This was `if (loading) return`, which discarded it: tapping Hot, or
     * typing, while the first listing was still in flight set `sort`/`query`
     * and then threw the reload away, and nothing re-issued it when the old
     * request settled. The grid then rendered the OLD answer under a bar
     * saying Hot, or under a search term it had never sent -- on a slow phone,
     * routinely (PRESEAL-001 of the pre-v305 audit).
     *
     * So only PAGING is guarded here, against a double tap on Load more. A
     * reset always goes, and the generation below makes the superseded
     * response harmless. */
    if (loading && !reset) return;
    var myGen = ++gen;
    loading = true;
    errEl.hidden = true;
    empty.hidden = true;
    more.disabled = true;
    if (reset) {
      cursor = null;
      while (list.firstChild) list.removeChild(list.firstChild);
    }
    var url = api + '?limit=' + PAGE + '&sort=' + sort
            + (query ? '&q=' + encodeURIComponent(query) : '')
            + (cursor ? '&cursor=' + encodeURIComponent(cursor) : '');
    if (noneEl) noneEl.hidden = true;
    return fetch(url, { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (body) {
        /* SUPERSEDED: a newer load has started, so this answer describes a
           sort or a search the person has already moved on from. Drop it
           without touching the grid, the cursor or the loading flag -- the
           newer request owns all three now. */
        if (myGen !== gen) return;
        var items = (body && body.items) || [];
        for (var i = 0; i < items.length; i++) list.appendChild(tile(items[i]));
        if (items.length) window.SkriblInline.mount(list);
        cursor = (body && body.next_cursor) || null;
        more.hidden = !cursor;
        /* Two empty states: nothing in the gallery at all, and nothing that
           matches what was typed. */
        empty.hidden = list.children.length > 0 || !!query;
        if (noneEl) noneEl.hidden = list.children.length > 0 || !query;
      })
      .catch(function () {
        if (myGen !== gen) return;
        errEl.hidden = false;
        more.hidden = true;
      })
      .then(function () {
        /* The stale arm must not clear the flag either: the live request is
           still running and would be left thinking nothing is in flight. */
        if (myGen !== gen) return;
        loading = false;
        more.disabled = false;
      });
  }

  /* ---- the report sheet ------------------------------------------------
     A report is a row in the operator's queue (POST /api/skribls/<id>/report),
     never an action on the post, and the sheet's words say so. One sheet for
     the page, opened per tile; lib/modalfocus.js owns focus. 429 and any
     other refusal are said in the sheet, which stays open for another try. */
  var sheet = document.getElementById('reportSheet');
  var form = document.getElementById('reportForm');
  var note = document.getElementById('reportNote');
  var status = document.getElementById('reportStatus');
  var send = document.getElementById('reportSend');
  var csrf = document.body.getAttribute('data-skribl-csrf');
  var reporting = null;       /* { id, button } while the sheet is open */

  function say(msg, bad) {
    status.textContent = msg || '';
    status.hidden = !msg;
    status.classList.toggle('error', !!bad);
  }

  /* ---- THE CARD MENU ------------------------------------------------------
     One element for the whole grid, built on first use and moved to whichever
     button asked for it.

     VIEWER ACTIONS ONLY, and that is a scope decision worth stating rather
     than hiding. The auditor asked for an owner variant -- Open, Edit, Copy
     link, Share, visibility, Delete -- and two of those cannot be honoured
     here. This page does not know who you are: `data-skribl-me` is emitted by
     the LIBRARY template and not this one, so the card cannot tell your Skribl
     from anybody else's. And there is no Edit: `PATCH /api/skribls/<id>`
     accepts exactly one field, visibility, because a posted Skribl's payload
     is immutable by design -- an "edit" would be a duplicate into a new draft,
     which is a product decision and not a menu item.

     Both owner actions already exist on /library, where the page does know
     whose profile it is. Wiring them here needs the gallery route to pass the
     signed-in id, which is a small change with a real authorisation question
     attached, so it is left for its own pass rather than smuggled into this
     one. */
  var menuEl = null, menuFor = null, menuOpener = null;

  function closeMenu(refocus) {
    if (!menuEl || menuEl.hidden) return;
    menuEl.hidden = true;
    if (menuOpener) {
      menuOpener.setAttribute('aria-expanded', 'false');
      if (refocus) menuOpener.focus();
    }
    menuFor = null; menuOpener = null;
  }

  /* The menu's own glyphs, in the stroked 24-box every other icon on this page
     is drawn in. Same four the editor's sheet uses for the same four ideas:
     an arrow leaving a frame for Open, two linked rings for a link, a node
     graph for Share, a flag for Report. `.cmItem svg` caps them at 18px --
     the mistake the caption mark made is one rule away at all times. */
  var MENU_ICON = {
    open: '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
        + '<polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>',
    link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/>'
        + '<path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    share: '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/>'
        + '<circle cx="18" cy="19" r="3"/><line x1="8.6" y1="10.5" x2="15.4" y2="6.5"/>'
        + '<line x1="8.6" y1="13.5" x2="15.4" y2="17.5"/>',
    flag: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V4s-1 1-4 1-5-2-8-2-4 1-4 1z"/>'
        + '<line x1="4" y1="22" x2="4" y2="15"/>'
  };
  function menuGlyph(name) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"'
      + ' stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"'
      + ' aria-hidden="true" focusable="false">' + MENU_ICON[name] + '</svg>';
  }

  /* THE GLYPH IS MARKUP AND THE LABEL IS NOT, which is the whole reason the
     words go in through `textContent` on a span of their own rather than into
     the same innerHTML as the icon. A title or a caption is somebody else's
     text; this menu's labels are ours today and the next item added here may
     not be. One habit, kept where it costs nothing. */
  function menuItem(label, onPick, hook, glyph) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'cmItem' + (hook ? ' ' + hook : '');
    b.setAttribute('role', 'menuitem');
    if (glyph) b.innerHTML = menuGlyph(glyph);
    var t = document.createElement('span');
    t.textContent = label;
    b.appendChild(t);
    b.addEventListener('click', function () { closeMenu(false); onPick(); });
    return b;
  }

  function buildMenu() {
    var m = document.createElement('div');
    m.className = 'cardMenu';
    m.setAttribute('role', 'menu');
    m.hidden = true;
    /* ARROW KEYS MOVE, ESCAPE LEAVES, and the focus goes back to the button
       that opened it -- a menu that dumps focus at the top of the document is
       a menu a keyboard cannot use twice. */
    m.addEventListener('keydown', function (e) {
      var items = [].slice.call(m.querySelectorAll('.cmItem'));
      var i = items.indexOf(document.activeElement);
      if (e.key === 'Escape') { e.preventDefault(); closeMenu(true); return; }
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        var n = e.key === 'ArrowDown' ? i + 1 : i - 1;
        if (n < 0) n = items.length - 1;
        if (n >= items.length) n = 0;
        if (items[n]) items[n].focus();
      }
    });
    document.body.appendChild(m);
    return m;
  }

  /* `sayOn`, NOT `say`. This file already had a module-level `say(msg, bad)`
     for the report sheet's status line, and a second `function say` in the same
     scope does not shadow it locally -- the later declaration hoists and wins
     for EVERY caller. So openReport's own `say('')` started calling this one
     with a button of '' and threw before it reached SkriblModal.open, and the
     only symptom was two a11y rows saying focus never entered the sheet.
     Nothing reported a redefinition; JavaScript does not consider it an error. */
  function sayOn(button, msg, rest) {
    button.title = msg;
    button.setAttribute('aria-label', msg);
    var live = document.getElementById('galleryStatus');
    if (live) live.textContent = msg;
    clearTimeout(button._t);
    button._t = setTimeout(function () {
      button.title = rest;
      button.setAttribute('aria-label', rest);
    }, 1600);
  }

  function openMenu(item, button) {
    if (menuFor === item.id && menuEl && !menuEl.hidden) { closeMenu(true); return; }
    if (!menuEl) menuEl = buildMenu();
    menuEl.innerHTML = '';
    /* Substituted, not assembled -- the same move the poster makes, so a host
       running the blueprint under a url_prefix gets a correct link without
       this file knowing the route. */
    var tpl = document.body.getAttribute('data-skribl-player') || '';
    var url = location.origin + tpl.replace('__ID__', encodeURIComponent(item.id));
    var rest = 'More';

    menuEl.appendChild(menuItem('Open', function () {
      window.open(url, '_blank', 'noopener');
    }, '', 'open'));
    /* ONE COPY IMPLEMENTATION, AND IT ANSWERS WHETHER THE TEXT ARRIVED.
       lib/postedui.js owns it; a handler that reports success from both arms
       of a promise is PRESEAL-002, and it shipped once already. */
    menuEl.appendChild(menuItem('Copy link', function () {
      var copier = window.SkriblPostedUI && window.SkriblPostedUI.copyText;
      if (!copier) { sayOn(button, "Couldn't copy the link", rest); return; }
      copier(url).then(function (ok) {
        sayOn(button, ok ? 'Link copied' : "Couldn't copy the link", rest);
      });
    }, '', 'link'));
    /* Share only where the platform has one. A "Share..." that silently does
       nothing is worse than an item that is not there. */
    if (navigator.share) {
      menuEl.appendChild(menuItem('Share\u2026', function () {
        navigator.share({ title: item.title || 'A Skribl', url: url })
          .catch(function () {});
      }, '', 'share'));
    }
    var hr = document.createElement('div');
    hr.className = 'cmDiv';
    menuEl.appendChild(hr);
    /* `cmReport` is a HOOK, not a style: verify_a11y's modal census drives the
       real path to the report sheet, and that path is now two clicks. A recipe
       that matched the word would break the day the word changes. */
    menuEl.appendChild(menuItem('Report', function () {
      openReport(item.id, button);
    }, 'cmReport danger', 'flag'));

    /* PLACED AGAINST THE VIEWPORT, not just below the button: a card in the
       last row would otherwise open a menu below the fold. */
    menuEl.hidden = false;
    var r = button.getBoundingClientRect();
    var mh = menuEl.offsetHeight, mw = menuEl.offsetWidth;
    var top = r.bottom + 6;
    if (top + mh > window.innerHeight - 8) top = Math.max(8, r.top - mh - 6);
    var left = Math.min(r.right - mw, window.innerWidth - mw - 8);
    menuEl.style.top = (top + window.scrollY) + 'px';
    menuEl.style.left = (Math.max(8, left) + window.scrollX) + 'px';

    menuFor = item.id; menuOpener = button;
    button.setAttribute('aria-expanded', 'true');
    var first = menuEl.querySelector('.cmItem');
    if (first) first.focus();
  }

  document.addEventListener('click', function (e) {
    if (menuEl && !menuEl.hidden && !menuEl.contains(e.target)) closeMenu(false);
  });
  window.addEventListener('resize', function () { closeMenu(false); });
  /* A menu pinned to a button that has scrolled away points at nothing. */
  window.addEventListener('scroll', function () { closeMenu(false); }, true);

  function openReport(id, button) {
    reporting = { id: id, button: button };
    form.reset();
    /* Already reported from this page: the sheet opens as the record of
       that, with nothing to send. The button stays focusable (it is where
       focus returns on close — a disabled button cannot take it). */
    var done = button.getAttribute('data-reported') === '1';
    say(done ? 'You already reported this one. Thanks.' : '');
    send.disabled = done;
    sheet.hidden = false;
    if (window.SkriblModal) window.SkriblModal.open(sheet, button);
  }

  function closeReport() {
    if (sheet.hidden) return;
    sheet.hidden = true;
    if (window.SkriblModal) window.SkriblModal.close(sheet);
    reporting = null;
  }

  document.getElementById('reportCancel').addEventListener('click', closeReport);
  sheet.addEventListener('click', function (e) { if (e.target === sheet) closeReport(); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !sheet.hidden) { e.preventDefault(); closeReport(); }
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!reporting || send.disabled) return;
    var reason = (form.querySelector('input[name=reason]:checked') || {}).value;
    if (!reason) { say('Pick a reason.', true); return; }
    var target = reporting;
    var headers = { 'Content-Type': 'application/json' };
    if (csrf) headers['X-Skribl-CSRF'] = csrf;
    send.disabled = true;
    say('Sending…');
    /* The route is the listing's URL plus the id, exactly as the poster URL
       is built from the macro's: no path assembled from a literal, so a
       url_prefix is honoured. */
    fetch(api + '/' + encodeURIComponent(target.id) + '/report', {
      method: 'POST', headers: headers, credentials: 'same-origin',
      body: JSON.stringify({ reason: reason, note: note.value.trim() })
    }).then(function (r) {
      if (r.status === 429) throw new Error('Too many reports from here right now. Try again later.');
      if (!r.ok) return r.json().catch(function () { return {}; })
        .then(function (j) { throw new Error(j.error || ('Could not send (HTTP ' + r.status + ').')); });
      return r.json();
    }).then(function () {
      /* SAID ON THE TILE: the button becomes the record that this reader
         reported this post, and cannot be pressed again this page-load. The
         server would answer a second one the same way and write nothing. */
      target.button.textContent = 'Reported';
      target.button.setAttribute('aria-pressed', 'true');
      target.button.setAttribute('data-reported', '1');
      say('Thanks. The people who run this site will look at it.');
      send.disabled = true;
    }).catch(function (err) {
      say(err.message || 'Could not send the report.', true);
      send.disabled = false;
    });
  });

  /* ---- New / Hot, and the search box --------------------------------- */
  var tabs = document.querySelectorAll('.tabs .tab[data-sort]');
  Array.prototype.forEach.call(tabs, function (tab) {
    tab.addEventListener('click', function () {
      var want = tab.getAttribute('data-sort') === 'hot' ? 'hot' : 'new';
      if (want === sort) return;
      sort = want;
      Array.prototype.forEach.call(tabs, function (t) {
        var on = t === tab;
        t.classList.toggle('active', on);
        t.setAttribute('aria-pressed', String(on));
      });
      if (subEl) subEl.textContent = sort === 'hot'
        ? 'Most played in the last seven days. Tap one to watch it draw itself.'
        : 'Skribls people chose to show. Tap one to watch it draw itself.';
      load(true);
    });
  });
  var find = document.getElementById('galleryFind');
  var qEl = document.getElementById('galleryQ');
  var qTimer = null;
  function search() {
    var words = (qEl.value || '').trim().slice(0, 80);
    if (words === query) return;
    query = words;
    load(true);
  }
  find.addEventListener('submit', function (e) { e.preventDefault(); clearTimeout(qTimer); search(); });
  qEl.addEventListener('input', function () { clearTimeout(qTimer); qTimer = setTimeout(search, 350); });

  document.getElementById('galleryRetry').addEventListener('click', function () { load(true); });
  more.addEventListener('click', function () { load(false); });
  load(true);
})();

/* THE BOOT FLAG, and it must stay last (harness/browsing.py waits on it). */
window.__skriblBoot = Object.assign(window.__skriblBoot || {}, { gallery: true });
