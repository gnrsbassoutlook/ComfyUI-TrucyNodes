import os
import math
import torch
import torchaudio
import torch.nn.functional as F

# ======================================================================
# 1. 智能索引音频加载器 (全能旗舰版)
# 特性：按需加载、防越界、强制重采样、单双声道转换、双向垫音、时长帧数直出
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
                "skip_first": ("INT", {"default": 0, "min": 0, "max": 9999}),
                "load_cap": ("INT", {"default": -1, "min": -1, "max": 9999}),
                
                # --- 新增：强制格式转换 ---
                "fps": ("INT", {"default": 25, "min": 1, "max": 120, "step": 1}),
                "target_sample_rate": ([44100, 48000, 32000, 24000, 22050, 16000], {"default": 48000}),
                "channel_mode": (["Mono (单声道)", "Stereo (立体声)", "Keep Original (保持原样)"], {"default": "Mono (单声道)"}),
                
                # --- 新增：双向垫音控制 ---
                "pre_pad": ("BOOLEAN", {"default": False, "label_on": "PRE-ON", "label_off": "OFF"}),
                "pre_ms": (["250ms", "500ms", "750ms", "1000ms"], {"default": "500ms"}),
                "post_pad": ("BOOLEAN", {"default": False, "label_on": "POST-ON", "label_off": "OFF"}),
                "post_ms": (["250ms", "500ms", "750ms", "1000ms"], {"default": "250ms"}),
            }
        }
        
    RETURN_TYPES = ("AUDIO", "FLOAT", "INT", "STRING")
    RETURN_NAMES = ("audio", "total_sec", "total_frames", "filename")
    FUNCTION = "load_single_audio"
    CATEGORY = "TrucyNodes/Audio"

    @classmethod
    def IS_CHANGED(cls, directory_path, **kwargs):
        path = directory_path.strip().replace('"', '')
        return os.path.getmtime(path) if os.path.isdir(path) else float("NaN")

    def _generate_fallback_audio(self, target_sample_rate, channel_mode, duration_sec):
        """生成占位提示音 (1kHz Beep)"""
        num_samples = int(target_sample_rate * duration_sec)
        t = torch.linspace(0, duration_sec, num_samples)
        beep = torch.sin(2 * math.pi * 1000 * t).unsqueeze(0) # [1, Samples]
        
        # 处理声道
        if channel_mode == "Stereo (立体声)":
            beep = beep.repeat(2, 1) # [2, Samples]
            
        return {"waveform": beep.unsqueeze(0), "sample_rate": target_sample_rate}

    def load_single_audio(self, directory_path, index_mode, index, sort_by, skip_first, load_cap, 
                          fps, target_sample_rate, channel_mode, pre_pad, pre_ms, post_pad, post_ms):
        
        clean_path = directory_path.strip().replace('"', '')
        files = []
        if os.path.isdir(clean_path):
            exts = ('.mp3', '.wav', '.flac', '.ogg', '.m4a')
            files = [f for f in os.listdir(clean_path) if f.lower().endswith(exts)]
            files.sort() if sort_by.startswith("Alpha") else files.sort(key=lambda x: os.path.getctime(os.path.join(clean_path, x)))
            files = files[skip_first:]
            if load_cap != -1: files = files[:load_cap]

        actual_index = index if index_mode.startswith("0") else index - 1
        
        # ==========================================
        # 1. 加载阶段与容错
        # ==========================================
        if not files or actual_index < 0 or actual_index >= len(files):
            print(f"[TrucyNodes] WARNING: Audio index {index} out of range. Generating 1kHz beep.")
            w_dict = self._generate_fallback_audio(target_sample_rate, channel_mode, 1.0)
            return (w_dict, 1.0, fps, "OUT_OF_RANGE_BEEP")

        selected_file = files[actual_index]
        file_path = os.path.join(clean_path, selected_file)
        pure_name = os.path.splitext(selected_file)[0]

        try:
            waveform, sr = torchaudio.load(file_path) # [Channels, Samples]
        except Exception as e:
            print(f"[TrucyNodes] Load Error: {str(e)}")
            w_dict = self._generate_fallback_audio(target_sample_rate, channel_mode, 1.0)
            return (w_dict, 1.0, fps, f"LOAD_ERROR_{pure_name}")

        # ==========================================
        # 2. 格式转换阶段 (重采样 + 声道映射)
        # ==========================================
        if sr != target_sample_rate:
            resampler = torchaudio.transforms.Resample(sr, target_sample_rate)
            waveform = resampler(waveform)
            sr = target_sample_rate

        channels = waveform.shape[0]
        if channel_mode == "Mono (单声道)" and channels > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        elif channel_mode == "Stereo (立体声)" and channels == 1:
            waveform = waveform.repeat(2, 1)

        # ==========================================
        # 3. 垫音处理阶段 (Padding)
        # ==========================================
        if pre_pad:
            pad_s = int(pre_ms.replace("ms", "")) / 1000.0
            waveform = F.pad(waveform, (int(pad_s * sr), 0), "constant", 0)
        
        if post_pad:
            step = int(post_ms.replace("ms", "")) / 1000.0
            cur_s = waveform.shape[-1] / sr
            target_s = math.ceil(cur_s / step) * step
            pad_samples = int(target_s * sr) - waveform.shape[-1]
            if pad_samples > 0: 
                waveform = F.pad(waveform, (0, pad_samples), "constant", 0)

        # ==========================================
        # 4. 元数据计算与输出
        # ==========================================
        final_s = waveform.shape[-1] / sr
        total_frames = round(final_s * fps)
        
        # 补充 Batch 维度，符合 ComfyUI 标准格式
        audio_out = {"waveform": waveform.unsqueeze(0), "sample_rate": sr}
        
        return (audio_out, final_s, total_frames, pure_name)


