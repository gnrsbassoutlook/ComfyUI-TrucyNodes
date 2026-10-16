# 🎬 ComfyUI-TrucyNodes
**The All-in-One Cinematic Suite for AI Storyboarding, Asset Fusion, Production Logic, and LLM-Driven Prompting.**

---

## 📖 Overview
ComfyUI-TrucyNodes is a professional toolkit designed for AI cinematography workflows. It bridges the gap between creative scriptwriting and final high-fidelity visual production. Whether you are managing hundreds of text prompts, loading storyboard assets by index, building recursive rendering loops, running local GGUF language models through skill executors, or driving the MiniMax H3 reference-to-video pipeline, TrucyNodes provides the stability and precision required for industrial-grade production.

**[🇨🇳 中文说明](./README_CN.md)**

---

### [2026-10-17] Executor Cleanup: Generic VLM Labels + Sampling Fine-Tuning + llama.cpp Speed Knobs
🏷️ **VLM Runner labels are now generic** — connected images are tagged **图片1 … 图片8** and the video **视频1** inside the node, and the prompt asks for per-image descriptions. The H3/QWI tag dropdown is gone from this node (it never belonged to a skill workflow); Chat/Prompt keep their skill-family tag logic.
🛡️ **Null-safety on every media input** — all 8 image slots and the video port skip empty / muted / broken inputs with a log line (video mode with nothing usable gives a clear designed error, never a raw traceback).
🎚️ **Sampling fine-tuning on all three executors** (Chat / Prompt / VLM Runner): `top_p` / `top_k` / `repeat_penalty` / `seed` / `保留思考过程` — every default is "not set, not sent", so old workflows behave exactly as before. `top_p`/`seed` are standard OpenAI request fields (local + LM Studio + remote); `top_k`/`repeat_penalty` are llama.cpp-native (local + LM Studio; a strict API rejecting them triggers an automatic drop-and-retry).
⚡ **llama.cpp speed knobs on the loader** (modeled after llama-TE, Local GGUF only): KV cache K/V quantization (`q8_0` etc., default = untouched f16) and a three-state Flash Attention switch (default = don't touch llama.cpp's behavior).
🧹 The legacy generic `图片` port on Chat / Prompt is removed — the 9 numbered image slots cover it (old workflows wired to it need a one-time re-wire).

