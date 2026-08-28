/* Page spans — a contiguous run of Flip pages, and the operations on it.
 *
 * WHY A RUN AND NOT A SET. Flip's strip is a film, and the thing a person
 * reaches for is "these four frames" — an interval, not an arbitrary multi-
 * select. A set would need per-tile checkboxes and would make every operation
 * answer awkward questions (paste four non-adjacent pages WHERE?). An interval
 * has one honest answer to all of them, needs no chrome to express, and reads
 * off the strip at a glance because it is literally a stretch of film.
 *
 * THE ARRAY IS THE FORMAT. `frames` is a plain array in the payload, so every
 * operation here is a splice. Nothing in this file adds a field, and the player
 * cannot tell a span operation happened — which is the whole reason this was
 * buildable without an owner decision on the schema, unlike layers or text.
 *
 * PURE ON PURPOSE. No DOM, no globals, no Flip state. Flip owns the anchor and
 * the focus; this owns what those two numbers MEAN. That split is what lets the
 * awkward cases — a span that straddles the insertion point, a move that lands
 * inside itself — be tested headless instead of by dragging thumbnails.
 */
(function () {
  'use strict';

  /* normalise(a, b, n) -> {from, to} inclusive, clamped, ordered.
   *
   * Anchor and focus arrive in whatever order the user dragged, and either can
   * be stale after a delete. Ordering and clamping HERE means no caller has to
   * remember to, which is the bug this shape prevents: `frames[from..to]` with
   * from > to silently yields nothing, so a span that looked selected would
   * operate on air.
   */
  function normalise(a, b, n) {
    if (!(n > 0)) return null;
    var lo = Math.min(a, b), hi = Math.max(a, b);
    lo = Math.max(0, Math.min(n - 1, lo));
    hi = Math.max(0, Math.min(n - 1, hi));
    return { from: lo, to: hi };
  }

  function count(s) { return s ? s.to - s.from + 1 : 0; }
  function contains(s, i) { return !!s && i >= s.from && i <= s.to; }

  /* label(s) -> "4" or "4–7". An en dash, because it is a range and not a
   * subtraction; the strip renders this where a single page shows its number. */
  function label(s) {
    if (!s) return '';
    return s.from === s.to ? String(s.from + 1)
                           : (s.from + 1) + '–' + (s.to + 1);
  }

  /* extract(frames, s) -> the pages themselves, not copies. The caller decides
   * whether it wants clones (a copy does; a move does not). */
  function extract(frames, s) {
    return s ? frames.slice(s.from, s.to + 1) : [];
  }

  /* remove(frames, s) -> a NEW array with the span gone. Non-mutating, because
   * every caller here needs the before-state for undo anyway, and a function
   * that both mutates and returns invites using it as if it did only one.
   */
  function remove(frames, s) {
    if (!s) return frames.slice();
    return frames.slice(0, s.from).concat(frames.slice(s.to + 1));
  }

  /* insert(frames, at, pages) -> a NEW array with `pages` spliced in BEFORE
   * index `at`. `at` is clamped to the array, so "paste at the end" is just
   * at = length rather than a special case the caller has to spell.
   */
  function insert(frames, at, pages) {
    var i = Math.max(0, Math.min(frames.length, at));
    return frames.slice(0, i).concat(pages, frames.slice(i));
  }

  /* moveSpan(frames, s, to) -> a NEW array with the span moved so it sits
   * BEFORE the page currently at index `to`. `to === frames.length` means the
   * end.
   *
   * `to` INDEXES THE ORIGINAL ARRAY, not the result. That is the convention the
   * strip already uses — drag-to-reorder derives its target by counting tile
   * centres left of the pointer, i.e. against the layout on screen right now,
   * and `movePageTo` carries a comment about the same thing for a single page.
   * Two conventions for "where does this go" in one file is how a reorder lands
   * one slot off, so this one matches what is already there.
   *
   * The consequence, and it is the case that is always wrong first time: a span
   * moving RIGHTWARDS lands short by its own length unless the target is
   * adjusted, because the span is spliced out before it is spliced back and
   * every original index after it shifts down by `count`. Hence the subtraction
   * — and note it applies only when the target is past the span's END, which is
   * why the comparison is against `s.to` and not `s.from`.
   *
   * (This paragraph originally described the OPPOSITE convention while the code
   * did the right thing. It was caught by a hand-check whose expectation was
   * written from the prose — which is the same failure mode as the stale
   * docstrings v225 spent a release fixing, in the same week, by me.)
   *
   * A target inside the span itself is a no-op, not an error: it is what
   * dropping a span onto its own middle means, and the user sees nothing move.
   */
  function moveSpan(frames, s, to) {
    if (!s) return frames.slice();
    if (to >= s.from && to <= s.to + 1) return frames.slice();
    var pages = frames.slice(s.from, s.to + 1);
    var rest = remove(frames, s);
    var at = to > s.to ? to - count(s) : to;
    return insert(rest, at, pages);
  }

  /* after(s, n) -> where the span sits once it has been moved or pasted, so the
   * caller can keep it selected. Selection surviving its own operation is the
   * difference between a tool and a series of separate commands. */
  function at(from, n) { return { from: from, to: from + n - 1 }; }

  var api = {
    normalise: normalise, count: count, contains: contains, label: label,
    extract: extract, remove: remove, insert: insert, moveSpan: moveSpan,
    at: at
  };
  if (typeof window !== 'undefined') window.SkriblPageSpan = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
