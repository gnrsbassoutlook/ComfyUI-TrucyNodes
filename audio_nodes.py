import os
import math
import torch
import torchaudio
import torch.nn.functional as F

# ======================================================================
# 1. 音频加载器 (TrucyAudioLoaderIndex)
# ======================================================================
class TrucyAudioLoaderIndex:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory_path": ("STRING", {"default": "C:\\audio_assets"}),
                "index_mode": (["0-based (0,1,2...)", "1-based (1,2,3...)"], {"default": "0-based (0,1,2...)"}),
                "index": ("INT", {"default": 0, "min": 0, "max": 999999}),
                "sort_by": (["Alphabetical (A-Z)", "Creation Time (Oldest First)"], {"default": "Alphabetical (A-Z)"}),
                "target_sample_rate": ([44100, 48000, 16000, 22050, 24000, 8000], {"default": 44100}),
                "skip_first": ("INT", {"default": 0, "min": 0, "max": 9999}),
                "load_cap": ("INT", {"default": -1, "min": -1, "max": 9999}),
            }
        }
    RETURN_TYPES, RETURN_NAMES = ("AUDIO", "STRING"), ("audio", "filename")
    FUNCTION, CATEGORY = "load", "TrucyNodes/Audio"

    @classmethod
    def IS_CHANGED(cls, directory_path, **kwargs):
        path = directory_path.strip().replace('"', '')
        return os.getmtime(path) if os.path.isdir(path) else float("NaN")

    def load(self, directory_path, index_mode, index, sort_by, target_sample_rate, skip_first, load_cap):
        path = directory_path.strip().replace('"', '')
        files = []
        if os.path.isdir(path):
            exts = ('.mp3', '.wav', '.flac', '.ogg', '.m4a')
            files = [f for f in os.listdir(path) if f.lower().endswith(exts)]
            files.sort() if sort_by.startswith("Alpha") else files.sort(key=lambda x: os.path.getctime(os.path.join(path, x)))
            files = files[skip_first:]
            if load_cap != -1: files = files[:load_cap]

        idx = index if index_mode.startswith("0") else index - 1
        if not files or idx < 0 or idx >= len(files):
            t = torch.linspace(0, 1.0, target_sample_rate)
            beep = torch.sin(2 * math.pi * 1000 * t).unsqueeze(0).unsqueeze(0)
            return ({"waveform": beep, "sample_rate": target_sample_rate}, "OUT_OF_RANGE_BEEP")

        f_path = os.path.join(path, files[idx])
        waveform, sr = torchaudio.load(f_path)
        if sr != target_sample_rate:
            waveform = torchaudio.transforms.Resample(sr, target_sample_rate)(waveform)
        if waveform.dim() == 1: waveform = waveform.unsqueeze(0)
        return ({"waveform": waveform.unsqueeze(0), "sample_rate": target_sample_rate}, os.path.splitext(files[idx])[0])

# ======================================================================
# 2. 音频检测转换网关 (AudioLengthDetector)
# ======================================================================
class AudioLengthDetector:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO", ),
                "fps": ("INT", {"default": 24, "min": 1, "max": 120}),
                "target_sample_rate": ([44100, 48000, 32000, 24000, 22050, 16000], {"default": 48000}),
                "channel_mode": (["Stereo (立体声)", "Mono (单声道)"], {"default": "Stereo (立体声)"}),
                "pre_pad": ("BOOLEAN", {"default": False, "label_on": "PRE-ON", "label_off": "OFF"}),
                "pre_ms": (["250ms", "500ms", "750ms", "1000ms"], {"default": "500ms"}),
                "post_pad": ("BOOLEAN", {"default": True, "label_on": "POST-ON", "label_off": "OFF"}),
                "post_ms": (["250ms", "500ms", "750ms", "1000ms"], {"default": "250ms"}),
            }
        }
    RETURN_TYPES, RETURN_NAMES = ("AUDIO", "FLOAT", "INT"), ("audio", "length_sec", "total_frames")
    FUNCTION, CATEGORY, OUTPUT_NODE = "process", "TrucyNodes/Audio", True

    def process(self, audio, fps, target_sample_rate, channel_mode, pre_pad, pre_ms, post_pad, post_ms):
        w = audio["waveform"] 
        sr = audio["sample_rate"]
        
        # 1. 采样率转换
        if sr != target_sample_rate:
            resampler = torchaudio.transforms.Resample(sr, target_sample_rate)
            w = resampler(w.squeeze(0)).unsqueeze(0)
            sr = target_sample_rate

        # 2. 声道转换
        channels = w.shape[1]
        if channel_mode == "Mono (单声道)" and channels > 1:
            w = torch.mean(w, dim=1, keepdim=True)
        elif channel_mode == "Stereo (立体声)" and channels == 1:
            w = w.repeat(1, 2, 1)

        # 3. 前置垫音
        if pre_pad:
            pad_s = int(pre_ms.replace("ms", "")) / 1000.0
            w = F.pad(w, (int(pad_s * sr), 0), "constant", 0)
        
        # 4. 后置补齐
        if post_pad:
            step = int(post_ms.replace("ms", "")) / 1000.0
            cur_s = w.shape[-1] / sr
            target_s = math.ceil(cur_s / step) * step
            pad_samples = int(target_s * sr) - w.shape[-1]
            if pad_samples > 0: w = F.pad(w, (0, pad_samples), "constant", 0)
        
        final_s = w.shape[-1] / sr
        frames = round(final_s * fps)
        txt = f"采样率: {sr}Hz | 时长: {final_s:.3f}s | 帧数: {frames}"
        return {"ui": {"text": [txt]}, "result": ({"waveform": w, "sample_rate": sr}, final_s, frames)}

# ======================================================================
# 3. 静音生成 (EmptyAudioGenerator)
# ======================================================================
class EmptyAudioGenerator:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (["Seconds", "Frames"], {"default": "Seconds"}),
                "seconds": ("FLOAT", {"default": 1.0, "min": 0.0, "step": 0.001}),
                "frames": ("INT", {"default": 24, "min": 0}),
                "fps": ("INT", {"default": 24, "min": 1}),
                "sample_rate": ([44100, 48000, 16000], {"default": 44100}),
                "channels": (["Stereo", "Mono"], {"default": "Stereo"}),
            }
        }
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("AUDIO", "FLOAT", "INT"), ("audio", "length_sec", "total_samples"), "gen", "TrucyNodes/Audio"
    def gen(self, mode, seconds, frames, fps, sample_rate, channels):
        dur = frames / fps if mode == "Frames" else seconds
        chan = 2 if channels == "Stereo" else 1
        w = torch.zeros((1, chan, int(dur * sample_rate)))
        return ({"waveform": w, "sample_rate": sample_rate}, dur, w.shape[-1])