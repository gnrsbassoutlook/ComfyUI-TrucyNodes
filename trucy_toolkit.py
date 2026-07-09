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
def extract_numbers(text):
    if not text or text.strip() == "": return 0, 0.0
    match = re.search(r"[-+]?\d*\.\d+|[-+]?\d+", text)
    if match:
        num_str = match.group()
        try:
            f = float(num_str)
            return int(f), f
        except: return 0, 0.0
    return 0, 0.0

def create_placeholder(style):
    return torch.ones((1, 512, 512, 3)) if style == "White" else torch.zeros((1, 512, 512, 3))

def create_error_image(txt):
    img = Image.new('RGB', (512, 512), (128, 128, 128))
    try: font = ImageFont.truetype("arial.ttf", 40)
    except: font = ImageFont.load_default()
    ImageDraw.Draw(img).text((20, 200), f"MISSING:\n{txt}", (255, 0, 0), font=font)
    return torch.from_numpy(np.array(img).astype(np.float32) / 255.0)[None,]

def load_image_file(path):
    try:
        img = ImageOps.exif_transpose(Image.open(path).convert("RGB"))
        return torch.from_numpy(np.array(img).astype(np.float32) / 255.0)[None,]
    except: return None

# ========================================================
# 1. 🚀 字符加载器基类及节点 (String 5 / 10) - 增强精准匹配
# ========================================================
class BaseTrucyLoaderDirect:
    def process_common(self, folder_path, empty_style, count, **kwargs):
        images = []
        for i in range(1, count + 1):
            inp = str(kwargs.get(f"img_txt_{i}", "0")).strip()
            if inp in ["0", "", "none", "None"]:
                images.append(create_placeholder(empty_style))
                continue
            path = self.find_file_smart(folder_path.strip().replace('"', ''), inp)
            if path:
                img = load_image_file(path)
                images.append(img if img is not None else create_error_image(inp))
            else:
                images.append(create_error_image(inp))
        return tuple(images)

    def parse_id(self, text):
        # 严格解析出 前缀、数字、后缀字母
        match = re.match(r'^([a-zA-Z]+)(\d+)([a-zA-Z]?)$', text.strip())
        if match: 
            return match.group(1).lower(), int(match.group(2)), match.group(3).lower()
        return None, None, None

    def parse_filename(self, filename):
        # 解析文件名，支持 X1, X1a, X1-描述 等格式
        match = re.match(r'^([a-zA-Z]+)(\d+)([a-zA-Z]?)(?:[.\-_ \u4e00-\u9fa5].*)?$', filename)
        if match: 
            return match.group(1).lower(), int(match.group(2)), match.group(3).lower()
        return None, None, None

    def find_file_smart(self, folder, input_str):
        if not os.path.exists(folder): return None
        supported_exts = [".png", ".jpg", ".jpeg", ".webp", ".bmp"]
        input_str = input_str.strip()
        
        # 1. 第一优先级：绝对精确匹配 (假设用户输入就是完整文件名不带后缀)
        for ext in supported_exts:
            exact_path = os.path.join(folder, f"{input_str}{ext}")
            if os.path.isfile(exact_path): 
                return exact_path

        # 如果输入带有后缀，直接测试绝对路径
        direct_path = os.path.join(folder, input_str)
        if os.path.isfile(direct_path): 
            return direct_path

        # 2. 第二优先级：智能解析匹配 (解决 X1 和 X1a 的冲突)
        inp_prefix, inp_num, inp_suffix = self.parse_id(input_str)
        
        try:
            all_files = sorted(os.listdir(folder))
            if inp_prefix is not None:
                candidates = []
                for filename in all_files:
                    if not any(filename.lower().endswith(ext) for ext in supported_exts): 
                        continue
                    
                    name_stem = os.path.splitext(filename)[0]
                    f_prefix, f_num, f_suffix = self.parse_filename(name_stem)
                    
                    if f_prefix is None: 
                        continue
                    
                    # 【核心修复】：必须前缀、数字、后缀 *三个要素完全一致* 才算匹配！
                    # 如果你输入 X1 (suffix=""), 遇到 X1a (f_suffix="a") 时，这里的条件将判定为 False！
                    if (inp_prefix == f_prefix and inp_num == f_num and inp_suffix == f_suffix):
                        candidates.append(filename)
                        
                if candidates:
                    # 如果有多个候选（比如 X1.png 和 X1-描述.png），优先选名字最短的（即最纯粹的那个）
                    candidates.sort(key=len)
                    return os.path.join(folder, candidates[0])

            # 3. 第三优先级：降级模糊匹配 (仅当以上都不符合时)
            # 为了防止 X1 错误匹配到 X10 或 X1a，我们在匹配时要求必须遇到分隔符
            for filename in all_files:
                if any(filename.lower().endswith(ext) for ext in supported_exts):
                    name_stem = os.path.splitext(filename)[0]
                    # 只有当文件名恰好等于输入，或者输入之后紧跟的是分隔符/空格时才匹配
                    if name_stem == input_str or name_stem.startswith(input_str + "-") or name_stem.startswith(input_str + "_") or name_stem.startswith(input_str + " "):
                        return os.path.join(folder, filename)

        except Exception as e: 
            print(f"TrucyLoader Error: {e}")
            
        return None

