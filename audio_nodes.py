import os
import math
import torch
import torchaudio
import torch.nn.functional as F

# ======================================================================
# 1. 智能索引音频加载器 (TrucyAudioLoaderIndex)
# 特性：按需加载，全格式支持，自动重采样，具备“越界提示音”保护
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
        # 监测文件夹变动，确保文件增减后能实时刷新
        clean_path = directory_path.strip().replace('"', '')
        if os.path.isdir(clean_path):
            return os.path.getmtime(clean_path)
        return float("NaN")

    def load_single_audio(self, directory_path, index_mode, index, sort_by, target_sample_rate, skip_first, load_cap):
        clean_path = directory_path.strip().replace('"', '')
        
        # --- 步骤 1: 扫描并筛选文件 ---
        files = []
        if os.path.isdir(clean_path):
            exts = ('.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aiff')
            files = [f for f in os.listdir(clean_path) if f.lower().endswith(exts)]
            
            # 执行排序
            if sort_by == "Alphabetical (A-Z)":
                files.sort()
            else:
                files.sort(key=lambda x: os.path.getctime(os.path.join(clean_path, x)))
            
            # 应用 Skip 和 Cap
            files = files[skip_first:]
            if load_cap != -1:
                files = files[:load_cap]

        # --- 步骤 2: 计算实际索引 ---
        actual_index = index if index_mode == "0-based (0,1,2...)" else index - 1

        # --- 步骤 3: 核心逻辑 - 越界检查与提示音生成 ---
        # 如果文件夹里没图，或者索引超出了有效范围，直接生成 BEEP 音
        if not files or actual_index < 0 or actual_index >= len(files):
            print(f"[TrucyNodes] INFO: Index {index} is out of range. Generating 1kHz beep tone.")
            
            duration = 1.0  # 1秒时长
            num_samples = int(target_sample_rate * duration)
            t = torch.linspace(0, duration, num_samples)
            # 生成 1000Hz 标准正弦波 (Beep)
            tone_waveform = torch.sin(2 * math.pi * 1000 * t).unsqueeze(0) # [1, Samples]
            
            # 封装为 ComfyUI 标准音频字典: [Batch, Channels, Samples]
            fallback_audio = {
                "waveform": tone_waveform.unsqueeze(0), 
                "sample_rate": target_sample_rate
            }
            return (fallback_audio, "OUT_OF_RANGE_BEEP")

        # --- 步骤 4: 正常加载流程 ---
        selected_file = files[actual_index]
        file_path = os.path.join(clean_path, selected_file)
        pure_name = os.path.splitext(selected_file)[0]

        try:
            waveform, sr = torchaudio.load(file_path)
            # 自动重采样至目标频率
            if sr != target_sample_rate:
                resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sample_rate)
                waveform = resampler(waveform)
            
            # 确保张量维度正确 [Batch=1, Channels, Samples]
            if waveform.dim() == 1:
                waveform = waveform.unsqueeze(0)
            
            return ({"waveform": waveform.unsqueeze(0), "sample_rate": target_sample_rate}, pure_name)
            
        except Exception as e:
            print(f"[TrucyNodes] Error loading audio '{selected_file}': {str(e)}")
            # 读取物理文件失败时的二级兜底
            t = torch.linspace(0, 1.0, target_sample_rate)
            error_beep = torch.sin(2 * math.pi * 1000 * t).unsqueeze(0).unsqueeze(0)
            return ({"waveform": error_beep, "sample_rate": target_sample_rate}, f"LOAD_ERROR_{pure_name}")


# ======================================================================
# 2. 音频时长检测与补齐 (AudioLengthDetector)
# 特性：计算帧数，支持静音补齐，实时显示结果
# ======================================================================
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
            # 根据步长向上补齐（例如 1.1s 补齐到最近的 1.25s）
            step_sec = int(padding_level.replace("ms", "")) / 1000.0
            target_length_sec = math.ceil(original_length_sec / step_sec) * step_sec
            target_samples = int(target_length_sec * sample_rate)
            
            pad_length = target_samples - samples
            if pad_length > 0:
                # 在末尾填充 0 (绝对静音)
                padded_waveform = F.pad(waveform, (0, pad_length), "constant", 0)
            else:
                padded_waveform = waveform
            final_length_sec, final_waveform = target_length_sec, padded_waveform
        else:
            final_length_sec, final_waveform = original_length_sec, waveform
            
        total_frames = round(final_length_sec * fps)
        
        # 准备前端展示的文本
        text_out = f"【检测结果】\n"
        text_out += f"原始时长: {original_length_sec:.3f}s\n"
        text_out += f"补齐后时长: {final_length_sec:.3f}s\n"
        text_out += f"对应总帧数: {total_frames} (@{fps}fps)"
        
        return {"ui": {"text": [text_out]}, "result": ({"waveform": final_waveform, "sample_rate": sample_rate}, final_length_sec, total_frames)}


# ======================================================================
# 3. 基础静音生成器 (EmptyAudioGenerator)
# 特性：通过秒数或帧数精准生成占位静音轨
# ======================================================================
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
        # 计算具体时长
        duration = frames / fps if mode == "Frames" else seconds
        total_samples = int(duration * sample_rate)
        # 生成全 0 张量 [Batch=1, Channels, Samples]
        waveform = torch.zeros((1, channels, total_samples), dtype=torch.float32)
        
        return ({"waveform": waveform, "sample_rate": sample_rate}, duration, total_samples)