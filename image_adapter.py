import torch
import torch.nn.functional as F
import comfy.utils

class TrucyImageAdapter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "mode": (["Crop (Center)", "Stretch"], {"default": "Crop (Center)"}),
                "target_width": ("INT", {"default": 1920, "min": 64, "max": 8192, "step": 8}),
                "target_height": ("INT", {"default": 1080, "min": 64, "max": 8192, "step": 8}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "adapt_image"
    CATEGORY = "TrucyNodes/Image"

    def adapt_image(self, image, mode, target_width, target_height):
        # image 形状为 [Batch, Height, Width, Channels]
        _, current_h, current_w, _ = image.shape
        
        # 如果尺寸已经完全一致，直接跳过处理
        if current_h == target_height and current_w == target_width:
            return (image,)

        if mode == "Stretch":
            # 拉伸模式：不考虑比例，强行挤压/拉伸到目标尺寸
            samples = image.movedim(-1, 1) # 转为 [B, C, H, W]
            out = comfy.utils.common_upscale(samples, target_width, target_height, "bicubic", "disabled")
            return (out.movedim(1, -1),)

        else: # Crop (Center) 模式
            # 1. 先进行比例等缩放（如果宽度或高度比例不协调）
            samples = image.movedim(-1, 1)
            
            # 计算缩放比例，取大值以确保缩放后能覆盖目标区域
            width_ratio = target_width / current_w
            height_ratio = target_height / current_h
            scale_ratio = max(width_ratio, height_ratio)
            
            new_w = int(current_w * scale_ratio)
            new_h = int(current_h * scale_ratio)
            
            image_scaled = comfy.utils.common_upscale(samples, new_w, new_h, "bicubic", "disabled")
            image_scaled = image_scaled.movedim(1, -1)
            
            # 2. 居中裁切
            y_start = (new_h - target_height) // 2
            x_start = (new_w - target_width) // 2
            
            out = image_scaled[:, y_start:y_start + target_height, x_start:x_start + target_width, :]
            
            return (out,)

NODE_CLASS_MAPPINGS = {
    "TrucyImageAdapter": TrucyImageAdapter
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyImageAdapter": "Image Size Adapter (Trucy)"
}