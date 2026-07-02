import os
import math
import torch
import torchaudio
import torch.nn.functional as F

# ======================================================================
# 1. 智能索引音频加载器 (TrucyAudioLoaderIndex)
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
                "target_sample_rate": ([44100, 48000, 16000, 22050, 24000, 8000], {"default": 48000}), # 统一默认48k
                "skip_first": ("INT", {"default": 0, "min": 0, "max": 9999}),
                "load_cap": ("INT", {"default": -1, "min": -1, "max": 9999}),
            }
        }
    RETURN_TYPES, RETURN_NAMES = ("AUDIO", "STRING"), ("audio", "filename")
    FUNCTION, CATEGORY = "load", "TrucyNodes/Audio"

    @classmethod
    def IS_CHANGED(cls, directory_path, **kwargs):
        path = directory_path.strip().replace('"', '')
        return os.path.getmtime(path) if os.path.isdir(path) else float("NaN")

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
                "fps": ("INT", {"default": 25, "min": 1, "max": 120}), # 默认改为25fps
                "target_sample_rate": ([44100, 48000, 32000, 24000, 22050, 16000], {"default": 48000}), # 默认改为48k
                "channel_mode": (["Stereo (立体声)", "Mono (单声道)"], {"default": "Stereo (立体声)"}),
                "pre_pad": ("BOOLEAN", {"default": False, "label_on": "PRE-ON", "label_off": "OFF"}),
                "pre_ms": (["250ms", "500ms", "750ms", "1000ms"], {"default": "500ms"}),
                "post_pad": ("BOOLEAN", {"default": True, "label_on": "POST-ON", "label_off": "OFF"}),
                "post_ms": (["250ms", "500ms", "750ms", "1000ms"], {"default": "250ms"}),
            }
        }
    # 统一命名为 total_sec
    RETURN_TYPES, RETURN_NAMES = ("AUDIO", "FLOAT", "INT"), ("audio", "total_sec", "total_frames")
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
                "frames": ("INT", {"default": 25, "min": 0}), # 默认改为25帧
                "fps": ("INT", {"default": 25, "min": 1}),    # 默认改为25fps
                "sample_rate": ([44100, 48000, 32000, 24000, 22050, 16000], {"default": 48000}), # 默认48k
                "channels": (["Stereo", "Mono"], {"default": "Stereo"}),
            }
        }
    
    # 核心修改：将 total_samples 改为 total_frames，并统一时长命名为 total_sec
    RETURN_TYPES = ("AUDIO", "FLOAT", "INT")
    RETURN_NAMES = ("audio", "total_sec", "total_frames")
    FUNCTION = "gen"
    CATEGORY = "TrucyNodes/Audio"
    
    def gen(self, mode, seconds, frames, fps, sample_rate, channels):
        # 统一计算总秒数
        if mode == "Frames":
            total_sec = frames / fps
            total_frames = frames
        else:
            total_sec = seconds
            total_frames = round(seconds * fps)
            
        chan = 2 if channels == "Stereo" else 1
        
        # 生成对应时长的静音张量
        w = torch.zeros((1, chan, int(total_sec * sample_rate)))
        
        return ({"waveform": w, "sample_rate": sample_rate}, total_sec, total_frames)
        
