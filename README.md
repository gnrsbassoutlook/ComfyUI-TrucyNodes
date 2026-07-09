# 🎬 ComfyUI-TrucyNodes
**The All-in-One Cinematic Suite for AI Storyboarding, Asset Fusion, and Production Logic.**

---

## 📖 Overview
ComfyUI-TrucyNodes is a professional toolkit designed for AI cinematography workflows. It bridges the gap between creative scriptwriting and final high-fidelity visual production. Whether you are managing hundreds of text prompts, merging complex character/scene assets with **Flux2-Klein**, or building recursive rendering loops, TrucyNodes provides the stability and precision required for industrial-grade production.

**[🇨🇳 中文说明](./README_CN.md)**

---

### [2026-07-03] Production-Grade Pipeline Integration: Performance & Stability
🎬 Cinematic Video Loader (TrucyVideoLoaderIndex): Added a professional proxy media pipeline.
Resolution/FPS Proxying: Added dynamic downsampling and frame skipping (e.g., 4/8/12 FPS) to drastically reduce VRAM usage during audio-visual conditioning.
Intelligent Fallback: Implemented "Out-of-Bounds" protection—if an index is invalid, the node safely generates a 1kHz beep tone instead of crashing.
🚀 Trucy LTX MSR Prep: Added background-target selection logic, allowing seamless swapping of composition foundations without breaking the LTX IC LoRA alignment.
🛠️ Production Robustness: Integrated ExecutionBlocker across all bridge nodes to safely halt downstream execution, saving compute during debugging.
🏗️ Architecture Consolidation: Completed the final unification of the TrucyNodes namespace, cleaning up all obsolete Matrix references.


### [2026-06-26] The "Director's Cut" Update: Precision & Performance
🛡️ New Feature: Trucy Image Bridge (5ch/10ch): Introduced a lossless image passthrough node designed to clean up complex workspaces.
Zero Overhead: Uses pure Python pointer pass-through. Consumes 0 MB of VRAM/RAM.
Smart Blockers: Features built-in disable_out boolean toggles powered by ComfyUI's native ExecutionBlocker. Turning a channel "OFF" will physically halt all downstream nodes (KSamplers, Video Encoders) connected to it, saving massive amounts of compute time during testing.
🔢 Trucy Text To Number Converter: Simplified the input mechanism. The node now features a direct text-input box (removed forceInput), allowing manual typing while still outputting perfectly extracted Strings, Integers, and Floats.
✨ Polish & Cleanup: Refined image_adapter.py by removing redundant boolean inputs from the Bridge nodes to keep the UI clean and strictly functional.

## 🚀 Core Modules

### 1. High-Fidelity Visual Fusion (Klein Nodes)
Designed specifically for **Flux2-Klein** model, allowing seamless blending of up to 10 image assets.
*   **TrucyKleinEncode**: 
    *   **Follow Node (W/H)**: Replicates the high-end alignment logic. Assets are projected onto a full-frame canvas for 1:1 spatial accuracy. (RSA is ignored).
    *   **Use RSA Scaling**: Performance mode. Only the `base_target` remains full resolution, while others are compressed via **RSA (Reference Square Area)** logic to double sampling speed.
    *   **Base Target System**: Designate any asset (e.g., `img5` for background) as the physical foundation for Latent/Mask output.

### 2. Recursive Logic & Batch Loops
*   **TrucyForLoop (Start / End)**: A high-performance recursive loop system.
    *   Supports **9 simultaneous data channels** (values 1-9) plus Flow and Index.
    *   Advanced range parsing (e.g., `1-3, 5, 10-12`).
    *   Synchronous state passing across iterations.

### 3. Industrial Toolkit (trucy_toolkit.py)
*   **Trucy Image Loader (String 5/10)**: Accepts IDs (e.g., "X1") or filenames directly. Smart matching ensures you find the right asset even with partial names.
*   **Trucy Text Splitter (5/10)**: Now supports **None (Direct Split)**. Split strings using delimiters (| , #) with or without bracket constraints.
*   **Trucy ID Extractor**: Snipe IDs from text. Newly upgraded to support **2-character IDs** (like `X1`) by making the 3rd slot optional.
*   **Trucy String Slicer**: Precise "surgical" text cutting using custom left/right delimiters.
*   **Trucy Asset Grid (5/10)**: Create low-VRAM thumbnail grids to preview your visual assets.

### 4. Smart Data & Media Handling
*   **TrucyExcelReader**: Load storyboard data from Excel. Features **Smart Number Extraction** (Regex-based) to grab parameters from messy text.
*   **TrucyImageAdapter**: The "Resolution Bridge." Perfect for **1088p -> 1080p** conversion with lossless center cropping or stretching.
*   **TrucyTxtBatchLoader**: Batch load TXT files by index. Ideal for feeding story scripts into loops.
*   **TrucyTxtPreviewAndSave**: A smart viewer/saver with auto-incrementing filenames and robust path fallback (saves to Documents if the drive is missing).

### 5. Audio & Video Production
*   **TrucyAudioLoaderIndex**: High-efficiency audio loading. Features **Auto-Resampling** (44.1k/48k) and a **1kHz Beep Fallback** for missing files.
*   **TrucyVideoCombine**: Direct FFmpeg pipe encoding. Zero intermediate files. Supports high-quality H.264 MP4, WebP, and GIF with audio muxing.

---

## 🛠️ Installation
1. `cd custom_nodes`
2. `git clone https://github.com/gnrsbassoutlook/ComfyUI-TrucyNodes.git`
3. Restart ComfyUI.

---

## 📄 License
MIT License