class TrucyImageLoaderString5(BaseTrucyLoaderDirect):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {"folder_path": ("STRING", {"default": "C:/Images"}), "empty_style": (["White", "Black"],)},
            "optional": {f"img_txt_{i}": ("STRING", {"forceInput": True, "default": "0"}) for i in range(1, 6)}
        }
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("IMAGE",)*5, tuple(f"Img_{i}" for i in range(1, 6)), "run", "TrucyNodes/Toolkit"
    def run(self, folder_path, empty_style, **kwargs): return self.process_common(folder_path, empty_style, 5, **kwargs)

class TrucyImageLoaderString10(BaseTrucyLoaderDirect):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {"folder_path": ("STRING", {"default": "C:/Images"}), "empty_style": (["White", "Black"],)},
            "optional": {f"img_txt_{i}": ("STRING", {"forceInput": True, "default": "0"}) for i in range(1, 11)}
        }
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("IMAGE",)*10, tuple(f"Img_{i}" for i in range(1, 11)), "run", "TrucyNodes/Toolkit"
    def run(self, folder_path, empty_style, **kwargs): return self.process_common(folder_path, empty_style, 10, **kwargs)

# ========================================================
# 2. 🚀 智能文本拆分器系列 (15路 / 30路全口径输出)
# ========================================================
TRUCY_SEPARATORS = ["|", "#", "@", "$", "%", "&", "*", "~", "!", "^", "(", ")", "-", "_", "+", "=", "{", "}", "[", "]", "<", ">", ":", ";", ",", ".", "/", "\\"]

class BaseTrucySplitter:
    def split_logic(self, text_input, bracket_style, separator, bracket_index, count):
        if not text_input: return tuple([""]*count + [0]*count + [0.0]*count)
        
        if bracket_style == "None (Direct Split)":
            parts = [p.strip() for p in text_input.split(separator)]
        else:
            left, right = bracket_style[0], bracket_style[1]
            matches = re.findall(f"{re.escape(left)}(.*?){re.escape(right)}", text_input, re.DOTALL)
            idx = bracket_index - 1
            parts = [p.strip() for p in matches[idx].split(separator)] if 0 <= idx < len(matches) else []

        s_out, i_out, f_out = [], [], []
        for i in range(count):
            seg = parts[i] if i < len(parts) else ""
            num_i, num_f = extract_numbers(seg)
            s_out.append(seg)
            i_out.append(num_i)
            f_out.append(num_f)
        return tuple(s_out + i_out + f_out)

class TrucyPromptSplitter5(BaseTrucySplitter):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text_input": ("STRING", {"forceInput": True}),
                "bracket_style": (["None (Direct Split)", "[]", "{}", "()", "<>", "【】", "《》", "（）", "“”"], {"default": "None (Direct Split)"}),
                "separator": (TRUCY_SEPARATORS, {"default": "|"}),
                "bracket_index": ("INT", {"default": 1, "min": 1}),
            }
        }
    RETURN_TYPES = ("STRING",)*5 + ("INT",)*5 + ("FLOAT",)*5
    RETURN_NAMES = tuple([f"Text_{i}" for i in range(1, 6)] + [f"Int_{i}" for i in range(1, 6)] + [f"Float_{i}" for i in range(1, 6)])
    FUNCTION, CATEGORY = "run", "TrucyNodes/Toolkit"
    def run(self, **kwargs): return self.split_logic(count=5, **kwargs)

