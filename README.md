# 🎬 ComfyUI-TrucyNodes
**Advanced Cinematic Suite for AI Storyboarding & High-Fidelity Visual Consistency**

---

## 📖 Overview
ComfyUI-TrucyNodes is a professional-grade toolkit designed for high-end AI cinematography. It specializes in solving the "Asset Fusion" challenge where multiple characters, props, and environments must be merged into a single, cohesive shot. Specifically optimized for **Flux2-Klein** and advanced image-to-video pipelines.

**[🇨🇳 中文说明](./README_CN.md)**

---

## 🚀 Core Node: TrucyKleinEncode (The Fusion Director)
This is the flagship node of the suite. It manages the complex logic of injecting up to **10 different image assets** into the latent space while maintaining strict spatial control.

### 🛠️ Detailed Parameter Definitions:

*   **`width` & `height`** 📏:
    *   Defines the global canvas resolution. 
    *   *Cinematography Tip*: For Flux-based models, always use **1088** for height. It ensures 16-pixel alignment, preventing sampling errors and artifacts.

*   **`main_prompt_ratio`** ⚖️:
    *   **The Power Scale**: Controls the balance between your text instructions and visual assets.
    *   **Logic**: Uses the non-linear formula `8*r*(r-1) - 6*r + 6`.
    *   **0.5 (Default)**: Perfect 1:1 parity between text and images.
    *   **> 0.5**: Favors the **Text Prompt**. Use this if the model ignores actions (e.g., "screaming," "running").
    *   **< 0.5**: Favors the **Asset Texture**. Use this if the character's likeness is drifting from the reference.

*   **`non_base_alignment`** 🔄: **[The Engine Selector]**
    *   **`Follow Node (W/H)`**: 🚀 **High-Fidelity Mode**.
        *   **Logic**: Every connected asset (`img1-10`) is internally projected onto a full-frame black canvas matching your global width/height.
        *   **RSA Logic**: In this mode, **RSA (Reference Square Area) settings are COMPLETELY IGNORED**.
        *   **Result**: 1:1 spatial coordinate mapping for all assets. Best for complex scenes where every prop must be exactly positioned.
    *   **`Use RSA Scaling`**: ⚡ **Performance Mode**.
        *   **Logic**: Only the asset selected in `base_target` remains at full resolution. 
        *   **RSA Logic**: **The RSA Value is ACTIVATED** for all other secondary assets.
        *   **Result**: Dramatically faster sampling speeds (up to 50% faster) and lower VRAM usage by compressing secondary asset tokens.

*   **`rsa_value` (Reference Square Area)** 📐:
    *   **Status**: Active **ONLY** during `Use RSA Scaling` mode.
    *   **Function**: Defines the pixel area limit for secondary assets. 
    *   **Values**: **1024** is the sweet spot. Lower values (768/512) increase speed further; higher values (1280+) preserve more fine texture on secondary characters.

*   **`base_target`** 🎯:
    *   Designates the "Anchor Asset." Typically, you should select your background (e.g., `img5`).
    *   This selected image becomes the physical foundation for the Latent output.
    *   **Important**: The `base_mask` input is strictly bound to the asset chosen here.

*   **`img1` - `img10` & `strengths`** 🖼️:
    *   **Hard-Coded Mapping**: If you plug a character into the `img4` port, you **must** use the tag `img4` in your prompt.
    *   **Optimization**: Setting a strength to **0.0** completely severs the connection, ensuring zero computational cost for that slot.

---

## 🖼️ TrucyImageAdapter (Resolution Bridge)
Bridges the gap between AI generation standards (**1088p**) and professional video industry standards (**1080p**).

*   **`mode` Options**:
    *   **`Crop (Center)`** ✂️: **[Recommended]** Calculates the exact 8-pixel difference and removes 4px from the top and 4px from the bottom. This ensures 1:1 pixel accuracy with **zero distortion or stretching**.
    *   **`Stretch`** 🎨: Forcibly resizes the image to the target dimensions regardless of original proportions.

---

## 📊 TrucyExcelReader (Script-to-Asset Pipeline)
Automates the storyboard process by ingesting script data directly from Excel.

*   **Quoted Path Support**: Automatically strips double quotes (`""`) from paths, allowing you to "Copy as Path" directly from Windows Explorer into the node.
*   **Smart Extraction**: Uses Regex to find the **first valid number** in any string. 
    *   *Example*: Input "Scene_05.5_Final" -> Outputs Float: **5.5** | Int: **5**.

---

## 🔊 Audio Synchronization Tools
*   **`Audio Detector & Padder`** ⏱️: Calculates the exact frame requirements based on FPS. It features "Stepped Padding" (e.g., 250ms/500ms), ensuring the AI video length aligns perfectly with musical or rhythmic beats to prevent sync-drift.
*   **`Empty Audio Generator`** 🔇: Generates high-fidelity silent tracks (44.1kHz). Used for cinematic timing or as placeholders in complex video sequences.

---

### 5. Text Asset Management (TXT Nodes) 📄
A powerful suite for handling storyboards, scripts, and prompt sequences.

*   **TrucyTxtBatchLoader**:
    *   **Logic**: Scans a directory for `.txt` files.
    *   **Sorting**: Supports `Alphabetical (A-Z)` and `Creation Time (Oldest First)`.
    *   **Indexing**: Use the `index` to select a specific file (ideal for batch loops).
    *   **Outputs**: 
        1. `selected_content`: Text from the chosen file.
        2. `selected_filename`: The name of the file (without extension).
        3. `merged_content`: All files in the folder merged into one string (separated by empty lines).
        4. `merged_with_headers`: All files merged with their filenames as headers.
    *   **Auto-Update**: Built-in `IS_CHANGED` logic ensures the data refreshes instantly when you modify files externally.

*   **TrucyTxtPreviewAndSave**:
    *   **Preview**: Displays the input text directly on the node UI.
    *   **Smart Saving**: 
        - Separate inputs for `directory_path` and `file_name`.
        - **Auto-Increment**: If a file exists, it adds `_1`, `_2` to prevent overwriting.
        - **Robust Fallback**: If the target path is invalid (e.g., wrong drive letter), it automatically saves to `Documents/TrucyNodes_Output`.
    *   **Encoding**: Switchable between `UTF-8` and `ANSI (GBK)` for downstream software compatibility.

### 6. Audio Loader by Index 🎵
Designed for high-performance audio handling in cinematic workflows.

*   **Efficiency**: Unlike standard loaders, it only reads the **specific file** requested by the `index`, drastically reducing memory usage.
*   **Multi-Format**: Supports `.mp3`, `.wav`, `.flac`, `.ogg`, `.m4a`, etc.
*   **Auto-Resampling**: Built-in high-quality resampler (44.1k, 48k, etc.) to ensure all audio clips match your video project requirements.
*   **Safety Fallback**: If the `index` is out of bounds or the folder is empty, the node generates a **1-second 1kHz Sine Wave (Beep)** instead of crashing your workflow.

## 🛠️ Installation & Maintenance

1.  Navigate to `ComfyUI/custom_nodes/`.
2.  Clone the repository:
    ```bash
    git clone https://github.com/gnrsbassoutlook/ComfyUI-TrucyNodes.git
    ```
3.  **To Push your local changes to GitHub**:
    ```bash
    git add .
    git commit -m "docs: Comprehensive industrial-grade manual update"
    git push origin main
    ```

---

## 📄 License
MIT License