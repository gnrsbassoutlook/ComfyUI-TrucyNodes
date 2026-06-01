import os
import re

# --- 辅助函数：智能提取第一个数字 ---
def extract_numbers(text):
    if not text or text.strip() == "":
        return 0, 0.0
    # 匹配第一个整数或浮点数
    match = re.search(r"[-+]?\d*\.\d+|[-+]?\d+", text)
    if match:
        num_str = match.group()
        try:
            res_f = float(num_str)
            res_i = int(res_f)
            return res_i, res_f
        except:
            return 0, 0.0
    return 0, 0.0

# ======================================================================
# 1. 文本索引加载器 (TrucyTxtBatchLoader)
# ======================================================================
class TrucyTxtBatchLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory_path": ("STRING", {"default": "C:\\scripts"}),
                "index_mode": (["0-based (0,1,2...)", "1-based (1,2,3...)"], {"default": "0-based (0,1,2...)"}),
                "index": ("INT", {"default": 0, "min": 0, "max": 999999}),
                "sort_by": (["Alphabetical (A-Z)", "Creation Time (Oldest First)"], {"default": "Alphabetical (A-Z)"}),
                "skip_first": ("INT", {"default": 0, "min": 0, "max": 9999}),
                "load_cap": ("INT", {"default": -1, "min": -1, "max": 9999}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("selected_content", "selected_filename", "merged_content", "merged_with_headers")
    FUNCTION = "load_texts"
    CATEGORY = "TrucyNodes/Text"

    @classmethod
    def IS_CHANGED(cls, directory_path, **kwargs):
        clean_path = directory_path.strip().replace('"', '')
        if os.path.isdir(clean_path): return os.path.getmtime(clean_path)
        return float("NaN")

    def load_texts(self, directory_path, index_mode, index, sort_by, skip_first, load_cap):
        clean_path = directory_path.strip().replace('"', '')
        if not os.path.isdir(clean_path): return ("Error: Directory not found", "N/A", "", "")
        files = [f for f in os.listdir(clean_path) if f.lower().endswith('.txt')]
        if not files: return ("No TXT files found", "N/A", "", "")
        if sort_by == "Alphabetical (A-Z)": files.sort()
        else: files.sort(key=lambda x: os.path.getctime(os.path.join(clean_path, x)))
        files = files[skip_first:]
        if load_cap != -1: files = files[:load_cap]
        if not files: return ("Index out of range", "N/A", "", "")
        
        actual_index = index if index_mode == "0-based (0,1,2...)" else index - 1
        all_contents, all_with_headers = [], []
        selected_content, selected_filename = "N/A", "OUT_OF_RANGE"
        
        for i, filename in enumerate(files):
            file_path = os.path.join(clean_path, filename)
            pure_name = os.path.splitext(filename)[0]
            content = ""
            for encoding in ['utf-8', 'gbk', 'utf-16']:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        content = f.read().strip()
                    break
                except: continue
            all_contents.append(content)
            all_with_headers.append(f"{pure_name}\n{content}")
            if i == actual_index:
                selected_content, selected_filename = content, pure_name

        merged_3 = "\n\n".join(all_contents)
        merged_4 = "\n\n".join(all_with_headers)
        return (selected_content, selected_filename, merged_3[:1000000], merged_4[:1000000])

# ======================================================================
# 2. 文本预览与智能保存 (TrucyTxtPreviewAndSave)
# ======================================================================
class TrucyTxtPreviewAndSave:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
                "save_to_file": ("BOOLEAN", {"default": False, "label_on": "Save ON", "label_off": "Save OFF"}),
                "directory_path": ("STRING", {"default": "C:\\output"}),
                "file_name": ("STRING", {"default": "scene_note"}),
                "encoding": (["UTF-8", "ANSI (GBK)"], {"default": "UTF-8"}),
            }
        }
    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "process_text"
    CATEGORY = "TrucyNodes/Text"

    def process_text(self, text, save_to_file, directory_path, file_name, encoding):
        if save_to_file and text:
            clean_dir = directory_path.strip().replace('"', '')
            try: os.makedirs(clean_dir, exist_ok=True)
            except:
                clean_dir = os.path.join(os.path.expanduser("~"), "Documents", "TrucyNodes_Output")
                os.makedirs(clean_dir, exist_ok=True)
            base_name = file_name.strip()
            if base_name.lower().endswith(".txt"): base_name = base_name[:-4]
            final_filename = f"{base_name}.txt"
            full_path = os.path.join(clean_dir, final_filename)
            counter = 1
            while os.path.exists(full_path):
                final_filename = f"{base_name}_{counter}.txt"
                full_path = os.path.join(clean_dir, final_filename)
                counter += 1
            file_enc = "utf-8" if encoding == "UTF-8" else "gbk"
            try:
                with open(full_path, "w", encoding=file_enc) as f: f.write(text)
            except Exception as e: print(f"Save Error: {str(e)}")
        return {"ui": {"text": [text]}, "result": (text,)}

