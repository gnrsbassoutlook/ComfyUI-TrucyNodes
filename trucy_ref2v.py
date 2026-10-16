"""TrucyLLM · ref2v Trucy 节点族（H3 Ref2VA，合并自 ComfyUI-TrucyLLM）。

三个节点（前两个拆对是缓存架构，第三个是合并版单框）：
  H3参考编码      —— 只吃参考素材 + vae/audio_vae，**刻意不含 prompt 输入**。
                    提示词变动时本节点输入哈希不变 → ComfyUI 直接复用缓存，
                    参考 latent / audio latent 零重算（AIEverything V2 架构）。
  H3提示词编码    —— clip + prompt + 上游 ref_data，只做 tokenize + 文本
                    encode + 挂载 minimax_refs，只有它因提示词变动重算。
  H3参考转视频    —— 合并版单框：输出 (latent, positive)，连线同官方
                    MiniMaxH3ReferenceToVideo；含 prompt 故 ComfyUI 内置缓存必
                    失效，改为节点内自管参考缓存（内容级 sha1 + VAE 实例身份
                    校验），同参考换提示词时同样不重新 encode。

端口全部常驻 optional（9 图 + 3 音频；视频参考已按用户决定摘除——99.99%
不用，官方 MiniMaxH3ReferenceToVideo 仍在册可作视频参考备用），无需任何前端
即插即用；空值安全（连续性铁律）：None / 零尺寸张量 / ExecutionBlocker 的
槽位一律跳过并记日志，绝不报错卡工作流；全部留空时输出空 AV latent + 空
ref_data，提示词编码照常出 Conditioning（等价纯文生视频工况）。

标签协议与官方一致：图片→<Picture i>（1-9，按 ref_items 出现顺序生成、
恒从 1 起，与官方 ref_image_0 起端口等价），音频→<Audio j>（1-3）。
"""
import hashlib
import math
import sys
import threading
import weakref
from collections import OrderedDict

# 官方 helper 复用（缩放数学/音频编码/空 AV latent 全部照官方，不自己重写，
# 保证与官方节点行为一致）；非 ComfyUI 环境（单测直 import）时置不可用标志。
try:
    from comfy_extras.nodes_minimax_h3 import (
        _resize, _encode_ref_audio, _empty_av_latent,
        CANVAS_MULTIPLE, REF_IMAGE_SHORT_EDGE,
    )
    _官方helper可用 = True
    _官方helper错误 = ""
except Exception as _e:  # pragma: no cover - 仅非 ComfyUI 环境
    _官方helper可用 = False
    _官方helper错误 = str(_e)

try:
    import node_helpers
except Exception:  # pragma: no cover
    node_helpers = None

# 双上下文导入兼容：ComfyUI 里本模块是插件包子模块，相对导入可解析；
# 单测以裸模块导入（无父包）时退回裸导入——调用方需已把插件根目录放上
# sys.path（各测试脚本均如此）。
try:
    from .trucy_media import _张量可用, _输入被静音, _日志
except ImportError:
    import os as _os

    _here = _os.path.dirname(_os.path.abspath(__file__))
    if _here not in sys.path:
        sys.path.insert(0, _here)
    from trucy_media import _张量可用, _输入被静音, _日志  # noqa: E402

# 槽位规模与官方图片/音频部分一致：9 图 / 3 独立音频
图槽上限 = 9
音频槽上限 = 3


# ---------------------------------------------------------------------------
# 纯函数（可单测，不碰模型）
# ---------------------------------------------------------------------------

def _图目标尺寸(w, h, width, height, mode):
    """官方 ref_image_size 数学复刻：match=缩到生成画面同像素面积；max=2048 短边。
    只缩不放；结果按 CANVAS_MULTIPLE(32) 对齐且不小于 32。
    """
    if mode == "max":
        scale = min(1.0, REF_IMAGE_SHORT_EDGE / min(w, h))
    else:  # "match"
        scale = min(1.0, math.sqrt((width * height) / (w * h)))
    tw = max(CANVAS_MULTIPLE, round(w * scale / CANVAS_MULTIPLE) * CANVAS_MULTIPLE)
    th = max(CANVAS_MULTIPLE, round(h * scale / CANVAS_MULTIPLE) * CANVAS_MULTIPLE)
    return tw, th


