import os
import math
import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2

import folder_paths
import node_helpers
import nodes

# 动态依赖检测与 ComfyUI 原生环境加载
try:
    from comfy.ldm.minimax.model import FRAME_PER_TOKEN, FRAME_RESCALE
    from comfy_extras.nodes_minimax_h3 import (
        _resize, _encode_ref_audio, _empty_av_latent,
        CANVAS_MULTIPLE, REF_IMAGE_SHORT_EDGE, FPS
    )
except ImportError:
    # 针对旧版或自定义环境的回退占位
    FRAME_PER_TOKEN = [1, 2, 4, 8, 16]
    FRAME_RESCALE = 1.0
    _resize = None
    _encode_ref_audio = None
    _empty_av_latent = None
    CANVAS_MULTIPLE = 16
    REF_IMAGE_SHORT_EDGE = 768
    FPS = 24

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


# ========================================================
# 2. 🚀 MiniMax H3 多参万能参考预处理 (TrucyMiniMaxH3Prep)
# 作用：全模态参数集中预编码并输出 ref_data，极大提升缓存复用率
# ========================================================
class TrucyMiniMaxH3Prep:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "vae": ("VAE",),
                "audio_vae": ("VAE",),
                "width": ("INT", {"default": 1344, "min": 32, "max": 8192, "step": 32}),
                "height": ("INT", {"default": 768, "min": 32, "max": 8192, "step": 32}),
                "length": ("INT", {"default": 124, "min": 5, "max": 3600, "step": 17}),
                "ref_image_size": (["match", "max"], {"default": "match"}),
            },
            "optional": {
                "ref_img1": ("IMAGE",),
                "ref_img2": ("IMAGE",),
                "ref_img3": ("IMAGE",),
                "ref_img4": ("IMAGE",),
                "ref_img5": ("IMAGE",),
                "ref_img6": ("IMAGE",),
                "ref_video1": ("IMAGE",),
                "ref_video1_audio": ("AUDIO",),
                "ref_video2": ("IMAGE",),
                "ref_video2_audio": ("AUDIO",),
                "ref_audio1": ("AUDIO",),
                "ref_audio2": ("AUDIO",),
                "keyframe_image": ("IMAGE",),
                "keyframe_audio": ("AUDIO",),
                "keyframe_target_idx": ("INT", {"default": 0, "min": 0, "max": 3600, "step": 1}),
            }
        }

    RETURN_TYPES = ("LATENT", "TRUCY_H3_REF")
    RETURN_NAMES = ("latent", "ref_data")
    FUNCTION = "prepare_data"
    CATEGORY = "TrucyNodes/Video"

    def prepare_data(self, vae, audio_vae, width, height, length, ref_image_size, **kwargs):
        if _empty_av_latent is None:
            raise RuntimeError("当前环境未找到 minimax_h3 基础支持包，请确认 ComfyUI 已更新至支持 MiniMax H3 的版本。")

        latent, frame_count = _empty_av_latent(width, height, length)
        samples = latent["samples"]

        ref_items = []
        ref_blocks = []

        # 1. 处理所有参考图片 (ref_img1 ~ ref_img6)
        for i in range(1, 7):
            img = kwargs.get(f"ref_img{i}")
            if img is not None and isinstance(img, torch.Tensor):
                h, w = img.shape[1], img.shape[2]
                scale = min(1.0, math.sqrt((width * height) / (w * h))) if ref_image_size == "match" else min(1.0, REF_IMAGE_SHORT_EDGE / min(w, h))
                tw = max(CANVAS_MULTIPLE, round(w * scale / CANVAS_MULTIPLE) * CANVAS_MULTIPLE)
                th = max(CANVAS_MULTIPLE, round(h * scale / CANVAS_MULTIPLE) * CANVAS_MULTIPLE)
                resized = _resize(img[:1], tw, th, "disabled")
                z = vae.encode(resized)
                ref_items.append({"type": "image", "data": resized})
                ref_blocks.append({"kind": "image", "latent_h": th // 16, "latent_w": tw // 16, "latent": z})

        # 2. 处理参考视频与对应音轨 (ref_video1, ref_video2)
        for i in range(1, 3):
            video_frames = kwargs.get(f"ref_video{i}")
            if video_frames is not None and isinstance(video_frames, torch.Tensor):
                soundtrack = kwargs.get(f"ref_video{i}_audio")
                vh, vw = video_frames.shape[1], video_frames.shape[2]
                
                # 比例适配
                cw = max(CANVAS_MULTIPLE, round(vw / CANVAS_MULTIPLE) * CANVAS_MULTIPLE)
                ch = max(CANVAS_MULTIPLE, round(vh / CANVAS_MULTIPLE) * CANVAS_MULTIPLE)
                frames = _resize(video_frames, cw, ch, "disabled")
                
                if frames.shape[0] > frame_count: 
                    frames = frames[:frame_count]
                n = frames.shape[0]
                if n < 5: 
                    continue
                while n % 17 != 5: 
                    n -= 1
                frames = frames[:n]
                
                z = vae.encode(frames)
                audio_latent, ref_audio_t = (None, 0)
                if soundtrack is not None:
                    audio_latent, ref_audio_t = _encode_ref_audio(audio_vae, soundtrack)
                    ref_items.append({"type": "audio"})
                
                sample_idx = list(range(0, frames.shape[0], FPS // 2))
                qwen_frames = frames[sample_idx]
                ref_items.append({"type": "video", "data": qwen_frames, "timestamps": [idx / 2.0 for idx in range(len(sample_idx))]})
                ref_blocks.append({
                    "kind": "video_audio" if ref_audio_t else "video",
                    "latent_t": z.shape[2], "latent_h": ch // 16, "latent_w": cw // 16,
                    "ref_audio_t": ref_audio_t, "latent": z, "audio_latent": audio_latent
                })

        # 3. 处理独立参考音频 (ref_audio1, ref_audio2)
        for i in range(1, 3):
            audio = kwargs.get(f"ref_audio{i}")
            if audio is not None:
                audio_latent, ref_audio_t = _encode_ref_audio(audio_vae, audio)
                ref_items.append({"type": "audio"})
                ref_blocks.append({"kind": "audio", "ref_audio_t": ref_audio_t, "audio_latent": audio_latent})

        # 4. 处理单插槽关键帧引导 (keyframe)
        keyframes = []
        kf_img = kwargs.get("keyframe_image")
        kf_audio = kwargs.get("keyframe_audio")
        kf_idx = kwargs.get("keyframe_target_idx", 0)

        if kf_img is not None or kf_audio is not None:
            video = samples.tensors[0]
            audio_track = samples.tensors[1]
            height_v = video.shape[3] * 16
            width_v = video.shape[4] * 16
            frame_count_v = sum(FRAME_PER_TOKEN[k % 5] for k in range(video.shape[2]))

            resolved_frame_index = kf_idx if kf_idx >= 0 else frame_count_v + kf_idx
            keyframe = {"resolved_frame_index": min(max(0, resolved_frame_index), frame_count_v - 1)}

            if kf_img is not None and isinstance(kf_img, torch.Tensor):
                guide_frames = kf_img.shape[0]
                if guide_frames < 5: 
                    guide_frames = 1
                else:
                    while guide_frames % 17 != 5: guide_frames -= 1
                frames_k = _resize(kf_img[:guide_frames], width_v, height_v, "center")
                keyframe["latent"] = vae.encode(frames_k)

            if kf_audio is not None:
                audio_latent_k, audio_rt = _encode_ref_audio(audio_vae, kf_audio)
                max_rt = math.floor(audio_track.shape[-1] - FRAME_RESCALE * resolved_frame_index)
                if max_rt >= 1:
                    if audio_rt > max_rt: 
                        audio_latent_k = audio_latent_k[..., :max_rt].clone()
                    keyframe["audio_latent"] = audio_latent_k

            keyframes.append(keyframe)

        ref_data = {
            "ref_items": ref_items,
            "ref_blocks": ref_blocks,
            "keyframes": keyframes,
        }

        return (latent, ref_data)


# ========================================================
# 3. 🚀 MiniMax H3 提示词编码与重算节点 (TrucyMiniMaxH3Prompt)
# 作用：置后重算提示词，接收 ref_data 附加条件，最大化命中缓存
# ========================================================
class TrucyMiniMaxH3Prompt:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "prompt": ("STRING", {"multiline": True, "dynamicPrompts": True, "default": ""}),
                "ref_data": ("TRUCY_H3_REF",),
            }
        }

    RETURN_TYPES = ("CONDITIONING",)
    RETURN_NAMES = ("positive",)
    FUNCTION = "encode_prompt"
    CATEGORY = "TrucyNodes/Video"

    def encode_prompt(self, clip, prompt, ref_data):
        ref_items = ref_data.get("ref_items", [])
        ref_blocks = ref_data.get("ref_blocks", [])
        keyframes = ref_data.get("keyframes", [])

        # 借助 clip 进行 tokenize 并注入 ref_items
        tokens = clip.tokenize(prompt, minimax_ref_items=ref_items)
        cond = clip.encode_from_tokens_scheduled(tokens)

        # 绑定视频/图像参考数据与关键帧数据到 Conditioning
        if ref_blocks:
            cond = node_helpers.conditioning_set_values(cond, {"minimax_refs": ref_blocks})
            
        if keyframes:
            cond = node_helpers.conditioning_set_values(cond, {"minimax_keyframes": keyframes})

        return (cond,)


NODE_CLASS_MAPPINGS = {
    "TrucyVideoLoaderIndex": TrucyVideoLoaderIndex,
    "TrucyMiniMaxH3Prep": TrucyMiniMaxH3Prep,
    "TrucyMiniMaxH3Prompt": TrucyMiniMaxH3Prompt
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyVideoLoaderIndex": "🚀 Video Loader by Index (Trucy)",
    "TrucyMiniMaxH3Prep": "🚀 MiniMax H3 Multi-Ref Data Prep (Trucy)",
    "TrucyMiniMaxH3Prompt": "🚀 MiniMax H3 Prompt & Conditioning (Trucy)"
}