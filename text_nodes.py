import os
import re
import shutil
import time

class AlwaysEqualProxy(str):
    def __eq__(self, _): return True
    def __ne__(self, _): return False
any_type = AlwaysEqualProxy("*")

def extract_numbers(text):
    if not text or str(text).strip() == "": return 0, 0.0
    match = re.search(r"[-+]?\d*\.\d+|[-+]?\d+", str(text))
    if match:
        num_str = match.group()
        try:
            res_f = float(num_str)
            res_i = int(res_f)
            return res_i, res_f
        except: return 0, 0.0
    return 0, 0.0

# ======================================================================
# 1. 文本索引加载器
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
        if sort_by == "Alphabetical (A-Z)": files.sort(key=lambda x: x.lower())
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
# 2. 文本预览与智能保存 (TrucyTxtPreviewAndSave) - 🍏 极简纯净版
# ======================================================================
class TrucyTxtPreviewAndSave:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "save_to_file": ("BOOLEAN", {"default": False, "label_on": "Save ON", "label_off": "Save OFF"}),
                "directory_path": ("STRING", {"default": "C:\\output"}),
                "file_name": ("STRING", {"default": "scene_note"}),
                "history_subfolder": ("STRING", {"default": "Pass_Prompt"}),
                "encoding": (["UTF-8", "ANSI (GBK)"], {"default": "UTF-8"}),
            },
            "optional": {
                "text": (any_type,),
            }
        }
    
    OUTPUT_NODE = True  # 告诉 ComfyUI 这是一个终端输出节点
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "process_text"
    CATEGORY = "TrucyNodes/Text"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # 只要节点在主逻辑链上，NaN 就能保证它每次被强制执行
        return float("NaN")

    def process_text(self, save_to_file, directory_path, file_name, history_subfolder, encoding, **kwargs):
        text = kwargs.get("text", "")
        # 处理阻断器信号
        text_str = str(text) if text is not None and type(text).__name__ != 'ExecutionBlocker' else ""

        # --- 保存逻辑 ---
        if save_to_file and text_str:
            clean_dir = directory_path.strip().replace('"', '')
            
            try: 
                os.makedirs(clean_dir, exist_ok=True)
            except:
                clean_dir = os.path.join(os.path.expanduser("~"), "Documents", "TrucyNodes_Output")
                os.makedirs(clean_dir, exist_ok=True)
                
            base_name = file_name.strip()
            if base_name.lower().endswith(".txt"): 
                base_name = base_name[:-4]
            
            main_file_path = os.path.join(clean_dir, f"{base_name}.txt")
            
            try:
                # 复制备份机制（防止 Windows 文件锁）
                if os.path.exists(main_file_path):
                    archive_dir = os.path.join(clean_dir, history_subfolder.strip())
                    os.makedirs(archive_dir, exist_ok=True)
                    counter = 1
                    backup_path = os.path.join(archive_dir, f"{base_name}_{counter}.txt")
                    
                    while os.path.exists(backup_path):
                        counter += 1
                        backup_path = os.path.join(archive_dir, f"{base_name}_{counter}.txt")
                    
                    shutil.copy2(main_file_path, backup_path)
                
                # 写入新内容
                file_enc = "utf-8" if encoding == "UTF-8" else "gbk"
                with open(main_file_path, "w", encoding=file_enc) as f: 
                    f.write(text_str)
                print(f"[TrucyNodes] 文本已成功保存至: {main_file_path}")
            
            except Exception as e: 
                print(f"\n❌ [TrucyNodes] 保存错误: {str(e)}\n")
        
        # 原封不动输出文本，方便连给后续节点或 Loop End
        return {"ui": {"text": [text_str]}, "result": (text_str,)}

