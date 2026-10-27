# Compile rules (restated from `scripts/compile_prompt.py`)

The upstream skill writes a `draft.json` and runs a Python compiler. This node has no shell, so
the same rules are restated here — apply them mentally and emit the compiled result directly.

The bundled `scripts/compile_prompt.py` is kept for reference and for any external agent that does
have a shell; its behaviour is authoritative. If a draft would be rejected there, do not emit it.

## Accepted draft shapes

Exactly one of two shapes is valid. A draft containing both `caption` and layout fields is invalid.

### Caption draft

- Allowed fields: `caption` only. Unknown fields are rejected.
- `caption` must be nonempty text.
- Compiled output = `caption` unchanged (no trimming beyond the model's own whitespace strip).

### Layout draft

Root fields — all six required, nothing else allowed:

| Field | Rule |
|---|---|
| `width`, `height` | `int > 0`, `% 16 == 0` |
| `bbox_coord_space` | exactly `"abs"` in the draft |
| `bbox_format` | exactly `"xyxy"` in the draft |
| `summary` | object, see below |
| `items` | nonempty flat array, see below |

`summary` — `caption` required; `meta`, `canvas`, `palette` optional:

- `caption`: nonempty text.
- `meta`: array of nonempty strings.
- `canvas`: one of `single`, `multi_panel`, `collage`.
- `palette`: array of nonempty strings.

`items[i]` — `label`, `caption`, `bbox` required; `text`, `tags`, `palette` optional:

- `label`: one of `object`, `character`, `text`.
- `caption`: nonempty text.
- `bbox`: array of exactly four finite numbers `[x1,y1,x2,y2]` with `x1 < x2`, `y1 < y2` and
  `0 <= x1 < x2 <= width`, `0 <= y1 < y2 <= height`. Out-of-bounds boxes are rejected by the
  compiler — it never clips them silently.
- `text`: required when `label` is `text`; must be nonempty. Exact visible characters, intended
  line breaks written as JSON `\n`.
- `tags`, `palette`: arrays of nonempty strings.

Any other key (`children`, `parent`, `id`, `elements`, `notes`, …) is rejected rather than dropped.

## Box conversion

Draft boxes are absolute pixels. The compiled form is centered on the canvas and ordered `yxyx`:

```
v1 = floor(y_min) - (height // 2)
v2 = floor(x_min) - (width  // 2)
v3 = ceil (y_max) - (height // 2)
v4 = ceil (x_max) - (width  // 2)
bbox_out = [v1, v2, v3, v4]
```

- `floor` on left/top, `ceil` on right/bottom: fractional edges are enclosed, matching the
  generation-time export.
- The compiler also requires `v1 < v3` and `v2 < v4`; a box thinner than one pixel on either axis
  fails at export precision, so never emit degenerate boxes.
- Centering subtracts half the canvas, so coordinates run negative on the left/top half. Negative
  values are correct and expected — never clamp them to zero.

Worked example (canvas 1536×1024):

```
box = [176, 224, 800, 864]      cx = 768, cy = 512
v1 = 224 - 512 = -288
v2 = 176 - 768 = -592
v3 = 864 - 512 =  352
v4 = 800 - 768 =   32
→ [-288,-592,352,32]
```

## Compiled output

- Serialized with `ensure_ascii=False`, `separators=(",", ":")`, `allow_nan=False` — compact,
  literal UTF-8 characters, no spaces after `,` or `:`.
- Keys in insertion order: `summary`, `items`, `bbox_coord_space`, `bbox_format`.
- `bbox_coord_space` becomes `"abs_centralized"`, `bbox_format` becomes `"yxyx"`.
- `width`, `height`, `bbox_coord_space` and `bbox_format` of the draft are **not** carried over;
  the canvas lives outside the prompt (the node prints it on the `尺寸：` line).
- Item key order follows the draft item's own order; `bbox` is replaced in place by the compiled
  array, so keep `bbox` where you want it.
- Newlines inside `text`/`caption` are escaped as `\n` in the JSON while remaining real newlines in
  the decoded string.
