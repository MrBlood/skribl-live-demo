# Blooby + Skribl: A Deeper Improvement Plan

**Product strategy and technical recommendations · November 2026**  
**Context:** Based on the uploaded v330 project and the current Another App editor.

> **Repository note (November 24, 2026):** This is a portable, text-first copy of the prior in-chat review, with the competing application's name replaced by **Another App**. Inline interactive illustrations are represented as descriptions or text diagrams. **The original Fill-in-Pad recommendation is superseded by the companion file `PAD_FILL_ARCHITECTURE_CLARIFICATION.md`**, following the product owner's clarification that stroke-by-stroke self-drawing is fundamental to Skribl Pad. Do not interpret the recommendation to add conventional flood fill to Pad as an accepted requirement.

After going back into the actual source code, I would change the priorities from our first comparison.

**I think Blooby has the potential to be more engaging than a traditional drawing website, but it needs to become dramatically easier to create, finish, share, and respond to drawings.**

There are three parts to the product:

- **Skribl Pad:** The place people create drawings that replay themselves.
- **Skribl Flip:** The place people make animations.
- **Blooby:** The social platform that connects the drawings, artists, and conversations.

These three pieces should reinforce each other, but they shouldn't become one complicated interface.

My recommendation is to concentrate on **reliable everyday drawing, replay-based social interaction, and making people want to return** before attempting to match every advanced feature in Another App.

## 1. First priority: Fix the experience people already have

The most important discovery from your project's November 23 handoff is that there are already specific, observed usability issues worth fixing before adding major features.

Your handoff records two iPhone text-tool problems: text jumping or moving unexpectedly while typing inside Blooby's embedded Pad, and text that doesn't drag properly with a finger. It also describes a desktop help carousel that cannot be scrolled using a mouse.

These are more urgent than adding another brush.

**What I would change:**

1. When a user places text on the canvas, it should stay there until they deliberately drag it. Clicking elsewhere should not unexpectedly relocate it.
2. Typing inside the embedded Pad should not move the drawing area or hide the text controls.
3. Every horizontally scrolling help carousel should have visible desktop navigation.
4. Any fix to shared text behavior must be tested in both Pad and Flip, on standalone pages and inside Blooby.

I would make these the first release because the goal is simple: **a first-time artist should never have to fight the editor to make something.**

## 2. Build the right drawing tools—not the most drawing tools

Another App has a clear advantage in editable layers, fill, blend brushes, and selection modes. Its current editor also has configurable fill tolerance, feathering, and layer controls.

I would concentrate on four improvements.

### A. Add two real editable layers to Skribl Pad

**Highest-value major editor feature.**

Start with just two layers:

- **Clean ink:** The finished strokes, with visibility and lock controls.
- **Rough sketch:** The construction lines, with visibility, opacity, and lock controls.

An artist sketches on Rough, reduces its opacity, and draws the final lines on Clean. Each layer can be hidden, reordered, and locked. A Merge action can come later.

There's an architectural issue to solve first: your current recording format primarily stores timed points and stroke groups. A genuine layer must survive saving, undoing, exporting, publishing, and playback.

I would introduce a versioned layer identifier for each stroke group and update both playback engines together. Existing drawings without layer identifiers should still play exactly as before.

**The success test:** Draw Blooby on Rough, ink him on Clean, hide Rough, publish, and watch him redraw correctly. Save and reopen the editable version, and both layers must remain available.

### B. Add a Fill Bucket to Pad — ORIGINAL SUGGESTION, NOW SUPERSEDED

**Original priority assessment: High · Complexity: Medium–high.**

The existing Fill tool in Flip is the starting point. Artists should not have to move into an animation workflow just to color a basic shape.

I originally proposed a Fill tool with:

- One-tap fill of a closed area.
- An adjustable tolerance setting tucked into the tool's options.
- An option to fill behind black outlines.
- Undo that reverses a single fill.
- Correct behavior on transparent backgrounds.

**The unusual requirement:** A fill must be part of the recorded drawing, not simply painted into a bitmap that the replay cannot reconstruct.

I proposed defining a replayable fill operation and validating what happens if the outline is moved, recolored, or deleted later. A raster snapshot might be useful as a rendering cache, but it shouldn't be the only editable representation.

