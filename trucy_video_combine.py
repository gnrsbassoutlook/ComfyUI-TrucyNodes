"""VHS Video Combine standard implementation compatible with all FeiHou & ComfyUI extensions."""

import copy
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import folder_paths
from comfy.cli_args import args

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


def _write_ffmetadata(metadata, path):
    def escape(key, value):
        text = json.dumps(value, ensure_ascii=False)
        text = text.replace("\\", "\\\\").replace(";", "\\;").replace("#", "\\#")
        text = text.replace("=", "\\=").replace("\n", "\\\n")
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
    """Standard Video Combine with Filenames(VHS_FILENAMES) and filepath(STRING) outputs."""

    @classmethod
    def INPUT_TYPES(cls):
        ffmpeg_formats, format_widgets = _get_video_formats()
        format_widgets["image/webp"] = [["lossless", "BOOLEAN", {"default": True}]]
        return {
            "required": {
                "images": ("IMAGE",),
                "frame_rate": ("FLOAT", {"default": 8.0, "min": 1.0, "step": 1.0}),
                "loop_count": ("INT", {"default": 0, "min": 0, "max": 100, "step": 1}),
                "filename_prefix": ("STRING", {"default": "AnimateDiff"}),
                "format": (["image/gif", "image/webp"] + ffmpeg_formats, {"formats": format_widgets}),
                "pingpong": ("BOOLEAN", {"default": False}),
                "save_output": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "audio": ("AUDIO",),
                "meta_batch": ("VHS_BatchManager",),
                "vae": ("VAE",),
                "custom_path": ("STRING", {"default": ""}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("VHS_FILENAMES", "STRING")
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

    def combine_video(self, images, frame_rate=8.0, loop_count=0, filename_prefix="AnimateDiff",
                      format="image/gif", pingpong=False, save_output=True, audio=None,
                      meta_batch=None, vae=None, custom_path="", prompt=None, extra_pnginfo=None,
                      unique_id=None, **format_values):

        prefix = filename_prefix
        if custom_path and str(custom_path).strip():
            clean_path = str(custom_path).strip().strip("/\\")
            prefix = os.path.join(clean_path, prefix)

        original_extra = extra_pnginfo or {}
        extra_info = copy.deepcopy(original_extra)
        workflow = extra_info.setdefault("workflow", {})
        workflow.setdefault("extra", {})["VHS_MetadataImage"] = False
        workflow["extra"]["VHS_KeepIntermediate"] = False

        result = _VHSVideoCombine().combine_video(
            images=images,
            frame_rate=frame_rate,
            loop_count=loop_count,
            filename_prefix=prefix,
            format=format,
            pingpong=pingpong,
            save_output=save_output,
            prompt=prompt,
            extra_pnginfo=extra_info,
            audio=audio,
            unique_id=unique_id,
            meta_batch=meta_batch,
            vae=vae,
            **format_values,
        )

        ui = result.get("ui", {})
        filenames = result.get("result", ((save_output, []),))[0]
        output_files = list(filenames[1])
        if not output_files:
            return {"ui": ui, "result": ((save_output, []), "")}

        final_path = output_files[-1]
        video_extensions = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"}
        if os.path.isfile(final_path) and Path(final_path).suffix.lower() in video_extensions:
            self._embed_metadata(final_path, self._metadata(prompt, original_extra))

        for path in output_files[:-1]:
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:
                pass

        preview = ui.get("gifs", [{}])[0]
        if preview:
            preview.pop("workflow", None)
            preview["filename"] = os.path.basename(final_path)
            preview["fullpath"] = final_path

        abs_final_path = os.path.abspath(final_path)
        # 严格返回：(视频包, 路径字符串)
        return {"ui": ui, "result": ((save_output, [final_path]), abs_final_path)}


NODE_CLASS_MAPPINGS = {
    "TrucyVideoCombine": TrucyVideoCombine
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyVideoCombine": "Video Combine (Trucy)"
}