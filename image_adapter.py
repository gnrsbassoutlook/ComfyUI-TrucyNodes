import torch
import torch.nn.functional as F
import numpy as np
import math
from PIL import Image, ImageDraw, ImageFont, ImageOps
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
            image_scaled = comfy.utils.common_upscale(samples, new_w, new_h, "bicubic", "disabled").movedim(1, -1)
            y_start = (new_h - target_height) // 2
            x_start = (new_w - target_width) // 2
            return (image_scaled[:, y_start:y_start + target_height, x_start:x_start + target_width, :],)


# ========================================================
# 🚀 智能防粘连网格拼图基类 (专为 VLM 识别优化)
# ========================================================
class BaseTrucyGrid:
    def create_grid(self, thumbnail_size, columns, add_labels, count, **kwargs):
        valid_images = []
        for i in range(1, count + 1):
            img_tensor = kwargs.get(f"img_{i}")
            if img_tensor is not None:
                t = img_tensor[0].cpu().numpy()
                pil_img = Image.fromarray(np.clip(255. * t, 0, 255).astype(np.uint8))
                valid_images.append((i, pil_img))

        if not valid_images:
            return (torch.zeros((1, 512, 512, 3)),)

        # 核心尺寸计算 (增加 40px 物理安全带)
        margin = 40
        cell_w = thumbnail_size + margin
        cell_h = thumbnail_size + margin
        
        # 自适应字体大小计算 (最舒适的比例)
        font_size = max(16, int(thumbnail_size * 0.08))
        label_h = int(font_size * 1.8) if add_labels else 0

        rows = math.ceil(len(valid_images) / columns)
        grid_w = columns * cell_w
        grid_h = rows * (cell_h + label_h)

        # 创建纯黑背景，这是 VLM 最喜欢的背景色，能形成高对比度
        grid_img = Image.new('RGB', (grid_w, grid_h), color=(0, 0, 0))
        draw = ImageDraw.Draw(grid_img)

        # 尝试加载标准字体
        try: font = ImageFont.truetype("arial.ttf", font_size)
        except: font = ImageFont.load_default()

        for idx, (original_idx, pimg) in enumerate(valid_images):
            r = idx // columns
            c = idx % columns
            
            # 计算当前格子的左上角坐标
            x_offset = c * cell_w
            y_offset = r * (cell_h + label_h)

            # 等比例缩放图片，使其长边不超过设定尺寸
            pimg.thumbnail((thumbnail_size, thumbnail_size), Image.Resampling.LANCZOS)
            
            # 计算图片居中位置
            paste_x = x_offset + (cell_w - pimg.width) // 2
            paste_y = y_offset + (cell_h - pimg.height) // 2

            # 【防粘连白框】：在图片外围画一圈 3 像素宽的白色亮框
            border_rect = [paste_x - 3, paste_y - 3, paste_x + pimg.width + 2, paste_y + pimg.height + 2]
            draw.rectangle(border_rect, outline=(255, 255, 255), width=3)

            # 粘贴原图
            grid_img.paste(pimg, (paste_x, paste_y))

            # 【智能 Label】：绘制巨大的 imgX 标签，水平居中对齐在图片下方
            if add_labels:
                label_text = f"img{original_idx}"
                # 兼容不同 PIL 版本的文本测宽
                if hasattr(draw, "textbbox"):
                    text_w = draw.textbbox((0, 0), label_text, font=font)[2]
                else:
                    text_w = len(label_text) * (font_size * 0.6)
                
                text_x = x_offset + (cell_w - text_w) // 2
                text_y = y_offset + cell_h
                draw.text((text_x, text_y), label_text, fill=(240, 240, 240), font=font)

        # 导出为张量
        output_tensor = torch.from_numpy(np.array(grid_img).astype(np.float32) / 255.0).unsqueeze(0)
        return (output_tensor,)

class TrucyAssetGrid5(BaseTrucyGrid):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                # 经典分辨率下拉菜单，防傻瓜式输入
                "thumbnail_size": ([256, 512, 768, 1024, 1280, 1920], {"default": 512}),
                "columns": ("INT", {"default": 5, "min": 1, "max": 5}),
                "add_labels": ("BOOLEAN", {"default": True}),
            },
            "optional": {f"img_{i}": ("IMAGE",) for i in range(1, 6)}
        }
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("IMAGE",), ("Grid",), "run", "TrucyNodes/Image"
    def run(self, **kwargs): return self.create_grid(count=5, **kwargs)

class TrucyAssetGrid10(BaseTrucyGrid):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "thumbnail_size": ([256, 512, 768, 1024, 1280, 1920], {"default": 256}),
                "columns": ("INT", {"default": 5, "min": 1, "max": 10}),
                "add_labels": ("BOOLEAN", {"default": True}),
            },
            "optional": {f"img_{i}": ("IMAGE",) for i in range(1, 11)}
        }
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("IMAGE",), ("Grid",), "run", "TrucyNodes/Image"
    def run(self, **kwargs): return self.create_grid(count=10, **kwargs)

NODE_CLASS_MAPPINGS = {
    "TrucyImageAdapter": TrucyImageAdapter,
    "TrucyAssetGrid5": TrucyAssetGrid5,
    "TrucyAssetGrid10": TrucyAssetGrid10
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyImageAdapter": "🚀 Image Size Adapter (Trucy)",
    "TrucyAssetGrid5": "🚀 Trucy Asset Grid (5)",
    "TrucyAssetGrid10": "🚀 Trucy Asset Grid (10)"
}