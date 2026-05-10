import os
import re
import json
import math
import numpy as np
import torch
from PIL import Image, ImageOps, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo
import folder_paths

# ========================================================
# 核心工具函数
# ========================================================
def create_placeholder(style):
    if style == "White": return torch.ones((1, 512, 512, 3), dtype=torch.float32)
    else: return torch.zeros((1, 512, 512, 3), dtype=torch.float32)

def create_error_image(text_content):
    width, height = 512, 512
    img = Image.new('RGB', (width, height), color=(128, 128, 128))
    draw = ImageDraw.Draw(img)
    try: font = ImageFont.truetype("arial.ttf", 60)
    except: font = ImageFont.load_default()
    draw.text((20, 200), f"MISSING:\n{text_content}", fill=(255, 0, 0), font=font)
    image = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(image)[None,]

def load_image_file(file_path):
    try:
        img = Image.open(file_path).convert("RGB")
        img = ImageOps.exif_transpose(img)
        image = np.array(img).astype(np.float32) / 255.0
        return torch.from_numpy(image)[None,]
    except Exception as e:
        print(f"TrucyLoader Error: {e}")
        return None

# ========================================================
# Trucy 字符加载器基类
# ========================================================
class BaseTrucyLoaderDirect:
    def process_common(self, folder_path, empty_style, count, **kwargs):
        images = []
        for i in range(1, count + 1):
            inp = kwargs.get(f"img_txt_{i}", "0")
            inp_str = str(inp).strip()
            if inp_str == "0" or inp_str == "" or inp_str.lower() == "none":
                images.append(create_placeholder(empty_style))
                continue
            path = self.find_file_smart(folder_path, inp_str)
            if path:
                img = load_image_file(path)
                images.append(img if img is not None else create_error_image(f"Error Loading:\n{inp_str}"))
            else:
                images.append(create_error_image(inp_str))
        return tuple(images)

    def parse_id(self, text):
        match = re.match(r'^([a-zA-Z]+)(\d+)([a-zA-Z]?)$', text.strip())
        if match: return match.group(1).lower(), int(match.group(2)), match.group(3).lower()
        return None, None, None

    def parse_filename(self, filename):
        match = re.match(r'^([a-zA-Z]+)(\d+)([a-zA-Z]?)(?:[.\-_ \u4e00-\u9fa5].*)?$', filename)
        if match: return match.group(1).lower(), int(match.group(2)), match.group(3).lower()
        return None, None, None

    def find_file_smart(self, folder, input_str):
        if not os.path.exists(folder): return None
        input_str = input_str.strip()
        inp_prefix, inp_num, inp_suffix = self.parse_id(input_str)
        supported_exts = ["png", "jpg", "jpeg", "webp", "bmp"]
        try:
            all_files = sorted(os.listdir(folder))
            if inp_prefix is not None:
                candidates = []
                for filename in all_files:
                    if not any(filename.lower().endswith(ext) for ext in supported_exts): continue
                    f_prefix, f_num, f_suffix = self.parse_filename(os.path.splitext(filename)[0])
                    if f_prefix is None: continue
                    if (inp_prefix == f_prefix and inp_num == f_num and inp_suffix == f_suffix):
                        candidates.append(filename)
                if candidates:
                    candidates.sort(key=len)
                    return os.path.join(folder, candidates[0])
            direct_path = os.path.join(folder, input_str)
            if os.path.isfile(direct_path): return direct_path
            for ext in supported_exts:
                test_path = os.path.join(folder, f"{input_str}.{ext}")
                if os.path.exists(test_path): return test_path
            if inp_prefix is None: 
                for filename in all_files:
                    if filename.startswith(input_str) and any(filename.lower().endswith(ext) for ext in supported_exts):
                        return os.path.join(folder, filename)
        except Exception as e: print(f"TrucyLoader Error: {e}")
        return None

# ========================================================
# 具体节点实现
# ========================================================
class TrucyImageLoaderString5(BaseTrucyLoaderDirect):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "C:/Images/Assets", "multiline": False}),
                "empty_style": (["White", "Black"], {"default": "White"}),
            },
            "optional": {
                f"img_txt_{i}": ("STRING", {"default": "0", "multiline": False, "forceInput": True}) for i in range(1, 6)
            }
        }
    RETURN_TYPES = ("IMAGE",) * 5
    RETURN_NAMES = tuple(f"Img_{i}" for i in range(1, 6))
    FUNCTION = "process"
    CATEGORY = "TrucyNodes/Toolkit"
    def process(self, folder_path, empty_style, **kwargs):
        return self.process_common(folder_path, empty_style, 5, **kwargs)

