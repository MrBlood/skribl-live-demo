# Blooby vs. Another App — Feature and Product Comparison

**Reviewed:** November 23, 2026  
**Blooby source:** uploaded `skribl-live-demo-main (1).zip` / Skribl v330  
**Another App:** its public editor and help pages (its address is kept out of this repository)

> **Repository note (November 24, 2026):** The owner's refined follow-up, in `docs/research/blooby-skribl-refined-review/`, supersedes this comparison where the two differ. Above all, conventional Fill stays in Flip and is not planned for Pad, whose replay draws itself stroke by stroke: the owner's clarification, in that folder's `PAD_FILL_ARCHITECTURE_CLARIFICATION.md`. Do not read this report's "Add Fill to Pad" or "Bring Fill and Select to Pad" as an accepted build request.

> This is a readable, static export of the prior comparison. Interactive checkboxes, live images, and in-chat widgets have been converted to ordinary text. The assessment is based on the uploaded code and publicly exposed Another App information, **not** a benchmarked hands-on session in both products.

## The big picture

**Blooby does not need to become a copy of Another App.** Your app already has sophisticated features that Another App doesn't emphasize, especially recording and replaying the actual drawing process.

But Another App has advantages in the core drawing workflow and in connecting artwork to a community.

There's an important distinction in your upload: **Skribl Pad and Skribl Flip are implemented drawing tools, while the full Blooby social-network experience is still being built.** This comparison evaluates the implemented features rather than counting planned features as finished.

The code review also found that your social foundation is further along than the high-level roadmap might suggest: accounts, profiles, follows, likes, comments, bookmarks, reposts, mentions, and **Draw back** already exist in the source.

## 1. Side-by-side feature comparison

“Better” means a stronger implementation or workflow on paper, not a benchmarked performance result.

| Feature | Blooby (uploaded v330) | Another App | Assessment |
|---|---|---|---|
| Basic drawing | Pen, marker, pencil, airbrush | Circle, square, airbrush and specialty brushes | Different strengths |
| **Real drawing layers** | No independent editable drawing-layer stack | Up to 4; reorder, hide, merge | **Another App leads** |
| **Selection tools** | Rectangle selection and transforms in Flip | Freehand, polygon and brush selection; add/subtract; feather | **Another App leads** |
| Fill bucket | Available in Flip | Available in its main editor, with tolerance | **Another App leads** |
| Shading/effects | Airbrush, blur and liquify in Flip | Airbrush, halftone and blending | Mixed |
| Shapes and text | Shapes; text drawn as replayable ink | Text and image placement | Different strengths |
| Animation | Flip with pages, holds, onion skin, tweening | Frame-by-frame, per-layer timelines, onion skin | Mixed; Another App stronger layering |
| Drawing replay | Records timed strokes and replays their creation | Animation is the primary playback workflow | **Blooby leads** |
| Music/video | Music loops, trimming, video export | Audio controls appear in current editor; animation export | Blooby replay integration stands out |
| Export | PNG, GIF, video | Image download, GIF, PNG frame sequences | Different strengths |
| Save/resume | Local files, autosave, account drafts | Project files and unsaved-work recovery | Both strong |
| Social interactions | Posts, likes, follows, comments, reposts, bookmarks | Posts, profiles, follows, sketch threads | Both have foundations |
| Collaborative drawing | Draw back: replies extend an original timed drawing | Remixes form linked visual family trees | **Another App leads in branching** |
| Community access | Invite-only sign-up | Public registration, with guest-post option shown | **Another App easier to join** |
| Mobile workflow | Dedicated responsive Pad and Flip layouts | Phone editor requests landscape orientation | **Blooby more flexible** |

Another App's drawing and social features are documented in its own drawing and collaboration guide and its current editor.

## 2. Where Another App is meaningfully ahead

### A. Real layers are the most important drawing-tool gap

This is the clearest missing capability.

**Another App:** Artists can draw on one layer without disturbing another, hide layers, reorder them, and merge them. Its animation mode gives each layer its own sequence of frames.

**Blooby:** Your “Stroke layers” setting prevents dark overlap artifacts within a translucent stroke. It is useful, but it is **not** the same as independently editable drawing layers.

This matters for drawing Blooby himself: the purple body could be on one layer, black outline on another, pink cheek on a third. Artists could alter these without damaging other components.

**Recommendation:** Start with two editable layers—perhaps **Sketch** and **Ink**—with visibility, layer ordering and a merge option. Eventually support additional layers.

**Important technical consequence:** The replay player must know not only *when* a stroke was drawn, but *which layer* it belongs to and how subsequent edits affect playback. This is a data-model change, not just an extra toolbar button.

### B. Another App's selection tool is more versatile

Blooby Flip supports rectangular selection, moving, scaling, rotating, duplication and stamps, which is already more than a basic editor.

Another App adds freehand selection, polygon selection, brush-shaped selection, adding and subtracting from selections, and adjustable feathering.

**Recommendation:** Prioritize **freehand lasso selection**, then bring selection to Pad. Being able to draw a rough circle around an eye, move it, and continue drawing would help character creators. Retain stroke-aware editing where possible to avoid breaking replay.

### C. Its fill workflow is more accessible

Another App makes fill available in its main drawing toolset, with a tolerance control. Blooby has Fill in Flip but not as a standard Pad tool.

**Recommendation:** **Add Fill to Pad**, without forcing users to switch to Flip; reveal tolerance only when needed.

### D. Another App has more options for painting and shading

Another App exposes halftone, soft airbrush and blending tools, with controls for texture, coverage, flow and strength. Blooby has advanced effects of its own, including Blur and Liquify in Flip, but Another App's options are oriented more directly around painting and shading.

