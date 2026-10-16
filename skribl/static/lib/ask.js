/* Ask: How it works as one question in your own words (owner, after v323:
 * the Ask mock, "All yes"; piece two of the help in four layers, FUTURE.md
 * 6p). One module for the Pad and Flip.
 *
 * THE FIELD DECIDES THE PAGE. Empty, How it works shows Ask's home: the
 * one-minute tour, what people often ask, the examples to watch and Name
 * every button (lib/helplearn.js's view, which used to be the Watch tab).
 * Typed into, it shows the answers: the best how-to answer first, then every
 * entry that matches (lib/helpsearch.js, which knows the everyday cousins of
 * the words: "repeat" finds the loop entries).
 *
 * AN ANSWER is a job people ask about, in a few steps in the app's own words,
 * with its example and SHOW ME: How it works steps aside and the real button
 * lights up with its card (lib/learncard.js), one step at a time; tapping the
 * lit button goes on to the next, and Back to Ask comes back to the answer.
 *
 * No answer is invented for a button that is not on the page: each answer
 * names the editor it is for, and Show me skips a step whose button is not
 * there to light (it is then said in words, with no arrow).
 */
(function () {
  'use strict';
  var drawer = document.getElementById('helpDrawer');
  var input = document.getElementById('helpSearch');
  var best = document.getElementById('askBest');
  var often = document.getElementById('askOften');
  var answerEl = document.getElementById('askAnswer');
  if (!drawer || !input || !answerEl) return;
  var isFlip = !!document.getElementById('strip');
  var MENU = isFlip ? '#moreBtn' : '#menuBtn';

  // id, editor ('pad', 'flip' or both), title, the line under it, the words
  // it answers, its example (demo: a real Skribl; clip: a phone recording),
  // its steps (the words, and the button each lights), related answers.
  var ANSWERS = [
    { id: 'music', title: 'Add a song that loops', sub: 'Music under your drawing', clip: 'music',
      words: ['loop', 'song', 'music', 'sound', 'repeat', 'audio'],
      steps: [['Tap <b>Photo and music</b>, then <b>Music</b>.', '#mediaOpenBtn', 'Photo and music'],
              ['Pick a song.', '#mediaTabMusic', 'Music'],
              ['Drag the two handles to choose the part that repeats, then <b>Preview Loop</b> to hear it.']],
      related: ['export', 'post'] },
    { id: 'speed', ed: 'pad', title: 'Replay it faster or slower', sub: 'From a quarter speed to sixteen times', clip: 'speed',
      words: ['speed', 'fast', 'slow', 'time-lapse', 'timelapse', 'watch', 'replay'],
      steps: [['Tap <b>Play</b>.', '#playBtn', 'Play'],
              ['Tap the speed under the replay.', '.rl-speed', 'Speed'],
              ['Pick from ¼× to 16×, or <b>Fit</b> to watch it all in about 30 seconds.']],
      related: ['takes', 'post'] },
    { id: 'fps', ed: 'flip', title: 'Make it play faster or slower', sub: 'Pages per second',
      words: ['speed', 'fast', 'slow', 'fps', 'pages per second'],
      steps: [['Tap <b>Tune</b>.', '#tuneBtn', 'Tune'],
              ['Pick how many pages play each second.', '#fps', 'Pages per second']],
      related: ['move', 'floop'] },
    { id: 'takes', ed: 'pad', title: 'Draw more over a replay', sub: 'Add a take', clip: 'takes',
      words: ['take', 'record', 'again', 'more', 'add'],
      steps: [['Play your drawing, or stop where you want.', '#playBtn', 'Play'],
              ['Tap <b>Add take</b>.', '#addTakePill', 'Add take'],
              ['Draw. The replay plays every take in order.']],
      related: ['speed', 'post'] },
    { id: 'post', title: 'Share it as a link', sub: 'Post', clip: 'post',
      words: ['share', 'link', 'post', 'publish', 'send'],
      steps: [['Tap <b>Post</b>.', '#postBtn', 'Post'],
              ['Give it a title, and a caption if you like.'],
              ['Post it, then copy the link.']],
      related: ['export'] },
    { id: 'export', title: 'Save it as a video or GIF', sub: 'Export', clip: 'export',
      words: ['export', 'video', 'gif', 'mp4', 'download', 'png', 'picture'],
      steps: [['Open the <b>⋯</b> menu.', MENU, 'Menu'],
              ['Tap <b>Export</b>.', isFlip ? '#miExport' : '#exportItem', 'Export'],
              ['Pick a picture, a video with its music, or a looping GIF.']],
      related: ['post', 'music'] },
    { id: 'photo', title: 'Put a photo under my drawing', sub: 'Background image', clip: 'photo',
      words: ['photo', 'picture', 'image', 'background', 'trace'],
      steps: [['Tap <b>Photo and music</b>, then <b>Photo</b>.', '#mediaOpenBtn', 'Photo and music'],
              ['Pick a picture.', '#mediaTabPhoto', 'Photo'],
              ['Fill, fit or move it, then draw on top.']],
      related: ['music'] },
    { id: 'undo', title: 'Undo a mistake', sub: 'And Redo', words: ['undo', 'redo', 'mistake', 'oops', 'back'],
      steps: [['Tap <b>Undo</b> to take back the last stroke.', isFlip ? '#undo' : '#undoBtn', 'Undo'],
              ['Tap <b>Redo</b> to put it back.', isFlip ? '#redo' : '#redoBtn', 'Redo']],
      related: ['new'] },
    { id: 'pen', title: 'Change colour and size', sub: 'Pen', demo: 'pen',
      words: ['colour', 'color', 'size', 'thick', 'thin', 'brush', 'pen'],
      steps: [['Tap <b>Pen</b> again to open colour and brush.', '#penToolBtn', 'Pen'],
              ['Drag sideways on Pen to change the size.']],
      related: ['undo'] },
    { id: 'new', title: 'Start a new drawing', sub: 'New', words: ['new', 'start', 'blank', 'fresh', 'clear'],
      steps: [['Open the <b>⋯</b> menu.', MENU, 'Menu'],
              ['Tap <b>New</b>, pick a shape, then <b>Start a new Skribl</b>. Undo brings the old one back.', '#menuNewTile', 'New']],
      related: ['drafts'] },
    { id: 'drafts', title: 'Save it and come back later', sub: 'Your drafts', words: ['save', 'draft', 'keep', 'later', 'open'],
      steps: [['Open the <b>⋯</b> menu.', MENU, 'Menu'],
              ['Tap <b>Save</b>. It stays on this browser.', '#saveCloudDraftItem', 'Save'],
              ['Find it again in <b>Your drafts</b>.']],
      related: ['new', 'export'] },
    { id: 'move', ed: 'flip', title: 'Make it move', sub: 'Pages', demo: 'flip-wave',
      words: ['move', 'animate', 'animation', 'page', 'frame', 'flipbook'],
      steps: [['Draw on the first page.'],
              ['Tap <b>Duplicate</b> for a copy.', '#addcopy', 'Duplicate'],
              ['Nudge the drawing a little and redraw it. Tap <b>Play</b> to watch it move.', '#play', 'Play']],
      related: ['floop', 'fps'] },
    { id: 'floop', ed: 'flip', title: 'Make a Flip that loops', sub: 'Plays round and round',
      words: ['loop', 'repeat', 'gif', 'forever'],
      steps: [['Tap <b>Play</b>: Flip plays your pages round and round.', '#play', 'Play'],
              ['To share the loop, export a GIF from the <b>⋯</b> menu.', MENU, 'Menu']],
      related: ['move', 'export'] }
  ];
  var mine = ANSWERS.filter(function (a) { return !a.ed || a.ed === (isFlip ? 'flip' : 'pad'); });
  var byId = {}; mine.forEach(function (a) { byId[a.id] = a; });
  var OFTEN = isFlip ? ['move', 'floop', 'music', 'post'] : ['music', 'speed', 'takes', 'post'];

  var CHEV = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>';
  function esc(t) { var d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
  function rowHtml(a) {
    return '<button type="button" class="ask-row" role="listitem" data-answer="' + a.id + '"><span class="ask-row-t">' + esc(a.title)
      + '<span class="ask-row-sub">' + esc(a.sub) + '</span></span>' + CHEV + '</button>';
  }
  if (often) often.innerHTML = OFTEN.map(function (id) { return byId[id]; }).filter(Boolean).map(rowHtml).join('');

  // ---- matching ------------------------------------------------------------
  function score(a, q) {
    var words = (window.SkriblHelpSearch && window.SkriblHelpSearch.cousins) ? window.SkriblHelpSearch.cousins(q) : [q];
    var s = 0;
    words.forEach(function (w) {
      if (a.words.some(function (k) { return k === w || (w.length >= 3 && k.indexOf(w) === 0); })) s += w === q ? 3 : 1;
    });
    if (a.title.toLowerCase().indexOf(q) >= 0) s += 2;
    return s;
  }
  function bestFor(q) {
    var top = null, topS = 0;
    mine.forEach(function (a) { var s = score(a, q); if (s > topS) { top = a; topS = s; } });
    return top;
  }

  var helpLearn = function () { return window.SkriblHelpLearn; };
  var lastView = 'home';
  function onInput() {
    var q = input.value.trim().toLowerCase();
    var hl = helpLearn();
    var look = document.getElementById('helpLook');
    if (look) look.classList.toggle('ask-searching', !!q);
    if (!q) { if (best) best.hidden = true; if (hl) hl.show('home'); lastView = 'home'; return; }
    var a = bestFor(q);
    if (best) {
      best.hidden = !a;
      if (a) best.innerHTML = '<p class="ask-k">Best match</p><div class="ask-best-card"><p class="ask-best-t">' + esc(a.title)
        + '</p><p class="ask-best-sub">' + esc(a.sub) + '</p><div class="ask-best-do">'
        + '<button type="button" class="ask-go" data-show="' + a.id + '">Show me</button>'
        + '<button type="button" class="ask-go quiet" data-answer="' + a.id + '">How</button></div></div>'
        + '<p class="ask-k">Also</p>';
    }
    if (hl && hl.view() !== 'look') hl.show('look');
    lastView = 'look';
  }
  input.addEventListener('input', onInput);

  // ---- an answer -------------------------------------------------------------
  var shown = null, example = null;
  function openAnswer(id) {
    var a = byId[id];
    if (!a) return;
    shown = a;
    if (example) { example.stop(); example = null; }
    var related = (a.related || []).map(function (r) { return byId[r]; }).filter(Boolean);
    answerEl.innerHTML = '<button type="button" class="ask-back" id="askBack"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6"/></svg>Ask</button>'
      + '<h2 class="ask-answer-t" id="askAnswerT" tabindex="-1"></h2><div class="ask-answer-pic"></div>'
      + '<ol class="ask-steps">' + a.steps.map(function (s) { return '<li><span>' + s[0] + '</span></li>'; }).join('') + '</ol>'
      + '<button type="button" class="ask-go ask-show" data-show="' + a.id + '">Show me</button>'
      + (related.length ? '<h3 class="ask-k">Related</h3><div class="ask-list" role="list">' + related.map(rowHtml).join('') + '</div>' : '');
    answerEl.querySelector('.ask-answer-t').textContent = a.title;
    var pic = answerEl.querySelector('.ask-answer-pic');
    var lc = window.SkriblLearnCard;
    example = (lc && lc.picture) ? lc.picture({ demo: a.demo, clip: a.clip }, pic) : null;
    if (!example) pic.remove();
    var hl = helpLearn();
    if (hl) hl.show('answer');
    answerEl.querySelector('.ask-answer-t').focus({ preventScroll: true });
  }
  // Back to Ask's home from the answers: the field emptied, focus in it.
  function home() {
    if (input.value) { input.value = ''; input.dispatchEvent(new Event('input', { bubbles: true })); }
    var hl = helpLearn();
    if (hl) hl.show('home');
    input.focus({ preventScroll: true });
  }
  function back() {
    if (example) { example.stop(); example = null; }
    var hl = helpLearn();
    if (hl) hl.show(input.value.trim() ? 'look' : 'home');
    input.focus({ preventScroll: true });
  }
  function showMe(id) {
    var a = byId[id];
    var lc = window.SkriblLearnCard;
    if (!a || !lc || !lc.steps) return;
    if (example) { example.stop(); example = null; }
    if (typeof window.closeHelpDrawer === 'function') window.closeHelpDrawer();
    setTimeout(function () {
      lc.steps(a.steps.map(function (s) { return { html: s[0], sel: s[1] || null, name: s[2] || a.title }; }), {
        title: a.title,
        back: function () { if (typeof window.openHelpDrawer === 'function') window.openHelpDrawer(); setTimeout(function () { openAnswer(a.id); }, 80); }
      });
    }, 420);
  }

  drawer.addEventListener('click', function (e) {
    var t = e.target.closest('[data-answer], [data-show], #askBack, #askLookBack, #askTour, #askBrowse');
    if (!t || !drawer.contains(t)) return;
    if (t.id === 'askBack') { back(); return; }
    if (t.id === 'askLookBack') { home(); return; }
    if (t.id === 'askTour') { var hl = helpLearn(); if (hl) hl.watch(t.getAttribute('data-tour')); return; }
    if (t.id === 'askBrowse') { input.value = ''; input.dispatchEvent(new Event('input', { bubbles: true })); var h = helpLearn(); if (h) h.show('look'); return; }
    if (t.hasAttribute('data-show')) { showMe(t.getAttribute('data-show')); return; }
    openAnswer(t.getAttribute('data-answer'));
  });
  // Escape on an answer or the answers goes back a step, not out of How it works.
  var lookEl = document.getElementById('helpLook');
  drawer.addEventListener('keydown', function (e) {
    var v = document.getElementById('learnViewer');
    if (e.key !== 'Escape' || (v && !v.hidden)) return;      // the viewer closes first
    if (!answerEl.hidden) { e.stopPropagation(); e.preventDefault(); back(); }
    else if (lookEl && !lookEl.hidden) { e.stopPropagation(); e.preventDefault(); home(); }
  }, true);

  // Every opening starts at Ask's home with an empty field.
  new MutationObserver(function () {
    if (drawer.hidden) { if (example) { example.stop(); example = null; } return; }
    if (input.value) { input.value = ''; input.dispatchEvent(new Event('input', { bubbles: true })); }
  }).observe(drawer, { attributes: true, attributeFilter: ['hidden'] });

}());