class TrucyPromptSplitter10(BaseTrucySplitter):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text_input": ("STRING", {"forceInput": True}),
                "bracket_style": (["None (Direct Split)", "[]", "{}", "()", "<>", "【】", "《》", "（）", "“”"], {"default": "None (Direct Split)"}),
                "separator": (TRUCY_SEPARATORS, {"default": "|"}),
                "bracket_index": ("INT", {"default": 1, "min": 1}),
            }
        }
    RETURN_TYPES = ("STRING",)*10 + ("INT",)*10 + ("FLOAT",)*10
    RETURN_NAMES = tuple([f"Text_{i}" for i in range(1, 11)] + [f"Int_{i}" for i in range(1, 11)] + [f"Float_{i}" for i in range(1, 11)])
    FUNCTION, CATEGORY = "run", "TrucyNodes/Toolkit"
    def run(self, **kwargs): return self.split_logic(count=10, **kwargs)


# ========================================================
# 3. 🚀 ID 提取器 (支持 2位 到 5位 智能识别)
# ========================================================
class TrucyIDExtractor:
    @classmethod
    def INPUT_TYPES(s):
        t_req = ["Any (A-Z,0-9)", "Letter (A-Z)", "Upper (A-Z)", "Lower (a-z)", "Digit (0-9)"]
        t_opt = ["Ignore (End)"] + t_req
        return {
            "required": {
                "text_input": ("STRING", {"forceInput": True}),
                "search_mode": (["Auto (Smart 2-5 chars)", "Custom (Define Slots)"], {"default": "Auto (Smart 2-5 chars)"}),
                "match_index": ("INT", {"default": 1, "min": 1}),
                "remainder_length": ("INT", {"default": 0, "min": 0}),
            },
            "optional": {f"char_{i}_type": (t_req if i<3 else t_opt, {"default": "Any (A-Z,0-9)" if i<3 else "Ignore (End)"}) for i in range(1, 6)}
        }
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("STRING", "STRING", "STRING"), ("ID", "Remainder", "Combined"), "run", "TrucyNodes/Toolkit"

    def run(self, text_input, search_mode, match_index, remainder_length, **kwargs):
        matches = []
        if search_mode.startswith("Auto"):
            for m in re.finditer(r'[a-zA-Z0-9]+', text_input):
                val = m.group(0)
                if 2 <= len(val) <= 5 and not val.isalpha(): matches.append(m)
        else:
            def g(t):
                if "Ignore" in t: return ""
                if "Digit" in t: return "[0-9]"
                if "Upper" in t: return "[A-Z]"
                if "Lower" in t: return "[a-z]"
                if "Letter" in t: return "[a-zA-Z]"
                return "[a-zA-Z0-9]"
            pat = f"({''.join([g(kwargs.get(f'char_{i}_type', 'Ignore (End)')) for i in range(1, 6)])})"
            matches = list(re.finditer(pat, text_input))
        
        idx = match_index - 1
        if 0 <= idx < len(matches):
            m = matches[idx]
            ext_id = m.group(1) if "Custom" in search_mode else m.group(0)
            rem = re.sub(r'^[ :：\-_.]+', '', text_input[m.end():]).strip()
            if remainder_length > 0: rem = rem[:remainder_length]
            return (ext_id, rem, f"{ext_id} {rem}" if rem else ext_id)
        return ("0", "", "0")