**Important correction:** The product owner clarified that Pad intentionally omits instant fill because its identity is the visible process of a drawing drawing itself, whereas Flip is animation-oriented and already has Fill. **Do not implement conventional flood fill in Pad based on the paragraph above.** See `PAD_FILL_ARCHITECTURE_CLARIFICATION.md` for a revised recommendation that protects this product distinction.

### C. Improve selection rather than replace it

One correction to my earlier comparison: **Pad already has rectangular, stroke-group-based selection** in `skribl/static/editor_draw.js`, not just Flip. That gives us a better starting point than I initially credited.

I would add a freehand lasso using your existing `SkriblSelect` infrastructure. Start by selecting complete stroke groups.

That approach preserves the integrity of lines when replaying. Cutting individual points out of a stroke risks introducing unnatural connections and strange playback behavior.

The first release should support drawing a freehand selection, moving the selected strokes, duplicating them, undoing the operation, and reopening the edited drawing.

I would defer feathered, pixel-accurate selection until you decide how raster edits should coexist with timed strokes.

### D. Make the default toolset much smaller than the available toolset

The original example of everyday actions was **Draw · Erase · Fill · Select · Undo · Color**. Following the owner's clarification, **omit Fill from Pad's proposed default shelf**, leaving **Draw · Erase · Select · Undo · Color** unless a replay-native coloring approach is explicitly designed and approved.

More advanced brushes, liquify, mirror, shaping, and specialized controls should remain available, but shouldn't compete for attention when someone is simply trying to draw.

I wouldn't remove the current features. I'd use contextual controls and a customizable tool shelf so experienced artists can get to what they need.

## 3. Turn Draw back into Blooby's signature social feature

**Priority: Very high · Potential product differentiation: Very high.**

This is where I would make the largest investment in Blooby itself.

Another App makes a remix part of an artwork's family tree. Artists can follow branches and see how a drawing evolves.

Your Draw back feature already does something compelling: it replays the original artist's strokes, followed by the responding artist's strokes. The existing `social/drawback.py` even compresses a long original into an introduction of roughly three seconds before the new contribution.

That is a strong foundation. I would expand it in three specific ways.

### A. Make each person's contribution independently watchable

Today, Draw back's server joins the original and response into one timed drawing.

Instead, I'd work toward a replay with identifiable contributions. In the original interface concept, a **Drawn together** player shows a finished illustration plus separate bands labeled **Original artist — body, face, outline** and **Second artist — waving hand, doodles**.

A viewer could:

- **Play all** (the default, to keep things effortless).
- **Play original only**.
- **Play added strokes only**.

A viewer could watch the whole collaboration, replay just one person's addition, or see the result without waiting for the original again.

### B. Solve Draw back's data ownership before extending it

Your November 23 handoff already raises an important question: should a Draw back be stored as a combined copy, or as separate contributions linked to the original?

I would favor the second approach for future drawings, while keeping existing combined posts compatible.

Each contribution would have its own strokes and a reference to its parent. The viewer would see them composited together.

Benefits:

- Recoloring the answerer's strokes would no longer require modifying the original.
- The viewer could show or hide particular contributions.
- A conversation could extend across multiple artists without repeatedly copying every preceding stroke.
- Drawing ancestry would be much easier to represent.

**An essential decision comes first:** What happens if the original artist deletes or restricts their drawing? A referenced system can honor removal more naturally, but it also changes what happens to everyone else's contributions. You need an explicit, understandable rule before changing the storage model.

This is not just an engineering decision. It's a creator-rights decision.

### C. Give Draw back a visual family tree

Let every drawing show the contributions that grew from it.

```text
                    Original sketch
                  “Blooby says hello”
                         |
              +----------+----------+
              |                     |
         New colors             Funny face
          Artist 2               Artist 3
              |
        Animated version
           Artist 4
```

For a first version, you don't need a sophisticated graph renderer. A post could simply show its parent, its direct Draw backs, and a **View all versions** link.

I'd build that before adding support for Draw back on multi-page Flip animations.

**Important:** You already have replay-ending actions, Draw back counters, per-contributor drawing times, notifications, and creator permission controls. Those should be retained and improved—not rebuilt.

## 4. Fix the current Draw back interface before expanding it

There's a very concrete problem in the handoff: the **“Drawing back on…”** pill can remain over the canvas and block the area where someone needs to draw.

