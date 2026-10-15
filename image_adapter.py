import os
import re
import math
import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import comfy.utils

def _natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def _create_empty_tensor(style):
    if style == "Black":
        return torch.zeros((1, 512, 512, 3), dtype=torch.float32)
    elif style == "White":
        return torch.ones((1, 512, 512, 3), dtype=torch.float32)
    return None

# ========================================================
# 1. 图像索引加载器 (单图)
# ========================================================
class TrucyImageLoaderIndex:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory_path": ("STRING", {"default": "C:\\images"}),
                "index_mode": (["0-based (0,1,2...)", "1-based (1,2,3...)"], {"default": "0-based (0,1,2...)"}),
                "index": ("INT", {"default": 0, "min": 0, "max": 999999}),
                "sort_by": (["Natural / Alphabetical (A-Z)", "Creation Time (Oldest First)"], {"default": "Natural / Alphabetical (A-Z)"}),
                "skip_first": ("INT", {"default": 0, "min": 0, "max": 9999}),
                "load_cap": ("INT", {"default": -1, "min": -1, "max": 9999}),
                "empty_style": (["None", "Black", "White"], {"default": "None"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT", "STRING")
    RETURN_NAMES = ("image", "width", "height", "filename")
    FUNCTION = "load_image"
    CATEGORY = "TrucyNodes/Image"

    @classmethod
    def IS_CHANGED(cls, directory_path, **kwargs):
        path = directory_path.strip().replace('"', '')
        return os.path.getmtime(path) if os.path.isdir(path) else float("NaN")

    def load_image(self, directory_path, index_mode, index, sort_by, skip_first, load_cap, empty_style):
        clean_path = directory_path.strip().replace('"', '')
        valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff')
        files = []

        if os.path.isdir(clean_path):
            files = [f for f in os.listdir(clean_path) if f.lower().endswith(valid_exts)]
            if sort_by.startswith("Natural"):
                files.sort(key=_natural_sort_key)
            else:
                files.sort(key=lambda x: os.path.getctime(os.path.join(clean_path, x)))
            files = files[skip_first:]
            if load_cap != -1:
                files = files[:load_cap]

        actual_index = index if index_mode.startswith("0") else index - 1

        if not files or actual_index < 0 or actual_index >= len(files):
            print(f"[TrucyNodes] INFO: Image index {index} out of range. Style: {empty_style}")
            res_tensor = _create_empty_tensor(empty_style)
            w, h = (512, 512) if res_tensor is not None else (0, 0)
            return (res_tensor, w, h, "OUT_OF_RANGE")

        target_file = files[actual_index]
        file_path = os.path.join(clean_path, target_file)
        pure_name = os.path.splitext(target_file)[0]

        try:
            with Image.open(file_path) as img:
                img = ImageOps.exif_transpose(img).convert("RGB")
                img_np = np.array(img).astype(np.float32) / 255.0
                out_tensor = torch.from_numpy(img_np)[None,]
                return (out_tensor, img.width, img.height, pure_name)
        except Exception as e:
            print(f"[TrucyNodes] Image Load Error ({target_file}): {e}")
            res_tensor = _create_empty_tensor(empty_style)
            w, h = (512, 512) if res_tensor is not None else (0, 0)
            return (res_tensor, w, h, f"LOAD_ERROR_{pure_name}")

# ========================================================
# 2. 6通道图片批量加载器 (TrucyImageLoader6)
# ========================================================
class TrucyImageLoader6:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory_path": ("STRING", {"default": "C:\\images"}),
                "sort_by": (["Natural / Alphabetical (A-Z)", "Creation Time (Oldest First)"], {"default": "Natural / Alphabetical (A-Z)"}),
                "start_index": ("INT", {"default": 0, "min": 0, "max": 999999}),
                "empty_style": (["None", "Black", "White"], {"default": "None"}),
            }
        }

    RETURN_TYPES = ("IMAGE",) * 6
    RETURN_NAMES = tuple(f"img_{i}" for i in range(1, 7))
    FUNCTION = "load_images"
    CATEGORY = "TrucyNodes/Image"

    @classmethod
    def IS_CHANGED(cls, directory_path, **kwargs):
        path = directory_path.strip().replace('"', '')
        return os.path.getmtime(path) if os.path.isdir(path) else float("NaN")

    def load_images(self, directory_path, sort_by, start_index, empty_style):
        clean_path = directory_path.strip().replace('"', '')
        valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff')
        files = []

        if os.path.isdir(clean_path):
            files = [f for f in os.listdir(clean_path) if f.lower().endswith(valid_exts)]
            if sort_by.startswith("Natural"):
                files.sort(key=_natural_sort_key)
            else:
                files.sort(key=lambda x: os.path.getctime(os.path.join(clean_path, x)))
            files = files[start_index:start_index + 6]

        outputs = []
        for i in range(6):
            if i < len(files):
                file_path = os.path.join(clean_path, files[i])
                try:
                    with Image.open(file_path) as img:
                        img = ImageOps.exif_transpose(img).convert("RGB")
                        img_np = np.array(img).astype(np.float32) / 255.0
                        outputs.append(torch.from_numpy(img_np)[None,])
                except Exception:
                    outputs.append(_create_empty_tensor(empty_style))
            else:
                outputs.append(_create_empty_tensor(empty_style))

        return tuple(outputs)