# ======================================================================
# 2. 音频检测转换网关 (AudioLengthDetector)
# ======================================================================
class AudioLengthDetector:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO", ),
                "fps": ("INT", {"default": 25, "min": 1, "max": 120}),
                "target_sample_rate": ([44100, 48000, 32000, 24000, 22050, 16000], {"default": 48000}),
                "channel_mode": (["Stereo (立体声)", "Mono (单声道)", "Keep Original (保持原样)"], {"default": "Stereo (立体声)"}),
                "pre_pad": ("BOOLEAN", {"default": False, "label_on": "PRE-ON", "label_off": "OFF"}),
                "pre_ms": (["250ms", "500ms", "750ms", "1000ms"], {"default": "500ms"}),
                "post_pad": ("BOOLEAN", {"default": True, "label_on": "POST-ON", "label_off": "OFF"}),
                "post_ms": (["250ms", "500ms", "750ms", "1000ms"], {"default": "250ms"}),
            }
        }
    RETURN_TYPES, RETURN_NAMES = ("AUDIO", "FLOAT", "INT"), ("audio", "total_sec", "total_frames")
    FUNCTION, CATEGORY, OUTPUT_NODE = "process", "TrucyNodes/Audio", True

    def process(self, audio, fps, target_sample_rate, channel_mode, pre_pad, pre_ms, post_pad, post_ms):
        w = audio["waveform"] 
        sr = audio["sample_rate"]
        
        if sr != target_sample_rate:
            resampler = torchaudio.transforms.Resample(sr, target_sample_rate)
            w = resampler(w.squeeze(0)).unsqueeze(0)
            sr = target_sample_rate

        channels = w.shape[1]
        if channel_mode == "Mono (单声道)" and channels > 1:
            w = torch.mean(w, dim=1, keepdim=True)
        elif channel_mode == "Stereo (立体声)" and channels == 1:
            w = w.repeat(1, 2, 1)

        if pre_pad:
            pad_s = int(pre_ms.replace("ms", "")) / 1000.0
            w = F.pad(w, (int(pad_s * sr), 0), "constant", 0)
        
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
# 3. 静音生成器 (EmptyAudioGenerator)
# ======================================================================
class EmptyAudioGenerator:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (["Seconds", "Frames"], {"default": "Seconds"}),
                "seconds": ("FLOAT", {"default": 1.0, "min": 0.0, "step": 0.001}),
                "frames": ("INT", {"default": 25, "min": 0}),
                "fps": ("INT", {"default": 25, "min": 1}),
                "sample_rate": ([44100, 48000, 32000, 24000, 22050, 16000], {"default": 48000}),
                "channels": (["Stereo", "Mono"], {"default": "Stereo"}),
            }
        }
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = ("AUDIO", "FLOAT", "INT"), ("audio", "total_sec", "total_frames"), "gen", "TrucyNodes/Audio"
    
    def gen(self, mode, seconds, frames, fps, sample_rate, channels):
        if mode == "Frames":
            total_sec = frames / fps
            total_frames = frames
        else:
            total_sec = seconds
            total_frames = round(seconds * fps)
            
        chan = 2 if channels == "Stereo" else 1
        w = torch.zeros((1, chan, int(total_sec * sample_rate)))
        return ({"waveform": w, "sample_rate": sample_rate}, total_sec, total_frames)

