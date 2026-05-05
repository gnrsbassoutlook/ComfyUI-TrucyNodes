\# 🎬 ComfyUI-TrucyNodes

\*\*An Advanced Cinematic Suite for AI Storyboarding \& Visual Consistency\*\*



\[!\[GitHub Stars](https://img.shields.io/github/stars/gnrsbassoutlook/ComfyUI-TrucyNodes?style=social)](https://github.com/gnrsbassoutlook/ComfyUI-TrucyNodes)

\[!\[ComfyUI](https://img.shields.io/badge/ComfyUI-Plugin-blue)](https://github.com/comfyanonymous/ComfyUI)



\*\*\[🇨🇳 中文说明](./README\_CN.md)\*\*



ComfyUI-TrucyNodes is a professional-grade node set designed for AI Cinematography and Storyboarding. It is specifically built to solve the "Hallucination" and "Misalignment" issues in multi-asset fusion, particularly when using the \*\*Flux2-Klein\*\* model.



\---



\## 🔥 Core Node: TrucyKleinEncode (The Director's Palette)

This is the heart of the suite. It allows you to inject up to \*\*10 image assets\*\* (characters, props, backgrounds) into one scene with pixel-perfect spatial control.



\### 🛠️ Detailed Parameter Logic:



\- \*\*`width` \& `height`\*\* 📏: Sets the target canvas resolution.

&#x20;   - \*Note\*: For Flux2 models, it is highly recommended to use \*\*1088\*\* instead of 1080 to ensure the height is divisible by 16 for maximum model stability.



\- \*\*`main\_prompt\_ratio`\*\* ⚖️: Controls the power balance between your Text Prompt and Image Assets.

&#x20;   - Uses a non-linear influence formula: `8\*r\*(r-1) - 6\*r + 6`.

&#x20;   - \*\*0.5 (Default)\*\*: Perfect 1:1 balance. Mirroring the best settings from high-end specialized nodes.

&#x20;   - \*\*> 0.5\*\*: Favors the Text. Use this if the model is ignoring your action commands (e.g., "fighting," "jumping").

&#x20;   - \*\*< 0.5\*\*: Favors the Images. Use this if the character's face doesn't look enough like your asset.



\- \*\*`non\_base\_alignment`\*\* 🔄: \*\*\[The Performance Logic Switch]\*\*

&#x20;   - \*\*`Follow Node (W/H)`\*\*: 🚀 \*\*Ultra-Precision Mode\*\*. 

&#x20;       - Every image from `img1` to `img10` is internally placed on a full-frame black canvas matching the node's W/H. 

&#x20;       - This creates a \*\*1:1 physical coordinate system\*\* for every asset.

&#x20;       - \*\*RSA SETTINGS ARE COMPLETELY IGNORED\*\* in this mode. It provides the highest quality but consumes significantly more VRAM and sampling time.

&#x20;   - \*\*`Use RSA Scaling`\*\*: ⚡ \*\*Optimized Mode\*\*.

&#x20;       - Only the image selected in `base\_target` remains full resolution.

&#x20;       - All other "secondary" assets (like props or extra characters) are resized based on the \*\*RSA Value\*\*. This drastically reduces KSampler computation time (often by 50%+) while maintaining character likeness.



\- \*\*`rsa\_value`\*\* (Reference Square Area) 📐:

&#x20;   - \*\*Active ONLY when `non\_base\_alignment` is set to `Use RSA Scaling`\*\*.

&#x20;   - It defines the pixel area for secondary assets. 

&#x20;   - \*\*1024 (Default)\*\*: Balanced quality. 

&#x20;   - \*\*768 / 512\*\*: Lowers asset texture detail but makes the KSampler "fly."

&#x20;   - \*\*1280+\*\*: Near-perfect texture for secondary assets but increases sampling time.



\- \*\*`base\_target`\*\* 🎯:

&#x20;   - Defines which slot is the \*\*Physical Anchor\*\*.

&#x20;   - The selected image (usually `img5` for background) will be outputted through the pink `latent` port to the KSampler as the "base paint." 

&#x20;   - \*\*Crucial\*\*: The `base\_mask` only applies to the image selected here.



\- \*\*`img1` - `img10` \& `strengths`\*\* 🖼️:

&#x20;   - Strictly mapped input slots. If you connect a character to `img4`, use the tag `img4` in your prompt.

&#x20;   - Setting strength to \*\*0.0\*\* completely disables the slot, saving both VRAM and calculation cycles.



\---



\## 🖼️ TrucyImageAdapter (Resolution Bridge)

Bridges the gap between technical AI resolutions (\*\*1088p\*\*) and professional video standards (\*\*1080p\*\*).



\- \*\*`mode`\*\*:

&#x20;   - \*\*`Crop (Center)`\*\*: ✂️ The Gold Standard for 1088 -> 1080. It mathematically calculates the difference and shaves 4 pixels from the top and bottom. No stretching, no distortion—just pure 1:1 pixel mapping.

&#x20;   - \*\*`Stretch`\*\*: 🎨 Ignores aspect ratio and forces the image to fit the target W/H.



\---



\## 📊 TrucyExcelReader (Smart Production Loader)

Automates your storyboard workflow by reading script data from Excel files.



\- \*\*Windows Path Support\*\*: Automatically sanitizes paths copied from Windows Explorer (removing double quotes `""`).

\- \*\*Smart Number Extractor\*\*: Using Regex to find the \*\*first\*\* number (Int or Float) in a text block.

&#x20;   - \*Example\*: "Shot 01.25 sequence" -> Outputs \*\*1.25\*\* (float) and \*\*1\*\* (int).



\---



\## 🔊 Audio Suite (Sync \& Timing)

\- \*\*`Audio Detector \& Padder`\*\* ⏱️: Calculates exact frame counts based on FPS and audio length. Supports padding steps (e.g., 250ms) to ensure video rendering ends perfectly on a beat, avoiding audio desync.

\- \*\*`Empty Audio Generator`\*\* 🔇: Creates high-fidelity silence tracks (44.1kHz default) by seconds or frame counts. Essential for timing shots in a cinematic sequence.



\---



\## 📦 Installation \& Push

1\. Clone to `ComfyUI/custom\_nodes/ComfyUI-TrucyNodes`.

2\. Push updates to your repo:

```bash

git add .

git commit -m "feat: Detailed README and logic unification"

git push origin main

