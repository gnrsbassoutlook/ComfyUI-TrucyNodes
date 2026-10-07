"""VHS Video Combine standard implementation compatible with all FeiHou & ComfyUI extensions."""

import copy
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import folder_paths
import torchaudio
from comfy.cli_args import args

# 导入 ComfyUI 官方/标准 VIDEO 对象封装
try:
    from comfy_api.input_impl import VideoFromFile
except ImportError:
    try:
        from comfy_api.input.video_types import VideoFromFile
    except ImportError:
        VideoFromFile = None

try:
    from comfy.utils import ProgressBar
except Exception:
    ProgressBar = None

from .vhs_compat.nodes import VideoCombine as _VHSVideoCombine
from .vhs_compat.nodes import get_video_formats as _get_video_formats
from .vhs_compat import server as _vhs_server  # noqa: F401


def _ffmpeg_path():
    forced = os.environ.get("VHS_FORCE_FFMPEG_PATH")
    if forced:
        return forced
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
        return get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def _supports_nvenc(ff):
    """检测当前 ffmpeg 是否支持 NVIDIA GPU 硬件加速 (h264_nvenc)"""
    try:
        r = subprocess.run([ff, '-hide_banner', '-encoders'],
                           capture_output=True, text=True, timeout=10)
        return 'h264_nvenc' in (r.stdout + r.stderr)
    except Exception:
        return False


def _write_ffmetadata(metadata, path):
    def escape(key, value):
        text = json.dumps(value, ensure_ascii=False)
        text = text.replace("\\", "\\\\").replace(";", "\\;").replace("#", "\\#")
        text = text.replace("=", "\\=")
        text = text.replace("\n", "\\\n")
        return f"{key}={text}"

    with open(path, "w", encoding="utf-8") as stream:
        stream.write(";FFMETADATA1\n")
        for key in ("prompt", "workflow"):
            if key in metadata:
                stream.write(escape(key, metadata[key]) + "\n")
        for key, value in metadata.items():
            if key not in {"prompt", "workflow"}:
                stream.write(escape(key, value) + "\n")


