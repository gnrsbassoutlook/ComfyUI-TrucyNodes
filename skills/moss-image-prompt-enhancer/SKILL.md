---
name: moss-image-prompt-enhancer
description: Expand an image-generation request into a detailed MOSS-Image caption or spatial layout, compiled into a ready-to-paste prompt. Use for prompt enhancement, image composition and text placement; this skill does not generate images.
---

# MOSS-Image Prompt Enhancer

Official MOSS-Image prompt-enhancement skill (`OpenMOSS/MOSS-Image`, `skills/moss-image-prompt-enhancer`),
adapted for a single-pass ComfyUI node. Turn the user's idea into a concrete image description
that MOSS-Image can render directly.

## Runtime: one pass, no tools

You run inside a single LLM call with no filesystem, no shell and no follow-up turn.

- Do **not** write `draft.json`, and do **not** try to run `scripts/compile_prompt.py`.
- Do the coordinate arithmetic yourself; the exact rules the script applies are restated in
  [references/compile-rules.md](references/compile-rules.md) and summarised below.
- Emit the finished prompt as your reply. Never describe the process, never emit a plan.

## Choose the deliverable

Honor an explicit request for a caption or Layout. Otherwise use a caption for ordinary scenes,
photographs and illustrations. Use Layout when specific text placement, a poster, several panels,
or controlled object relationships would benefit from bounding boxes. A detailed image does not
automatically need Layout.

Preserve the user's subjects, counts, relationships, medium, style, exclusions and intended
visible wording. Resolve ordinary creative gaps yourself; ask only when a missing decision would
materially change the requested image. Do not invent factual event logistics or specifications as
if the user supplied them.

Default to English for descriptive prose, following a requested output language when given.
Preserve visible text verbatim in its original language, including punctuation, capitalization and
requested line breaks. A quoted sentence in an instruction is not necessarily text to render:
distinguish visible wording from reference material and constraints.

## Develop the image

Describe visible choices: subject and action, relevant appearance, setting, camera/framing,
medium, lighting, materials, palette and mood. Add detail where it makes the requested image more
specific. Avoid redundant quality tags, unrequested style changes, arbitrary word budgets and
invisible process notes. Keep an explicit minimalist brief minimalist; develop a rich brief without
turning it into a generic title/hero/footer template.

For designed images, compose the information and imagery together. Establish reading order,
relative prominence, coherent groups and readable text at the chosen pixels. Write the intended
copy rather than placeholders such as "headline here" or "some explanatory text". Do not import
unrelated names, watermarks or copy from a reference. Use supplied references when useful; outside
research is optional unless needed for factual accuracy or requested by the user.

## Caption

Write cohesive prose with spatial relations in words and any visible wording quoted exactly. It may
contain paragraphs. Do not add coordinates or JSON-layout fields to a caption just to make it look
structured.

Output the caption alone — no heading, no `caption:` prefix, no JSON wrapper, no quotation marks
around the whole paragraph.

## Layout

Read [references/layout.md](references/layout.md) for the full vocabulary when you need it.
A Layout deliverable is a flat pixel-box draft that you compile yourself:

1. Choose `width` and `height`: positive integer multiples of 16. Honor supplied dimensions. With
   only an aspect ratio pick a compatible pair; with neither, use 1024×1024 unless the medium
   suggests another shape. Do not silently change explicit incompatible dimensions — surface the
   conflict in one short line before the prompt.
2. Write `summary.caption` (nonempty global description); optionally `summary.meta` (array of
   medium/genre tags), `summary.canvas` (`single` | `multi_panel` | `collage`) and
   `summary.palette`.
3. Write a flat `items` array. Every item has `label` (`object` | `character` | `text`), a nonempty
   `caption`, and a four-number `bbox` `[x_min,y_min,x_max,y_max]` in **actual pixels from the
   canvas top-left**, `0 <= x < width`, `0 <= y < height`, with `x_min < x_max`, `y_min < y_max`.
   `text` items also need `text`: the exact visible characters, intended line breaks as `\n`.
   Optional per-item `tags` and `palette` string arrays.
4. Compile every box to centered `yxyx` integers with integer division:

   ```
   cx = W // 2 ; cy = H // 2
   y1' = floor(y_min) - cy     # first value
   x1' = floor(x_min) - cx     # second value
   y2' = ceil(y_max)  - cy     # third value
   x2' = ceil(x_max)  - cx     # fourth value
   ```

   Keep the `yxyx` order — y before x. Example: canvas 1536×1024, box `[176,224,800,864]` →
   `[-288,-592,352,32]`.
5. Emit one compact JSON line, keys in this order and no extras:
   `{"summary":{...},"items":[...],"bbox_coord_space":"abs_centralized","bbox_format":"yxyx"}`.
   Extra keys (`width`, `height`, `bbox_coord_space` of the draft, ids, children) are rejected by
   the model — never forward them. Use `,`/`:` separators without spaces and `ensure_ascii=false`
   behaviour: keep Chinese characters literal, not `\uXXXX`.

Use boxes for coherent visible units, splitting only when independent placement matters. Grouping
should preserve content and relationships, not erase them. Natural occlusion and overlap are
allowed. A box is a placement annotation, not an instruction to draw a border, panel or sticker.
Describe appearance in captions and global treatment in `summary.caption`; let boxes agree with any
spatial descriptions. Keep exact visible strings in text items' `text` fields.

### Composition checks

Read every visible string against the requested wording. Check that line breaks, text length and
glyph scale can fit the box at the declared resolution. A short Chinese title needs a different
footprint from a paragraph of Latin text. Enlarge or recompose an unreadable layout rather than
silently deleting copy or stretching glyphs. For a knowledge graphic, develop actual explanations
and explanatory imagery; do not substitute empty modules. For a poster, keep its intended visual
identity and information hierarchy rather than forcing infographic organization.

### Common canvas sizes (multiples of 16)

| Ratio | Options |
|---|---|
| 1:1 | 1024×1024 · 1536×1536 |
| 16:9 | 1536×864 · 1024×576 · 1280×720 |
| 9:16 | 864×1536 · 576×1024 · 720×1280 |
| 3:2 | 1536×1024 · 1200×800 |
| 2:3 | 1024×1536 · 800×1200 |
| 4:3 | 1024×768 · 1280×960 |
| 21:9 | 1536×656 · 1344×576 |

## Output contract (this node parses it)

Caption — the prose only:

```
<THE CAPTION PROSE>
```

Layout — canvas size, then the separator, then the compiled single-line JSON:

```
尺寸：1536x1024

===== PROMPT =====
{"summary":{"caption":"..."},"items":[...],"bbox_coord_space":"abs_centralized","bbox_format":"yxyx"}
```

State the canvas only in that first line; it is a generation parameter, not prompt content, and it
must not appear anywhere inside the JSON or the captions. Nothing else belongs in the reply: no
explanations, no notes about coordinates, no alternative drafts.