### [2026-10-16] The "Brain & Reference" Update: LLM Loader + Skill Runner + VLM Runner + MiniMax H3 ref2v
🧠 **LLM Loader Trucy** (merged from ComfyUI-TrucyLLM): the brain loader — one node, three brain types (LAN LM Studio / remote API / local GGUF). It only loads a brain and never runs a skill; its **LLM** output port feeds both the **Skill Runner Trucy** family and the **VLM Runner Trucy** node.
🛠️ **Skill Runner Trucy**: the real skill executors — Skill Loader → Chat / Prompt (H3·QWI) → Unload Model, plus the API preset address book and the zero-interruption quality layer.
👁️ **VLM Runner Trucy**: image + video reasoning with no skill machinery — **8 image slots or 1 video, mutually exclusive**. Local GGUF brains receive the **video file itself** (Qwen-VL reads video natively via llama.cpp mtmd + ffmpeg, with timestamps); remote brains / missing ffmpeg / failed native send automatically degrade to evenly-sampled frames. No text mode by design — that's the Chat node's job.
🎬 **ref2v Trucy**: MiniMax H3 Ref2VA reference encoding in two interchangeable forms — the cache-layer dual nodes (no prompt input on the reference encoder, so ComfyUI's built-in cache skips VAE re-encoding when only the prompt changes) and a merged single-frame node with internal LRU caching.
🧹 Cleanup: removed the long-dead legacy Klein encode nodes and the two obsolete H3 prep/prompt nodes; every remaining node is listed in this README.

### [2026-07-03] Production-Grade Pipeline Integration: Performance & Stability
🎬 Cinematic Video Loader (TrucyVideoLoaderIndex): Added a professional proxy media pipeline.
Resolution/FPS Proxying: Added dynamic downsampling and frame skipping (e.g., 4/8/12 FPS) to drastically reduce VRAM usage during audio-visual conditioning.
Intelligent Fallback: Implemented "Out-of-Bounds" protection—if an index is invalid, the node safely generates a 1kHz beep tone instead of crashing.
🚀 Trucy LTX MSR Prep: Added background-target selection logic, allowing seamless swapping of composition foundations without breaking the LTX IC LoRA alignment.
🛠️ Production Robustness: Integrated ExecutionBlocker across all bridge nodes to safely halt downstream execution, saving compute during debugging.
🏗️ Architecture Consolidation: Completed the final unification of the TrucyNodes namespace, cleaning up all obsolete Matrix references.


### [2026-06-26] The "Director's Cut" Update: Precision & Performance
🛡️ New Feature: Trucy Image Bridge (6ch/10ch): Introduced a lossless image passthrough node designed to clean up complex workspaces.
Zero Overhead: Uses pure Python pointer pass-through. Consumes 0 MB of VRAM/RAM.
Smart Blockers: Features built-in disable_out boolean toggles powered by ComfyUI's native ExecutionBlocker. Turning a channel "OFF" will physically halt all downstream nodes (KSamplers, Video Encoders) connected to it, saving massive amounts of compute time during testing.
🔢 Trucy Text To Number Converter: Simplified the input mechanism. The node now features a direct text-input box (removed forceInput), allowing manual typing while still outputting perfectly extracted Strings, Integers, and Floats.
✨ Polish & Cleanup: Refined image_adapter.py by removing redundant boolean inputs from the Bridge nodes to keep the UI clean and strictly functional.

## 🚀 Core Modules

**50 nodes in total.** Categories in the ComfyUI menu: `TrucyNodes/Logic`, `/Image`, `/Toolkit`, `/Text`, `/Excel`, `/Audio`, `/Video`, `/LLM Loader`, `/Skill Runner`, `/VLM Runner`, `/ref2v`.

### 1. Logic & Flow Control
*   **Trucy For Loop (Start / End, 9ch / 2ch)**: High-performance recursive loop system.
    *   9ch supports **9 simultaneous data channels** (values 1-9) plus Flow and Index; 2ch is the lightweight variant.
    *   Advanced range parsing (e.g., `1-3, 5, 10-12`) with index mode and step control.
    *   Synchronous state passing across iterations.
*   **Trucy Any Switch (6ch / 10ch)**: Any-type multi-input selector — LATENT / IMAGE / AUDIO / STRING / INT / FLOAT all pass through one node.
*   **Trucy Control Bridge**: Boolean control bridge. Its `disable_out` throws ComfyUI's native ExecutionBlocker, physically halting everything downstream (no fake images, no wasted compute during debugging).
*   **Trucy Remote Toggle 6x6**: Mute/bypass whole node groups by node ID — fill in the A/B ID lists and flip behavior without touching the canvas.
*   **Trucy 5-way Mute/Bypass Nodes-Remote (TrucyMasterIntRouter)**: One master integer routes execution across five node groups by value.
*   **Trucy Frame & Seconds Converter**: Frame ↔ second conversion with rounding modes; outputs INT + FLOAT.

### 2. Image Pipeline
*   **Trucy Image Loader by Index / Image Loader (6ch)**: Directory + index loading with out-of-bounds fallback; the 6ch variant loads a sorted run of six images in one node.
*   **Trucy Image Loader (String 6/10)**: Accepts IDs (e.g., "X1") or filenames directly. Smart matching finds the right asset even with partial names; empty slots get placeholders.
*   **Trucy Image Bridge (6ch / 10ch)**: Lossless passthrough. Pure pointer passing, 0 MB overhead, with ExecutionBlocker cut-off per channel.
*   **Trucy Image Size Adapter**: The "Resolution Bridge." Perfect for **1088p -> 1080p** conversion with lossless center cropping or stretching.
*   **Trucy Asset Grid (6 / 10)**: Low-VRAM thumbnail grids to preview your visual assets, with labels and empty placeholders.

### 3. Text & Data Toolkit
*   **Trucy Text Splitter (6/10)**: Split strings with delimiter + optional bracket constraints, or **None (Direct Split)**.
*   **Trucy ID Extractor**: Snipe IDs (like `X1`) from text, with search mode and remainder output.
*   **Trucy String Slicer / Text Smart Slicer**: Surgical text cutting with custom left/right delimiters.
*   **Trucy Text Symbol Sniffer**: Pull symbols/numbers out of multi-slot text inputs.
*   **Trucy Text Cleaner**: Keyword removal and fuzzy cleanup for messy LLM or Excel output.
*   **Trucy Text to Number Converter**: Direct text input box; outputs String, Int, Float, and Boolean.
*   **Trucy Doc Loader**: Absolute-path loader for TXT / MD / DOCX with encoding auto-detection.
*   **Trucy TXT Loader by Index**: Batch load TXT scripts by index — ideal for feeding loops.
*   **Trucy Text Preview & Save**: Smart viewer/saver with auto-incrementing filenames and path fallback.
*   **Trucy Folder Iterator**: Walk a folder with filter modes and feed file paths downstream.
*   **Trucy Dataset Saver**: Save image + caption pairs to disk for dataset building.

### 4. Excel-Driven Storyboards
*   **TrucyExcelReader**: Load a single cell from any sheet. Features **Smart Number Extraction** (regex-based) to grab parameters from messy text.
*   **TrucyExcelReader6 / TrucyExcelReader10**: Batch-read 6/10 columns per row — one Excel row drives one shot in a loop.

### 5. Audio & Video Production
*   **TrucyAudioLoaderIndex**: High-efficiency audio loading with **auto-resampling** (44.1k/48k) and a **1kHz beep fallback** for missing files.
*   **Trucy Audio Detector & Padder (AudioLengthDetector)**: Report length in seconds/frames and pad to a target length.
*   **Trucy Empty Audio Generator**: Synthesize silent audio by seconds or frames (conditioning placeholder).
*   **Trucy Save Audio**: Save AUDIO to disk in multiple formats with resampling.
*   **TrucyVideoLoaderIndex**: Professional proxy video pipeline — FPS frame skipping (4/8/12), resolution proxying, and out-of-bounds protection.
*   **TrucyVideoCombine**: Direct FFmpeg pipe encoding (lives in the VHS category). Zero intermediate files. H.264 MP4 / WebP / GIF with audio muxing.

### 6. LLM Loader Trucy (brain loader)
Loads one of three brain types and outputs it on the **LLM** port. It runs no skill by itself — the same brain feeds the **Skill Runner Trucy** family (section 7) and the **VLM Runner Trucy** node (section 8).

*   **🚀 LLM Loader Trucy**: three brain types in one dropdown —
    *   **LAN LM Studio** (`http://<Mac-IP>:1234/v1`, default `gemma-4-e4b-it`)
    *   **Remote API**: DeepSeek / OpenAI / any OpenAI-compatible service (`api_base` + `api_key` + `model`; bare domains like `https://api.deepseek.com` auto-complete to `/v1`). The `model` box is a free-text required field — type any model ID, including relay/aggregator names like `gemini-3.1-flash-lite-preview`; API presets only pre-fill it and never lock it
    *   **Local GGUF**: runs `.gguf` files from `ComfyUI/models/LLM` (subfolders included) on your own GPU, with mmproj vision projector, `n_ctx` / `n_gpu_layers` / `n_batch`, and Qwen3.8-style thinking controls
    *   **Local-only speed knobs (llama.cpp, modeled after llama-TE — the fastest LLM pack in the community)**: `KV cache K/V type` (default `不指定` = untouched llama.cpp f16; `q8_0` saves VRAM and is often faster on big models with long context) and `Flash Attention` (three-state: `off` = don't touch llama.cpp's default; `on` / `off` = explicit override). These are load-time llama.cpp parameters — **they only exist for Local GGUF**; equivalent tuning for LM Studio / remote APIs happens in their own UIs

**API preset address book**: the loader node carries an `API Preset` dropdown + `+ Save as API Preset` button (saved to `api_presets.json` in the plugin folder — it contains keys in plaintext, do not share the folder).

### 7. Skill Runner Trucy (skill executors)
The real skill-executor family: **LLM Loader → Skill Loader → Chat / Prompt → Unload Model**.

*   **🚀 Skill Loader Trucy**: scans the bundled `skills/` (plus `comfyUI-llama-TE/skills` when present); fix one skill or let the brain auto-pick.
*   **🚀 Skill Runner Trucy · Chat**: brain + skill + prompt → text, with **12 reference slots** (🖼️ images 1-9 / 🎵 audio 1-3). Empty slots are skipped and logged, never crash the pipeline. (The old generic `图片` port is gone — the 9 image slots cover it with exact numbering.)
*   **🚀 Skill Runner Trucy · Prompt (H3/QWI)**: two official prompt-skill families in one node — **H3** (MiniMax video prompts, `[Shot N]` storyboards with soundscape/music) and **Qwen-Image-2.1** (image prompt rewriting). Quality layer checks output and logs issues with **zero pipeline interruption** (optional one-shot auto-repair, off by default).
*   **🚀 Skill Runner Trucy · Unload Model**: frees local GGUF VRAM before sampling; attach its wildcard `upstream` input to the prompt node's output.
*   **Sampling fine-tuning** (Chat / Prompt / VLM Runner, every default = "not set, not sent"): `top_p` / `seed` are standard OpenAI request fields (local + LM Studio + remote); `top_k` / `repeat_penalty` are llama.cpp-native (local + LM Studio; strict APIs ignore them, and a 400 rejection triggers an automatic drop-and-retry); `保留思考过程` is Local-GGUF-thinking only. See section 8 for the full breakdown.
*   **Unload after inference** (on all three executors — Chat / Prompt / VLM Runner, off by default): Local GGUF only — automatically unloads the model after inference to hand VRAM back (the next inference reloads it, slightly slower). When several executors share one LLM Loader, enable it on the last one; or keep using the dedicated Unload Model node. No effect on remote APIs / LM Studio (the model isn't local).

### 8. VLM Runner Trucy (image / video reasoning)
Pure **system prompt + user prompt + images or video → text** — **no Skill Loader involved** (that's the only difference from the Skill Runner family). Modeled after `comfyUI-llama-TE`'s `QwenTE图像推理` and extended with video input.

*   **🚀 VLM Runner Trucy**: LLM (any of the three brain types) + `input mode` (**image / video — mutually exclusive, never both**) + system & user prompts → text:
    *   **Image mode**: 🖼️ reference images 1-8. The node tags them internally as **图片1 … 图片8** (generic plain-language labels — no H3/QWI skill family applies to this node), and the prompt asks the model to describe each image separately. Slot numbers are preserved (a muted/broken slot is skipped and logged, never renumbered)
    *   **Video mode**: 🎬 one video (LoadVideo output), tagged **视频1**. Local GGUF brains receive the **video file itself** — llama.cpp's mtmd decodes it via ffmpeg subprocesses (needs `ffmpeg` + `ffprobe` on PATH; ComfyUI packs usually ship them) and Qwen-VL reads it natively at ~4 fps with timestamps. Remote brains, missing ffmpeg, or a failed native send **automatically degrade to evenly-sampled frames** (`视频抽帧数`, default 8) sent as images — each frame keeps its timestamp, so temporal analysis survives the fallback
    *   Wiring both sides at once? The mode dropdown decides what goes to the brain; the other side is ignored with a log line
*   **Null-safe on every media input**: an empty / muted / broken image slot or video port is skipped with a log line (or, in video mode with nothing usable, a clear designed error) — never a raw traceback, never an empty prompt sent to the brain
*   **No text mode by design** — pure-text chat is the Skill Runner's Chat node. A mode with nothing connected fails with a clear message instead of sending an empty prompt.
*   **Sampling fine-tuning** (all three executors share these controls; every default = "not set, not sent" — old workflows keep their exact behavior):
    *   `top_p` / `seed` are **standard OpenAI request fields** — they work per-request on Local GGUF, LM Studio, and remote APIs alike
    *   `top_k` / `repeat_penalty` are **llama.cpp-native fields** — they work on Local GGUF and LM Studio; strict OpenAI-compatible APIs have no such fields (they're usually ignored, and if an endpoint rejects them with HTTP 400 the node drops them and retries once, so the pipeline never breaks)
    *   `保留思考过程` (keep thinking): Local GGUF thinking models only — keeps the inline `<think>…</think>` block instead of stripping it (remote reasoning models return thinking separately on the API side, so this switch does nothing for them)
    *   Equivalent tuning beyond temperature/top_p for remote brains belongs in the LM Studio / API provider's own UI
*   **Unload after inference** (off by default): Local GGUF only — unloads the model after inference to hand VRAM back (the next inference reloads it, slightly slower); no effect on remote brains.
*   **Note**: what actually reaches the model depends on the brain. Local GGUF needs an mmproj projector; DeepSeek's API now accepts images (returns model `deepseek-flash`) — its video mode falls back to sampled frames.

### 9. H3 ref2v Trucy (MiniMax H3 Ref2VA)
Reference-to-video conditioning for the official MiniMax H3 pipeline, in two interchangeable forms (identical reference-encoding math, verified by unit tests):

*   **🚀 H3 ref2v Trucy · Reference Encode (cache layer)**: reference images/audio + dual VAE → AV latent + ref_data. **Deliberately has no prompt input** — change the prompt and ComfyUI's built-in node cache skips VAE re-encoding entirely.
*   **🚀 H3 ref2v Trucy · Prompt Encode (exit)**: clip + prompt + upstream ref_data → positive conditioning (only this node re-runs when the prompt changes).
*   **🚀 H3 ref2v Trucy · Reference to Video (merged)**: single-frame version with the same wiring as the official `MiniMaxH3ReferenceToVideo` node; because it contains the prompt, it manages an internal LRU cache (content-level sha1 per slot + VAE instance identity + weak-ref liveness).

Both forms reuse the official helpers (`_resize` / `_encode_ref_audio` / `_empty_av_latent`), follow the official `<Picture N>` / `<Audio N>` tag scheme (slot numbers are 1-based here vs `ref_image_0` officially — purely a kwargs key name, results are identical), and are null-safe end to end. Video reference ports were removed by decision (use the official `MiniMaxH3ReferenceToVideo` node if ever needed; the collection backend stays dormant in `trucy_media.py`).

---

## 🛠️ Installation
1. `cd custom_nodes`
2. `git clone https://github.com/gnrsbassoutlook/ComfyUI-TrucyNodes.git`
3. Restart ComfyUI.

### Dependencies

**ComfyUI Manager** is recommended — it automatically runs
`pip install -r requirements.txt` when installing this pack. Manual install:
run the same command inside your ComfyUI python environment.

| Dependency | Required? | Notes |
|---|---|---|
| `requests` | ✅ auto | Remote LLM / API presets |
| `openpyxl` | ✅ auto | Excel reader nodes |
| ComfyUI-Impact-Pack | Optional | Any-Switch / Control Bridge nodes. If missing, only those 4 nodes are skipped — everything else still registers |
| `llama-cpp-python` (CUDA/Metal) | Optional | Only needed for the **Local GGUF** LLM mode |

Everything else (torch / numpy / PIL / torchaudio) ships with ComfyUI itself.

**Local GGUF mode** needs `llama-cpp-python` — no compiling required. Grab a
pre-built wheel from [JamePeng/llama-cpp-python releases](https://github.com/JamePeng/llama-cpp-python/releases)
(CUDA 12.4 / 12.6 / 12.8 / 13.1, Python 3.10–3.14, Windows / Linux x64 — see
the releases page for the exact list) and `pip install` the whl matching your
CUDA + Python version. Building from source is also supported (see the
comments in `requirements.txt`).

---

## 🧭 Model & Parameter Recommendations

> **One rule to remember first**: `n_ctx`, thinking mode, reasoning effort,
> `n_gpu_layers`, `n_batch`, KV cache quantization, Flash Attention and the mmproj
> projector are **only tuned inside the node for Local GGUF** (they are llama.cpp
> load-time parameters). For LM Studio and remote APIs those live server-side
> (the LM Studio load screen / your API provider).
> **Request-level sampling** (`temperature` / `max_tokens` / `top_p` / `seed`) are
> standard OpenAI request fields — all three brain types accept them per request.
> `top_k` / `repeat_penalty` are llama.cpp-native: Local GGUF and LM Studio honor
> them; strict OpenAI-compatible APIs don't have those fields (a 400 rejection
> triggers an automatic drop-and-retry).
> **Qwen official sampling**: thinking ON → `temperature=1.0 / top_p=0.95 /
> top_k=20`; thinking OFF → `temperature=0.7 / top_p=0.80 / top_k=20`. Local GGUF
> can now set these precisely on the node; mirror them in the LM Studio / API UI.

### Local GGUF (the loader's Local GGUF section)

| Model | n_ctx | Thinking | Reasoning effort | mmproj | Notes |
|---|---|---|---|---|---|
| Qwen3.8-27B IQ2_XXS (16 GB card — this project's tested config) | 16384 | ON | medium | required for vision | Daily driver on a 5060Ti 16 GB; xhigh gains little at IQ2 and is much slower |
| Qwen3.8-27B Q4_K_M+ (24 GB+ card) | 32768 | ON | xhigh | required for vision | xhigh only pays off once quantization is gentler |
| Qwen3-VL / Qwen3.5-VL / Qwen3.6-VL series | 16384–32768 | per model (Qwen3-VL uses force_reasoning) | — | required | VL models cannot see images without an mmproj |
| 7B–14B small models | 8192 | OFF or low | low | optional | Fast but drifts on strict formats — fine for tagging, keep away from the big H3 skill |

Local ground rules:

- The H3 skill needs at least 8192 ctx; each 1280-px reference image costs ~1K+
  tokens, so 3 images + skill text blow past 8K easily — **16384 is the safe pick**
- `n_gpu_layers=-1` (everything on GPU); when VRAM runs out, rescue in this
  order: lower it → lower `n_ctx` → drop 参考图最长边 (max image edge) to 768/512
- `n_batch` 512 is the speed/VRAM sweet spot; drop to 256 under pressure
- **Speed knobs borrowed from llama-TE** (Local GGUF only): `KV cache K/V type =
  q8_0` saves VRAM and is often faster on big models with long context (quality
  cost is small; default `不指定` keeps llama.cpp's native f16 — zero behavior
  change). `Flash Attention` is three-state: `不开启` doesn't touch llama.cpp's
  default, `开启` / `关闭` explicitly override. Both are load-time parameters, so
  changing them reloads the model once
- To hand VRAM back right after inference: enable **推理后自动卸载** (unload
  after inference) on the executor node (off by default, Local GGUF only — the
  next inference reloads the model, slightly slower), or keep using the
  dedicated Unload Model node

### LAN LM Studio

| Model | Server-side n_ctx | Node temperature | Node max_tokens | Notes |
|---|---|---|---|---|
| gemma-4-e4b-it | ≥ 16384 (8192 makes thinking explode) | 0.7 | 4096 | Reads constraints but never converges its thinking; for production prefer a Qwen |
| qwen3-vl / qwen3 series | 16384 | 0.7 (1.0 with thinking on) | 4096 | Lightweight vision/tagging workhorse |
| others | ¼–½ of the model's max | 0.7 | 4096 | n_ctx and the thinking switch live in the LM Studio load screen, not in ComfyUI |

### Remote API

| Model | temperature | max_tokens | Notes |
|---|---|---|---|
| deepseek-chat | 0.7 (0.3–0.5 for structured H3/QWI) | 4096–8192 | Accepts images now; context is server-side — the node only tunes sampling |
| deepseek-reasoner | leave default (thinking model self-regulates) | ≥ 8192 | Thinking also burns max_tokens — too small gets truncated |
| gpt-4o / gpt-4.1 etc. | 0.7 | 4096–8192 | General purpose; some newer models only expose reasoning-effort tiers — check their docs |
| gemini-\*-flash-lite (relay) | 0.7 | 4096 | Fast and light; vision works, occasional detail misreads |
| other relay models | 0.7 | 4096 | Follow the provider's docs; switch instantly via the API Preset dropdown |

### Sampling by task (all three executor nodes)

| Task | temperature | max_tokens | Notes |
|---|---|---|---|
| H3 video prompt | 0.3–0.5 | ≥ 4096 | Structured output wants stability — low temp keeps storyboards in line |
| QWI image prompt | 0.5–0.7 | ≥ 4096 | — |
| VLM image/video description | 0.3–0.5 | 2048–4096 | Descriptions must be accurate — don't let the model improvise |
| Chat / creative talk | 0.8–1.0 | 4096 | More divergence, more ideas — and more drift |

### Control cheat sheet

| Control | Plain language | When to touch it |
|---|---|---|
| `n_ctx` | The model's workbench: skill text + image tokens + generation all share it | Raise it on "context exceeded", or shrink images / lower n_ctx |
| Thinking mode | Switch for thinking-style models: ON = better but slower | Keep ON for strict formats like H3 |
| Reasoning effort | Only active with thinking ON: xhigh slowest/best · medium balanced · low fastest | medium is plenty at IQ2 quantization |
| `n_gpu_layers` | How many layers live on the GPU: -1 = all, 0 = pure CPU | Lower it (e.g. 20) when VRAM overflows |
| `n_batch` | Prompt tokens processed per batch: bigger = faster, hungrier | Drop to 256 under VRAM pressure |
| KV cache K/V type | (Local GGUF only, llama.cpp) How precisely the KV cache is stored: q8_0 saves VRAM, often faster too | q8_0 for big models / long ctx; default 不指定 = llama.cpp's native f16 |
| Flash Attention | (Local GGUF only, llama.cpp) Faster attention when on; three-state so the default stays untouched | Try 开启; if the environment misbehaves, 关闭 |
| `temperature` | Higher = more divergence: 0.3 reproducible, 1.0 creative | See the task table above |
| `max_tokens` | Max tokens per reply; thinking also spends this budget | Raise it when output gets truncated |
| `top_p` | Keep only the top-p probability mass each step (standard OpenAI field — works on local, LM Studio, and remote) | Qwen reference: 0.95 thinking / 0.80 non-thinking; 0 = not set |
| `top_k` | Keep only the top-k candidates each step (llama.cpp-native: local + LM Studio) | Qwen reference: 20; 0 = not set |
| `repeat_penalty` | >1 suppresses repetition loops (llama.cpp-native: local + LM Studio) | Try 1.05–1.15 when the model repeats itself; 1.0 = not set |
| `seed` | Fix the randomness for reproducible results (standard OpenAI field) | Fix it when A/B-testing prompt changes; 0 = not set (random) |
| Keep thinking | Keep the model's <think> block in the output (Local GGUF thinking models only) | When you want to inspect the reasoning; default off |
| Max image edge | How far images are shrunk before sending | 768/512 on small ctx to avoid token blowout |
| Unload after inference | Throws the model out of VRAM after inference (next inference reloads, slightly slower) | Enable before image gen/sampling needs the VRAM; no effect on remote brains |

## 📄 License
MIT License
