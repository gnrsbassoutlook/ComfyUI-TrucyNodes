import os, re, json, math, numpy as np, torch
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

class BaseTrucyLoaderDirect:
    def process_common(self, folder_path, empty_style, count, **kwargs):
        images = []
        for i in range(1, count + 1):
            inp = str(kwargs.get(f"img_txt_{i}", "0")).strip()
            if inp in ["0", "", "none", "None"]:
                images.append(create_placeholder(empty_style))
                continue
            path = self.find_file_smart(folder_path.strip().replace('"', ''), inp)
            img = load_image_file(path) if path else None
            images.append(img if img is not None else create_error_image(inp))
        return tuple(images)

    def find_file_smart(self, folder, input_str):
        if not os.path.exists(folder): return None
        for ext in ["png", "jpg", "jpeg", "webp"]:
            p = os.path.join(folder, f"{input_str}.{ext}")
            if os.path.exists(p): return p
        try:
            for f in os.listdir(folder):
                if f.startswith(input_str) and f.lower().endswith((".png",".jpg",".jpeg",".webp")): return os.path.join(folder, f)
        except: pass
        return None

class TrucyImageLoaderString5(BaseTrucyLoaderDirect):
    @classmethod
    def INPUT_TYPES(s): return {"required": {"folder_path": ("STRING", {"default": "C:/Images"}), "empty_style": (["White", "Black"],)}, "optional": {f"img_txt_{i}": ("STRING", {"forceInput": True}) for i in range(1, 6)}}
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("IMAGE",)*5, tuple(f"Img_{i}" for i in range(1, 6)), "run", "TrucyNodes/Toolkit"
    def run(self, folder_path, empty_style, **kwargs): return self.process_common(folder_path, empty_style, 5, **kwargs)

class TrucyImageLoaderString10(BaseTrucyLoaderDirect):
    @classmethod
    def INPUT_TYPES(s): return {"required": {"folder_path": ("STRING", {"default": "C:/Images"}), "empty_style": (["White", "Black"],)}, "optional": {f"img_txt_{i}": ("STRING", {"forceInput": True}) for i in range(1, 11)}}
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("IMAGE",)*10, tuple(f"Img_{i}" for i in range(1, 11)), "run", "TrucyNodes/Toolkit"
    def run(self, folder_path, empty_style, **kwargs): return self.process_common(folder_path, empty_style, 10, **kwargs)

# ========================================================
# 🚀 智能拆分器（扩充了分隔符列表）
# ========================================================
TRUCY_SEPARATORS = ["|", "#", "@", "$", "%", "&", "*", "~", "!", "^", "(", ")", "-", "_", "+", "=", "{", "}", "[", "]", "<", ">", ":", ";", ",", ".", "/", "\\"]

class BaseTrucySplitter:
    def split_logic(self, text_input, bracket_style, separator, bracket_index, count):
        if not text_input: return tuple([""]*count + [0]*count + [0.0]*count)
        if bracket_style == "None (Direct Split)": parts = [p.strip() for p in text_input.split(separator)]
        else:
            left, right = bracket_style[0], bracket_style[1]
            matches = re.findall(f"{re.escape(left)}(.*?){re.escape(right)}", text_input, re.DOTALL)
            parts = [p.strip() for p in matches[bracket_index-1].split(separator)] if 0 < bracket_index <= len(matches) else []
        s_out, i_out, f_out = [], [], []
        for i in range(count):
            seg = parts[i] if i < len(parts) else ""
            num_i, num_f = extract_numbers(seg)
            s_out.append(seg); i_out.append(num_i); f_out.append(num_f)
        return tuple(s_out + i_out + f_out)

class TrucyPromptSplitter5(BaseTrucySplitter):
    @classmethod
    def INPUT_TYPES(s): return {"required": {"text_input": ("STRING", {"forceInput": True}), "bracket_style": (["None (Direct Split)", "[]", "{}", "()", "<>", "【】", "《》"],), "separator": (TRUCY_SEPARATORS,), "bracket_index": ("INT", {"default": 1, "min": 1})}}
    RETURN_TYPES = ("STRING",)*5 + ("INT",)*5 + ("FLOAT",)*5
    RETURN_NAMES = tuple([f"Text_{i}" for i in range(1, 6)] + [f"Int_{i}" for i in range(1, 6)] + [f"Float_{i}" for i in range(1, 6)])
    FUNCTION, CATEGORY = "run", "TrucyNodes/Toolkit"
    def run(self, **kwargs): return self.split_logic(count=5, **kwargs)

