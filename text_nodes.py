import os
import re

class TrucyTxtBatchLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory_path": ("STRING", {"default": "C:\\scripts"}),
                "sort_by": (["Alphabetical (A-Z)", "Creation Time (Oldest First)"], {"default": "Alphabetical (A-Z)"}),
                "skip_first": ("INT", {"default": 0, "min": 0, "max": 9999}),
                "load_cap": ("INT", {"default": 100, "min": 1, "max": 9999}),
                "index": ("INT", {"default": 0, "min": 0, "max": 9999}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("selected_content", "selected_filename", "merged_content", "merged_with_headers")
    FUNCTION = "load_texts"
    CATEGORY = "TrucyNodes/Text"

    @classmethod
    def IS_CHANGED(cls, directory_path, **kwargs):
        # 监测文件夹修改时间，确保外部修改文件后 ComfyUI 能立即感知并刷新
        clean_path = directory_path.strip().replace('"', '')
        if os.path.isdir(clean_path):
            return os.path.getmtime(clean_path)
        return float("NaN")

    def load_texts(self, directory_path, sort_by, skip_first, load_cap, index):
        clean_path = directory_path.strip().replace('"', '')
        if not os.path.isdir(clean_path):
            return ("Error: Directory not found", "N/A", "", "")

        files = [f for f in os.listdir(clean_path) if f.lower().endswith('.txt')]
        if not files:
            return ("No TXT files found", "N/A", "", "")

        if sort_by == "Alphabetical (A-Z)":
            files.sort()
        else:
            files.sort(key=lambda x: os.path.getctime(os.path.join(clean_path, x)))

        files = files[skip_first : skip_first + load_cap]
        if not files:
            return ("Index out of range", "N/A", "", "")

        all_contents = []
        all_with_headers = []
        selected_content = ""
        selected_filename = ""
        
        for i, filename in enumerate(files):
            file_path = os.path.join(clean_path, filename)
            pure_name = os.path.splitext(filename)[0]
            
            # 多编码尝试，解决中文乱码痛点
            content = ""
            for encoding in ['utf-8', 'gbk', 'utf-16']:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        content = f.read().strip()
                    break
                except:
                    continue
            
            all_contents.append(content)
            all_with_headers.append(f"{pure_name}\n{content}")

            if i == (index % len(files)):
                selected_content = content
                selected_filename = pure_name

        merged_3 = "\n\n".join(all_contents)
        merged_4 = "\n\n".join(all_with_headers)

        # 性能保护：防止超大文本撑爆浏览器前端渲染
        max_chars = 1000000 
        if len(merged_3) > max_chars: merged_3 = merged_3[:max_chars] + "..."
        if len(merged_4) > max_chars: merged_4 = merged_4[:max_chars] + "..."

        return (selected_content, selected_filename, merged_3, merged_4)


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
            os.makedirs(clean_dir, exist_ok=True)

            base_name = file_name.strip()
            if base_name.lower().endswith(".txt"):
                base_name = base_name[:-4]
            
            # 核心：自动编号逻辑，防止覆盖旧文件
            final_filename = f"{base_name}.txt"
            full_path = os.path.join(clean_dir, final_filename)
            counter = 1
            while os.path.exists(full_path):
                final_filename = f"{base_name}_{counter}.txt"
                full_path = os.path.join(clean_dir, final_filename)
                counter += 1
            
            file_enc = "utf-8" if encoding == "UTF-8" else "gbk"
            try:
                with open(full_path, "w", encoding=file_enc) as f:
                    f.write(text)
                print(f"[TrucyNodes] Saved: {full_path}")
            except Exception as e:
                print(f"[TrucyNodes] Save Error: {str(e)}")
        
        return {"ui": {"text": [text]}, "result": (text,)}

NODE_CLASS_MAPPINGS = {
    "TrucyTxtBatchLoader": TrucyTxtBatchLoader,
    "TrucyTxtPreviewAndSave": TrucyTxtPreviewAndSave
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyTxtBatchLoader": "TXT Batch Loader (Trucy)",
    "TrucyTxtPreviewAndSave": "Text Preview & Save (Trucy)"
}