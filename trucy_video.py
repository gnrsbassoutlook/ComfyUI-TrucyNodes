import os
import shutil
import subprocess
import torch
import torch.nn.functional as F
import numpy as np
import folder_paths
import soundfile as sf
from PIL import Image
import random

class TrucyVideoCombine:
    """
    【🚀 翠西-视频合成】
    功能：将图片序列编码为高清视频。
    🚀 核心特性：
    1. 零垃圾：内存直通 FFmpeg，不产生中间图片文件。
    2. 比例修正：支持 Crop(裁切)/Stretch(拉伸)，解决 1088px 适配问题。
    3. 音频混流：支持输入 Audio 节点，自动合成音视频。
    """
    
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE",),
                "frame_rate": ("INT", {"default": 24, "min": 1, "max": 120, "step": 1}),
                "loop_count": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
                "filename_prefix": ("STRING", {"default": "Trucy_Video"}),
                "format": (["video/h264-mp4", "video/webp", "image/gif"],),
                "crf": ("INT", {"default": 20, "min": 0, "max": 51}),
                "aspect_ratio": (["Original", "16:9", "4:3", "3:2", "9:16", "3:4", "2:3", "1:1", "21:9"], {"default": "Original"}),
                "resize_mode": (["Crop Center", "Stretch"], {"default": "Crop Center"}),
                "preview_gif": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "audio": ("AUDIO",), 
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_path",)
    OUTPUT_NODE = True
    CATEGORY = "TrucyNodes/Video"
    FUNCTION = "combine_video"

    def get_ffmpeg_path(self):
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path: return ffmpeg_path
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        possible_paths = [
            os.path.join(base_path, "ffmpeg/bin/ffmpeg.exe"),
            os.path.join(base_path, "ffmpeg/ffmpeg-exe/bin/ffmpeg.exe"),
        ]
        for path in possible_paths:
            if os.path.exists(path): return path
        return None

    def combine_video(self, images, frame_rate, loop_count, filename_prefix, format, crf, preview_gif, aspect_ratio, resize_mode, audio=None):
        ffmpeg_path = self.get_ffmpeg_path()
        if ffmpeg_path is None:
            raise RuntimeError("Trucy Video Error: ffmpeg.exe not found!")

        # 比例处理逻辑保持不变，仅更新内部变量名
        output_dir = folder_paths.get_output_directory()
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, output_dir, images[0].shape[1], images[0].shape[0])
        
        ext = {"video/h264-mp4": "mp4", "video/webp": "webp", "image/gif": "gif"}.get(format, "mp4")
        file_name = f"{filename}_{counter:05}_.{ext}"
        file_path = os.path.join(full_output_folder, file_name)

        images_np = (np.clip(images.cpu().numpy(), 0, 1) * 255).astype(np.uint8)
        batch, height, width, channels = images_np.shape

        audio_args = []
        temp_audio_path = None
        if audio is not None:
            try:
                waveform = audio['waveform'].squeeze().cpu().numpy()
                if waveform.ndim == 2 and waveform.shape[0] < waveform.shape[1]: waveform = waveform.T
                temp_audio_path = os.path.join(folder_paths.get_temp_directory(), f"trucy_audio_{counter}.wav")
                sf.write(temp_audio_path, waveform, audio['sample_rate'])
                audio_args = ["-i", temp_audio_path, "-c:a", "aac", "-shortest"] 
            except: pass

        cmd = [ffmpeg_path, "-y", "-f", "rawvideo", "-vcodec", "rawvideo", "-s", f"{width}x{height}", "-pix_fmt", "rgb24", "-r", str(frame_rate), "-i", "-"]
        if audio_args: cmd.extend(audio_args)
        if format == "video/h264-mp4": cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf), "-preset", "slow"]
        elif format == "video/webp": cmd += ["-c:v", "libwebp", "-loop", str(loop_count), "-lossless", "0", "-quality", str(100 - crf*2)]
        else: cmd += ["-f", "gif", "-loop", str(loop_count)]
        cmd.append(file_path)

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)
        for i in range(batch): p.stdin.write(images_np[i].tobytes())
        p.communicate()

        if temp_audio_path and os.path.exists(temp_audio_path): os.remove(temp_audio_path)

        return {"ui": {"text": [file_path]}, "result": (file_path,)}

NODE_CLASS_MAPPINGS = {"TrucyVideoCombine": TrucyVideoCombine}
NODE_DISPLAY_NAME_MAPPINGS = {"TrucyVideoCombine": "🚀 Trucy Video Combine | 翠西-视频合成"}