# ======================================================================
# 3. 文本符号嗅探器
# ======================================================================
class TrucySymbolSniffer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "index_base": (["1-based (1 to 6)", "0-based (0 to 5)"], {"default": "1-based (1 to 6)"}),
                "slot_1": ("STRING", {"default": ""}),
                "slot_2": ("STRING", {"default": "@"}),
                "slot_3": ("STRING", {"default": "#"}),
                "slot_4": ("STRING", {"default": "$"}),
                "slot_5": ("STRING", {"default": "%"}),
                "slot_6": ("STRING", {"default": "^"}),
            },
            "optional": {
                "text_input": (any_type,),
            }
        }
    RETURN_TYPES = ("INT", "STRING", "STRING")
    RETURN_NAMES = ("int_value", "string_value", "text_directout")
    FUNCTION = "sniff"
    CATEGORY = "TrucyNodes/Text"

    def sniff(self, index_base, **kwargs):
        text_input = kwargs.get("text_input", "")
        text_str = str(text_input) if text_input is not None and type(text_input).__name__ != 'ExecutionBlocker' else ""

        slots = [kwargs.get(f"slot_{i}", "").strip() for i in range(1, 7)]
        seen = {}
        for i, s in enumerate(slots):
            if s != "" and s in seen: return (-1, f"Error: Duplicate '{s}'", text_str)
            seen[s] = i
        match_index = -1
        empty_slot_index = -1
        for i in range(5, -1, -1):
            if slots[i] == "":
                empty_slot_index = i
                continue
            if slots[i] in text_str:
                match_index = i
                break
        if match_index == -1 and empty_slot_index != -1: match_index = empty_slot_index
        if match_index == -1: return (-1, "N/A", text_str)
        final_val = match_index + 1 if index_base.startswith("1") else match_index
        return (final_val, str(final_val), text_str)

# ======================================================================
# 4. 纯文字智能转换器
# ======================================================================
class TrucyTextToNumber:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"text": ("STRING", {"default": "", "multiline": True})}
        }
    RETURN_TYPES = ("STRING", "INT", "FLOAT", "BOOLEAN")
    RETURN_NAMES = ("string", "int", "float", "boolean")
    FUNCTION = "convert"
    CATEGORY = "TrucyNodes/Text"

    def convert(self, text):
        res_i, res_f = extract_numbers(text)
        clean_text = text.strip().lower()
        if clean_text in ["0", "0.0", "", "none", "null", "false"]: res_b = False
        else: res_b = True
        return (text, res_i, res_f, res_b)

# ======================================================================
# 5. 智能文本切割器 (TrucyTextSlicerSmart)
# ======================================================================
class TrucyTextSlicerSmart:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "left_delimiter": ("STRING", {"default": "<prompt>"}),
                "right_delimiter": ("STRING", {"default": "</prompt>"}),
                "match_index": ("INT", {"default": 1, "min": 1, "max": 999}),
                "include_delimiters": ("BOOLEAN", {"default": False, "label_on": "包含符号", "label_off": "排除符号"}),
                "strict_mode": ("BOOLEAN", {"default": True, "label_on": "严格边界(防污染)", "label_off": "普通匹配"}),
            },
            "optional": {"text_input": (any_type,)}
        }
    RETURN_TYPES = ("STRING", "INT", "FLOAT")
    RETURN_NAMES = ("string_value", "int_value", "float_value")
    FUNCTION = "slice_text"
    CATEGORY = "TrucyNodes/Text"

    def _find_strict(self, text, delimiter, start_pos=0):
        escaped_delim = re.escape(delimiter)
        pattern = r'(?:^|[\r\n\s])(' + escaped_delim + r')(?:[\r\n\s]|$)'
        search_area = text[start_pos:]
        match = re.search(pattern, search_area)
        if match:
            return start_pos + match.start(1)
        return -1

    def slice_text(self, left_delimiter, right_delimiter, match_index, include_delimiters, strict_mode, **kwargs):
        text_input = kwargs.get("text_input", None)
        if text_input is None or type(text_input).__name__ == 'ExecutionBlocker': return ("", 0, 0.0)
        text_str = str(text_input)
        if text_str.strip() == "": return ("", 0, 0.0)

        left = left_delimiter.strip()
        right = right_delimiter.strip()

        if left == "" and right == "":
            res_int, res_float = extract_numbers(text_str)
            return (text_str.strip(), res_int, res_float)

        pos, start_pos = 0, -1
        for _ in range(match_index):
            if strict_mode:
                found = self._find_strict(text_str, left, pos)
            else:
                found = text_str.find(left, pos)
                
            if found == -1: return ("OUT_OF_RANGE", 0, 0.0)
            start_pos = found
            pos = found + len(left)

        content_start = start_pos + len(left)
        
        if right == "":
            inner_content = text_str[content_start:]
            string_output = text_str[start_pos:] if include_delimiters else inner_content
        else:
            if strict_mode:
                end_pos = self._find_strict(text_str, right, content_start)
            else:
                end_pos = text_str.find(right, content_start)
                
            if end_pos == -1: return ("OUT_OF_RANGE", 0, 0.0)
            inner_content = text_str[content_start:end_pos]
            string_output = text_str[start_pos : end_pos + len(right)] if include_delimiters else inner_content

        cleaned_output = string_output.strip()
        cleaned_inner = inner_content.strip()
        res_int, res_float = extract_numbers(cleaned_inner)
        return (cleaned_output, res_int, res_float)