class TrucyImageLoaderString10(BaseTrucyLoaderDirect):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "C:/Images/Assets", "multiline": False}),
                "empty_style": (["White", "Black"], {"default": "White"}),
            },
            "optional": {
                f"img_txt_{i}": ("STRING", {"default": "0", "multiline": False, "forceInput": True}) for i in range(1, 11)
            }
        }
    RETURN_TYPES = ("IMAGE",) * 10
    RETURN_NAMES = tuple(f"Img_{i}" for i in range(1, 11))
    FUNCTION = "process"
    CATEGORY = "TrucyNodes/Toolkit"
    def process(self, folder_path, empty_style, **kwargs):
        return self.process_common(folder_path, empty_style, 10, **kwargs)

class TrucyFolderIterator:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "C:/Images", "multiline": False}),
                "image_index": ("INT", {"default": 0, "min": 0, "max": 99999}),
                "filter_mode": (["Contains", "Not Contains"], {"default": "Contains"}),
                "filter_text": ("STRING", {"default": "", "multiline": False}),
                "extension": (["All", "png", "jpg", "jpeg", "webp", "bmp"], {"default": "All"}),
                "empty_style": (["White", "Black"], {"default": "White"}),
            }
        }
    RETURN_TYPES = ("IMAGE", "STRING", "INT")
    RETURN_NAMES = ("Image", "Filename", "Count")
    FUNCTION = "load"
    CATEGORY = "TrucyNodes/Toolkit"
    def load(self, folder_path, image_index, filter_mode, filter_text, extension, empty_style):
        if not os.path.exists(folder_path): return (create_placeholder(empty_style), "None", 0)
        files = os.listdir(folder_path)
        valid_exts = [".png", ".jpg", ".jpeg", ".webp", ".bmp"] if extension == "All" else [f".{extension}"]
        filtered = []
        for f in files:
            if not any(f.lower().endswith(ext) for ext in valid_exts): continue
            if filter_text:
                if (filter_mode == "Contains" and filter_text not in f) or (filter_mode == "Not Contains" and filter_text in f): continue
            filtered.append(f)
        if not filtered: return (create_placeholder(empty_style), "None", 0)
        filtered.sort()
        target = filtered[image_index % len(filtered)]
        img = load_image_file(os.path.join(folder_path, target))
        return (img if img is not None else create_error_image(target), target, len(filtered))

# 【升级】文本拆分器：支持无括号直接分割
class TrucyPromptSplitter5:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text_input": ("STRING", {"default": "", "multiline": True, "forceInput": True}),
                "bracket_style": (["None (Direct Split)", "[]", "{}", "()", "<>", "''", '""', "【】", "《》", "（）", "“”"], {"default": "None (Direct Split)"}),
                "separator": (["|", ",", "-", "_", "+", "=", "&", "@", "#", "$", "%", "^", "*", "~"], {"default": "|"}),
                "bracket_index": ("INT", {"default": 1, "min": 1, "max": 99}),
            },
        }
    RETURN_TYPES = ("STRING",) * 5
    RETURN_NAMES = tuple(f"Text_{i}" for i in range(1, 6))
    FUNCTION = "split"
    CATEGORY = "TrucyNodes/Toolkit"
    def split(self, text_input, bracket_style, separator, bracket_index):
        if bracket_style == "None (Direct Split)":
            parts = [p.strip() for p in text_input.split(separator)]
        else:
            left, right = bracket_style[0], bracket_style[1]
            matches = re.findall(f"{re.escape(left)}(.*?){re.escape(right)}", text_input, re.DOTALL)
            idx = bracket_index - 1
            parts = [p.strip() for p in matches[idx].split(separator)] if 0 <= idx < len(matches) else []
        final = ["0"] * 5
        for i in range(min(5, len(parts))): final[i] = parts[i] if parts[i] else "0"
        return tuple(final)

class TrucyPromptSplitter10(TrucyPromptSplitter5):
    RETURN_TYPES = ("STRING",) * 10
    RETURN_NAMES = tuple(f"Text_{i}" for i in range(1, 11))
    def split(self, text_input, bracket_style, separator, bracket_index):
        if bracket_style == "None (Direct Split)":
            parts = [p.strip() for p in text_input.split(separator)]
        else:
            left, right = bracket_style[0], bracket_style[1]
            matches = re.findall(f"{re.escape(left)}(.*?){re.escape(right)}", text_input, re.DOTALL)
            idx = bracket_index - 1
            parts = [p.strip() for p in matches[idx].split(separator)] if 0 <= idx < len(matches) else []
        final = ["0"] * 10
        for i in range(min(10, len(parts))): final[i] = parts[i] if parts[i] else "0"
        return tuple(final)