# ========================================================
# 3. 图像分辨率适配器
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

    RETURN_TYPES, RETURN_NAMES = ("IMAGE",), ("image",)
    FUNCTION, CATEGORY = "adapt_image", "TrucyNodes/Image"

    def adapt_image(self, image, mode, target_width, target_height):
        if image is None:
            return (None,)
        _, current_h, current_w, _ = image.shape
        if current_h == target_height and current_w == target_width:
            return (image,)

        samples = image.movedim(-1, 1)
        if mode == "Stretch":
            out = comfy.utils.common_upscale(samples, target_width, target_height, "bicubic", "disabled")
            return (out.movedim(1, -1),)
        else:
            scale_ratio = max(target_width / current_w, target_height / current_h)
            new_w, new_h = int(current_w * scale_ratio), int(current_h * scale_ratio)
            image_scaled = comfy.utils.common_upscale(samples, new_w, new_h, "bicubic", "disabled").movedim(1, -1)
            y_start = (new_h - target_height) // 2
            x_start = (new_w - target_width) // 2
            return (image_scaled[:, y_start:y_start + target_height, x_start:x_start + target_width, :],)

# ========================================================
# 4. VLM 专用防粘连资产网格 (BaseTrucyGrid)
# ========================================================
class BaseTrucyGrid:
    def create_grid(self, thumbnail_size, columns, add_labels, label_empty, empty_placeholder, count, **kwargs):
        grid_items = []
        
        for i in range(1, count + 1):
            img_tensor = kwargs.get(f"img_{i}")
            if img_tensor is not None:
                t = img_tensor[0].cpu().numpy()
                pil_img = Image.fromarray(np.clip(255. * t, 0, 255).astype(np.uint8))
                grid_items.append({"idx": i, "img": pil_img, "is_placeholder": False})
            else:
                if empty_placeholder == "Black Placeholder":
                    ph_img = Image.new("RGB", (thumbnail_size, thumbnail_size), (0, 0, 0))
                    grid_items.append({"idx": i, "img": ph_img, "is_placeholder": True})
                elif empty_placeholder == "White Placeholder":
                    ph_img = Image.new("RGB", (thumbnail_size, thumbnail_size), (255, 255, 255))
                    grid_items.append({"idx": i, "img": ph_img, "is_placeholder": True})
                elif empty_placeholder == "Skip (Ignore)":
                    continue

        if not grid_items:
            return (torch.zeros((1, 512, 512, 3), dtype=torch.float32),)

        margin = 40
        cell_w, cell_h = thumbnail_size + margin, thumbnail_size + margin
        font_size = max(16, int(thumbnail_size * 0.08))
        label_h = int(font_size * 1.8) if add_labels else 0

        rows = math.ceil(len(grid_items) / columns)
        grid_img = Image.new('RGB', (columns * cell_w, rows * (cell_h + label_h)), color=(0, 0, 0))
        draw = ImageDraw.Draw(grid_img)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        for idx, item in enumerate(grid_items):
            r, c = idx // columns, idx % columns
            x_offset, y_offset = c * cell_w, r * (cell_h + label_h)
            pimg = item["img"]
            pimg.thumbnail((thumbnail_size, thumbnail_size), Image.Resampling.LANCZOS)
            paste_x = x_offset + (cell_w - pimg.width) // 2
            paste_y = y_offset + (cell_h - pimg.height) // 2

            # 绘制边框
            draw.rectangle([paste_x - 3, paste_y - 3, paste_x + pimg.width + 2, paste_y + pimg.height + 2], outline=(255, 255, 255), width=3)
            grid_img.paste(pimg, (paste_x, paste_y))

            # 标签写入逻辑：
            # 1. 真实图片：只要勾选了 add_labels 就会写字
            # 2. 空占位图：只有同时勾选了 add_labels 和 label_empty 时才会写字
            should_draw_label = add_labels and (not item["is_placeholder"] or label_empty)
            if should_draw_label:
                label_text = f"img{item['idx']}"
                text_w = draw.textbbox((0, 0), label_text, font=font)[2] if hasattr(draw, "textbbox") else len(label_text) * (font_size * 0.6)
                draw.text((x_offset + (cell_w - text_w) // 2, y_offset + cell_h), label_text, fill=(240, 240, 240), font=font)

        out_tensor = torch.from_numpy(np.array(grid_img).astype(np.float32) / 255.0).unsqueeze(0)
        return (out_tensor,)

class TrucyAssetGrid6(BaseTrucyGrid):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "thumbnail_size": ([256, 512, 768, 1024, 1280, 1920], {"default": 512}),
                "columns": ("INT", {"default": 6, "min": 1, "max": 6}),
                "add_labels": ("BOOLEAN", {"default": True}),
                "label_empty": ("BOOLEAN", {"default": False}),  # 开启则给空图也写上 imgX 标签，关闭则空图无字
                "empty_placeholder": (["Black Placeholder", "White Placeholder", "Skip (Ignore)"], {"default": "Black Placeholder"}),
            },
            "optional": {f"img_{i}": ("IMAGE",) for i in range(1, 7)}
        }
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("IMAGE",), ("Grid",), "run", "TrucyNodes/Image"
    def run(self, **kwargs): return self.create_grid(count=6, **kwargs)

