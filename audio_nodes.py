import os
import math
import torch
import torchaudio
import torch.nn.functional as F

# --- 1. 高效索引音频加载器 (带 1kHz 提示音保护) ---
class TrucyAudioLoaderIndex:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory_path": ("STRING", {"default": "C:\\audio_assets"}),
                "index_mode": (["0-based (0,1,2...)", "1-based (1,2,3...)"], {"default": "0-based (0,1,2...)"}),
                "index": ("INT", {"default": 0, "min": 0, "max": 999999}),
                "sort_by": (["Alphabetical (A-Z)", "Creation Time (Oldest First)"], {"default": "Alphabetical (A-Z)"}),
                "target_sample_rate": ([44100, 48000, 16000, 22050, 8000], {"default": 44100}),
                "skip_first": ("INT", {"default": 0, "min": 0, "max": 9999}),
                "load_cap": ("INT", {"default": -1, "min": -1, "max": 9999}),
            }
        }

    RETURN_TYPES = ("AUDIO", "STRING")
    RETURN_NAMES = ("audio", "filename")
    FUNCTION = "load_single_audio"
    CATEGORY = "TrucyNodes/Audio"

    @classmethod
    def IS_CHANGED(cls, directory_path, **kwargs):
        clean_path = directory_path.strip().replace('"', '')
        if os.path.isdir(clean_path):
            return os.path.getmtime(clean_path)
        return float("NaN")

    def load_single_audio(self, directory_path, index_mode, index, sort_by, target_sample_rate, skip_first, load_cap):
        clean_path = directory_path.strip().replace('"', '')
        
        # 扫描目录
        files = []
        if os.path.isdir(clean_path):
            exts = ('.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aiff')
            files = [f for f in os.listdir(clean_path) if f.lower().endswith(exts)]
            if sort_by == "Alphabetical (A-Z)":
                files.sort()
            else:
                files.sort(key=lambda x: os.path.getctime(os.path.join(clean_path, x)))
            
            files = files[skip_first:]
            if load_cap != -1:
                files = files[:load_cap]

        actual_index = index if index_mode == "0-based (0,1,2...)" else index - 1

        # --- 核心改进：索引越界保护，生成 1kHz 提示音 ---
        if not files or actual_index < 0 or actual_index >= len(files):
            print(f"[TrucyNodes] WARNING: Audio index out of range. Generating 1kHz beep.")
            duration = 1.0 # 1秒
            t = torch.linspace(0, duration, int(target_sample_rate * duration))
            # 生成标准的 1000Hz 正弦波
            beep_waveform = torch.sin(2 * math.pi * 1000 * t).unsqueeze(0) 
            # 格式：[Batch=1, Channels=1, Samples]
            fallback_audio = {"waveform": beep_waveform.unsqueeze(0), "sample_rate": target_sample_rate}
            return (fallback_audio, "INDEX_OUT_OF_RANGE_BEEP")

        # 正常读取
        selected_file = files[actual_index]
        file_path = os.path.join(clean_path, selected_file)
        pure_name = os.path.splitext(selected_file)[0]

        try:
            waveform, sr = torchaudio.load(file_path)
            if sr != target_sample_rate:
                resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sample_rate)
                waveform = resampler(waveform)
            # 统一转为单声道(如果需要)或者保持，这里我们加上 Batch 维度
            if waveform.dim() == 1:
                waveform = waveform.unsqueeze(0)
            return ({"waveform": waveform.unsqueeze(0), "sample_rate": target_sample_rate}, pure_name)
        except Exception as e:
            print(f"[TrucyNodes] Load Error: {str(e)}")
            t = torch.linspace(0, 1.0, target_sample_rate)
            beep = torch.sin(2 * math.pi * 1000 * t).unsqueeze(0).unsqueeze(0)
            return ({"waveform": beep, "sample_rate": target_sample_rate}, "LOAD_ERROR_BEEP")

# --- 2. 音频时长检测与补齐 ---
class AudioLengthDetector:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO", ),
                "fps": ("INT", {"default": 24, "min": 1, "max": 120, "step": 1}),
                "enable_padding": ("BOOLEAN", {"default": True, "label_on": "ON", "label_off": "OFF"}),
                "padding_level": (["250ms", "500ms", "750ms", "1000ms"], {"default": "250ms"}),
            }
        }

    RETURN_TYPES = ("AUDIO", "FLOAT", "INT")
    RETURN_NAMES = ("audio", "length_sec", "total_frames")
    FUNCTION = "process_audio"
    CATEGORY = "TrucyNodes/Audio"
    OUTPUT_NODE = True

    def process_audio(self, audio, fps, enable_padding, padding_level):
        waveform = audio["waveform"]
        sample_rate = audio["sample_rate"]
        samples = waveform.shape[-1]
        original_length_sec = samples / sample_rate
        
        if enable_padding:
            step_sec = int(padding_level.replace("ms", "")) / 1000.0
            target_length_sec = math.ceil(original_length_sec / step_sec) * step_sec
            target_samples = int(target_length_sec * sample_rate)
            pad_length = target_samples - samples
            if pad_length > 0:
                padded_waveform = F.pad(waveform, (0, pad_length), "constant", 0)
            else:
                padded_waveform = waveform
            final_length_sec, final_waveform = target_length_sec, padded_waveform
        else:
            final_length_sec, final_waveform = original_length_sec, waveform
            
        total_frames = round(final_length_sec * fps)
        text_out = f"【检测结果】\n原始时长: {original_length_sec:.3f}s\n最终时长: {final_length_sec:.3f}s\n帧数: {total_frames} (@{fps}fps)"
        return {"ui": {"text": [text_out]}, "result": ({"waveform": final_waveform, "sample_rate": sample_rate}, final_length_sec, total_frames)}

# --- 3. 空音频生成器 ---
class EmptyAudioGenerator:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (["Seconds", "Frames"], {"default": "Seconds"}),
                "seconds": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3600.0, "step": 0.001}),
                "frames": ("INT", {"default": 24, "min": 0, "max": 1000000}),
                "fps": ("INT", {"default": 24, "min": 1, "max": 120}),
                "sample_rate": ([44100, 48000, 16000, 22050, 8000], {"default": 44100}),
                "channels": ("INT", {"default": 2, "min": 1, "max": 6}),
            }
        }

    RETURN_TYPES = ("AUDIO", "FLOAT", "INT")
    RETURN_NAMES = ("audio", "length_sec", "total_samples")
    FUNCTION = "generate_silence"
    CATEGORY = "TrucyNodes/Audio"

    def generate_silence(self, mode, seconds, frames, fps, sample_rate, channels):
        duration = frames / fps if mode == "Frames" else seconds
        total_samples = int(duration * sample_rate)
        waveform = torch.zeros((1, channels, total_samples), dtype=torch.float32)
        return ({"waveform": waveform, "sample_rate": sample_rate}, duration, total_samples)