# 【升级】ID 提取器：第三位也可选 Ignore，支持 X1 这样的 2位 ID
class TrucyIDExtractor:
    @classmethod
    def INPUT_TYPES(s):
        t_req = ["Any (A-Z,0-9)", "Letter (A-Z)", "Upper (A-Z)", "Lower (a-z)", "Digit (0-9)"]
        t_opt = ["Ignore (End)"] + t_req
        return {
            "required": {
                "text_input": ("STRING", {"default": "", "multiline": True, "forceInput": True}),
                "search_mode": (["Auto (Smart 3-5 chars)", "Custom (Define Slots)"], {"default": "Auto (Smart 3-5 chars)"}),
                "match_index": ("INT", {"default": 1, "min": 1, "max": 99}),
                "remainder_length": ("INT", {"default": 0, "min": 0, "max": 9999}),
            },
            "optional": {
                "char_1_type": (t_req, {"default": "Any (A-Z,0-9)"}),
                "char_2_type": (t_req, {"default": "Any (A-Z,0-9)"}),
                "char_3_type": (t_opt, {"default": "Ignore (End)"}), # 升级点
                "char_4_type": (t_opt, {"default": "Ignore (End)"}),
                "char_5_type": (t_opt, {"default": "Ignore (End)"}),
            }
        }
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("ID", "Remainder", "Combined")
    FUNCTION = "extract"
    CATEGORY = "TrucyNodes/Toolkit"
    def get_reg(self, t):
        if "Ignore" in t: return ""
        if "Any" in t: return "[a-zA-Z0-9]"
        if "Letter" in t and "Upper" not in t and "Lower" not in t: return "[a-zA-Z]"
        if "Upper" in t: return "[A-Z]"
        if "Lower" in t: return "[a-z]"
        if "Digit" in t: return "[0-9]"
        return "."
    def extract(self, text_input, search_mode, match_index, remainder_length, char_1_type, char_2_type, char_3_type, char_4_type, char_5_type):
        matches = []
        if search_mode.startswith("Auto"):
            for m in re.finditer(r'[a-zA-Z0-9]+', text_input):
                if 2 <= len(m.group(0)) <= 5 and not m.group(0).isalpha(): matches.append(m)
        else:
            pat = f"({self.get_reg(char_1_type)}{self.get_reg(char_2_type)}{self.get_reg(char_3_type)}{self.get_reg(char_4_type)}{self.get_reg(char_5_type)})"
            matches = list(re.finditer(pat, text_input))
        idx = match_index - 1
        if 0 <= idx < len(matches):
            tm = matches[idx]
            ext_id = tm.group(0) if search_mode.startswith("Auto") else tm.group(1)
            rem = re.sub(r'^[ :：\-_.]+', '', text_input[tm.end():]).strip()
            if remainder_length > 0: rem = rem[:remainder_length]
            return (ext_id, rem, f"{ext_id} {rem}" if rem else ext_id)
        return ("0", "", "0")

class TrucyStringSlicer:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text_input": ("STRING", {"default": "", "multiline": True, "forceInput": True}),
                "left_delimiter": ("STRING", {"default": "-", "multiline": False}),
                "right_delimiter": ("STRING", {"default": "]", "multiline": False}),
                "match_index": ("INT", {"default": 1, "min": 1, "max": 99}),
                "include_delimiters": ("BOOLEAN", {"default": False}),
            }
        }
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("Middle", "L_Part", "R_Part", "L+R")
    FUNCTION = "chop"
    CATEGORY = "TrucyNodes/Toolkit"
    def chop(self, text_input, left_delimiter, right_delimiter, match_index, include_delimiters):
        if not text_input or not left_delimiter or not right_delimiter: return ("N/A",)*4
        pos = 0
        for _ in range(match_index):
            start = text_input.find(left_delimiter, pos)
            if start == -1: return ("N/A",)*4
            pos = start + len(left_delimiter)
        end = text_input.find(right_delimiter, pos)
        if end == -1: return ("N/A",)*4
        if include_delimiters:
            return (text_input[start : end + len(right_delimiter)], text_input[:start], text_input[end + len(right_delimiter):], text_input[:start] + text_input[end + len(right_delimiter):])
        else:
            return (text_input[pos : end], text_input[:start], text_input[end + len(right_delimiter):], text_input[:start] + text_input[end + len(right_delimiter):])

