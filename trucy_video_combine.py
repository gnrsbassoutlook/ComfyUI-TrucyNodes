"""
Trucy Video Combine Node
基于最新 Video Combine V2 深度优化：
1. 单视频输出（无冗余 PNG / 无中间静音文件，完整注入 Workflow 元数据）
2. 自动移除合成音频后烦人的 '-audio' 后缀，保持干净命名
3. 支持自定义保存路径 (custom_path)
4. 输出绝对文件路径 (filepath) 文本插槽
5. 全输入带默认值的容错机制，防止前端报错插口丢失
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
            display_name="🚀 Video-Combine-Trucy",
            category="TrucyNodes/Video",
            description="无冗余文件的视频保存节点，去-audio后缀，支持自定义路径并输出绝对文件路径。",
            search_aliases=["video combine", "trucy video", "保存视频", "视频合并"],
            inputs=[
                io.MultiType.Input(io.Image.Input("images"), [io.Image, io.Latent]),
                io.Audio.Input("audio", optional=True),
                VHSBatchManager.Input("meta_batch", display_name="meta_batch", optional=True),
                io.Vae.Input("vae", optional=True),
                # 借鉴肥猴 v2.9.4：使用带默认值的 optional + socketless，杜绝缺失输入报错
                io.Float.Input("frame_rate", default=8.0, min=1.0, step=1.0, optional=True, socketless=True),
                io.Int.Input("loop_count", default=0, min=0, max=100, step=1, optional=True, socketless=True),
                io.String.Input("filename_prefix", default="AnimateDiff", optional=True, socketless=True),
                io.String.Input("custom_path", default="", display_name="custom_path (optional)", optional=True, socketless=True),
                io.Combo.Input(
                    "format",
                    options=["image/gif", "image/webp"] + ffmpeg_formats,
                    extra_dict={"formats": format_widgets},
                    optional=True,
                    socketless=True,
                ),
                io.Boolean.Input("pingpong", default=False, optional=True, socketless=True),
                io.Boolean.Input("save_output", default=True, optional=True, socketless=True),
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
        frame_rate=8.0,
        loop_count=0,
        filename_prefix="AnimateDiff",
        format="image/gif",
        pingpong=False,
        save_output=True,
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

        # 1. 嵌入工作流元数据
        video_extensions = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"}
        if os.path.splitext(final_path)[1].lower() in video_extensions:
            cls._embed_metadata(final_path, cls._metadata(cls.hidden.prompt, original_extra))

        # 2. 清理原版生成的中间无声视频等非最终文件
        for path in output_files[:-1]:
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:
                pass

        # 3. 彻底清除烦人的 '-audio' 后缀
        file_dir, file_name = os.path.split(final_path)
        name_stem, ext = os.path.splitext(file_name)
        if name_stem.endswith("-audio"):
            clean_stem = name_stem[:-6]
            clean_name = f"{clean_stem}{ext}"
            clean_path = os.path.join(file_dir, clean_name)
            # 如果目标已存在（例如同名），先移除
            if os.path.exists(clean_path):
                try: os.remove(clean_path)
                except OSError: pass
            try:
                os.rename(final_path, clean_path)
                final_path = clean_path
                file_name = clean_name
            except Exception as e:
                print(f"[TrucyVideoCombine] 重命名去除 -audio 失败: {e}")

        # 4. 自定义路径处理
        resolved_output_path = final_path
        clean_custom = (custom_path or "").strip().replace('"', "")
        if clean_custom:
            try:
                target_dir = os.path.abspath(clean_custom)
                os.makedirs(target_dir, exist_ok=True)
                target_file = os.path.join(target_dir, file_name)
                shutil.copy2(final_path, target_file)
                resolved_output_path = target_file
            except Exception as e:
                print(f"[TrucyVideoCombine] 复制到自定义路径失败: {e}")

        # 同步更新 UI 返回中的文件名显示（防止前端找不到预览）
        clean_final_name = os.path.basename(final_path)
        if "gifs" in ui:
            for item in ui["gifs"]:
                if "filename" in item and item["filename"].endswith(f"-audio{ext}"):
                    item["filename"] = clean_final_name

        return io.NodeOutput((save_output, [final_path]), resolved_output_path, ui=ui)