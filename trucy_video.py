import os
import shutil
import subprocess
import torch
import torch.nn.functional as F
import numpy as np
import folder_paths
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont
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

    def process_aspect_ratio(self, images, aspect_ratio, resize_mode):
        if aspect_ratio == "Original": return images
        _, curr_h, curr_w, _ = images.shape
        try:
            w_ratio, h_ratio = map(int, aspect_ratio.split(":"))
            target_ratio = w_ratio / h_ratio
        except: return images
        target_h_by_w = int(curr_w / target_ratio)
        target_w_by_h = int(curr_h * target_ratio)
        if resize_mode == "Crop Center":
            if target_h_by_w <= curr_h:
                final_w, final_h = curr_w, target_h_by_w
            else:
                final_w, final_h = target_w_by_h, curr_h
            final_w -= final_w % 2
            final_h -= final_h % 2
            center_y, center_x = curr_h // 2, curr_w // 2
            start_y = max(0, center_y - final_h // 2)
            start_x = max(0, center_x - final_w // 2)
            images = images[:, start_y:start_y+final_h, start_x:start_x+final_w, :]
        elif resize_mode == "Stretch":
            final_w = curr_w
            final_h = int(curr_w / target_ratio)
            final_w -= final_w % 2
            final_h -= final_h % 2
            img_permuted = images.permute(0, 3, 1, 2)
            img_resized = F.interpolate(img_permuted, size=(final_h, final_w), mode="bilinear", align_corners=False)
            images = img_resized.permute(0, 2, 3, 1)
        return images

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
                "frame_count": ([17, 25, 33, 41, 49, 51, 57], {"default": 41}),
                "bg_target": (["None"] + [f"img{i}" for i in range(1, 6)], {"default": "img5"}),
            },
            "optional": {
                "img1": ("IMAGE",),
                "img2": ("IMAGE",),
                "img3": ("IMAGE",),
                "img4": ("IMAGE",),
                "img5": ("IMAGE",), 
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

    def create_video_frames(self, width, height, frame_count, bg_target, **kwargs):
        regular_images = []
        background_image = None
        
        for i in range(1, 6):
            slot_name = f"img{i}"
            image = kwargs.get(slot_name)
            
            if self._is_valid_image(image):
                prepared_img = self._prepare_image(image, (width, height))
                if slot_name == bg_target:
                    background_image = prepared_img
                else:
                    regular_images.append(prepared_img)

        images_to_process = regular_images
        if background_image is not None:
            images_to_process.append(background_image)

        if not images_to_process:
            print("[TrucyNodes] Warning: LTX MSR received 0 valid images. Generating placeholder to prevent crash.")
            error_img = self._create_error_image(width, height)
            images_to_process.append(self._prepare_image(error_img, (width, height)))

        frames = self._expand_frames(images_to_process, frame_count)
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


# ========================================================
# 3. 🚀 智能代理视频加载器 (TrucyVideoLoaderIndex)
# 包含自动抽帧、降分辨率代理生成、以及纯音视频分离提取
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
                # --- 代理降级选项 ---
                "target_fps": (["Original", "16", "12", "8", "4"], {"default": "Original"}),
                "max_size": (["Original", "1280", "1024", "832", "768", "720", "512", "480", "256", "128"], {"default": "Original"}),
                # --- 音频提取选项 ---
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
        try: font = ImageFont.truetype("arial.ttf", 40)
        except: font = ImageFont.load_default()
        draw.text((50, 200), f"ERROR:\n{text}", fill=(255, 255, 255), font=font)
        tensor = torch.from_numpy(np.array(img).astype(np.float32) / 255.0)[None,]
        return tensor

    def load_video(self, directory_path, index_mode, index, sort_by, file_format, skip_first, load_cap, target_fps, max_size, audio_sample_rate):
        import torchaudio
        
        # 1. 路径清洗
        clean_path = directory_path.strip().replace('"', '')
        if not os.path.isdir(clean_path):
            return (self._generate_error_frame("DIR_NOT_FOUND"), None, 24.0, 1, 0.0, "ERROR")

        # 2. 文件扫描
        ext = f".{file_format.lower()}"
        files = [f for f in os.listdir(clean_path) if f.lower().endswith(ext)]
        if not files:
            return (self._generate_error_frame("NO_VIDEO_FOUND"), None, 24.0, 1, 0.0, "ERROR")

        if sort_by.startswith("Alpha"): files.sort(key=lambda x: x.lower())
        else: files.sort(key=lambda x: os.path.getctime(os.path.join(clean_path, x)))

        files = files[skip_first:]
        if load_cap != -1: files = files[:load_cap]

        actual_index = index if index_mode.startswith("0") else index - 1
        if actual_index < 0 or actual_index >= len(files):
            return (self._generate_error_frame("OUT_OF_BOUNDS"), None, 24.0, 1, 0.0, "ERROR")

        selected_file = files[actual_index]
        file_path = os.path.join(clean_path, selected_file)
        pure_name = os.path.splitext(selected_file)[0]

        # --- 3. 读取视频帧与 Proxy 代理压缩 ---
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return (self._generate_error_frame("CORRUPTED_VIDEO"), None, 24.0, 1, 0.0, pure_name)

        orig_fps = float(cap.get(cv2.CAP_PROP_FPS))
        if orig_fps <= 0: orig_fps = 24.0
        
        total_orig_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        total_sec = total_orig_frames / orig_fps

        # 抽帧逻辑计算
        frame_skip = 1
        if target_fps != "Original":
            t_fps = float(target_fps)
            if t_fps < orig_fps:
                frame_skip = max(1, int(round(orig_fps / t_fps)))

        # 缩放逻辑计算
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
                target_w = int(orig_w * scale)
                target_h = int(orig_h * scale)
                # 保证被 2 整除以防报错
                target_w = target_w - (target_w % 2)
                target_h = target_h - (target_h % 2)

        frames = []
        frame_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            # 执行抽帧
            if frame_idx % frame_skip == 0:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # 执行降分辨率
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

        # --- 4. 音轨提取与统一 ---
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
                streamer.add_basic_audio_stream(
                    frames_per_chunk=-1, 
                    stream_index=audio_stream_idx,
                    sample_rate=audio_sample_rate
                )
                streamer.process_all_packets()
                chunk = streamer.pop_chunks()[0]
                if chunk is not None:
                    waveform = chunk.T.unsqueeze(0)
                    audio_dict = {"waveform": waveform, "sample_rate": audio_sample_rate}
        except:
            pass

        if audio_dict is None:
            silence_samples = int(audio_sample_rate * 1.0)
            silent_wav = torch.zeros((1, 2, silence_samples), dtype=torch.float32)
            audio_dict = {"waveform": silent_wav, "sample_rate": audio_sample_rate}

        print(f"[TrucyNodes] Loaded Proxy Video: {selected_file} | Extracted {final_frames_count} frames | Orig FPS: {orig_fps}")

        return (image_tensor, audio_dict, orig_fps, final_frames_count, total_sec, pure_name)


NODE_CLASS_MAPPINGS = {
    "TrucyVideoCombine": TrucyVideoCombine,
    "TrucyLTXMSR": TrucyLTXMSR,
    "TrucyVideoLoaderIndex": TrucyVideoLoaderIndex
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyVideoCombine": "🚀 Trucy Video Combine",
    "TrucyLTXMSR": "🚀 Trucy LTX MSR (Video Prep)",
    "TrucyVideoLoaderIndex": "🚀 Video Loader by Index (Trucy)"
}