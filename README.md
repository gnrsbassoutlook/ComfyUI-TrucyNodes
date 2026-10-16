# 🎬 ComfyUI-TrucyNodes
**The All-in-One Cinematic Suite for AI Storyboarding, Asset Fusion, Production Logic, and LLM-Driven Prompting.**

---

## 📖 Overview
ComfyUI-TrucyNodes is a professional toolkit designed for AI cinematography workflows. It bridges the gap between creative scriptwriting and final high-fidelity visual production. Whether you are managing hundreds of text prompts, loading storyboard assets by index, building recursive rendering loops, running local GGUF language models through skill executors, or driving the MiniMax H3 reference-to-video pipeline, TrucyNodes provides the stability and precision required for industrial-grade production.

**[🇨🇳 中文说明](./README_CN.md)**

---

### [2026-10-16] The "Brain & Reference" Update: LLM Skill Runner + MiniMax H3 ref2v
🧠 **Skill Runner Trucy** (merged from ComfyUI-TrucyLLM): a skill-executor node family — LLM (LAN LM Studio / remote API / local GGUF) → Skill Loader → Chat / Prompt (H3·QWI) → Unload Model. The brain output port is named **LLM**. Includes the API preset address book and the zero-interruption quality layer.
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

**49 nodes in total.** Categories in the ComfyUI menu: `TrucyNodes/Logic`, `/Image`, `/Toolkit`, `/Text`, `/Excel`, `/Audio`, `/Video`, `/Skill Runner`, `/ref2v`.

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

### 6. Skill Runner Trucy (LLM + Skills)
A **skill executor** that turns any OpenAI-compatible brain into a node-driven prompt factory. The "brain" output port is named **LLM** and feeds the skill nodes.

*   **🚀 Skill Runner Trucy · LLM**: three brain types in one dropdown —
    *   **LAN LM Studio** (`http://<Mac-IP>:1234/v1`, default `gemma-4-e4b-it`)
    *   **Remote API**: DeepSeek / OpenAI / any OpenAI-compatible service (`api_base` + `api_key` + `model`; bare domains like `https://api.deepseek.com` auto-complete to `/v1`). The `model` box is a free-text required field — type any model ID, including relay/aggregator names like `gemini-3.1-flash-lite-preview`; API presets only pre-fill it and never lock it
    *   **Local GGUF**: runs `.gguf` files from `ComfyUI/models/LLM` (subfolders included) on your own GPU, with mmproj vision projector, `n_ctx` / `n_gpu_layers` / `n_batch`, and Qwen3.8-style thinking controls
*   **🚀 Skill Runner Trucy · Skill Loader**: scans the bundled `skills/` (plus `comfyUI-llama-TE/skills` when present); fix one skill or let the brain auto-pick.
*   **🚀 Skill Runner Trucy · Chat**: brain + skill + prompt → text, with **12 reference slots** (🖼️ images 1-9 / 🎵 audio 1-3). Empty slots are skipped and logged, never crash the pipeline.
*   **🚀 Skill Runner Trucy · Prompt (H3/QWI)**: two official prompt-skill families in one node — **H3** (MiniMax video prompts, `[Shot N]` storyboards with soundscape/music) and **Qwen-Image-2.1** (image prompt rewriting). Quality layer checks output and logs issues with **zero pipeline interruption** (optional one-shot auto-repair, off by default).
*   **🚀 Skill Runner Trucy · Unload Model**: frees local GGUF VRAM before sampling; attach its wildcard `upstream` input to the prompt node's output.

**API preset address book**: the LLM node carries an `API Preset` dropdown + `+ Save as API Preset` button (saved to `api_presets.json` in the plugin folder — it contains keys in plaintext, do not share the folder).

### 7. Vision Trucy (image reasoning)
Pure **system prompt + user prompt + images → text** — **no Skill Loader involved** (that's the only difference from the Skill Runner family). Modeled after `comfyUI-llama-TE`'s `QwenTE图像推理`, with the same **8 image inputs**.

*   **🚀 Vision Trucy · Image Reasoning**: LLM (any of the three brain types) + `input mode` (image / text) + system & user prompts + 🖼️ reference images 1-8 (+ 🎵 audio 1-3) → text. Great for batch image captioning, reference-asset analysis (e.g. feeding character sheets / locations into the H3 ref2v pipeline), or any vision Q&A — straight from a prompt box, zero skill machinery.
*   Reuses the whole media layer: null-safe slots, `<Picture N>` / `<imageN>` tagging (auto-detected, H3 fallback), quality logging without interruption.
*   **Note**: whether images actually reach the model depends on the brain. Local GGUF needs an mmproj projector; DeepSeek's API now accepts images (returns model `deepseek-flash`); text-only models will error on image mode — switch the mode to text.

### 8. H3 ref2v Trucy (MiniMax H3 Ref2VA)
Reference-to-video conditioning for the official MiniMax H3 pipeline, in two interchangeable forms (identical reference-encoding math, verified by unit tests):

*   **🚀 ref2v Trucy · Reference Encode (cache layer)**: reference images/audio + dual VAE → AV latent + ref_data. **Deliberately has no prompt input** — change the prompt and ComfyUI's built-in node cache skips VAE re-encoding entirely.
*   **🚀 ref2v Trucy · Prompt Encode (exit)**: clip + prompt + upstream ref_data → positive conditioning (only this node re-runs when the prompt changes).
*   **🚀 ref2v Trucy · Reference to Video (merged)**: single-frame version with the same wiring as the official `MiniMaxH3ReferenceToVideo` node; because it contains the prompt, it manages an internal LRU cache (content-level sha1 per slot + VAE instance identity + weak-ref liveness).

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

## 📄 License
MIT License
