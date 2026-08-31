"""
Trucy Video Combine Node
基于肥猴大佬修改版 Video Combine 优化重构，集成：
1. 单视频输出（无冗余 PNG / 无中间静音文件，完整注入 Workflow 元数据）
2. 支持自定义保存路径 (custom_path)
3. 增加绝对文件路径 (filepath) 文本输出
"""

import copy
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import folder_paths
import nodes as comfy_nodes
from comfy.cli_args import args
from comfy_api.latest import io

VHSBatchManager = io.Custom("VHS_BatchManager")
VHSFilenames = io.Custom("VHS_FILENAMES")
FORMAT_DIRECTORY = Path(__file__).with_name("video_formats")


def _original_vhs_class():
    """获取原版 VHS 节点类"""
    node_class = comfy_nodes.NODE_CLASS_MAPPINGS.get("VHS_VideoCombine")
    if node_class is None:
        raise RuntimeError(
            "Video-Combine-Trucy 需要先安装 ComfyUI-VideoHelperSuite (VHS) 插件！"
        )
    return node_class


def _format_definitions():
    """优先从原版 VHS 获取格式定义，否则从本地 video_formats 目录读取"""
    original = comfy_nodes.NODE_CLASS_MAPPINGS.get("VHS_VideoCombine")
    if original is not None:
        try:
            config = original.INPUT_TYPES()["required"]["format"]
            return list(config[0]), copy.deepcopy(config[1]["formats"])
        except Exception:
            pass

    names = [path.stem for path in FORMAT_DIRECTORY.glob("*.json")]
    formats = [f"video/{name}" for name in names]
    widgets = {"image/webp": [["lossless", "BOOLEAN", {"default": True}]]}
    return formats, widgets


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


class TrucyVideoCombine(io.ComfyNode):
    """Trucy 增强版视频合并节点"""

    @classmethod
    def define_schema(cls):
        ffmpeg_formats, format_widgets = _format_definitions()
        format_widgets["image/webp"] = [["lossless", "BOOLEAN", {"default": True}]]

        return io.Schema(
            node_id="TrucyVideoCombine",
            display_name="Video-Combine-Trucy",
            category="TrucyNodes/Video",
            description="无冗余文件的视频保存节点，支持自定义路径并输出绝对文件路径。",
            search_aliases=["video combine", "trucy video", "保存视频", "视频合并"],
            inputs=[
                io.MultiType.Input(io.Image.Input("images"), [io.Image, io.Latent]),
                io.Audio.Input("audio", optional=True),
                VHSBatchManager.Input("meta_batch", display_name="meta_batch", optional=True),
                io.Vae.Input("vae", optional=True),
                io.Float.Input("frame_rate", default=8.0, min=1.0, step=1.0),
                io.Int.Input("loop_count", default=0, min=0, max=100, step=1),
                io.String.Input("filename_prefix", default="AnimateDiff"),
                io.String.Input("custom_path", default="", display_name="custom_path (optional)"),
                io.Combo.Input(
                    "format",
                    options=["image/gif", "image/webp"] + ffmpeg_formats,
                    extra_dict={"formats": format_widgets},
                ),
                io.Boolean.Input("pingpong", default=False),
                io.Boolean.Input("save_output", default=True),
            ],
            outputs=[
                VHSFilenames.Output("Filenames", display_name="视频"),
                io.String.Output("filepath", display_name="文件路径"),
            ],
            hidden=[io.Hidden.prompt, io.Hidden.extra_pnginfo, io.Hidden.unique_id],
            is_output_node=True,
        )

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
            raise ProcessLookupError("未找到 ffmpeg，无法向视频写入元数据。")
        folder = os.path.dirname(final_path)
        suffix = Path(final_path).suffix
        metadata_path = os.path.join(folder, f".trucy-metadata-{uuid.uuid4().hex}.txt")
        replacement = os.path.join(folder, f".trucy-final-{uuid.uuid4().hex}{suffix}")
        _write_ffmetadata(metadata, metadata_path)
        command = [
            ffmpeg, "-v", "error", "-y", "-i", final_path, "-i", metadata_path,
            "-map", "0", "-map_metadata", "1", "-c", "copy"
        ]
        if suffix.lower() in {".mp4", ".m4v", ".mov"}:
            command += ["-movflags", "use_metadata_tags"]
        command.append(replacement)
        try:
            completed = subprocess.run(command, capture_output=True, check=False)
            if completed.returncode != 0:
                raise RuntimeError(
                    "ffmpeg 嵌入元数据失败:\n" + completed.stderr.decode("utf-8", errors="replace")
                )
            os.replace(replacement, final_path)
        finally:
            for path in (metadata_path, replacement):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except OSError:
                    pass

    @classmethod
    def execute(
        cls,
        images,
        frame_rate,
        loop_count,
        filename_prefix,
        format,
        pingpong,
        save_output,
        custom_path="",
        audio=None,
        meta_batch=None,
        vae=None,
        **format_values,
    ):
        original_extra = cls.hidden.extra_pnginfo or {}
        extra_pnginfo = copy.deepcopy(original_extra)
        workflow = extra_pnginfo.setdefault("workflow", {})
        workflow.setdefault("extra", {})["VHS_MetadataImage"] = False
        workflow["extra"]["VHS_KeepIntermediate"] = False

        result = _original_vhs_class()().combine_video(
            images=images,
            frame_rate=frame_rate,
            loop_count=loop_count,
            filename_prefix=filename_prefix,
            format=format,
            pingpong=pingpong,
            save_output=save_output,
            prompt=cls.hidden.prompt,
            extra_pnginfo=extra_pnginfo,
            audio=audio,
            unique_id=cls.hidden.unique_id,
            meta_batch=meta_batch,
            vae=vae,
            **format_values,
        )

        ui = result.get("ui", {})
        filenames = result.get("result", ((save_output, []),))[0]
        output_files = list(filenames[1])
        if not output_files:
            return io.NodeOutput((save_output, []), "", ui=ui)

        final_path = output_files[-1]
        cls._embed_metadata(final_path, cls._metadata(cls.hidden.prompt, original_extra))

        # 清理原版生成的中间无声视频等非最终文件
        for path in output_files[:-1]:
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:
                pass

        # --- 自定义保存路径支持 ---
        resolved_output_path = final_path
        clean_custom = custom_path.strip().replace('"', "")
        if clean_custom:
            try:
                target_dir = os.path.abspath(clean_custom)
                os.makedirs(target_dir, exist_ok=True)
                dest_file = os.path.join(target_dir, os.path.basename(final_path))
                shutil.copy2(final_path, dest_file)
                resolved_output_path = dest_file
                print(f"[TrucyNodes] Video successfully saved to custom path: {dest_file}")
            except Exception as e:
                print(f"[TrucyNodes] Warning: Failed to copy to custom_path '{clean_custom}': {e}")

        preview = ui.get("gifs", [{}])[0]
        if preview:
            preview.pop("workflow", None)
            preview["filename"] = os.path.basename(final_path)
            preview["fullpath"] = resolved_output_path

        # 同时返回 视频结构元组 和 字符串格式的完整文件路径
        return io.NodeOutput(
            (save_output, [final_path]),
            os.path.abspath(resolved_output_path),
            ui=ui,
        )


NODE_CLASS_MAPPINGS = {
    "TrucyVideoCombine": TrucyVideoCombine,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyVideoCombine": "Video-Combine-Trucy",
}