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
import cv2

# ========================================================
# 1. 🚀 翠西-视频合成 (TrucyVideoCombine) 
# ========================================================
class TrucyVideoCombine:
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


# ========================================================
# 2. 🚀 翠西 LTX 视频预处理 (Trucy LTX MSR)
# ========================================================
class TrucyLTXMSR:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "width": ("INT", {"default": 1280, "min": 32, "max": 8192, "step": 32}),
                "height": ("INT", {"default": 720, "min": 32, "max": 8192, "step": 32}),
                # 核心修改：增加了 49, 51, 57 等实验性长帧数选项
                "frame_count": ([17, 25, 33, 41, 49, 51, 57], {"default": 41}),
            },
            "optional": {
                "img1": ("IMAGE",),
                "img2": ("IMAGE",),
                "img3": ("IMAGE",),
                "img4": ("IMAGE",),
                "img5_bg": ("IMAGE",), 
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("video_frames",)
    FUNCTION = "create_video_frames"
    CATEGORY = "TrucyNodes/Video"

    def _is_valid_image(self, img):
        if img is None: return False
        if type(img).__name__ == 'ExecutionBlocker': return False
        if not isinstance(img, torch.Tensor): return False
        return True

    def _create_error_image(self, width, height):
        img = Image.new('RGB', (width, height), color=(128, 0, 0))
        draw = ImageDraw.Draw(img)
        try: font = ImageFont.truetype("arial.ttf", max(40, width//15))
        except: font = ImageFont.load_default()
        draw.text((width//10, height//2), "MISSING ASSETS", fill=(255, 255, 255), font=font)
        tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0)[None,]
        return tensor

    def create_video_frames(self, width, height, frame_count, img5_bg=None, **kwargs):
        images = []
        
        for name in ("img1", "img2", "img3", "img4"):
            image = kwargs.get(name)
            if self._is_valid_image(image):
                images.append(self._prepare_image(image, (width, height)))

        if self._is_valid_image(img5_bg):
            images.append(self._prepare_image(img5_bg, (width, height)))

        if not images:
            print("[TrucyNodes] Warning: LTX MSR received 0 valid images. Generating placeholder to prevent crash.")
            error_img = self._create_error_image(width, height)
            images.append(self._prepare_image(error_img, (width, height)))

        frames = self._expand_frames(images, frame_count)
        output = torch.from_numpy(np.stack(frames).astype(np.float32) / 255.0)
        
        return (output,)

    @staticmethod
    def _tensor_to_rgb_array(image):
        if isinstance(image, torch.Tensor):
            if image.ndim == 4: image = image[0]
            image = image.detach().cpu().numpy()

        image = np.asarray(image)
        if image.dtype != np.uint8:
            image = np.clip(image * 255.0, 0, 255).astype(np.uint8)

        if image.ndim == 2: image = np.stack([image, image, image], axis=-1)
        elif image.shape[-1] == 4: image = image[..., :3]

        return np.ascontiguousarray(image)

    @staticmethod
    def _prepare_image(image, target_size):
        image_array = TrucyLTXMSR._tensor_to_rgb_array(image)
        pil_image = Image.fromarray(image_array).convert("RGB")
        image_array = np.array(pil_image)
        if image_array.shape[1] == target_size[0] and image_array.shape[0] == target_size[1]:
            return np.ascontiguousarray(image_array)
        return cv2.resize(image_array, target_size, interpolation=cv2.INTER_LANCZOS4)

    @staticmethod
    def _expand_frames(images, frame_count):
        base_count = frame_count // len(images)
        remainder = frame_count % len(images)
        frames = []
        for index, image in enumerate(images):
            repeats = base_count + (1 if index < remainder else 0)
            frames.extend([image] * repeats)
        return frames

NODE_CLASS_MAPPINGS = {
    "TrucyVideoCombine": TrucyVideoCombine,
    "TrucyLTXMSR": TrucyLTXMSR
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyVideoCombine": "🚀 Trucy Video Combine",
    "TrucyLTXMSR": "🚀 Trucy LTX MSR (Video Prep)"
}