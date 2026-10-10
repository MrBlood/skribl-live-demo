/* The app's marks for controls a script builds: plus, minus, close, check,
 * arrow, cloned from the <template id="skriblMark-NAME"> that
 * _skribl_marks.html puts on the page, so a script and a template draw the
 * same mark from one source.
 *
 *   SkriblMarks.get(name)        a fresh <svg>, or null when the page has none
 *   SkriblMarks.html(name, typed)  the mark as markup, for a row built as a string
 *   SkriblMarks.into(el, name, typed)
 *                                el's face becomes the mark; `typed` is the
 *                                character it used to be, kept only where the
 *                                page carries no marks
 */
(function (global) {
  'use strict';
  function get(name) {
    var t = global.document.getElementById('skriblMark-' + name);
    return t && t.content && t.content.firstElementChild ? t.content.firstElementChild.cloneNode(true) : null;
  }
  function into(el, name, typed) {
    var m = get(name);
    el.textContent = m ? '' : (typed || '');
    if (m) el.appendChild(m);
    return el;
  }
  function html(name, typed) {
    var m = get(name);
    return m ? m.outerHTML : (typed || '');
  }
  global.SkriblMarks = { get: get, into: into, html: html };
})(window);