# ======================================================================
# 3. 文本符号嗅探器 (TrucySymbolSniffer)
# ======================================================================
class TrucySymbolSniffer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_input": ("STRING", {"forceInput": True}),
                "index_base": (["1-based (1 to 6)", "0-based (0 to 5)"], {"default": "1-based (1 to 6)"}),
                "slot_1": ("STRING", {"default": ""}),
                "slot_2": ("STRING", {"default": "@"}),
                "slot_3": ("STRING", {"default": "#"}),
                "slot_4": ("STRING", {"default": "$"}),
                "slot_5": ("STRING", {"default": "%"}),
                "slot_6": ("STRING", {"default": "^"}),
            }
        }
    RETURN_TYPES = ("INT", "STRING", "STRING")
    RETURN_NAMES = ("int_value", "string_value", "text_directout")
    FUNCTION = "sniff"
    CATEGORY = "TrucyNodes/Text"

    def sniff(self, text_input, index_base, **kwargs):
        slots = [kwargs.get(f"slot_{i}", "").strip() for i in range(1, 7)]
        seen = {}
        for i, s in enumerate(slots):
            if s != "" and s in seen: return (-1, f"Error: Duplicate '{s}'", text_input)
            seen[s] = i
        match_index = -1
        empty_slot_index = -1
        for i in range(5, -1, -1):
            if slots[i] == "":
                empty_slot_index = i
                continue
            if slots[i] in text_input:
                match_index = i
                break
        if match_index == -1 and empty_slot_index != -1: match_index = empty_slot_index
        if match_index == -1: return (-1, "N/A", text_input)
        final_val = match_index + 1 if index_base.startswith("1") else match_index
        return (final_val, str(final_val), text_input)

# ======================================================================
# 4. 智能文本切割器 (TrucyTextSlicerSmart) - 高精清洗版
# ======================================================================
class TrucyTextSlicerSmart:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_input": ("STRING", {"forceInput": True}),
                "left_delimiter": ("STRING", {"default": "<prompt>"}),
                "right_delimiter": ("STRING", {"default": "End]"}),
                "match_index": ("INT", {"default": 1, "min": 1, "max": 999}),
                "include_delimiters": ("BOOLEAN", {"default": False, "label_on": "包含符号", "label_off": "排除符号"}),
            }
        }
    RETURN_TYPES = ("STRING", "INT", "FLOAT")
    RETURN_NAMES = ("string_value", "int_value", "float_value")
    FUNCTION = "slice_text"
    CATEGORY = "TrucyNodes/Text"

    def slice_text(self, text_input, left_delimiter, right_delimiter, match_index, include_delimiters):
        if not text_input:
            return ("", 0, 0.0)

        # 逻辑 A：如果左右分隔符均为空，直接直通输出
        if left_delimiter == "" and right_delimiter == "":
            res_int, res_float = extract_numbers(text_input)
            return (text_input.strip(), res_int, res_float)

        pos = 0
        start_pos = -1

        # 定位第 N 个匹配项的左边界
        for _ in range(match_index):
            found = text_input.find(left_delimiter, pos)
            if found == -1:
                return ("OUT_OF_RANGE", 0, 0.0)
            start_pos = found
            pos = found + len(left_delimiter)

        content_start = start_pos + len(left_delimiter)

        # 根据右边界切分
        if right_delimiter == "":
            inner_content = text_input[content_start:]
            string_output = text_input[start_pos:] if include_delimiters else inner_content
        else:
            end_pos = text_input.find(right_delimiter, content_start)
            if end_pos == -1:
                return ("OUT_OF_RANGE", 0, 0.0)
            
            inner_content = text_input[content_start:end_pos]
            
            if include_delimiters:
                string_output = text_input[start_pos : end_pos + len(right_delimiter)]
            else:
                string_output = inner_content

        # --- 核心改进：执行强力首尾清洗 (.strip()) ---
        # 即使你敲了回车换行，输出端也会把前后的空行全部过滤掉，直接呈现顶格文字！
        cleaned_output = string_output.strip()
        cleaned_inner = inner_content.strip()

        res_int, res_float = extract_numbers(cleaned_inner)

        return (cleaned_output, res_int, res_float)


NODE_CLASS_MAPPINGS = {
    "TrucyTxtBatchLoader": TrucyTxtBatchLoader,
    "TrucyTxtPreviewAndSave": TrucyTxtPreviewAndSave,
    "TrucySymbolSniffer": TrucySymbolSniffer,
    "TrucyTextSlicerSmart": TrucyTextSlicerSmart  
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyTxtBatchLoader": "🚀 TXT Loader by Index (Trucy)",
    "TrucyTxtPreviewAndSave": "🚀 Text Preview & Save (Trucy)",
    "TrucySymbolSniffer": "🚀 Text Symbol Sniffer (Trucy)",
    "TrucyTextSlicerSmart": "🚀 Text Smart Slicer (Trucy)"  
}