class TrucyVideoCombine:
    """Standard Video Combine with native VIDEO and filepath(STRING) outputs."""

    @classmethod
    def INPUT_TYPES(cls):
        ffmpeg_formats, format_widgets = _get_video_formats()
        format_widgets["image/webp"] = [["lossless", "BOOLEAN", {"default": True}]]
        
        # 将 video/h264-mp4 置顶作为默认首选
        all_formats = ["video/h264-mp4", "image/gif", "image/webp"] + [f for f in ffmpeg_formats if f != "video/h264-mp4"]
        
        return {
            "required": {
                "frame_rate": ("FLOAT", {"default": 16.0, "min": 1.0, "step": 1.0}),
                "loop_count": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
                "filename_prefix": ("STRING", {"default": "TrucyVideo"}),
                "format": (all_formats, {"formats": format_widgets, "default": "video/h264-mp4"}),
                "pingpong": ("BOOLEAN", {"default": False}),
                "save_output": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "images": ("IMAGE",),
                "video": ("VIDEO",),
                "audio": ("AUDIO",),
                "custom_path": ("STRING", {"default": r"D:\ComfyUI-Output"}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("VIDEO", "STRING")
    RETURN_NAMES = ("video", "filepath")
    OUTPUT_NODE = True
    CATEGORY = "Video Helper Suite 🎥🅥🅗🅢"
    FUNCTION = "combine_video"

    @staticmethod
    def _metadata(prompt, extra_pnginfo):
        if getattr(args, "disable_metadata", False):
            return {}
        metadata = dict(extra_pnginfo or {})
        if prompt is not None:
            metadata["prompt"] = prompt
        return metadata

    @staticmethod
    def _embed_metadata(final_path, metadata):
        if not metadata:
            return
        ffmpeg = _ffmpeg_path()
        if not ffmpeg:
            raise ProcessLookupError("ffmpeg is required to embed ComfyUI metadata.")
        folder = os.path.dirname(final_path)
        suffix = Path(final_path).suffix
        metadata_path = os.path.join(folder, f".feihou-vhs-metadata-{uuid.uuid4().hex}.txt")
        replacement = os.path.join(folder, f".feihou-vhs-final-{uuid.uuid4().hex}{suffix}")
        _write_ffmetadata(metadata, metadata_path)
        command = [ffmpeg, "-v", "error", "-y", "-i", final_path, "-i", metadata_path,
                   "-map", "0", "-map_metadata", "1", "-c", "copy"]
        if suffix.lower() in {".mp4", ".m4v", ".mov"}:
            command += ["-movflags", "use_metadata_tags"]
        command.append(replacement)
        try:
            completed = subprocess.run(command, capture_output=True, check=False)
            if completed.returncode != 0:
                raise RuntimeError("ffmpeg could not embed ComfyUI metadata:\n" + completed.stderr.decode("utf-8", errors="replace"))
            os.replace(replacement, final_path)
        finally:
            for path in (metadata_path, replacement):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except OSError:
                    pass

    def _clean_audio_suffix(self, file_path):
        if not os.path.isfile(file_path):
            return file_path
        dir_name, base_name = os.path.split(file_path)
        name, ext = os.path.splitext(base_name)
        if name.endswith("-audio"):
            clean_base_name = name[:-6] + ext
            target_path = os.path.join(dir_name, clean_base_name)
            if os.path.exists(target_path):
                try:
                    os.remove(target_path)
                except OSError:
                    pass
            try:
                os.replace(file_path, target_path)
                return target_path
            except OSError:
                return file_path
        return file_path

    def _process_video_input(self, video, audio, target_dir, filename_prefix, save_output):
        ffmpeg = _ffmpeg_path()
        if not ffmpeg:
            raise RuntimeError("ffmpeg 未找到，请确保系统中已正确配置 ffmpeg。")

        in_video_path = None
        temp_input_to_clean = None
        if hasattr(video, "get_stream_source"):
            src = video.get_stream_source()
            if isinstance(src, (str, os.PathLike)) and Path(src).exists():
                in_video_path = str(src)
        if not in_video_path and isinstance(video, (str, os.PathLike)) and Path(video).exists():
            in_video_path = str(video)

        if not in_video_path:
            temp_dir = Path(folder_paths.get_temp_directory())
            temp_input_to_clean = str(temp_dir / f"trucy_tmp_in_{uuid.uuid4().hex}.mp4")
            if hasattr(video, "save_to"):
                video.save_to(temp_input_to_clean)
                in_video_path = temp_input_to_clean
            else:
                raise ValueError("无法解析输入的 VIDEO 对象数据源。")

        out_folder = target_dir
        os.makedirs(out_folder, exist_ok=True)
        out_filename = f"{filename_prefix}_{uuid.uuid4().hex[:8]}.mp4"
        final_path = os.path.join(out_folder, out_filename)

        temp_audio_path = None
        if audio is not None and "waveform" in audio and "sample_rate" in audio:
            waveform = audio["waveform"]
            sample_rate = audio["sample_rate"]
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_audio_path = f.name
            torchaudio.save(temp_audio_path, waveform.squeeze(0), sample_rate=sample_rate)

            cmd = [
                ffmpeg, "-y", "-v", "error",
                "-i", in_video_path,
                "-i", temp_audio_path,
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                final_path
            ]
        else:
            cmd = [
                ffmpeg, "-y", "-v", "error",
                "-i", in_video_path,
                "-c", "copy",
                final_path
            ]

        try:
            res = subprocess.run(cmd, capture_output=True, check=False)
            if res.returncode != 0:
                raise RuntimeError("ffmpeg 处理输入视频失败:\n" + res.stderr.decode("utf-8", errors="replace"))
        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except OSError:
                    pass
            if temp_input_to_clean and os.path.exists(temp_input_to_clean):
                try:
                    os.remove(temp_input_to_clean)
                except OSError:
                    pass

        return final_path

    def combine_video(self, frame_rate=16.0, loop_count=0, filename_prefix="TrucyVideo",
                      format="video/h264-mp4", pingpong=False, save_output=True,
                      images=None, video=None, audio=None, custom_path=r"D:\ComfyUI-Output",
                      prompt=None, extra_pnginfo=None, unique_id=None, **format_values):

        if images is None and video is None:
            raise ValueError("【Trucy 提示】: 'images' 和 'video' 输入至少需要连接一个！")
        if images is not None and video is not None:
            raise ValueError("【Trucy 提示】: 'images' 和 'video' 只能二选一输入，不能同时连接！")

        original_extra = extra_pnginfo or {}

        target_custom_path = str(custom_path).strip() if (custom_path and str(custom_path).strip()) else None
        default_out_dir = folder_paths.get_output_directory()
        has_custom = bool(target_custom_path and os.path.normcase(os.path.abspath(target_custom_path)) != os.path.normcase(os.path.abspath(default_out_dir)))

        # 2. 如果输入的是绿色 video 端口
        if video is not None:
            internal_dir = folder_paths.get_temp_directory() if has_custom else (default_out_dir if save_output else folder_paths.get_temp_directory())
            internal_path = self._process_video_input(video, audio, internal_dir, filename_prefix, False if has_custom else save_output)
            self._embed_metadata(internal_path, self._metadata(prompt, original_extra))
            
            final_return_path = internal_path
            
            if has_custom and os.path.isfile(internal_path):
                try:
                    os.makedirs(target_custom_path, exist_ok=True)
                    dest_path = os.path.join(target_custom_path, os.path.basename(internal_path))
                    if os.path.normcase(os.path.abspath(internal_path)) != os.path.normcase(os.path.abspath(dest_path)):
                        shutil.copy2(internal_path, dest_path)
                    final_return_path = dest_path
                except Exception as e:
                    print(f"[TrucyVideoCombine] 复制到自定义路径异常: {e}")

            video_out = VideoFromFile(final_return_path) if VideoFromFile is not None else final_return_path
            
            ui_info = {
                "gifs": [{
                    "filename": os.path.basename(internal_path),
                    "subfolder": "",
                    "type": "temp" if has_custom else ("output" if save_output else "temp"),
                    "format": "video/mp4",
                    "t": uuid.uuid4().hex[:6]
                }]
            }
            return {"ui": ui_info, "result": (video_out, final_return_path)}

        # 3. 如果输入的是蓝色 images 图像序列
        prefix = filename_prefix

        extra_info = copy.deepcopy(original_extra)
        workflow = extra_info.setdefault("workflow", {})
        workflow.setdefault("extra", {})["VHS_MetadataImage"] = False
        workflow["extra"]["VHS_KeepIntermediate"] = False

        vhs_save_output = False if has_custom else save_output

        result = _VHSVideoCombine().combine_video(
            images=images,
            frame_rate=frame_rate,
            loop_count=loop_count,
            filename_prefix=prefix,
            format=format,
            pingpong=pingpong,
            save_output=vhs_save_output,
            prompt=prompt,
            extra_pnginfo=extra_info,
            audio=audio,
            unique_id=unique_id,
            meta_batch=None,
            vae=None,
            **format_values,
        )

        ui = result.get("ui", {})
        filenames = result.get("result", ((vhs_save_output, []),))[0]
        output_files = list(filenames[1])
        if not output_files:
            return {"ui": ui, "result": (None, "")}

        internal_final_path = output_files[-1]

        for path in output_files[:-1]:
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:
                pass

        internal_final_path = self._clean_audio_suffix(internal_final_path)

        video_extensions = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"}
        if os.path.isfile(internal_final_path) and Path(internal_final_path).suffix.lower() in video_extensions:
            self._embed_metadata(internal_final_path, self._metadata(prompt, original_extra))
            
            final_return_path = internal_final_path

        if target_custom_path and os.path.isfile(internal_final_path):
            try:
                os.makedirs(target_custom_path, exist_ok=True)
                dest_path = os.path.join(target_custom_path, os.path.basename(internal_final_path))
                if os.path.normcase(os.path.abspath(internal_final_path)) != os.path.normcase(os.path.abspath(dest_path)):
                    shutil.copy2(internal_final_path, dest_path)
                final_return_path = dest_path
            except Exception as e:
                print(f"[TrucyVideoCombine] 复制到自定义路径异常: {e}")

        preview = ui.get("gifs", [{}])[0]
        if preview:
            preview.pop("workflow", None)
            preview["filename"] = os.path.basename(internal_final_path)
            if "fullpath" in preview:
                del preview["fullpath"]
            preview["t"] = uuid.uuid4().hex[:6]

        abs_final_return = os.path.abspath(final_return_path)
        video_out = VideoFromFile(abs_final_return) if VideoFromFile is not None else abs_final_return

        return {"ui": ui, "result": (video_out, abs_final_return)}


# ==============================================================================
# 🚀 新增节点：TrucyVideoCombineFast（完全继承原节点，引入 Topaz 极速批次管道）
# ==============================================================================
class TrucyVideoCombineFast(TrucyVideoCombine):
    """继承原节点全部接口与前端特性，但针对 images 序列合成引入 Topaz 级快速批次推流与 GPU 硬件编码。"""

    def _fast_mux_audio(self, ff, video_path, audio):
        """流复制极速合并音频（耗时 < 0.05s）"""
        try:
            wf = audio.get('waveform')
            sr = int(audio.get('sample_rate', 44100))
        except Exception:
            return video_path

        if wf is None or wf.numel() == 0:
            return video_path

        wf = wf.detach().cpu().float()
        if wf.dim() == 3:
            wf = wf.squeeze(0)
        channels = wf.size(0)
        audio_data = wf.transpose(0, 1).contiguous().numpy().tobytes()

        out_path = video_path[:-4] + '-audio.mp4'
        mux_args = [ff, '-v', 'error', '-y', '-i', video_path,
                    '-ar', str(sr), '-ac', str(channels),
                    '-f', 'f32le', '-i', '-',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                    '-shortest', out_path]
        try:
            r = subprocess.run(mux_args, input=audio_data,
                               capture_output=True, timeout=600)
            if r.returncode == 0 and os.path.isfile(out_path):
                try:
                    os.remove(video_path)
                except OSError:
                    pass
                return out_path
        except Exception as e:
            print(f'[TrucyVideoCombineFast] 音频合并异常: {e}')
        return video_path

    def combine_video(self, frame_rate=16.0, loop_count=0, filename_prefix="TrucyVideo",
                      format="video/h264-mp4", pingpong=False, save_output=True,
                      images=None, video=None, audio=None, custom_path=r"D:\ComfyUI-Output",
                      prompt=None, extra_pnginfo=None, unique_id=None, **format_values):

        # 1. 如果输入的是 video，或者选择了非常规非 mp4 格式，直接走父类的标准流程
        if video is not None or format != "video/h264-mp4" or images is None or images.size(0) == 0:
            return super().combine_video(
                frame_rate=frame_rate, loop_count=loop_count, filename_prefix=filename_prefix,
                format=format, pingpong=pingpong, save_output=save_output,
                images=images, video=video, audio=audio, custom_path=custom_path,
                prompt=prompt, extra_pnginfo=extra_pnginfo, unique_id=unique_id, **format_values
            )

        # 2. 针对 images + video/h264-mp4 执行 Topaz 极速渲染流
        original_extra = extra_pnginfo or {}
        target_custom_path = str(custom_path).strip() if (custom_path and str(custom_path).strip()) else None
        default_out_dir = folder_paths.get_output_directory()
        has_custom = bool(target_custom_path and os.path.normcase(os.path.abspath(target_custom_path)) != os.path.normcase(os.path.abspath(default_out_dir)))

        # 目录确定
        internal_dir = folder_paths.get_temp_directory() if has_custom else (default_out_dir if save_output else folder_paths.get_temp_directory())
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, internal_dir)
        os.makedirs(full_output_folder, exist_ok=True)
        out_filename = f"{filename}_{counter:05}.mp4"
        internal_final_path = os.path.join(full_output_folder, out_filename)

        # 处理 pingpong
        t = images
        if pingpong and t.size(0) > 2:
            import torch
            t = torch.cat([t, t.flip(dims=[0])[1:-1]], dim=0)

        total_frames, h, w, c = t.shape
        in_pix = 'rgba' if c == 4 else 'rgb24'

        ff = _ffmpeg_path()
        crf = format_values.get("crf", 19)
        pix_fmt = format_values.get("pix_fmt", "yuv420p")

        # 优先使用 GPU h264_nvenc 硬件加速，自动回退 CPU libx264
        if _supports_nvenc(ff):
            enc_args = ['-c:v', 'h264_nvenc', '-pix_fmt', pix_fmt,
                        '-preset', 'p7', '-rc', 'vbr', '-cq', str(crf), '-b:v', '0']
        else:
            enc_args = ['-c:v', 'libx264', '-pix_fmt', pix_fmt,
                        '-crf', str(crf), '-preset', 'medium']

        args = [ff, '-v', 'error', '-f', 'rawvideo', '-pix_fmt', in_pix,
                '-color_range', 'pc', '-colorspace', 'rgb',
                '-color_primaries', 'bt709', '-color_trc', 'iec61966-2-1',
                '-s', f'{w}x{h}', '-r', str(frame_rate), '-i', '-'] \
            + enc_args \
            + ['-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2:out_color_matrix=bt709',
               '-color_range', 'tv', '-colorspace', 'bt709',
               '-color_primaries', 'bt709', '-color_trc', 'bt709',
               '-movflags', '+faststart', '-y', internal_final_path]

        pbar = ProgressBar(total_frames) if ProgressBar is not None else None

        # Topaz 批次 SIMD 快速转换推流（256 帧一组）
        BATCH = 256
        import torch
        with subprocess.Popen(args, stdin=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            for start in range(0, total_frames, BATCH):
                batch = t[start:start + BATCH].detach()
                if batch.is_cuda:
                    batch = batch.cpu()
                # 矢量化快速提升并转 uint8
                arr = batch.float().clamp_(0.0, 1.0).mul_(255.0).round_().to(torch.uint8).numpy()
                proc.stdin.write(arr.tobytes())
                if pbar is not None:
                    pbar.update(len(batch))
            proc.stdin.close()
            err = proc.stderr.read()
            proc.wait()

        if proc.returncode != 0:
            if os.path.exists(internal_final_path):
                try:
                    os.remove(internal_final_path)
                except OSError:
                    pass
            raise RuntimeError('TrucyVideoCombineFast ffmpeg 失败:\n' + err.decode(errors='replace')[-800:])

        # 合并音频
        if audio is not None:
            internal_final_path = self._fast_mux_audio(ff, internal_final_path, audio)

        # 剔除 -audio 后缀
        internal_final_path = self._clean_audio_suffix(internal_final_path)

        # 嵌入元数据
        if format_values.get("save_metadata", True):
            self._embed_metadata(internal_final_path, self._metadata(prompt, original_extra))

        final_return_path = internal_final_path

        # 自定义路径存储
        if target_custom_path and os.path.isfile(internal_final_path):
            try:
                os.makedirs(target_custom_path, exist_ok=True)
                dest_path = os.path.join(target_custom_path, os.path.basename(internal_final_path))
                if os.path.normcase(os.path.abspath(internal_final_path)) != os.path.normcase(os.path.abspath(dest_path)):
                    shutil.copy2(internal_final_path, dest_path)
                final_return_path = dest_path
            except Exception as e:
                print(f"[TrucyVideoCombineFast] 复制到自定义路径异常: {e}")

        # 前端 UI 字典构建
        ui_info = {
            "gifs": [{
                "filename": os.path.basename(internal_final_path),
                "subfolder": subfolder if not has_custom else "",
                "type": "temp" if has_custom else ("output" if save_output else "temp"),
                "format": "video/mp4",
                "t": uuid.uuid4().hex[:6]
            }]
        }

        abs_final_return = os.path.abspath(final_return_path)
        video_out = VideoFromFile(abs_final_return) if VideoFromFile is not None else abs_final_return

        return {"ui": ui_info, "result": (video_out, abs_final_return)}


NODE_CLASS_MAPPINGS = {
    "TrucyVideoCombine": TrucyVideoCombine,
    "TrucyVideoCombineFast": TrucyVideoCombineFast,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyVideoCombine": "Video Combine (Trucy)",
    "TrucyVideoCombineFast": "Video Combine Fast (Trucy)",
}