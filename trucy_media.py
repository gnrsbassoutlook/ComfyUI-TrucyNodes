"""TrucyLLM · 多参考素材输入层（图片1-9 / 音频1-3；视频端口已按用户决定摘除）。

两条铁律（用户底线，源自批处理连续性要求）：
1. 编号保留输入槽位号（从 1 起），空槽位不重编号——与下游多参 text encoder 一一对应；
2. 空值安全：None / 零尺寸张量 / ExecutionBlocker（上游被静音的占位对象）/
   转换失败一律跳过并记日志，绝不报错卡流水线；空槽位不进发给 LLM 的 payload。

标签规范按 Skill 家族切换：H3 = <Picture N>/<Audio N>；QWI = <imageN>。
上送方式：图片 → JPEG data URI（最长边 1280）；音频 → numpy STFT 频谱图。
收集视频/_分析视频 为休眠后端（端口已摘除，无节点调用，单测仍覆盖；
复活 = 恢复 视频槽输入() 注册 + 节点里加一行 收集视频(kwargs)）。
不依赖 ComfyUI，可独立单测。
"""
import os

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
图片槽上限 = 9          # H3 官方 9 张；QWI 官方 10 张，做 9 槽覆盖两者
视频槽上限 = 3          # H3 官方 3 个
音频槽上限 = 3          # H3 官方 3 个
参考图最长边 = 1280     # 发给 LLM 前缩放（提示词重写看内容，不需要原图精度）
采样帧最长边 = 1024     # 视频采样帧分辨率
视频采样帧数 = 4
音频截断秒 = 15.0       # 超长音频只分析前 15 秒（控 STFT 成本）


def _日志(msg):
    print(f"\033[36m[TrucyLLM·素材]\033[0m {msg}")


# ---------------------------------------------------------------------------
# 输入端口声明（ optional ，未连接 = None，旧工作流零影响）
# ---------------------------------------------------------------------------
def 图片槽输入(数量=None):
    """参考图槽位（1 起编号，编号即下游 text encoder 槽位号）。

    数量=None 时用默认上限 9（H3 官方参考位上限）；
    图像推理等对齐 llama-TE 形态的节点传 8（llama-TE 的 QwenTE图像推理 即 8 图输入）。
    """
    上限 = 图片槽上限 if 数量 is None else max(1, min(int(数量), 图片槽上限))
    return {
        f"🖼️ 参考图{i}": ("IMAGE", {
            "tooltip": f"参考图片槽位 {i}/{上限}（1 起编号，与下游多参 text encoder 槽位一一对应；"
                       "空置/断连不报错，也不会发给大脑）。H3 模式按 <Picture N> 引用，"
                       "Qwen-Image-2.1 模式按 <imageN> 引用。",
        })
        for i in range(1, 上限 + 1)
    }


# 视频参考端口已按用户决定从所有节点摘除（99.99% 不用），端口声明随之删除；
# 收集视频/_分析视频 保留为休眠后端（无任何节点调用，单测仍覆盖），
# 复活方式：恢复本函数注册 + 在对话/H3提示词节点里加一行 收集视频(kwargs)。


def 音频槽输入():
    return {
        f"🎵 参考音频{i}": ("AUDIO", {
            "tooltip": f"参考音频槽位 {i}/{音频槽上限}（H3 模式用；自动生成频谱图发给视觉大脑；"
                       "Qwen-Image-2.1 模式自动忽略；空置不报错）。",
        })
        for i in range(1, 音频槽上限 + 1)
    }


# ---------------------------------------------------------------------------
# 空值判定（核心铁律 2）
# ---------------------------------------------------------------------------
def _输入被静音(t):
    """ComfyUI 里上游节点被静音/旁路（mode=mute）时，输入端口收到的不是真实值，
    而是 comfy_execution.graph_utils.ExecutionBlocker 占位对象。

    按类型名识别（不 import，避免非 ComfyUI 环境导入炸）。不识别的后果：
    放行后在下游属性访问处崩掉，或报一条具有误导性的「分析失败」。
    """
    return t is not None and type(t).__name__ == "ExecutionBlocker"


