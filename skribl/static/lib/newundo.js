/* NEW SKRIBL, AND THE WAY BACK: one offer for both editors.
 *
 * The owner's yes (Q4): "Flip shows the same chip, from the same code." After
 * New Skribl the Pad said "New Skribl" with an Undo beside it, and Undo said
 * "Restored" with a Redo; Flip said nothing, and its way back was Undo clear,
 * inside the pages drawer, where nobody who had just left the menu would look.
 * Both say the same now, through this.
 *
 *   offer({ say, undo, redo })
 *     say(msg, action)   the editor's own toast (the Pad's showToast, Flip's
 *                        chip); action, when given, is { label, onClick }
 *     undo()             bring the last drawing back; false when it could not
 *     redo()             start over again, which offers again itself
 *
 * Kind: nothing is lost by New. The words and the order are the Pad's, which
 * the owner has used since New Skribl had an Undo.
 */
(function (global) {
  'use strict';

  function offer(o) {
    o.say('New Skribl', { label: 'Undo', onClick: function () {
      var ok;
      try { ok = o.undo() !== false; } catch (e) { ok = false; }
      if (!ok) { o.say('Couldn’t restore that'); return; }
      o.say('Restored', { label: 'Redo', onClick: o.redo });
    } });
  }

  global.SkriblNewUndo = { offer: offer };
})(window);