# ========================================================
# 其他工具：网格与数据集
# ========================================================
class BaseTrucyGrid:
    def create_grid(self, thumbnail_size, columns, add_labels, count, **kwargs):
        imgs = [(i, Image.fromarray(np.clip(255.*kwargs[f"img_{i}"][0].cpu().numpy(),0,255).astype(np.uint8))) for i in range(1, count+1) if kwargs.get(f"img_{i}") is not None]
        if not imgs: return (torch.zeros((1, 512, 512, 3)), )
        rows, cell = math.ceil(len(imgs)/columns), thumbnail_size
        text_h = 30 if add_labels else 0
        grid = Image.new('RGB', (columns * cell, rows * (cell + text_h)), (20,20,20))
        draw = ImageDraw.Draw(grid)
        try: font = ImageFont.truetype("arial.ttf", 20)
        except: font = ImageFont.load_default()
        for idx, (oidx, pimg) in enumerate(imgs):
            pimg.thumbnail((cell-10, cell-10))
            x, y = (idx % columns) * cell, (idx // columns) * (cell + text_h)
            grid.paste(pimg, (x + (cell - pimg.width)//2, y + (cell - pimg.height)//2 + text_h))
            if add_labels: draw.text((x + (cell - len(f"Img {oidx}")*10)//2, y + 5), f"Img {oidx}", fill=(200,200,200), font=font)
        return (torch.from_numpy(np.array(grid).astype(np.float32)/255.0).unsqueeze(0),)

class TrucyAssetGrid5(BaseTrucyGrid):
    @classmethod
    def INPUT_TYPES(s): return {"required": {"thumbnail_size": ("INT", {"default": 256, "min": 64, "max": 1024}), "columns": ("INT", {"default": 5, "min": 1, "max": 5}), "add_labels": ("BOOLEAN", {"default": True})}, "optional": {f"img_{i}": ("IMAGE",) for i in range(1,6)}}
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("IMAGE",), ("Grid",), "run", "TrucyNodes/Toolkit"
    def run(self, **kwargs): return self.create_grid(count=5, **kwargs)

class TrucyAssetGrid10(BaseTrucyGrid):
    @classmethod
    def INPUT_TYPES(s): return {"required": {"thumbnail_size": ("INT", {"default": 256, "min": 64, "max": 1024}), "columns": ("INT", {"default": 5, "min": 1, "max": 10}), "add_labels": ("BOOLEAN", {"default": True})}, "optional": {f"img_{i}": ("IMAGE",) for i in range(1,11)}}
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("IMAGE",), ("Grid",), "run", "TrucyNodes/Toolkit"
    def run(self, **kwargs): return self.create_grid(count=10, **kwargs)

class TrucyDatasetSaver:
    def __init__(self): self.output_dir = folder_paths.get_output_directory()
    @classmethod
    def INPUT_TYPES(s): return {"required": {"images": ("IMAGE",), "text": ("STRING", {"multiline": True, "forceInput": True}), "filename_prefix": ("STRING", {"default": "train_data/img"}), "format": (["png", "jpg", "webp"], {"default": "png"}), "quality": ("INT", {"default": 95, "min": 1, "max": 100})}, "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}}
    RETURN_TYPES, OUTPUT_NODE, FUNCTION, CATEGORY = (), True, "save", "TrucyNodes/Toolkit"
    def save(self, images, text, filename_prefix, format, quality, prompt=None, extra_pnginfo=None):
        out_folder, name, counter, sub, prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
        res = []
        for img in images:
            pimg = Image.fromarray(np.clip(255.*img.cpu().numpy(), 0, 255).astype(np.uint8))
            stem = f"{name}_{counter:05}_"
            if format == "png":
                meta = PngInfo()
                if prompt: meta.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo:
                    for x in extra_pnginfo: meta.add_text(x, json.dumps(extra_pnginfo[x]))
                pimg.save(os.path.join(out_folder, f"{stem}.png"), pnginfo=meta, compress_level=4)
            elif format == "jpg":
                if pimg.mode == 'RGBA': pimg = pimg.convert('RGB')
                pimg.save(os.path.join(out_folder, f"{stem}.jpg"), quality=quality, optimize=True)
            else: pimg.save(os.path.join(out_folder, f"{stem}.webp"), quality=quality)
            with open(os.path.join(out_folder, f"{stem}.txt"), 'w', encoding='utf-8') as f: f.write(text)
            res.append({"filename": f"{stem}.{format}", "subfolder": sub, "type": "output"})
            counter += 1
        return {"ui": {"images": res}}