# ======================================================================
# 6. 文本污点清洗器 (TrucyTextCleaner) 
# ======================================================================
class TrucyTextCleaner:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "remove_keywords": ("STRING", {"default": "@img,@bg"}),
                "fuzz_direction": (["Forward (向后)", "Backward (向前)", "Both (前后)", "Target Only (仅目标)"], {"default": "Forward (向后)"}),
                "fuzz_type": (["Digits (数字)", "Letters (字母)", "Chinese (中文)", "Any (任意字符)"], {"default": "Digits (数字)"}),
                "fuzz_length": ("INT", {"default": 3, "min": 1, "max": 99}),
            },
            "optional": {
                "text_input": (any_type,),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("cleaned_text",)
    FUNCTION = "clean_text"
    CATEGORY = "TrucyNodes/Text"

    def clean_text(self, remove_keywords, fuzz_direction, fuzz_type, fuzz_length, **kwargs):
        text_input = kwargs.get("text_input", None)
        if text_input is None or type(text_input).__name__ == 'ExecutionBlocker':
            return ("",)
            
        text_str = str(text_input)
        if not text_str.strip() or not remove_keywords.strip():
            return (text_str,)

        targets = [t.strip() for t in re.split(r'[,，]', remove_keywords) if t.strip()]
        if not targets: return (text_str,)

        escaped_targets = [re.escape(t) for t in targets]
        target_group = f"({'|'.join(escaped_targets)})"

        type_map = {
            "Digits (数字)": r"\d",
            "Letters (字母)": r"[a-zA-Z]",
            "Chinese (中文)": r"[\u4e00-\u9fa5]",
            "Any (任意字符)": r"."
        }
        f_char = type_map.get(fuzz_type, r".")
        fuzz_pattern = f"{f_char}{{0,{fuzz_length}}}"

        if fuzz_direction == "Forward (向后)": pattern = f"{target_group}{fuzz_pattern}"
        elif fuzz_direction == "Backward (向前)": pattern = f"{fuzz_pattern}{target_group}"
        elif fuzz_direction == "Both (前后)": pattern = f"{fuzz_pattern}{target_group}{fuzz_pattern}"
        else: pattern = target_group

        cleaned_text = re.sub(pattern, "", text_str)
        cleaned_text = re.sub(r' +', ' ', cleaned_text).strip()

        return (cleaned_text,)

NODE_CLASS_MAPPINGS = {
    "TrucyTxtBatchLoader": TrucyTxtBatchLoader,
    "TrucyTxtPreviewAndSave": TrucyTxtPreviewAndSave,
    "TrucySymbolSniffer": TrucySymbolSniffer,
    "TrucyTextToNumber": TrucyTextToNumber,
    "TrucyTextSlicerSmart": TrucyTextSlicerSmart,
    "TrucyTextCleaner": TrucyTextCleaner
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyTxtBatchLoader": "🚀 TXT Loader by Index (Trucy)",
    "TrucyTxtPreviewAndSave": "🚀 Text Preview & Save (Trucy)",
    "TrucySymbolSniffer": "🚀 Text Symbol Sniffer (Trucy)",
    "TrucyTextToNumber": "🚀 Text to Number Converter (Trucy)",
    "TrucyTextSlicerSmart": "🚀 Text Smart Slicer (Trucy)",
    "TrucyTextCleaner": "🚀 Text Cleaner (Trucy)"
}