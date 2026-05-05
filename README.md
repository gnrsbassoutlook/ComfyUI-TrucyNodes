\[\*\*中文版\*\*](./README\_CN.md) | \[\*\*English\*\*](./README.md)



\---

ComfyUI-TrucyNodes Manual

Advanced toolset for AI cinematography and professional visual storytelling, optimized for Flux2-Klein workflows.

🚀 Node Details

1\. TrucyKleinEncode

A high-precision conditioning node for merging up to 10 image assets into a single scene.

main\_prompt\_ratio: Balance between Text and Image. 0.5 is the default (1:1). >0.5 favors the prompt; <0.5 favors asset texture.

non\_base\_alignment:

Follow Node (W/H): Replicates the high-quality logic. Every asset (img1-10) is placed on a full-frame black canvas based on the node's width/height settings. RSA settings are ignored in this mode.

Use RSA Scaling: Performance mode. Only the base\_target image remains full resolution. Other assets are resized according to the rsa\_value, significantly increasing speed.

rsa\_value (Reference Square Area): Active only in Use RSA Scaling mode. Defines the pixel area for secondary assets. 1024 = 1024x1024 area.

base\_target: Designates which input (img1-10) is the background anchor for the output Latent and Mask.

img1-10 \& strengths: Image inputs and their respective multipliers. Setting strength to 0 disables the slot completely.

2\. TrucyImageAdapter

Bridges the gap between Flux (1088p) and standard Video HD (1080p).

Crop (Center): Recommended for 1088->1080. Cuts 4px from top and bottom. No distortion.

Stretch: Resizes image to fit target resolution exactly.

3\. TrucyExcelReader

Excel Path: Supports quoted paths from Windows Explorer.

Smart Number Extraction: Automatically extracts the first number found in the string. (e.g., "ID 05.5-v2" outputs 5.5).

4\. Audio Detector \& Padder

Calculates exact video frames from audio. Uses padding steps (e.g., 250ms) to ensure perfect sync between AI video and audio tracks.