# ======================================================================
# 4. 音频保存器 (TrucySaveAudio) - 终极包边版
# ======================================================================
class TrucySaveAudio:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO", ),
                "filename_prefix": ("STRING", {"default": "TrucyAudio"}),
                "directory_path": ("STRING", {"default": ""}), 
                "format": (["mp3", "wav", "flac"], {"default": "mp3"}),
                "target_sample_rate": ([48000, 44100, 32000, 24000, 16000], {"default": 48000}),
                "channel_mode": (["Mono (单声道)", "Stereo (立体声)", "Keep Original (保持原样)"], {"default": "Mono (单声道)"}),
                "mp3_bitrate": (["320k", "256k", "192k", "128k"], {"default": "320k"}),
                # 新增：前置与后置垫音开关
                "pre_pad": ("BOOLEAN", {"default": False, "label_on": "PRE-ON (前置)", "label_off": "OFF"}),
                "pre_ms": (["250ms", "500ms", "750ms", "1000ms"], {"default": "500ms"}),
                "post_pad": ("BOOLEAN", {"default": False, "label_on": "POST-ON (后置)", "label_off": "OFF"}),
                "post_ms": (["250ms", "500ms", "750ms", "1000ms"], {"default": "500ms"}),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("saved_path",)
    FUNCTION = "save_audio"
    CATEGORY = "TrucyNodes/Audio"
    OUTPUT_NODE = True

    def save_audio(self, audio, filename_prefix, directory_path, format, target_sample_rate, channel_mode, mp3_bitrate, pre_pad, pre_ms, post_pad, post_ms):
        import folder_paths
        
        waveform = audio["waveform"] # [Batch, Channels, Samples]
        sr = audio["sample_rate"]
        
        # 1. 决定保存目录
        clean_dir = directory_path.strip().replace('"', '')
        if clean_dir == "":
            output_dir = folder_paths.get_output_directory()
        else:
            try:
                os.makedirs(clean_dir, exist_ok=True)
                output_dir = clean_dir
            except Exception as e:
                print(f"[TrucyNodes] Invalid directory_path. Falling back to default output. Error: {e}")
                output_dir = folder_paths.get_output_directory()

        # 2. 获取防重名路径
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, output_dir)
        final_filename = f"{filename}_{counter:05}.{format}"
        save_path = os.path.join(full_output_folder, final_filename)

        # 3. 提取核心张量
        if waveform.dim() == 3:
            w = waveform[0] # [Channels, Samples]
        else:
            w = waveform
            
        # 4. 采样率转换
        if sr != target_sample_rate:
            resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sample_rate)
            w = resampler(w)
            sr = target_sample_rate

        # 5. 声道转换
        channels = w.shape[0]
        if channel_mode == "Mono (单声道)" and channels > 1:
            w = torch.mean(w, dim=0, keepdim=True)
        elif channel_mode == "Stereo (立体声)" and channels == 1:
            w = w.repeat(2, 1)

        # --- 6. 核心追加：导出前物理垫音 ---
        if pre_pad:
            pad_s = int(pre_ms.replace("ms", "")) / 1000.0
            pad_samples = int(pad_s * sr)
            # 在 Samples 维度 (dim=-1) 的前面填充
            w = F.pad(w, (pad_samples, 0), "constant", 0)
            
        if post_pad:
            pad_s = int(post_ms.replace("ms", "")) / 1000.0
            pad_samples = int(pad_s * sr)
            # 在 Samples 维度 (dim=-1) 的后面填充
            w = F.pad(w, (0, pad_samples), "constant", 0)

        # 7. 转换形状并保存
        w_np = w.T.cpu().numpy() # 转为 [Samples, Channels] 供 sf 写入

        try:
            if format in ["wav", "flac"]:
                import soundfile as sf
                sf.write(save_path, w_np, sr, format=format.upper())
            elif format == "mp3":
                import soundfile as sf
                from pydub import AudioSegment
                
                temp_wav = save_path.replace(".mp3", "_temp.wav")
                sf.write(temp_wav, w_np, sr, format="WAV")
                
                audio_segment = AudioSegment.from_wav(temp_wav)
                audio_segment.export(save_path, format="mp3", bitrate=mp3_bitrate)
                
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)
                    
            print(f"[TrucyNodes] Successfully saved audio to: {save_path}")
            return {"ui": {"text": [save_path]}, "result": (save_path,)}
            
        except Exception as e:
            error_msg = f"Failed to save audio: {str(e)}"
            print(f"[TrucyNodes] Error: {error_msg}")
            return {"ui": {"text": [error_msg]}, "result": (error_msg,)}