def _张量可用(t):
    """None / 空串 / 零尺寸 / 空批次 / ExecutionBlocker 都算空值。

    覆盖 Excel 制表 n/a → 硬盘空图 → 端口为空 的整条场景：
    未连接（None）、LoadImage 输出空张量（如 [1,0,0,3]）都安全跳过。
    ExecutionBlocker：ComfyUI 里上游节点被静音/旁路时送进端口的占位对象
    （comfy_execution.graph_utils.ExecutionBlocker）——没有 shape/numel，
    不识别会被当成有效值放行，然后在下游 .shape[1] 崩掉。
    """
    if t is None:
        return False
    if isinstance(t, str):
        return bool(t.strip())
    if type(t).__name__ == "ExecutionBlocker":
        return False
    try:
        shape = tuple(getattr(t, "shape", ()) or ())
        if shape and any(int(d) <= 0 for d in shape):
            return False
        numel = getattr(t, "numel", None)
        if callable(numel):
            try:
                if int(numel()) == 0:
                    return False
            except Exception:
                pass
    except Exception:
        return True
    return True


def 已连接音频(kwargs):
    """是否接入了任意音频槽位（QWI 模式用来发忽略提示）。

    视频端口已摘除，这里只查音频槽位；键名 🎵 必须与 音频槽输入() 逐字一致。
    """
    for i in range(1, 音频槽上限 + 1):
        if kwargs.get(f"🎵 参考音频{i}") is not None:
            return True
    return False