class TrucyPromptSplitter10(BaseTrucySplitter):
    @classmethod
    def INPUT_TYPES(s): return {"required": {"text_input": ("STRING", {"forceInput": True}), "bracket_style": (["None (Direct Split)", "[]", "{}", "()", "<>", "【】", "《》"],), "separator": (TRUCY_SEPARATORS,), "bracket_index": ("INT", {"default": 1, "min": 1})}}
    RETURN_TYPES = ("STRING",)*10 + ("INT",)*10 + ("FLOAT",)*10
    RETURN_NAMES = tuple([f"Text_{i}" for i in range(1, 11)] + [f"Int_{i}" for i in range(1, 11)] + [f"Float_{i}" for i in range(1, 11)])
    FUNCTION, CATEGORY = "run", "TrucyNodes/Toolkit"
    def run(self, **kwargs): return self.split_logic(count=10, **kwargs)

class TrucyIDExtractor:
    @classmethod
    def INPUT_TYPES(s):
        t_req, t_opt = ["Any (A-Z,0-9)", "Letter (A-Z)", "Upper (A-Z)", "Digit (0-9)"], ["Ignore (End)", "Any (A-Z,0-9)", "Letter (A-Z)", "Upper (A-Z)", "Digit (0-9)"]
        return {"required": {"text_input": ("STRING", {"forceInput": True}), "search_mode": (["Auto (Smart 2-5 chars)", "Custom (Define Slots)"],), "match_index": ("INT", {"default": 1}), "remainder_length": ("INT", {"default": 0})}, "optional": {f"char_{i}_type": (t_req if i<3 else t_opt, {"default": "Any (A-Z,0-9)" if i<3 else "Ignore (End)"}) for i in range(1, 6)}}
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("STRING", "STRING", "STRING"), ("ID", "Remainder", "Combined"), "run", "TrucyNodes/Toolkit"
    def run(self, text_input, search_mode, match_index, remainder_length, **kwargs):
        matches = []
        if search_mode.startswith("Auto"):
            for m in re.finditer(r'[a-zA-Z0-9]+', text_input):
                val = m.group(0)
                if 2 <= len(val) <= 5 and not val.isalpha(): matches.append(m)
        else:
            def g(t): return "" if "Ignore" in t else "[0-9]" if "Digit" in t else "[A-Z]" if "Upper" in t else "[a-z]" if "Lower" in t else "[a-zA-Z]" if "Letter" in t else "[a-zA-Z0-9]"
            pat = f"({''.join([g(kwargs.get(f'char_{i}_type', 'Ignore')) for i in range(1, 6)])})"
            matches = list(re.finditer(pat, text_input))
        if 0 < match_index <= len(matches):
            m = matches[match_index-1]
            ext_id = m.group(1) if "Custom" in search_mode else m.group(0)
            rem = re.sub(r'^[ :：\-_.]+', '', text_input[m.end():]).strip()
            if remainder_length > 0: rem = rem[:remainder_length]
            return (ext_id, rem, f"{ext_id} {rem}" if rem else ext_id)
        return ("0", "", "0")

class TrucyStringSlicer:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"text_input": ("STRING", {"forceInput": True}), "left_delimiter": ("STRING", {"default": "-"}), "right_delimiter": ("STRING", {"default": "]"}), "match_index": ("INT", {"default": 1}), "include_delimiters": ("BOOLEAN", {"default": False})}}
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