class TrucyAssetGrid10(BaseTrucyGrid):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "thumbnail_size": ([256, 512, 768, 1024, 1280, 1920], {"default": 256}),
                "columns": ("INT", {"default": 5, "min": 1, "max": 10}),
                "add_labels": ("BOOLEAN", {"default": True}),
                "label_empty": ("BOOLEAN", {"default": False}),  # 开启则给空图也写上 imgX 标签，关闭则空图无字
                "empty_placeholder": (["Black Placeholder", "White Placeholder", "Skip (Ignore)"], {"default": "Black Placeholder"}),
            },
            "optional": {f"img_{i}": ("IMAGE",) for i in range(1, 11)}
        }
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("IMAGE",), ("Grid",), "run", "TrucyNodes/Image"
    def run(self, **kwargs): return self.create_grid(count=10, **kwargs)

# ========================================================
# 5. 纯图像无损直通桥接器
# ========================================================
class TrucyImageBridge6:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {"required": {}, "optional": {}}
        for i in range(1, 7):
            inputs["required"][f"pass_out_{i}"] = ("BOOLEAN", {"default": True, "label_on": f"Out {i} ON", "label_off": f"Out {i} OFF"})
            inputs["optional"][f"img{i}"] = ("IMAGE",)
        return inputs

    RETURN_TYPES = ("IMAGE",) * 6
    RETURN_NAMES = tuple(f"img{i}" for i in range(1, 7))
    FUNCTION, CATEGORY = "bridge", "TrucyNodes/Image"
    def bridge(self, **kwargs):
        return tuple(kwargs.get(f"img{i}") if kwargs.get(f"pass_out_{i}", True) else None for i in range(1, 7))

class TrucyImageBridge10:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {"required": {}, "optional": {}}
        for i in range(1, 11):
            inputs["required"][f"pass_out_{i}"] = ("BOOLEAN", {"default": True, "label_on": f"Out {i} ON", "label_off": f"Out {i} OFF"})
            inputs["optional"][f"img{i}"] = ("IMAGE",)
        return inputs

    RETURN_TYPES = ("IMAGE",) * 10
    RETURN_NAMES = tuple(f"img{i}" for i in range(1, 11))
    FUNCTION, CATEGORY = "bridge", "TrucyNodes/Image"
    def bridge(self, **kwargs):
        return tuple(kwargs.get(f"img{i}") if kwargs.get(f"pass_out_{i}", True) else None for i in range(1, 11))

# ========================================================
# 映射与注册
# ========================================================
NODE_CLASS_MAPPINGS = {
    "TrucyImageLoaderIndex": TrucyImageLoaderIndex,
    "TrucyImageLoader6": TrucyImageLoader6,
    "TrucyImageAdapter": TrucyImageAdapter,
    "TrucyAssetGrid6": TrucyAssetGrid6,
    "TrucyAssetGrid10": TrucyAssetGrid10,
    "TrucyImageBridge6": TrucyImageBridge6,
    "TrucyImageBridge10": TrucyImageBridge10
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyImageLoaderIndex": "🚀 Image Loader by Index (Trucy)",
    "TrucyImageLoader6": "🚀 Image Loader (6 Channels) (Trucy)",
    "TrucyImageAdapter": "🚀 Image Size Adapter (Trucy)",
    "TrucyAssetGrid6": "🚀 Trucy Asset Grid (6)",
    "TrucyAssetGrid10": "🚀 Trucy Asset Grid (10)",
    "TrucyImageBridge6": "🚀 Image Bridge (6ch) (Trucy)",
    "TrucyImageBridge10": "🚀 Image Bridge (10ch) (Trucy)"
}