My recommendation is to move the original artist's visibility setting into a small control near the tools. Show the attribution briefly when the editor opens, then allow it to collapse once drawing starts.

The creator should still be able to switch the original between **faint**, **full**, and **hidden**. Your code already supports these states in `skribl/static/lib/drawback.js`.

The success test is straightforward: no drawing surface should be obscured by a persistent interface element, even at mobile screen sizes.

## 5. Improve the journey from first visit to first drawing

Another App communicates its basic loop clearly: draw something, post it, and let others remix it. Its current site also shows a guest-post option in the posting flow.

Blooby should explain its own difference just as quickly.

I'd give a new visitor three immediate paths:

1. **Just draw.** Open Skribl Pad with a blank canvas and start immediately.
2. **Watch a drawing come alive.** See a short Blooby replay, then try making your own.
3. **Draw with someone.** Start from a public drawing that welcomes contributions.

Your project already has help demonstrations and a carefully designed Make flow. I'd reuse those rather than create an entirely new tutorial system.

I would not make registration mandatory before someone can try Pad. Keep drawing available to visitors. Invite them to sign up when they want to keep or share their work across devices.

Because your uploaded social site is still invite-only, this is a recommendation for a future public onboarding flow, not a suggestion to remove your present access controls immediately.

**Important qualification:** Blooby's home page already has an animated Blooby introduction, **“Make a skribl,” “Look around,”** and guest drawing access. Those are good choices. I wouldn't replace that page wholesale with the welcome concept above.

What I'd improve is the path **after** the visitor watches the introduction.

## 6. Make watching a drawing lead naturally to making one

**Priority: Very high · Complexity: Low–medium.**

This is a product-design opportunity, not necessarily a large new feature.

Think about the following journey:

1. **Someone opens Blooby.** They see the animated introduction that already exists.
2. **They watch a real drawing replay.** Show a finished piece that is interesting enough to make them want to try it.
3. **They see an easy next action.** “Try drawing this” or “Add your own” rather than a generic invitation to explore more menus.
4. **Pad opens in a useful starting state.** A blank canvas for an original drawing, or a faint reference for a contribution.
5. **They finish and share.** They can preview their own replay, choose to save, share a link, or make a post when eligible.

The goal is to eliminate decisions between inspiration and drawing.

You already have some of the necessary actions, including Draw back at the end of a replay. I would test how prominent they should be, where they should appear, and whether people understand them.

For example, a first-time visitor may understand **“Add to this drawing”** more readily than **“Draw back.”** Keep **Draw back** as the feature's brand name, but explain it in plain language the first time.

**Success test:** Ask five people who have never used the site to watch a drawing and add something to it. Observe where they stop, hesitate, or choose the wrong control.

## 7. Make the drawing replay itself more useful

**Priority: High · Potential differentiation: Very high.**

Skribl already records a drawing's timing, supports variable-speed playback, and can display timed likes along its progress line.

I think you can do more with that information without turning the player into a video editor.

### My favorite addition: “Learn from this drawing”

Imagine somebody posts a beautifully drawn character. A viewer could choose to watch normally or learn how the artist made it.

The original illustrative player had three optional chapter controls:

- **1. Outline:** Watch the outer shape and structure take form.
- **2. Color:** See how color is built and refined.
- **3. Details:** Follow the finishing touches and expression.

This is an illustrative interface, not a working replay of an uploaded drawing.

I wouldn't try to automatically infer every stage of a drawing. Start by allowing the artist to mark two or three meaningful moments on the replay timeline while publishing.

A viewer could then jump directly to **Outline**, **Color**, or **Details** and slow that segment down.

Skribl becomes both entertainment and a way to learn.

**Technical starting point:** Store optional chapter markers as timestamps on the drawing's existing playback timeline. They should survive playback-speed changes and not alter the underlying recorded strokes.

A related later feature is **“Try this step”**—pause at a chapter and open Pad with a reference. But that's a second release, not a prerequisite for the chapter markers.

## 8. Give the community reasons to draw together

**Priority: High · Complexity: Low for a manual pilot.**

Another App explicitly promotes challenges and collaboration as community activities.

Blooby already has a feed, Gallery, likes, follows, and conversations. What I'd add is a more intentional reason to participate.