**Recommendation:** Improve shading before adding novelty brushes. A soft shading brush and smudge/blend tool would be particularly useful. **Three excellent, intuitive painting tools are more valuable than twenty hard-to-find tools.**

### E. Another App handles layered animation more flexibly

Both have legitimate animation systems.

Blooby Flip has frame duplication, reordering, onion skinning, per-page holds, tweening, playback controls and animation export.

Another App's important difference is that animation frames belong to individual layers, so an artist could hold Blooby's body still while animating a waving arm or blinking eyes. It also supports importing image sequences and exporting PNG frames.

**Recommendation:** Consider layered animation eventually, but **do not replace Flip's existing page-based model right now**. It's easier to understand and already supports substantial animation work.

## 3. Social features: the gap is smaller than it first appears

The uploaded `social/` code includes foundations for accounts, drawn profile pictures, follows, likes, comments, notifications, bookmarks, reposts, quote posts, mentions, moderation and feeds.

**Do not start over on social.** There is significant work already implemented.

### Another App's differentiator: art family trees

Another App centers the **remix**. Someone draws, another person changes it, and versions remain connected to their parents so the community can trace an idea's development.

Blooby's **Draw back** is already a promising alternative. The feature preserves the original drawing, puts it faintly underneath, and adds a second artist's strokes. A replay shows the original creation followed by the response.

This makes collaboration interesting not only as a finished image, but as **two people drawing the same idea over time**.

There are existing restrictions: Draw back applies to eligible single-page Pad drawings and excludes some edited content, including recolored drawings.

**Recommendation:** Improve Draw back rather than create a separate remix system like Another App's. Make contributions easier to explore, show drawing ancestry, and gradually widen eligibility.

### Proposed feature: The Drawing Family

```
Original drawing (Artist A)
             |
      +------+------+
      |             |
Draw back       Draw back
(Artist B)      (Artist C)
      |             |
      +------+------+
             |
       Watch it evolve
   (replay each contribution)
```

Imagine someone drawing Blooby, then three artists adding different expressions, outfits or animations. Viewers navigate the branches and watch each contribution happen.

**Another App lets users follow the ancestry of the image. Blooby could let people follow both the ancestry and the drawing process.**

This is a **proposed** product feature, not a finished feature in the ZIP.

## 4. What Blooby already does well—and should protect

### Recorded drawing playback

Pad records actual strokes with timestamps and replays them, with scrubbing and speed controls. This is arguably Blooby's strongest differentiator. A drawing that recreates itself can be more engaging than a static upload.

### Music synchronized with artwork

Music trimming, looping and video export support small performances, illustrated stories and musical animations. Keep music and replay closely connected.

### Phone-friendly workflows

Pad and Flip include responsive controls and separate interaction models. Another App's phone editor requests landscape orientation. Blooby can aim for easier casual mobile creativity.

### Built-in teaching experience

The uploaded code has a “How it works” system with playable demonstrations, examples and contextual help. This is a meaningful strength, though the teaching experience should remain easy to find and follow.

## 5. Recommended feature backlog

These are **product priorities**, not implementation-time estimates.

| Priority | Feature | Why | Relative effort |
|---|---|---|---|
| P1 | **Bring Fill and Select to Pad** | More capable core drawing without switching to Flip | Medium |
| P1 | **Prototype two editable drawing layers** | Sketch/Ink layers with visibility and ordering; verify replay correctness | High |
| P1 | **Make existing tools easier to discover** | Clearer contextual controls for Fill, Smudge, Onion Skin, Recolor | Low–medium |
| P2 | **Improve Draw back and its family tree** | Easier to explore branches and expand eligible drawing types | High |
| P2 | **Add editable image objects** | Move, resize, rotate and set opacity, instead of only importing as background | High |
| P2 | **Add frame-sequence import/export** | PNG sequence interchange with other drawing programs | Medium |
| P3 | **Add collaborative drawing prompts** | Challenges and shared projects that invite Draw back responses | Medium–high |

### A technical prerequisite

Your `FUTURE.md` notes that the S3/local media-storage backend already exists, but deployment storage configuration should be handled before significantly increasing drawing payload sizes. I agree with that direction.

Also, **do not expand public sign-up solely to match Another App** before your launch requirements, particularly moderation and legal review, are complete.

## 6. What I would not copy

**Do not merge Pad and Flip into one enormous editor** just because Another App has drawing and animation in the same place. Pad records a drawing performance; Flip makes frame-based animation. Those are related but distinct jobs.

**Do not put every tool into the default toolbar.** Preserve your minimal, canvas-first design. Make important tools easy to reach and hide uncommon controls behind sensible menus.

## Final assessment

| Product | Main strength |
|---|---|
| **Another App** | Flexible drawing and remixing: more sophisticated editable layers and selections, plus an understandable visual history of collaborations |
| **Blooby** | Creative process and replay: drawings that create themselves on playback, with music, animation and timed contributions |

The **biggest immediate improvement** is Pad's everyday editing experience, especially Fill and selection.

The **biggest longer-term improvement** is real editable layers that preserve replay.

The **most distinctive opportunity** is Draw back. If collaborative drawings become entertaining to **watch**, not just interesting to look at, Blooby can develop a clearly different identity from Another App.

> The goal shouldn't be “Another App with a new name.” It should be **a social drawing platform where watching people create is as enjoyable as seeing what they created.**

---

## Reference links

- Another App's editor (its address is kept out of this repository)
- Another App's help and feature information (likewise)
- Blooby comparison source: `skribl-live-demo-main (1).zip`, supplied in the same conversation. Not included inside this export.