def _音频可用(a):
    """AUDIO 端口判定：dict 且 waveform 张量非空。"""
    if not isinstance(a, dict):
        return False
    return _张量可用(a.get("waveform"))


# ---------------------------------------------------------------------------
# 槽位声明（全常驻 optional，无需前端）
# ---------------------------------------------------------------------------

def _参考图槽输入():
    return {
        f"🖼️ 参考图{i}": ("IMAGE", {
            "tooltip": f"参考图槽位 {i}/{图槽上限}（标签 <Picture N> 按接线顺序生成、从 1 起，"
                       "与官方 ref_image_0 起端口等价；空置/断连不报错，也不进任何编码）。",
        })
        for i in range(1, 图槽上限 + 1)
    }


def _参考音频槽输入():
    return {
        f"🎵 参考音频{i}": ("AUDIO", {
            "tooltip": f"独立参考音频槽位 {i}/{音频槽上限}（标签 <Audio N> 按接线顺序生成；"
                       "空置不报错）。需接 audio_vae 才会编码进 DiT 通道。",
        })
        for i in range(1, 音频槽上限 + 1)
    }


# ---------------------------------------------------------------------------
# 编码核心（双节点与合并版单节点共用；纯逻辑，日志由调用方打）
# ---------------------------------------------------------------------------

