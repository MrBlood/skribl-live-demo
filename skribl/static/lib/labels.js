/* WORDS IN A BUTTON SIT IN THE MIDDLE BY THEIR CAPITALS, in any font.
 *
 * The owner, from the phone: "Make your first Skribl doesn't look centered
 * vertically in the button", then: "if this happened here, it happened all
 * over?" It had. A flex-centred button centres its label's LINE BOX, and where
 * the capitals sit inside that box depends on the font's ascent and descent:
 * harness/check_centring.py found word labels 1-2.5px high across Pad, Flip,
 * the Library and the Gallery. Trimmed to cap height and baseline (text-box,
 * as the recording clock is), the box IS the capitals, and centring it centres
 * them -- in Segoe UI and SF as in the faces this box has.
 *
 * Trim applies to a text box, not to a flex container, so each label needs its
 * own element. This gives it one: a word written straight into a control is
 * moved into <span class="lbl"> (the same text node, so code holding it still
 * updates it), and a label set later (textContent = ...) is wrapped as it
 * lands. The rule is labels.css .lbl, and it works in a flex control (the
 * span is the item) and a block one (the span is the line, top-aligned);
 * where text-box is unsupported, nothing changes. A label that already has
 * its own span is marked .lbl-own instead (trimmed, its display untouched).
 * Left alone: a control with more than one piece of text, a tile with its
 * mark above its word, and a control already trimmed by its own rule.
 */
(function (global) {
  'use strict';
  var doc = global.document;
  var SEL = 'button, a.make, [role="button"], [role="tab"]';

  var cs = function (el) { return global.getComputedStyle(el); };
  // A label already in its own span: words only (a nested span for a longer
  // wording is fine), no mark inside it, and not already trimmed.
  // (A span taken out of the flow -- read to a screen reader only, or a badge
  // pinned to a corner -- is not the label.)
  function wordsOnly(el) {
    return el.tagName === 'SPAN' && !el.querySelector('svg, img') && /\S/.test(el.textContent)
      && !/absolute|fixed/.test(cs(el).position);
  }

  function wrap(el) {
    if (!el || el.nodeType !== 1 || !el.matches(SEL)) return;
    var texts = [], words = [];
    for (var n = el.firstChild; n; n = n.nextSibling) {
      if (n.nodeType === 3 && /\S/.test(n.nodeValue)) texts.push(n);
      else if (n.nodeType === 1 && !/^(svg|img)$/i.test(n.tagName) && /\S/.test(n.textContent)) words.push(n);
    }
    // ONE label, or leave it: words mixed with inline elements (a sentence
    // with a bold word in it) would stop breaking where they should.
    if (texts.length + words.length !== 1) return;
    // A tile with its mark ABOVE its word is not a centred line, and a control
    // already trimmed by its own rule (Flip's hold badge) is done.
    var st = cs(el);
    if (/flex/.test(st.display) && /column/.test(st.flexDirection)) return;
    if (st.textBoxTrim === 'trim-both') return;
    if (texts.length) {
      var s = doc.createElement('span');
      s.className = 'lbl';
      el.insertBefore(s, texts[0]);
      s.appendChild(texts[0]);   // the same node: code holding it still updates it
    } else if (wordsOnly(words[0]) && !words[0].classList.contains('lbl-own')
               && cs(words[0]).textBoxTrim !== 'trim-both') {
      words[0].classList.add('lbl-own');   // trimmed, its own display kept (its own rule may hide it)
    }
  }
  function all(root) {
    if (root.nodeType !== 1) return;
    if (root.matches(SEL)) wrap(root);
    root.querySelectorAll(SEL).forEach(wrap);
  }
  function start() {
    all(doc.body);
    new MutationObserver(function (list) {
      for (var i = 0; i < list.length; i++) {
        var m = list[i], t = m.target;
        if (t.nodeType === 1 && t.matches(SEL)) wrap(t);
        for (var j = 0; j < m.addedNodes.length; j++) all(m.addedNodes[j]);
      }
    }).observe(doc.body, { childList: true, subtree: true });
  }
  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', start); else start();
  global.SkriblLabels = { wrap: wrap };
})(window);
