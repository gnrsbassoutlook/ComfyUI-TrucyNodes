# 🎬 ComfyUI-TrucyNodes
**The All-in-One Cinematic Suite for AI Storyboarding, Asset Fusion, and Production Logic.**

---

## 📖 Overview
ComfyUI-TrucyNodes is a professional toolkit designed for AI cinematography workflows. It bridges the gap between creative scriptwriting and final high-fidelity visual production. Whether you are managing hundreds of text prompts, merging complex character/scene assets with **Flux2-Klein**, or building recursive rendering loops, TrucyNodes provides the stability and precision required for industrial-grade production.

**[🇨🇳 中文说明](./README_CN.md)**

---

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