def _参考编码核心(vae, audio_vae, width, height, ref_image_size, kwargs):
    """参考素材 → (ref_items, ref_blocks, 图数, 音频数, 跳过)。

    vae/audio_vae 可为 None（对应素材只进文本编码器）；端口若收到
    ExecutionBlocker（上游被旁路/静音）由调用方按 None 等效处理。
    槽位级 try/except：单槽故障只记跳过，不扩散。
    不含空 AV latent 生成（与 length 相关，由调用方按需生成）。
    """
    ref_items = []   # 送 tokenizer 的呈现序列（决定 <Picture i>/<Audio j> 编号）
    ref_blocks = []  # 送 DiT 的 latent 块（每步重注入，不参与去噪）
    跳过 = []
    图数 = 音频数 = 0

    # --- 图片（<Picture i>，只取首帧） ---
    for i in range(1, 图槽上限 + 1):
        img = kwargs.get(f"🖼️ 参考图{i}")
        if not _张量可用(img):
            if img is not None:
                跳过.append(f"参考图{i}（空张量）")
            continue
        try:
            h, w = int(img.shape[1]), int(img.shape[2])
            tw, th = _图目标尺寸(w, h, width, height, ref_image_size)
            resized = _resize(img[:1], tw, th, "disabled")
            ref_items.append({"type": "image", "data": resized})
            if vae is not None:
                z = vae.encode(resized)
                ref_blocks.append({"kind": "image", "latent_h": th // 16,
                                   "latent_w": tw // 16, "latent": z})
            图数 += 1
        except Exception as e:
            跳过.append(f"参考图{i}（{e}）")

    # --- 独立音频（<Audio j>） ---
    # 注意：查找键必须与 _参考音频槽输入() 声明键逐字一致（emoji 极易 drift，
    # 曾因声明用 🎵、查找用生僻 emoji 导致音频槽静默失效——空值铁律还不报错）
    for i in range(1, 音频槽上限 + 1):
        audio = kwargs.get(f"🎵 参考音频{i}")
        if not _音频可用(audio):
            if audio is not None:
                跳过.append(f"参考音频{i}（空音频）")
            continue
        try:
            ref_items.append({"type": "audio"})
            if audio_vae is not None:
                audio_latent, ref_audio_t = _encode_ref_audio(audio_vae, audio)
                ref_blocks.append({"kind": "audio", "ref_audio_t": ref_audio_t,
                                   "audio_latent": audio_latent})
            音频数 += 1
        except Exception as e:
            跳过.append(f"参考音频{i}（{e}）")

    return ref_items, ref_blocks, 图数, 音频数, 跳过


def _提示词编码核心(clip, prompt, ref_items, ref_blocks):
    """prompt + ref_data → (conditioning, 是否降级)。

    降级路径（clip 不支持 minimax_ref_items）也必须挂 minimax_refs——
    参考 latent 走 DiT 通道与该扩展无关，重构时曾在此漏挂，被单测抓回。
    """
    try:
        tokens = clip.tokenize(prompt, minimax_ref_items=ref_items)
    except TypeError:
        # 接错了文本编码器（非 MiniMax H3 CLIP）——降级不卡队列，
        # 参考 latent 仍可经 DiT 通道生效（minimax_refs 照常挂载）。
        tokens = clip.tokenize(prompt)
        降级 = True
    else:
        降级 = False
    cond = clip.encode_from_tokens_scheduled(tokens)
    if ref_blocks:
        cond = node_helpers.conditioning_set_values(cond, {"minimax_refs": ref_blocks})
    return cond, 降级


# ---------------------------------------------------------------------------
# 节点一：参考编码（缓存层）—— 刻意不含 prompt 输入
# ---------------------------------------------------------------------------

class TrucyH3RefEncode:
    """H3 Ref2VA 参考编码层：素材 → AV latent + ref_data。

    本节点没有 prompt 输入——连续生视频时提示词每镜都变，而本节点输入不变，
    ComfyUI 直接命中缓存，参考不重新 encode（AIEverything V2 缓存架构）。
    """

    @classmethod
    def INPUT_TYPES(cls):
        required = {
            "width": ("INT", {
                "default": 1344, "min": 32, "max": 8192, "step": 32,
                "tooltip": "生成画面宽（像素），32 对齐。",
            }),
            "height": ("INT", {
                "default": 768, "min": 32, "max": 8192, "step": 32,
                "tooltip": "生成画面高（像素），32 对齐。",
            }),
            "length": ("INT", {
                "default": 124, "min": 5, "max": 3600, "step": 17,
                "tooltip": "帧数@24fps（124≈5s；自动向上对齐到模型 17k+5 网格，官方训练区间约 124-362）。",
            }),
            "ref_image_size": (["match", "max"], {
                "default": "match",
                "tooltip": "参考图缩放：match=缩放到生成画面同像素面积（只缩不放，快）；"
                           "max=2048 短边（身份保真最好，但参考 token 每个采样步都过，慢数倍）。",
            }),
        }
        optional = {
            "vae": ("VAE", {
                "tooltip": "H3 视频 VAE（models/vae/minimax_h3_video_vae_*）。"
                           "不接=参考只进文本编码器，conditioning 里无 latent 块。",
            }),
            "audio_vae": ("VAE", {
                "tooltip": "H3 音频 VAE（models/vae/minimax_h3_audio_vae_*）。"
                           "不接=音频参考只进文本编码器，不进 DiT 通道。",
            }),
        }
        optional.update(_参考图槽输入())
        optional.update(_参考音频槽输入())
        return {"required": required, "optional": optional}

    RETURN_TYPES = ("LATENT", "*")
    RETURN_NAMES = ("latent", "ref_data")
    FUNCTION = "run"
    CATEGORY = "TrucyNodes/H3 ref2v"

    def run(self, width, height, length, ref_image_size="match",
            vae=None, audio_vae=None, **kwargs):
        if not _官方helper可用:
            raise RuntimeError(f"ComfyUI 官方 H3 helper 不可用（{_官方helper错误}），"
                               "本节点必须在 ComfyUI 环境内运行")
        # 端口被旁路/静音时 ComfyUI 会送 ExecutionBlocker 占位对象——按 None 等效
        if _输入被静音(vae):
            vae = None
        if _输入被静音(audio_vae):
            audio_vae = None
        latent, _frame_count = _empty_av_latent(width, height, length)
        ref_items, ref_blocks, 图数, 音频数, 跳过 = _参考编码核心(
            vae, audio_vae, width, height, ref_image_size, kwargs)

        _日志(f"H3参考编码: 图{图数}/音频{音频数} → "
              f"ref_items={len(ref_items)} ref_blocks={len(ref_blocks)}"
              f"（{'vae+audio_vae 均已接' if vae is not None and audio_vae is not None else 'vae/audio_vae 有未接，对应素材仅进文本编码器'}）"
              + (f" | 跳过: {'; '.join(跳过)}" if 跳过 else ""))
        return (latent, {"ref_items": ref_items, "ref_blocks": ref_blocks})


# ---------------------------------------------------------------------------
# 节点二：提示词编码（Ref2V 出口）—— 只有它会因提示词变动重算
# ---------------------------------------------------------------------------

class TrucyH3PromptEncode:
    """H3 Ref2VA 提示词编码：prompt + ref_data → positive conditioning。

    上游接 TrucyH3RefEncode 的 ref_data（ANY 端口）。提示词变动时只有本节点
    重算（tokenize + 文本 encode），参考编码走 ComfyUI 缓存不重跑。
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP", {
                    "tooltip": "MiniMax H3 文本编码器（models/clip/qwen3vl_32b_minimax_h3_*）。",
                }),
                "prompt": ("STRING", {
                    "multiline": True, "default": "",
                    "tooltip": "H3 提示词全文（六段结构）。上游接 Prompt (H3/QWI) 节点的输出。",
                }),
                "ref_data": ("*", {
                    "tooltip": "来自 H3参考编码 的 ref_data（参考素材打包）。",
                }),
            },
        }

    RETURN_TYPES = ("CONDITIONING",)
    RETURN_NAMES = ("positive",)
    FUNCTION = "run"
    CATEGORY = "TrucyNodes/H3 ref2v"

    def run(self, clip, prompt, ref_data=None):
        ref_items, ref_blocks = [], []
        if isinstance(ref_data, dict):
            ref_items = ref_data.get("ref_items") or []
            ref_blocks = ref_data.get("ref_blocks") or []
        else:
            _日志("提示词编码: 未接 ref_data（或内容为空），按无参考提示词编码")

        cond, 降级 = _提示词编码核心(clip, prompt, ref_items, ref_blocks)
        if 降级:
            _日志("提示词编码: 当前 clip 不支持 minimax_ref_items（非 MiniMax H3 文本编码器），"
                  "降级为普通编码，参考仅走 DiT 通道")
        _日志(f"提示词编码: prompt {len(str(prompt or ''))} 字符 | "
              f"ref_items={len(ref_items)} ref_blocks={len(ref_blocks)}")
        return (cond,)


# ---------------------------------------------------------------------------
# 合并版单节点：参考编码 + 提示词编码（节点内自管参考缓存）
# ---------------------------------------------------------------------------
import torch  # noqa: E402

# 参考缓存：键 → (vae弱引用组, ref_items, ref_blocks, 图数, 音频数)
#
# 为什么合并版要自写缓存：单节点含 prompt 输入，ComfyUI 节点缓存按整个节点
# 的输入算指纹——提示词一变，整个节点（含参考编码）重跑。要保「同参考换
# 提示词不重新 encode」，只能在节点内对参考部分单独做缓存。
#
# 安全设计（防「静默复用旧 latent」这一最危险失败模式——换了图画面还是
# 旧的，而且不报错）：
#   1. 键含 vae/audio_vae 实例身份（id + 弱引用存活校验）——VAE 被卸载重载
#      （16GB 显存下 ComfyUI 会动态换出换入）后旧 latent 必 miss；
#   2. 键含每个槽位内容的逐字节 sha1（shape+dtype+字节流）——换图/换音频/
#      改动一个像素都 miss；
#   3. 键含 width/height/ref_image_size（影响参考图缩放目标→编码内容）；
#      length 不进键（只影响空 AV latent，与参考编码无关）。
_参考缓存 = OrderedDict()
_参考缓存锁 = threading.RLock()   # 历史教训：同线程可能重入，必须 RLock
_参考缓存上限 = 4


def _张量指纹(t):
    """张量内容指纹：shape + dtype + 逐字节 sha1（GPU 张量先同步回 CPU）。

    4 张 1344×768 参考图约 48MB，sha1 约 0.2-0.3s——相对 VAE 编码（数秒）
    可忽略；且只有合并版单节点走这条路。
    非张量（字符串路径/畸形值）返回固定标记——与「无有效素材」同等对待
    （核心路径对这类值也是 try 失败记跳过，行为一致；缓存键必须同构，
    否则键计算会崩在 try 之外——空值铁律的盲区）。
    """
    if not isinstance(t, torch.Tensor):
        return "-"
    h = hashlib.sha1()
    h.update(str(tuple(t.shape)).encode())
    h.update(str(t.dtype).encode())
    h.update(t.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def _音频指纹(a):
    if not isinstance(a, dict) or not isinstance(a.get("waveform"), torch.Tensor):
        return "-"
    h = hashlib.sha1()
    w = a["waveform"]
    h.update(str(tuple(w.shape)).encode())
    h.update(str(w.dtype).encode())
    h.update(str(a.get("sample_rate", "")).encode())
    h.update(w.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def _参考缓存键(vae, audio_vae, width, height, ref_image_size, kwargs):
    parts = [id(vae), id(audio_vae), int(width), int(height), ref_image_size]
    for i in range(1, 图槽上限 + 1):
        img = kwargs.get(f"🖼️ 参考图{i}")
        parts.append(_张量指纹(img) if _张量可用(img) else "-")
    for i in range(1, 音频槽上限 + 1):
        audio = kwargs.get(f"🎵 参考音频{i}")
        parts.append(_音频指纹(audio) if _音频可用(audio) else "-")
    return tuple(parts)


def _参考缓存查询(键, vae, audio_vae):
    """命中返回 (ref_items, ref_blocks, 图数, 音频数)；miss 返回 None。

    命中校验：键相同 + 条目里存的 VAE 弱引用仍活着且就是当前实例
    （防 Python id 复用——旧实例被 GC 后，新对象可能拿到同一个 id）。
    """
    with _参考缓存锁:
        条目 = _参考缓存.get(键)
        if 条目 is None:
            return None
        弱引用组, ref_items, ref_blocks, 图数, 音频数 = 条目
        for 当前, wr in ((vae, 弱引用组[0]), (audio_vae, 弱引用组[1])):
            if 当前 is None:
                continue
            if wr is None or wr() is not 当前:
                # 身份对不上（旧实例已死/被换出）——淘汰该条，判 miss
                _参考缓存.pop(键, None)
                return None
        _参考缓存.move_to_end(键)
        return ref_items, ref_blocks, 图数, 音频数


def _参考缓存存入(键, vae, audio_vae, ref_items, ref_blocks, 图数, 音频数):
    弱引用组 = []
    for v in (vae, audio_vae):
        try:
            弱引用组.append(weakref.ref(v) if v is not None else None)
        except TypeError:  # 个别对象不支持弱引用——退化为只信 id
            弱引用组.append(None)
    with _参考缓存锁:
        _参考缓存[键] = (tuple(弱引用组), ref_items, ref_blocks, 图数, 音频数)
        _参考缓存.move_to_end(键)
        while len(_参考缓存) > _参考缓存上限:
            _参考缓存.popitem(last=False)


class TrucyH3RefToVideo:
    """H3 Ref2VA 合并版：参考编码 + 提示词编码一个节点搞定。

    输出 (latent, positive conditioning)——直接喂 BasicGuider 与
    SamplerCustomAdvanced，连线形态与官方 MiniMaxH3ReferenceToVideo 一致
    （单框），但不丢缓存：节点内对参考部分自管缓存（内容级 sha1 +
    VAE 实例身份校验），同参考换提示词时不重新 encode，与拆双节点等价。

    缓存失效条件（任一不满足即重新编码，绝不静默复用旧 latent）：
    VAE 实例变化（卸载重载）/ 任一参考图或音频内容变化（逐字节比对）/
    宽高或 ref_image_size 变化 / 槽位占用模式变化（挪位也算）。
    """

    @classmethod
    def INPUT_TYPES(cls):
        required = {
            "width": ("INT", {
                "default": 1344, "min": 32, "max": 8192, "step": 32,
                "tooltip": "生成画面宽（像素），32 对齐。",
            }),
            "height": ("INT", {
                "default": 768, "min": 32, "max": 8192, "step": 32,
                "tooltip": "生成画面高（像素），32 对齐。",
            }),
            "length": ("INT", {
                "default": 124, "min": 5, "max": 3600, "step": 17,
                "tooltip": "帧数@24fps（124≈5s；自动向上对齐到模型 17k+5 网格，官方训练区间约 124-362）。",
            }),
            "ref_image_size": (["match", "max"], {
                "default": "match",
                "tooltip": "参考图缩放：match=缩放到生成画面同像素面积（只缩不放，快）；"
                           "max=2048 短边（身份保真最好，但参考 token 每个采样步都过，慢数倍）。",
            }),
            "clip": ("CLIP", {
                "tooltip": "MiniMax H3 文本编码器（models/clip/qwen3vl_32b_minimax_h3_*）。",
            }),
            "prompt": ("STRING", {
                "multiline": True, "default": "",
                "tooltip": "H3 提示词全文（六段结构）。上游接 Prompt (H3/QWI) 节点的输出。",
            }),
        }
        optional = {
            "vae": ("VAE", {
                "tooltip": "H3 视频 VAE（models/vae/minimax_h3_video_vae_*）。"
                           "不接=参考只进文本编码器，conditioning 里无 latent 块。",
            }),
            "audio_vae": ("VAE", {
                "tooltip": "H3 音频 VAE（models/vae/minimax_h3_audio_vae_*）。"
                           "不接=音频参考只进文本编码器，不进 DiT 通道。",
            }),
        }
        optional.update(_参考图槽输入())
        optional.update(_参考音频槽输入())
        return {"required": required, "optional": optional}

    RETURN_TYPES = ("LATENT", "CONDITIONING")
    RETURN_NAMES = ("latent", "positive")
    FUNCTION = "run"
    CATEGORY = "TrucyNodes/H3 ref2v"

    def run(self, width, height, length, ref_image_size="match",
            clip=None, prompt="", vae=None, audio_vae=None, **kwargs):
        if not _官方helper可用:
            raise RuntimeError(f"ComfyUI 官方 H3 helper 不可用（{_官方helper错误}），"
                               "本节点必须在 ComfyUI 环境内运行")
        # 端口被旁路/静音时 ComfyUI 会送 ExecutionBlocker 占位对象——按 None 等效
        if _输入被静音(vae):
            vae = None
        if _输入被静音(audio_vae):
            audio_vae = None
        latent, _frame_count = _empty_av_latent(width, height, length)

        键 = _参考缓存键(vae, audio_vae, width, height, ref_image_size, kwargs)
        命中 = _参考缓存查询(键, vae, audio_vae)
        if 命中 is not None:
            ref_items, ref_blocks, 图数, 音频数 = 命中
            _日志(f"H3参考编码: 缓存命中 → ref_items={len(ref_items)} "
                  f"ref_blocks={len(ref_blocks)}（图{图数}/音频{音频数} 跳过 VAE 编码，"
                  f"同参考换提示词时省此处）")
        else:
            ref_items, ref_blocks, 图数, 音频数, 跳过 = _参考编码核心(
                vae, audio_vae, width, height, ref_image_size, kwargs)
            _参考缓存存入(键, vae, audio_vae, ref_items, ref_blocks, 图数, 音频数)
            _日志(f"H3参考编码: 图{图数}/音频{音频数} → "
                  f"ref_items={len(ref_items)} ref_blocks={len(ref_blocks)}"
                  f"（{'vae+audio_vae 均已接' if vae is not None and audio_vae is not None else 'vae/audio_vae 有未接，对应素材仅进文本编码器'}）"
                  + (f" | 跳过: {'; '.join(跳过)}" if 跳过 else ""))

        cond, 降级 = _提示词编码核心(clip, prompt, ref_items, ref_blocks)
        if 降级:
            _日志("提示词编码: 当前 clip 不支持 minimax_ref_items（非 MiniMax H3 文本编码器），"
                  "降级为普通编码，参考仅走 DiT 通道")
        _日志(f"提示词编码: prompt {len(str(prompt or ''))} 字符 | "
              f"ref_items={len(ref_items)} ref_blocks={len(ref_blocks)}")
        return (latent, cond)


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "TrucyH3RefEncode": TrucyH3RefEncode,
    "TrucyH3PromptEncode": TrucyH3PromptEncode,
    "TrucyH3RefToVideo": TrucyH3RefToVideo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyH3RefEncode": "🚀 ref2v Trucy · 参考编码（缓存层）",
    "TrucyH3PromptEncode": "🚀 ref2v Trucy · 提示词编码（出口）",
    "TrucyH3RefToVideo": "🚀 ref2v Trucy · 参考转视频（合并版）",
}
