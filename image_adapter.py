import torch
import torch.nn.functional as F
import comfy.utils
import os, math, numpy as np
from PIL import Image, ImageDraw, ImageFont

# ========================================================
# 1. 核心适配节点 (保持不变)
# ========================================================
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
        _, current_h, current_w, _ = image.shape
        if current_h == target_height and current_w == target_width:
            return (image,)
        if mode == "Stretch":
            samples = image.movedim(-1, 1)
            out = comfy.utils.common_upscale(samples, target_width, target_height, "bicubic", "disabled")
            return (out.movedim(1, -1),)
        else:
            samples = image.movedim(-1, 1)
            width_ratio = target_width / current_w
            height_ratio = target_height / current_h
            scale_ratio = max(width_ratio, height_ratio)
            new_w, new_h = int(current_w * scale_ratio), int(current_h * scale_ratio)
            image_scaled = comfy.utils.common_upscale(samples, new_w, new_h, "bicubic", "disabled")
            image_scaled = image_scaled.movedim(1, -1)
            y_start = (new_h - target_height) // 2
            x_start = (new_w - target_width) // 2
            out = image_scaled[:, y_start:y_start + target_height, x_start:x_start + target_width, :]
            return (out,)

# ========================================================
# 2. 资产拼接网关 (视觉增强版 V7 - 极细边框 & 标签紧贴)
# ========================================================
class BaseTrucyGrid:
    def create_grid(self, thumbnail_size, columns, add_labels, count, **kwargs):
        valid_imgs = []
        for i in range(1, count + 1):
            img = kwargs.get(f"img_{i}")
            if img is not None:
                pimg = Image.fromarray(np.clip(255. * img[0].cpu().numpy(), 0, 255).astype(np.uint8))
                valid_imgs.append((i, pimg))
        
        if not valid_imgs:
            return (torch.zeros((1, 512, 512, 3)),)

        cell_max = int(thumbnail_size)
        rows = math.ceil(len(valid_imgs) / columns)
        
        # --- 精调比例参数 ---
        border_thickness = max(1, int(cell_max * 0.015))  # 极细白色框 (再减 5%)
        margin = int(cell_max * 0.02)                    # 边缘留白
        spacing = int(cell_max * 0.15)                   # 图片间距
        font_size = int(cell_max * 0.10)                 # 字体大小
        text_area_height = int(font_size * 1.5) 
        text_offset_y = -int(cell_max * 0.05)            # 文字大幅上提，紧贴相框
        
        # 缩放图片
        processed_data = []
        for orig_idx, pimg in valid_imgs:
            pimg.thumbnail((cell_max - border_thickness*2, cell_max - border_thickness*2), Image.Resampling.LANCZOS)
            processed_data.append((orig_idx, pimg))

        # 计算画布 (深墨绿色底: 0, 50, 0)
        grid_w = (columns * cell_max) + ((columns - 1) * spacing) + (2 * margin)
        grid_h = (rows * (cell_max + text_area_height)) + ((rows - 1) * spacing) + (2 * margin)
        
        grid = Image.new('RGB', (grid_w, grid_h), (0, 50, 0))
        draw = ImageDraw.Draw(grid)
        
        try:
            font_paths = ["arial.ttf", "msyh.ttc", "DejaVuSans.ttf"]
            font = None
            for p in font_paths:
                try: font = ImageFont.truetype(p, font_size); break
                except: continue
            if font is None: font = ImageFont.load_default()
        except: font = ImageFont.load_default()

        for idx, (original_idx, pimg) in enumerate(processed_data):
            row, col = idx // columns, idx % columns
            cell_x = margin + (col * (cell_max + spacing))
            cell_y = margin + (row * (cell_max + text_area_height + spacing))
            
            bw, bh = pimg.width + border_thickness * 2, pimg.height + border_thickness * 2
            bx = cell_x + (cell_max - bw) // 2
            by = cell_y + (cell_max - bh) // 2
            
            # 绘制白色相框
            draw.rectangle([bx, by, bx + bw, by + bh], fill=(255, 255, 255))
            grid.paste(pimg, (bx + border_thickness, by + border_thickness))
            
            # 绘制标签 (白色字体)
            if add_labels:
                label_txt = f"img{original_idx}"
                tw = draw.textlength(label_txt, font=font) if hasattr(draw, "textlength") else font_size * 2
                tx = cell_x + (cell_max - tw) // 2
                ty = cell_y + cell_max + text_offset_y
                draw.text((tx, ty), label_txt, fill=(255, 255, 255), font=font)

        result = torch.from_numpy(np.array(grid).astype(np.float32) / 255.0).unsqueeze(0)
        return (result,)

class TrucyAssetGrid5(BaseTrucyGrid):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "thumbnail_size": (["256", "512", "768", "1024", "1280", "1920"], {"default": "512"}),
                "columns": ("INT", {"default": 5, "min": 1, "max": 10}),
                "add_labels": ("BOOLEAN", {"default": True}),
            },
            "optional": {f"img_{i}": ("IMAGE",) for i in range(1, 6)}
        }
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "run"
    CATEGORY = "TrucyNodes/Image"
    def run(self, **kwargs): return self.create_grid(count=5, **kwargs)

class TrucyAssetGrid10(BaseTrucyGrid):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "thumbnail_size": (["256", "512", "768", "1024", "1280", "1920"], {"default": "512"}),
                "columns": ("INT", {"default": 5, "min": 1, "max": 20}),
                "add_labels": ("BOOLEAN", {"default": True}),
            },
            "optional": {f"img_{i}": ("IMAGE",) for i in range(1, 11)}
        }
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "run"
    CATEGORY = "TrucyNodes/Image"
    def run(self, **kwargs): return self.create_grid(count=10, **kwargs)

NODE_CLASS_MAPPINGS = {
    "TrucyImageAdapter": TrucyImageAdapter,
    "TrucyAssetGrid5": TrucyAssetGrid5,
    "TrucyAssetGrid10": TrucyAssetGrid10
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyImageAdapter": "Image Size Adapter (Trucy)",
    "TrucyAssetGrid5": "🚀 Asset Grid (5ch) (Trucy)",
    "TrucyAssetGrid10": "🚀 Asset Grid (10ch) (Trucy)"
}