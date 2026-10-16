import os

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

# ========================================================
# 1. 🚀 智能代理视频加载器 (TrucyVideoLoaderIndex)
# ========================================================
class TrucyVideoLoaderIndex:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory_path": ("STRING", {"default": "C:\\video_assets"}),
                "index_mode": (["0-based (0,1,2...)", "1-based (1,2,3...)"], {"default": "0-based (0,1,2...)"}),
                "index": ("INT", {"default": 0, "min": 0, "max": 999999}),
                "sort_by": (["Alphabetical (A-Z)", "Creation Time (Oldest First)"], {"default": "Alphabetical (A-Z)"}),
                "file_format": (["mp4", "mov", "webm", "mkv", "avi"], {"default": "mp4"}),
                "skip_first": ("INT", {"default": 0, "min": 0, "max": 9999}),
                "load_cap": ("INT", {"default": -1, "min": -1, "max": 9999}),
                "target_fps": (["Original", "16", "12", "8", "4"], {"default": "Original"}),
                "max_size": (["Original", "1280", "1024", "832", "768", "720", "512", "480", "256", "128"], {"default": "Original"}),
                "audio_sample_rate": ([48000, 44100, 32000, 24000, 16000], {"default": 48000}),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "AUDIO", "FLOAT", "INT", "FLOAT", "STRING")
    RETURN_NAMES = ("image_frames", "audio", "original_fps", "total_frames", "total_sec", "filename")
    FUNCTION = "load_video"
    CATEGORY = "TrucyNodes/Video"

    @classmethod
    def IS_CHANGED(cls, directory_path, **kwargs):
        path = directory_path.strip().replace('"', '')
        return os.path.getmtime(path) if os.path.isdir(path) else float("NaN")

    def _generate_error_frame(self, text):
        img = Image.new('RGB', (512, 512), color=(128, 0, 0))
        draw = ImageDraw.Draw(img)
        try: 
            font = ImageFont.truetype("arial.ttf", 40)
        except: 
            font = ImageFont.load_default()
        draw.text((50, 200), f"ERROR:\n{text}", fill=(255, 255, 255), font=font)
        tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0)[None,]
        return tensor

    def load_video(self, directory_path, index_mode, index, sort_by, file_format, skip_first, load_cap, target_fps, max_size, audio_sample_rate):
        clean_path = directory_path.strip().replace('"', '')
        if not os.path.isdir(clean_path):
            return (self._generate_error_frame("DIR_NOT_FOUND"), None, 24.0, 1, 0.0, "ERROR")

        ext = f".{file_format.lower()}"
        files = [f for f in os.listdir(clean_path) if f.lower().endswith(ext)]
        if not files:
            return (self._generate_error_frame("NO_VIDEO_FOUND"), None, 24.0, 1, 0.0, "ERROR")

        if sort_by.startswith("Alpha"): 
            files.sort(key=lambda x: x.lower())
        else: 
            files.sort(key=lambda x: os.path.getctime(os.path.join(clean_path, x)))

        files = files[skip_first:]
        if load_cap != -1: 
            files = files[:load_cap]

        actual_index = index if index_mode.startswith("0") else index - 1
        if actual_index < 0 or actual_index >= len(files):
            return (self._generate_error_frame("OUT_OF_BOUNDS"), None, 24.0, 1, 0.0, "ERROR")

        selected_file = files[actual_index]
        file_path = os.path.join(clean_path, selected_file)
        pure_name = os.path.splitext(selected_file)[0]

        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return (self._generate_error_frame("CORRUPTED_VIDEO"), None, 24.0, 1, 0.0, pure_name)

        orig_fps = float(cap.get(cv2.CAP_PROP_FPS))
        total_orig_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if orig_fps <= 0: 
            orig_fps = 24.0
        total_sec = total_orig_frames / orig_fps

        frame_skip = 1
        if target_fps != "Original":
            t_fps = float(target_fps)
            if t_fps < orig_fps:
                frame_skip = max(1, int(round(orig_fps / t_fps)))

        resize_flag = False
        target_w, target_h = 0, 0
        if max_size != "Original":
            max_s = int(max_size)
            orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            current_max = max(orig_w, orig_h)
            if current_max > max_s:
                resize_flag = True
                scale = max_s / current_max
                target_w, target_h = int(orig_w * scale), int(orig_h * scale)
                target_w, target_h = target_w - (target_w % 2), target_h - (target_h % 2)

        frames = []
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret: 
                break
            if frame_idx % frame_skip == 0:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if resize_flag: 
                    frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
                frames.append(frame)
            frame_idx += 1
        cap.release()

        if frames:
            image_tensor = torch.from_numpy(np.stack(frames).astype(np.float32) / 255.0)
            final_frames_count = len(frames)
        else:
            image_tensor = self._generate_error_frame("EMPTY_AFTER_CROP")
            final_frames_count = 1

        audio_dict = None
        try:
            from torchaudio.io import StreamReader
            streamer = StreamReader(file_path)
            audio_stream_idx = -1
            for i in range(streamer.num_src_streams):
                if streamer.get_src_stream_info(i).media_type == "audio":
                    audio_stream_idx = i
                    break
            if audio_stream_idx != -1:
                streamer.add_basic_audio_stream(frames_per_chunk=-1, stream_index=audio_stream_idx, sample_rate=audio_sample_rate)
                streamer.process_all_packets()
                chunk = streamer.pop_chunks()[0]
                if chunk is not None:
                    audio_dict = {"waveform": chunk.T.unsqueeze(0), "sample_rate": audio_sample_rate}
        except: 
            pass

        if audio_dict is None:
            silence_samples = int(audio_sample_rate * 1.0)
            audio_dict = {"waveform": torch.zeros((1, 2, silence_samples), dtype=torch.float32), "sample_rate": audio_sample_rate}

        return (image_tensor, audio_dict, orig_fps, final_frames_count, total_sec, pure_name)


NODE_CLASS_MAPPINGS = {
    "TrucyVideoLoaderIndex": TrucyVideoLoaderIndex,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyVideoLoaderIndex": "🚀 Video Loader by Index (Trucy)",
}