I would start with one recurring prompt, run manually before creating a complicated challenge system.

> **Example: This week's drawing prompt**  
> **Give Blooby a new expression!**  
> Make him surprised, sleepy, mischievous, or completely ridiculous.  
> Use Pad · Draw back welcome
>
> *Example community prompt, not a currently running event.*

The first version could be a featured post, with people contributing through Draw back. Their contributions would appear in a dedicated view of the original's branches.

Then, once participation is proven, add a formal challenge feature with a start/end date, an organizer, eligible submissions, and an archive.

I would not initially add competitive rankings or medals. The more useful goal is giving new artists an easy starting point and encouraging them to respond to one another.

A successful event isn't necessarily one that gets hundreds of likes. It's one where someone who would otherwise only watch decides to draw.

## 9. Make the Gallery better at helping people discover drawings they can interact with

**Priority: Medium–high · Complexity: Medium.**

Your Gallery already has **Following / Everyone**, **New / Hot**, search, and filters that respect blocks and mutes. Its Hot ranking uses plays over the last seven days.

I wouldn't replace those.

I'd add a way to discover art based on *what someone can do with it*, not just how recently or frequently it was watched.

| Gallery option | What it would show |
| --- | --- |
| New | Existing newest-first view |
| Hot | Existing recent-plays ranking |
| **Draw back ready** | Drawings whose creators permit contributions |
| **Drawing chains** | Drawings with multiple connected contributions |
| **Quick watches** | Short replays that are easy to enjoy in a few seconds |

Start with **Draw back ready**. You already store eligibility and creator permission information, so this is a relatively natural extension of the existing Gallery.

I'd defer **Drawing chains** until a proper ancestry model exists.

I'd also avoid making replay length the sole quality signal. A long, detailed drawing can be just as valuable as a quick doodle.

## 10. Improve sharing outside Blooby

**Priority: High · Complexity: Medium.**

Your project already has shareable links, rich preview cards, PNG exports, GIF exports, and video export. So the underlying functionality is largely there.

The next improvement is to make sharing the *experience of watching* easier.

My ideal flow would be:

1. Someone finishes a drawing.
2. They preview its replay.
3. They choose **Share drawing**.
4. The app offers a link or a short animated preview, without requiring them to navigate through advanced export settings.
5. The exported media includes optional, unobtrusive attribution to the creator and Blooby.

I would prototype a short replay teaser for messaging and other social networks. The regular link should still lead to the full, interactive replay.

This matters because people who have never heard of Blooby need to understand why its artwork is different from a static picture.

**The key product principle:** A shared Skribl should advertise its own special ability. A static thumbnail doesn't fully communicate that drawings can draw themselves.

## 11. Treat trust, accessibility, and performance as core features

These are less exciting than new brushes, but they're critical for a drawing-based social site.

### A. Creator control and attribution

Build on the permission controls you've already implemented for Draw back. Make it clear who created the original, who contributed, and whether additional contributions are allowed.

I would keep the original creator prominently credited on every branch.

Also add an optional artwork-description field at publishing time. Your project has already invested heavily in screen-reader accessibility and automated accessibility checks; describing artwork itself is the logical next step.

### B. Public-launch safety

Your social implementation has report, block, mute, and moderation foundations. Your roadmap intentionally delays open sign-up until the necessary safety and legal requirements are addressed.

I agree with that approach.

Before broad public registration, verify that moderators can handle reports involving both original drawings and derived drawings, including removal, appeals, and the visibility of related contributions.

Don't rush into direct messaging just because conventional social networks have it. Private messages introduce substantial moderation requirements without improving Skribl's core drawing workflow.

### C. Storage and performance

Your `skribl/storage.py` already implements inline, local-disk, and S3-compatible storage. The application currently defaults to inline storage unless the deployment is configured otherwise.

**Before adding data-heavy layers or richer media, establish the external-storage configuration and test it in the deployment.**

Keep the drawing payload versioned, and ensure old drawings can still be replayed.

I would also add a performance acceptance test for any new layer or fill operation on a lower-powered phone, using the existing long-replay benchmarks as a baseline. (The Fill reference is historical; the accompanying clarification recommends keeping conventional Fill in Flip.)

And keep the standalone Skribl player lightweight. It should not load the editor merely to show a drawing in the Blooby feed.