class TrucyFolderIterator:
    @classmethod
    def INPUT_TYPES(s): return {"required": {"folder_path": ("STRING", {"default": "C:/Images"}), "image_index": ("INT", {"default": 0}), "filter_mode": (["Contains", "Not Contains"],), "filter_text": ("STRING", {"default": ""}), "extension": (["All", "png", "jpg", "jpeg", "webp"],), "empty_style": (["White", "Black"],)}}
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("IMAGE", "STRING", "INT"), ("Image", "Filename", "Count"), "load", "TrucyNodes/Toolkit"
    def load(self, folder_path, image_index, filter_mode, filter_text, extension, empty_style):
        if not os.path.exists(folder_path): return create_placeholder(empty_style), "None", 0
        valid = [f for f in os.listdir(folder_path) if any(f.lower().endswith(e) for e in ([f".{extension}"] if extension != "All" else [".png",".jpg",".jpeg",".webp"]))]
        if filter_text: valid = [f for f in valid if (filter_text in f) == (filter_mode == "Contains")]
        if not valid: return create_placeholder(empty_style), "None", 0
        valid.sort(); target = valid[image_index % len(valid)]
        img = load_image_file(os.path.join(folder_path, target))
        return img if img is not None else create_error_image(target), target, len(valid)

class BaseTrucyGrid:
    def create_grid(self, thumbnail_size, columns, add_labels, count, **kwargs):
        imgs = [(i, Image.fromarray(np.clip(255.*kwargs[f"img_{i}"][0].cpu().numpy(),0,255).astype(np.uint8))) for i in range(1, count+1) if kwargs.get(f"img_{i}") is not None]
        if not imgs: return (torch.zeros((1, 512, 512, 3)),)
        rows, cell, th = math.ceil(len(imgs)/columns), thumbnail_size, 30 if add_labels else 0
        grid = Image.new('RGB', (columns * cell, rows * (cell + th)), (20,20,20))
        for idx, (oidx, pimg) in enumerate(imgs):
            pimg.thumbnail((cell-10, cell-10))
            x, y = (idx%columns)*cell, (idx//columns)*(cell+th)
            grid.paste(pimg, (x+(cell-pimg.width)//2, y+(cell-pimg.height)//2+th))
            if add_labels: ImageDraw.Draw(grid).text((x+5, y+5), f"Img {oidx}", fill=(200,200,200))
        return (torch.from_numpy(np.array(grid).astype(np.float32)/255.0).unsqueeze(0),)

class TrucyAssetGrid5(BaseTrucyGrid):
    @classmethod
    def INPUT_TYPES(s): return {"required": {"thumbnail_size": ("INT", {"default": 256}), "columns": ("INT", {"default": 5}), "add_labels": ("BOOLEAN", {"default": True})}, "optional": {f"img_{i}": ("IMAGE",) for i in range(1,6)}}
    RETURN_TYPES, FUNCTION, CATEGORY = ("IMAGE",), "run", "TrucyNodes/Toolkit"
    def run(self, **kwargs): return self.create_grid(count=5, **kwargs)

class TrucyAssetGrid10(BaseTrucyGrid):
    @classmethod
    def INPUT_TYPES(s): return {"required": {"thumbnail_size": ("INT", {"default": 256}), "columns": ("INT", {"default": 5}), "add_labels": ("BOOLEAN", {"default": True})}, "optional": {f"img_{i}": ("IMAGE",) for i in range(1,11)}}
    RETURN_TYPES, FUNCTION, CATEGORY = ("IMAGE",), "run", "TrucyNodes/Toolkit"
    def run(self, **kwargs): return self.create_grid(count=10, **kwargs)

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

NODE_CLASS_MAPPINGS = {
    "TrucyImageLoaderString5": TrucyImageLoaderString5, "TrucyImageLoaderString10": TrucyImageLoaderString10,
    "TrucyFolderIterator": TrucyFolderIterator, "TrucyPromptSplitter5": TrucyPromptSplitter5,
    "TrucyPromptSplitter10": TrucyPromptSplitter10, "TrucyIDExtractor": TrucyIDExtractor,
    "TrucyStringSlicer": TrucyStringSlicer, "TrucyAssetGrid5": TrucyAssetGrid5,
    "TrucyAssetGrid10": TrucyAssetGrid10, "TrucyDatasetSaver": TrucyDatasetSaver
}