# ========================================================
# 4. 🚀 文本切割器 (TrucyStringSlicer)
# ========================================================
class TrucyStringSlicer:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "text_input": ("STRING", {"forceInput": True}),
                "left_delimiter": ("STRING", {"default": "-"}),
                "right_delimiter": ("STRING", {"default": "]"}),
                "match_index": ("INT", {"default": 1}),
                "include_delimiters": ("BOOLEAN", {"default": False}),
            }
        }
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("STRING",)*4, ("Middle", "L_Part", "R_Part", "L+R"), "run", "TrucyNodes/Toolkit"
    def run(self, text_input, left_delimiter, right_delimiter, match_index, include_delimiters):
        pos = 0
        for _ in range(match_index):
            start = text_input.find(left_delimiter, pos)
            if start == -1: return ("N/A",)*4
            pos = start + len(left_delimiter)
        end = text_input.find(right_delimiter, pos)
        if end == -1: return ("N/A",)*4
        if include_delimiters: return text_input[start:end+len(right_delimiter)], text_input[:start], text_input[end+len(right_delimiter):], text_input[:start]+text_input[end+len(right_delimiter):]
        return text_input[pos:end], text_input[:start], text_input[end+len(right_delimiter):], text_input[:start]+text_input[end+len(right_delimiter):]


# ========================================================
# 5. 🚀 文件夹遍历器 (TrucyFolderIterator)
# ========================================================
class TrucyFolderIterator:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "folder_path": ("STRING", {"default": "C:/Images"}),
                "image_index": ("INT", {"default": 0, "min": 0}),
                "filter_mode": (["Contains", "Not Contains"],),
                "filter_text": ("STRING", {"default": ""}),
                "extension": (["All", "png", "jpg", "jpeg", "webp", "bmp"],),
                "empty_style": (["White", "Black"],),
            }
        }
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("IMAGE", "STRING", "INT"), ("Image", "Filename", "Count"), "load", "TrucyNodes/Toolkit"
    def load(self, folder_path, image_index, filter_mode, filter_text, extension, empty_style):
        if not os.path.exists(folder_path): return create_placeholder(empty_style), "None", 0
        valid = [f for f in os.listdir(folder_path) if any(f.lower().endswith(e) for e in ([f".{extension}"] if extension != "All" else [".png",".jpg",".jpeg",".webp",".bmp"]))]
        if filter_text: valid = [f for f in valid if (filter_text in f) == (filter_mode == "Contains")]
        if not valid: return create_placeholder(empty_style), "None", 0
        valid.sort()
        target = valid[image_index % len(valid)]
        img = load_image_file(os.path.join(folder_path, target))
        return img if img is not None else create_error_image(target), target, len(valid)


# ========================================================
# 6. 🚀 训练数据集保存器 (TrucyDatasetSaver)
# ========================================================
class TrucyDatasetSaver:
    def __init__(self): self.output_dir = folder_paths.get_output_directory()
    @classmethod
    def INPUT_TYPES(s): return {"required": {"images": ("IMAGE",), "text": ("STRING", {"multiline": True, "forceInput": True}), "filename_prefix": ("STRING", {"default": "train/img"}), "format": (["png", "jpg", "webp"],), "quality": ("INT", {"default": 95})}, "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}}
    RETURN_TYPES, OUTPUT_NODE, FUNCTION, CATEGORY = (), True, "save", "TrucyNodes/Toolkit"
    def save(self, images, text, filename_prefix, format, quality, prompt=None, extra_pnginfo=None):
        out_folder, name, counter, sub, prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
        for img in images:
            pimg = Image.fromarray(np.clip(255.*img.cpu().numpy(), 0, 255).astype(np.uint8))
            stem = f"{name}_{counter:05}_"
            if format == "png":
                meta = PngInfo()
                if prompt: meta.add_text("prompt", json.dumps(prompt))
                pimg.save(os.path.join(out_folder, f"{stem}.png"), pnginfo=meta)
            else: pimg.save(os.path.join(out_folder, f"{stem}.{format}"), quality=quality)
            with open(os.path.join(out_folder, f"{stem}.txt"), 'w', encoding='utf-8') as f: f.write(text)
            counter += 1
        return {"ui": {"images": []}}

# ========================================================
# 注册映射 
# ========================================================
NODE_CLASS_MAPPINGS = {
    "TrucyImageLoaderString5": TrucyImageLoaderString5,
    "TrucyImageLoaderString10": TrucyImageLoaderString10,
    "TrucyFolderIterator": TrucyFolderIterator,
    "TrucyPromptSplitter5": TrucyPromptSplitter5,
    "TrucyPromptSplitter10": TrucyPromptSplitter10,
    "TrucyIDExtractor": TrucyIDExtractor,
    "TrucyStringSlicer": TrucyStringSlicer,
    "TrucyDatasetSaver": TrucyDatasetSaver
}