## 12. The development order I would actually follow

These are dependency-based stages, not promises about calendar dates.

### Release A — Make everything dependable

*Finish before new major editor features.*

Fix iPhone text dragging, the embedded keyboard jump, How it works navigation, the obscured Draw back canvas, and any outstanding automated test failures.

**Definition of done:** Each reported issue has a reproduction test, an observed fix, and a check on the affected devices.

### Release B — Make Skribl easier to create with

*The core editor upgrade.*

The original recommendation said to prototype two editable layers, add fill to Pad, expand selection to a freehand lasso, and simplify access to everyday tools. Complete storage and payload-design prerequisites first.

**Corrected direction:** Prototype replay-compatible layers; add a freehand, stroke-aware lasso; simplify controls. **Leave conventional Fill in Flip**, rather than moving it into Pad. Refer to `PAD_FILL_ARCHITECTURE_CLARIFICATION.md` before planning coloring features.

**Definition of done:** Users can create, edit, save, reopen, and replay a character drawing without losing work or changing its appearance. Coloring should remain compatible with Pad's draw-itself identity.

### Release C — Make Blooby more collaborative

*Improve what makes the social network different.*

Improve Draw back discovery, add a simple drawing family-tree view, test the original-versus-contribution replay controls, and pilot a community prompt.

**Definition of done:** A user can discover a drawing, contribute to it, and explore its other contributions without getting lost.

### Release D — Improve growth and repeat use

*Make the experience sustainable.*

Add replay chapters, improve external sharing, refine the first-time drawing journey, and use small community experiments to determine which features lead to repeat creation.

**Definition of done:** You can measure whether visitors become artists, artists get responses, and creators return to draw again.

## 13. How to tell whether these improvements actually work

I'd track a small number of product measures before investing in larger features. These are **suggested measures**, not data collected from Blooby.

| Measure | What it tells you |
| --- | --- |
| First drawing completion | Can new visitors successfully make something? |
| Drawing-to-share rate | Do creators find their result worth showing? |
| Replay completion rate | Are people watching the creative process? |
| Draw back conversion | Does watching inspire participation? |
| Seven-day creator return | Do people come back to make more art? |
| Failed saves and publishing attempts | Is friction causing people to lose work or give up? |

I would track these as privacy-conscious aggregate events, rather than record individual drawing content for analytics.

You could then run small, controlled comparisons. For example, try two versions of the Draw back invitation and see which one helps more new users complete a contribution—not merely click the button.

## 14. What I would deliberately avoid for now

There are several things I wouldn't spend development time on yet: a recommendation algorithm, direct messaging, dozens of additional brushes, advanced painting filters, full four-layer animation timelines, or complicated competitive challenge systems.

None of those is inherently a bad idea. But they introduce substantial technical or operational work before you've established which experiences make Blooby special.

I would also avoid turning Blooby and Skribl into confusingly separate products. **Blooby should be the place people belong; Skribl should be the creative tool that makes the place distinctive.**

That leaves a very clear message:

> **Blooby**  
> A place where drawings come alive.  
> Make a Skribl. Watch it draw itself. Add your own. See where the idea goes.

## My five most important decisions for Blooby

If I were choosing what to do with the next significant development effort, this is the order I'd pick.

| Rank | Investment | Reason |
| --- | --- | --- |
| 1 | **Fix current drawing and navigation bugs** | Nobody stays with a tool that feels unpredictable. |
| 2 | **Add simple, replay-compatible layers and improve stroke-aware selection** | Makes the editor more useful without undermining Pad's self-drawing model. |
| 3 | **Develop Draw back into a genuine collaboration system** | Gives Blooby a differentiator beyond standard social posting. |
| 4 | **Improve the watch-to-draw journey** | Converts spectators into creators without requiring a complicated new feature. |
| 5 | **Use replay as a learning and sharing format** | Takes advantage of the technology Skribl already has instead of competing solely on brushes. |

The most important strategic choice is number three, even though I wouldn't build it first.

Another App's appeal is that **art evolves through people**. Skribl's advantage is that **you can watch the act of creation itself**.

Blooby can combine those ideas into something more distinctive: a drawing social network where people don't just share finished pictures—they contribute to the same creative story, and everyone can watch how it happened.

**That's the product I'd build toward.**