# ---------------------------------------------------------------------------
# 张量 → data URI
# ---------------------------------------------------------------------------
def _pil转data_uri(pil, 最长边=参考图最长边, 质量=88):
    """PIL → (data_uri, (w,h))。超长边缩放；有透明区存 PNG，否则 JPEG。"""
    import base64
    import io

    from PIL import Image

    image = pil
    if max(image.size) > 最长边:
        scale = 最长边 / float(max(image.size))
        image = image.resize(
            (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
            Image.Resampling.LANCZOS,
        )
    尺寸 = image.size
    buf = io.BytesIO()
    try:
        透明 = image.mode == "RGBA" and image.getchannel("A").getextrema()[0] < 255
    except Exception:
        透明 = False
    if 透明:
        image.save(buf, format="PNG", optimize=True)
        mime = "image/png"
    else:
        image.convert("RGB").save(buf, format="JPEG", quality=质量, optimize=True)
        mime = "image/jpeg"
    uri = f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    return uri, 尺寸


def _张量转data_uri列表(t, 最长边=参考图最长边):
    """ComfyUI IMAGE 张量 → [(data_uri, (w,h)), ...]；失败抛异常由调用方兜底。"""
    import numpy as np
    from PIL import Image

    if hasattr(t, "get_components"):  # 兼容 VideoInput 等容器类型
        comps = t.get_components()
        inner = getattr(comps, "images", None)
        if inner is not None:
            t = inner
    if hasattr(t, "cpu"):
        arr = t.cpu().numpy()
    elif isinstance(t, np.ndarray):
        arr = t
    else:
        raise ValueError(f"无法识别的图片输入类型: {type(t).__name__}")
    if arr.ndim == 3:
        arr = arr[None, ...]
    if arr.ndim != 4 or arr.shape[0] == 0:
        raise ValueError("图片批次为空")
    out = []
    for i in range(arr.shape[0]):
        frame = np.clip(arr[i] * 255.0, 0, 255).astype(np.uint8)
        h, w = int(frame.shape[0]), int(frame.shape[1])
        if h <= 0 or w <= 0:
            raise ValueError("零尺寸图片")
        if frame.ndim == 2:
            pil = Image.fromarray(frame, "L").convert("RGB")
        else:
            ch = int(frame.shape[2])
            if ch == 1:
                pil = Image.fromarray(frame[..., 0], "L").convert("RGB")
            elif ch == 3:
                pil = Image.fromarray(frame, "RGB")
            elif ch == 4:
                pil = Image.fromarray(frame, "RGBA")
            else:
                raise ValueError(f"不支持的通道数: {ch}")
        out.append(_pil转data_uri(pil, 最长边))
    return out


# ---------------------------------------------------------------------------
# 收集：图片（槽位编号保留）
# ---------------------------------------------------------------------------
def 收集图片(kwargs, 旧图=None, 最长边=None, 日志=_日志):
    """按槽位收集参考图。空/坏槽位跳过不报错。

    条目: {"kind": "图片", "slot": 槽位号或None(旧端口), "n": 标签编号,
           "label": 中文名, "uri": data_uri, "尺寸": (w, h)}
    旧「图片」端口（兼容老工作流）批次展开，编号接在已用槽位之后。
    最长边=None 时用全局参考图最长边（不在定义时绑定，免得改全局不生效）。
    """
    if 最长边 is None or int(最长边) <= 0:
        最长边 = 参考图最长边
    最长边 = int(最长边)
    条目 = []
    已用 = set()
    for slot in range(1, 图片槽上限 + 1):
        t = kwargs.get(f"🖼️ 参考图{slot}")
        if not _张量可用(t):
            if t is not None:
                日志(f"参考图{slot}: 输入为空/零尺寸，已跳过（不发给大脑）")
            continue
        try:
            uris = _张量转data_uri列表(t, 最长边)
        except Exception as e:
            日志(f"参考图{slot}: 转换失败（{e}），已跳过，不影响工作流继续")
            continue
        if not uris:
            continue
        if len(uris) > 1:
            日志(f"参考图{slot}: 批次含 {len(uris)} 张，仅取第 1 张（槽位与下游一一对应）")
        uri, 尺寸 = uris[0]
        条目.append({"kind": "图片", "slot": slot, "n": slot, "label": f"参考图{slot}",
                     "uri": uri, "尺寸": 尺寸})
        已用.add(slot)
    if _张量可用(旧图):
        try:
            uris = _张量转data_uri列表(旧图, 最长边)
        except Exception as e:
            日志(f"图片端口: 转换失败（{e}），已跳过")
            uris = []
        n = max(已用, default=0)
        for idx, (uri, 尺寸) in enumerate(uris, start=1):
            n += 1
            条目.append({"kind": "图片", "slot": None, "n": n,
                         "label": f"图片端口第{idx}张", "uri": uri, "尺寸": 尺寸})
    return 条目


# ---------------------------------------------------------------------------
# 收集：视频（cv2 采样帧）—— ※ 休眠后端：端口已摘除，无节点调用，单测仍覆盖
# ---------------------------------------------------------------------------
def _视频临时路径(video, slot):
    """VIDEO 对象 / 路径 / dict → 临时文件路径。返回 (path, 需清理)。"""
    import tempfile
    from pathlib import Path

    if isinstance(video, (str, os.PathLike)):
        p = str(video).strip()
        if p and Path(p).is_file():
            return p, False
        raise ValueError(f"参考视频{slot} 路径不存在")
    if isinstance(video, dict):
        for key in ("file_path", "path", "filename"):
            v = video.get(key)
            if isinstance(v, str) and Path(v).is_file():
                return v, False
        raise ValueError(f"参考视频{slot} 无法解析")
    if not hasattr(video, "save_to"):
        raise ValueError(f"参考视频{slot} 不是有效的 ComfyUI VIDEO 输入")
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    handle.close()
    try:
        saved = video.save_to(handle.name)
        ok = saved is not False and Path(handle.name).is_file() and Path(handle.name).stat().st_size > 0
        if not ok:
            raise ValueError(f"参考视频{slot} 保存失败")
        return handle.name, True
    except Exception:
        Path(handle.name).unlink(missing_ok=True)
        raise


def _分析视频(video, slot, 采样帧数=视频采样帧数):
    """均匀采样帧 → JPEG data URI（视觉大脑直接看画面内容）。"""
    import cv2
    import numpy as np
    from PIL import Image

    path, 临时 = _视频临时路径(video, slot)
    cap = None
    try:
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise ValueError("无法解码")
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if fps <= 0 or count <= 0 or w <= 0 or h <= 0:
            raise ValueError("缺少帧率/帧数/尺寸信息")
        duration = count / fps
        帧数 = max(2, int(采样帧数))
        时间点 = np.linspace(0.0, max(0.0, duration - 1.0 / fps), 帧数)
        frames = []
        for t in 时间点:
            cap.set(cv2.CAP_PROP_POS_MSEC, float(t) * 1000.0)
            ok, frame = cap.read()
            if not ok or frame is None:
                fi = min(count - 1, max(0, round(float(t) * fps)))
                cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
                ok, frame = cap.read()
            if not ok or frame is None:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            uri, _ = _pil转data_uri(Image.fromarray(rgb), 最长边=采样帧最长边, 质量=84)
            frames.append({"time": float(t), "uri": uri})
        if not frames:
            raise ValueError("未采集到有效帧")
        return {"duration": duration, "fps": fps, "width": w, "height": h, "frames": frames}
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
        if 临时:
            from pathlib import Path

            Path(path).unlink(missing_ok=True)


def 收集视频(kwargs, 采样帧数=视频采样帧数, 日志=_日志):
    条目 = []
    for slot in range(1, 视频槽上限 + 1):
        v = kwargs.get(f"🎞️ 参考视频{slot}")
        if v is None:
            continue
        if _输入被静音(v):
            日志(f"参考视频{slot}: 上游节点被静音（ExecutionBlocker），已跳过")
            continue
        try:
            info = _分析视频(v, slot, 采样帧数)
        except Exception as e:
            日志(f"参考视频{slot}: 采样失败（{e}），已跳过，不影响工作流继续")
            continue
        条目.append({"kind": "视频", "slot": slot, "n": slot, "label": f"参考视频{slot}", **info})
    return 条目


# ---------------------------------------------------------------------------
# 收集：音频（numpy STFT 频谱图，无需 matplotlib/ffmpeg）
# ---------------------------------------------------------------------------
def _音频波形(audio):
    """AUDIO dict → (mono float32 ndarray, sample_rate)。"""
    import numpy as np

    if not isinstance(audio, dict):
        raise ValueError("无法读取 AUDIO 输入")
    wf = audio.get("waveform")
    if wf is None:
        raise ValueError("AUDIO 输入缺少 waveform")
    if hasattr(wf, "detach"):
        wf = wf.detach()
    if hasattr(wf, "cpu"):
        wf = wf.cpu().numpy()
    arr = np.asarray(wf, dtype=np.float32)
    arr = np.squeeze(arr)
    if arr.ndim == 1:
        mono = arr
    elif arr.ndim == 2:
        mono = arr.mean(axis=0) if arr.shape[0] < arr.shape[1] else arr.mean(axis=1)
    else:
        raise ValueError(f"无法识别声道格式: {arr.shape}")
    sr = int(audio.get("sample_rate") or audio.get("sampler_rate") or 44100)
    return mono, sr


# viridis 风格色带（深紫→蓝→青→绿→黄）
_VIRIDIS = [(68, 1, 84), (59, 82, 139), (33, 145, 140), (94, 201, 98), (253, 231, 37)]


def _着色(gray_u8):
    import numpy as np
    from PIL import Image

    anchors = np.array(_VIRIDIS, dtype=np.float32)
    pos = np.linspace(0.0, 1.0, len(anchors))
    xs = np.linspace(0.0, 1.0, 256)
    lut = np.zeros((256, 3), dtype=np.uint8)
    for c in range(3):
        lut[:, c] = np.clip(np.interp(xs, pos, anchors[:, c]), 0, 255).astype(np.uint8)
    return Image.fromarray(lut[gray_u8], "RGB")


def _分析音频(audio, slot, 截断秒=音频截断秒):
    """波形 → 频谱图 data URI + 统计信息（时长/采样率/RMS/静音比例）。"""
    import base64
    import io

    import numpy as np
    from PIL import Image

    mono, sr = _音频波形(audio)
    n = min(mono.size, int(截断秒 * sr))
    x = mono[:n]
    frame, hop = 1024, 512
    if x.size < frame:
        raise ValueError("音频太短，无法生成频谱图")
    x = x - x.mean()
    starts = np.arange(0, x.size - frame + 1, hop)
    if starts.size < 2:
        raise ValueError("有效帧不足")
    win = np.hanning(frame).astype(np.float32)
    spec = np.abs(np.fft.rfft(x[starts[:, None] + np.arange(frame)[None, :]] * win, axis=1))
    db = 20.0 * np.log10(spec + 1e-8)
    fmax_bin = max(8, min(db.shape[1], int(8000.0 * frame / sr)))
    db = db[:, :fmax_bin]
    lo, hi = np.percentile(db, 5), np.percentile(db, 95)
    norm = np.clip((db - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    gray = (norm.T * 255.0).astype(np.uint8)  # [频率, 时间]
    img = _着色(gray)
    if img.width > 768:
        img = img.resize((768, max(1, round(img.height * 768 / img.width))),
                         Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    peak = float(np.abs(x).max()) or 1.0
    return {
        "duration": x.size / float(sr),
        "sample_rate": sr,
        "spectrogram_uri": uri,
        "rms": float(np.sqrt(np.mean(x * x))),
        "silence_ratio": float(np.mean(np.abs(x) < 0.01 * peak)),
    }


def 收集音频(kwargs, 日志=_日志):
    条目 = []
    for slot in range(1, 音频槽上限 + 1):
        a = kwargs.get(f"🎵 参考音频{slot}")
        if a is None:
            continue
        if _输入被静音(a):
            日志(f"参考音频{slot}: 上游节点被静音（ExecutionBlocker），已跳过")
            continue
        try:
            if isinstance(a, dict):
                wf = a.get("waveform")
                if wf is None or (hasattr(wf, "numel") and int(wf.numel()) == 0):
                    日志(f"参考音频{slot}: 波形为空，已跳过（不发给大脑）")
                    continue
            info = _分析音频(a, slot)
        except Exception as e:
            日志(f"参考音频{slot}: 分析失败（{e}），已跳过，不影响工作流继续")
            continue
        条目.append({"kind": "音频", "slot": slot, "n": slot, "label": f"参考音频{slot}", **info})
    return 条目


# ---------------------------------------------------------------------------
# 标签规范：按 Skill 家族切换（单节点内部切换）
# ---------------------------------------------------------------------------
_H3类目 = {"图片": "Picture", "视频": "Video", "音频": "Audio"}

# 标签家族登记册（严格匹配用：自动识别只认这些 Skill id，别的猜不出就不猜）
H3标签家族 = ("h3-prompt-writing",)
QWI标签家族 = (
    "qwen-image-2-1-prompter",           # 官方 8 步法 Skill
    "qwen-image-t2i-system-prompt",      # XB 转换版：官方 T2I 完整规范
    "qwen-image-edit-system-prompt",     # XB 转换版：官方 Edit 完整规范
)
# 对话节点「标签逻辑」下拉（手动指定优先于自动识别）
标签逻辑选项 = (
    "自动识别（按 Skill 严格匹配）",
    "H3（<Picture N>/<Video N>/<Audio N>）",
    "Qwen-Image-2.1（<imageN>）",
)


def 解析标签家族(标签逻辑="", skill=None, 有素材=True, 日志=_日志):
    """把「标签逻辑」下拉 + 已解析 skill 解析为 图像标签模式（bool）。

    手动指定优先；自动识别走严格登记册匹配——只有登记册内的 Skill id
    才参与判定。未接 Skill / 内联文件 / 第三方 Skill 无法判定时，
    按 H3（<Picture N>）兜底并记日志提示（绝不静默猜错家族）。
    """
    选择 = str(标签逻辑 or "").strip()
    if 选择.startswith("H3"):
        return False
    if 选择.startswith("Qwen") or 选择.startswith("QWI"):
        return True
    sid = str((skill or {}).get("id") or "").strip()
    if sid in H3标签家族:
        return False
    if sid in QWI标签家族:
        return True
    if 有素材:
        if sid:
            日志(f"输入媒体标签逻辑: Skill「{sid}」不在 H3/QWI 登记册内，无法严格判定标签家族，"
                f"已按 H3（<Picture N>）处理；若用 Qwen-Image-2.1 系 Skill，"
                f"请在对话节点「输入媒体标签逻辑」下拉手动选择")
        else:
            日志("输入媒体标签逻辑: 未连接 Skill（或为内联文件），无法严格判定标签家族，"
                "已按 H3（<Picture N>）处理；若需 <imageN> 标签，请在「输入媒体标签逻辑」下拉手动选择")
    return False


def _标签(kind, n, 图像模式):
    """图像模式（QWI 家族）→ <imageN>；否则（H3 家族）→ <Picture N> / <Video N> / <Audio N>。"""
    if 图像模式:
        return f"<image{n}>"
    return f"<{_H3类目[kind]} {n}>"


def 构建素材清单(图片, 视频, 音频, 图像模式):
    """写给模型看的素材清单（编号=槽位号，空槽位不存在，禁止引用）。"""
    lines = []
    if 图像模式:
        n = len(图片)
        lines.append("【本次调用参考图片】（编号即输入槽位号，与下游多参 text encoder 一一对应；"
                     "未接入的槽位不存在，禁止引用不存在的编号）")
        if n == 0:
            lines.append("本次未接入参考图片。")
        elif n == 1:
            e = 图片[0]
            lines.append(f"共 1 张：{_标签('图片', e['n'], True)}={e['label']}（已附图）。"
                         "按官方规范：单图不加 <imageN> 标签，直接以「图像」指代。")
        else:
            desc = "；".join(
                f"{_标签('图片', e['n'], True)}={e['label']}（{e['尺寸'][0]}x{e['尺寸'][1]}，已附图）"
                for e in 图片)
            lines.append(f"共 {n} 张：{desc}。多图必须使用 <imageN> 标记指代，各图属性解耦。")
    else:
        lines.append("【本次调用参考素材】（编号即输入槽位号，与下游多参 text encoder 一一对应；"
                     "未接入的槽位不存在，禁止在提示词中引用不存在的编号）")
        if 图片:
            desc = "；".join(
                f"{_标签('图片', e['n'], False)}={e['label']}（{e['尺寸'][0]}x{e['尺寸'][1]}，已附图）"
                for e in 图片)
            lines.append(f"图片（上限{图片槽上限}）：{desc}")
        else:
            lines.append(f"图片（上限{图片槽上限}）：无")
        if 视频:
            desc = "；".join(
                f"{_标签('视频', v['n'], False)}={v['label']}"
                f"（{v['duration']:.2f}秒，{v['fps']:.2f}fps，已附{len(v['frames'])}张采样帧）"
                for v in 视频)
            lines.append(f"视频（上限{视频槽上限}）：{desc}")
        else:
            lines.append(f"视频（上限{视频槽上限}）：无")
        if 音频:
            desc = "；".join(
                f"{_标签('音频', a['n'], False)}={a['label']}"
                f"（{a['duration']:.2f}秒，{a['sample_rate']}Hz，已附频谱图）"
                for a in 音频)
            lines.append(f"音频（上限{音频槽上限}）：{desc}")
        else:
            lines.append(f"音频（上限{音频槽上限}）：无")
    return "\n".join(lines)


def 构建媒体部分(图片, 视频, 音频, 图像模式):
    """组装 OpenAI 多模态 content parts（文字标签 + 图片）。空素材不会出现在这里。"""
    parts = []
    if 图像模式:
        for e in 图片:
            parts.append({"type": "text",
                          "text": f"Source {_标签('图片', e['n'], True)} ({e['label']}) follows."})
            parts.append({"type": "image_url", "image_url": {"url": e["uri"]}})
        return parts
    for e in 图片:
        parts.append({"type": "text",
                      "text": f"Source {_标签('图片', e['n'], False)} ({e['label']}) follows."})
        parts.append({"type": "image_url", "image_url": {"url": e["uri"]}})
    for v in 视频:
        for f in v["frames"]:
            parts.append({"type": "text", "text": (
                f"Analysis artifact for {_标签('视频', v['n'], False)}: sampled frame at "
                f"{f['time']:.3f}s. This is not a <Picture N> source.")})
            parts.append({"type": "image_url", "image_url": {"url": f["uri"]}})
    for a in 音频:
        parts.append({"type": "text", "text": (
            f"Analysis artifact for {_标签('音频', a['n'], False)}: time-frequency spectrogram. "
            "Use it only for timing, rhythm, energy, silence and dynamics; "
            "it is not a source picture.")})
        parts.append({"type": "image_url", "image_url": {"url": a["spectrogram_uri"]}})
    return parts