# ======================================================================
# 4. 音频保存器 (TrucySaveAudio)
# ======================================================================
try:
    import soundfile as sf
    import subprocess
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False

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

    def get_ffmpeg_path(self):
        import shutil
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path: return ffmpeg_path
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        possible_paths = [
            os.path.join(base_path, "ffmpeg/bin/ffmpeg.exe"),
            os.path.join(base_path, "ffmpeg/ffmpeg-exe/bin/ffmpeg.exe"),
            os.path.join(base_path, "venv/Scripts/ffmpeg.exe"),
        ]
        for path in possible_paths:
            if os.path.exists(path): return path
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except: pass
        return None

    def save_audio(self, audio, filename_prefix, directory_path, format, target_sample_rate, channel_mode, mp3_bitrate, pre_pad, pre_ms, post_pad, post_ms):
        if not HAS_SOUNDFILE:
            return {"ui": {"text": ["Error: Missing 'soundfile' library."]}, "result": ("Error",)}
            
        import folder_paths
        
        waveform = audio["waveform"]
        sr = audio["sample_rate"]
        
        clean_dir = directory_path.strip().replace('"', '')
        if clean_dir == "":
            output_dir = folder_paths.get_output_directory()
        else:
            try:
                os.makedirs(clean_dir, exist_ok=True)
                output_dir = clean_dir
            except Exception as e:
                output_dir = folder_paths.get_output_directory()

        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, output_dir)
        final_filename = f"{filename}_{counter:05}.{format}"
        save_path = os.path.join(full_output_folder, final_filename)

        if waveform.dim() == 3: w = waveform[0]
        else: w = waveform
            
        if sr != target_sample_rate:
            resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sample_rate)
            w = resampler(w)
            sr = target_sample_rate

        channels = w.shape[0]
        if channel_mode == "Mono (单声道)" and channels > 1:
            w = torch.mean(w, dim=0, keepdim=True)
        elif channel_mode == "Stereo (立体声)" and channels == 1:
            w = w.repeat(2, 1)

        if pre_pad:
            pad_s = int(pre_ms.replace("ms", "")) / 1000.0
            w = F.pad(w, (int(pad_s * sr), 0), "constant", 0)
        if post_pad:
            pad_s = int(post_ms.replace("ms", "")) / 1000.0
            w = F.pad(w, (0, int(pad_s * sr)), "constant", 0)

        w_np = w.T.cpu().numpy()

        try:
            if format in ["wav", "flac"]:
                import soundfile as sf
                sf.write(save_path, w_np, sr, format=format.upper())
            elif format == "mp3":
                temp_wav = save_path.replace(".mp3", "_temp.wav")
                import soundfile as sf
                sf.write(temp_wav, w_np, sr, format="WAV")
                
                ffmpeg_path = self.get_ffmpeg_path()
                if not ffmpeg_path:
                    raise RuntimeError("FFmpeg not found! Cannot convert to MP3.")

                cmd = [
                    ffmpeg_path, 
                    "-y", 
                    "-i", temp_wav, 
                    "-c:a", "libmp3lame", 
                    "-b:a", mp3_bitrate, 
                    save_path
                ]
                
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    
                subprocess.run(cmd, startupinfo=startupinfo, check=True)
                
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)
                    
            print(f"[TrucyNodes] Successfully saved audio to: {save_path}")
            return {"ui": {"text": [save_path]}, "result": (save_path,)}
            
        except Exception as e:
            error_msg = f"Failed to save audio: {str(e)}"
            return {"ui": {"text": [error_msg]}, "result": (error_msg,)}