/* A post's full screen: the button at the end of a post's line opens the link page's full screen around the post's own player.
 *
 * The owner, Nov 16: "yes to A and all your picks", to the mock of full
 * screen on the site's posts. A post played in the in-post player had no full
 * screen and no Restart, where its link page has both, and every link on the
 * site opens the post. So the full-screen button sits at the end of the
 * post's line, after Repeat, and opens the link page's own full screen:
 * lib/fullbar.js band(), the one Skribl's Gallery and the Library wear. Its
 * band (the scrubber in the drawing's shape and the words with every speed,
 * lent by the post's line; Restart, Play, Loop, Mute and Leave), the x, and
 * who drew it in the corner (the host's words for it, `data-skribl-full`).
 *
 * ONE PLAYER, ONE CLOCK. The drawing carries on from where it was, playing
 * or paused (one never loaded is played, the one call that loads and
 * shows), and leaving puts the post back as it was: the line given back
 * (inlineplayer.js unband), the button given the focus back.
 *
 * A HOST OPTS IN: skribl_inline(full=...) draws the button
 * (_skribl_inline_player.html), and skribl_full_assets() loads this with
 * the sheets and modules it needs. The button shows only once this has run
 * (html.skribl-postfull, postfull.css), so a page without it shows none.
 *
 * THE STAGE. The post's box is put, once, into a block of its own, which is
 * what goes full screen (lib/immersive.js: the real API, or on an iPhone the
 * stand-in pinned over the page), as the Gallery's tile does; the line stays
 * where it is, under the stage, and the player found it when it mounted.
 */
(function (global) {
  'use strict';

  var doc = global.document;
  if (!doc || !global.SkriblFullBar || !global.SkriblImmersive) return;
  doc.documentElement.classList.add('skribl-postfull');

  function stageOf(box) {
    var st = box.parentNode;
    if (st && st.classList && st.classList.contains('skribl-post-stage')) return st;
    st = doc.createElement('div');
    st.className = 'skribl-post-stage';
    box.parentNode.insertBefore(st, box);
    st.appendChild(box);
    return st;
  }

  /* The box the button's line belongs to: the line's own sibling before
     it, or inside it once the box has its stage. */
  function boxOf(btn) {
    var line = btn.closest('.skribl-inline-line'), p = line && line.previousElementSibling;
    if (!p) return null;
    return p.matches('[data-skribl-inline]') ? p : p.querySelector('[data-skribl-inline]');
  }

  function meta(box) {
    try { return JSON.parse(box.getAttribute('data-skribl-full') || 'null') || {}; } catch (e) { return {}; }
  }

  function make(st, box, pl) {
    var big = false, m = meta(box), it = {};
    /* The band sees the player only while full screen is up, so it borrows
       the post's line then, and lets it go when it ends. */
    it.bar = global.SkriblFullBar.attach(st, {
      player: function () { return big ? pl : null; },
      meta: function () { return m; },
      onExit: function () { it.imm.close(); }
    });
    it.imm = global.SkriblImmersive.attach(st, { onChange: function (on) {
      big = !!on;
      box.classList.toggle('is-immersive', big);
      box.classList.toggle('is-bare', big);
      if (big) {
        if (!pl.state().loaded) pl.play();
        it.bar.running(true);
        return;
      }
      it.bar.running(false);
      it.bar.sync();
      if (pl.unband) pl.unband();
      if (it.from && it.from.isConnected) {
        try { it.from.focus({ preventScroll: true }); } catch (e) {}
      }
    } });
    return it;
  }

  function open(btn) {
    var box = boxOf(btn), pl = box && box._skriblInline;
    if (!pl) return;
    var st = stageOf(box);
    if (!st._skFull) st._skFull = make(st, box, pl);
    st._skFull.from = btn;
    if (!st._skFull.imm.isOn()) st._skFull.imm.toggle();
  }

  /* CAPTURING: the line keeps its clicks from the host's page
     (inlineplayer.js stops them as they bubble, so a post that is a link
     does not open), and this must hear the press before that. */
  doc.addEventListener('click', function (e) {
    var b = e.target && e.target.closest && e.target.closest('.skribl-inline-full');
    if (!b) return;
    e.preventDefault();
    open(b);
  }, true);
})(window);
