import subprocess
import traceback

# 子进程编码补丁
_orig_Popen_init = subprocess.Popen.__init__
def _patched_Popen_init(self, *args, **kwargs):
    if kwargs.get("encoding") in ("utf-8", "utf8"):
        kwargs["errors"] = "replace"
    _orig_Popen_init(self, *args, **kwargs)
subprocess.Popen.__init__ = _patched_Popen_init

# 模块导入
# 注意：只依赖 ComfyUI 环境自带库（torch/PIL/numpy/comfy）的模块走硬导入；
#       依赖第三方库的模块（excel_nodes→openpyxl、trucy_switch→Impact Pack）
#       统一走下方 _safe_import——缺依赖时仅跳过对应节点，不影响其余节点注册
from .audio_nodes import TrucyAudioLoaderIndex, AudioLengthDetector, EmptyAudioGenerator, TrucySaveAudio
from .text_nodes import TrucyTxtBatchLoader, TrucyTxtPreviewAndSave, TrucySymbolSniffer, TrucyTextToNumber, TrucyTextSlicerSmart, TrucyTextCleaner
from .image_adapter import TrucyImageLoaderIndex, TrucyImageLoader6, TrucyImageAdapter, TrucyAssetGrid6, TrucyAssetGrid10, TrucyImageBridge6, TrucyImageBridge10
from .trucy_toolkit import TrucyImageLoaderString6, TrucyImageLoaderString10, TrucyFolderIterator, TrucyPromptSplitter6, TrucyPromptSplitter10, TrucyIDExtractor, TrucyStringSlicer, TrucyDatasetSaver
from .trucy_loop import TrucyForLoopStart9ch, TrucyForLoopEnd9ch, TrucyForLoopStart2ch, TrucyForLoopEnd2ch
from .trucy_remote import TrucyRemoteToggle6x6, TrucyMasterIntRouter

# 可选模块安全导入
def _safe_import(module_name, class_names):
    try:
        mod = __import__(f"{__name__}.{module_name}", fromlist=class_names)
        return [getattr(mod, c, None) for c in class_names]
    except Exception as e:
        print(f"[TrucyNodes] ❌ 导入 {module_name} 失败: {e}")
        return [None] * len(class_names)

(TrucyVideoLoaderIndex,) = _safe_import("trucy_video", ["TrucyVideoLoaderIndex"])
(TrucyVideoCombine,) = _safe_import("trucy_video_combine", ["TrucyVideoCombine"])
(TrucyDocLoader,) = _safe_import("trucy_doc", ["TrucyDocLoader"])

# 第三方依赖模块（容错导入）：
#   excel_nodes —— 需要 openpyxl（pip install openpyxl，已列入 requirements.txt）
#   trucy_switch —— 需要 ComfyUI-Impact-Pack 插件（ComfyUI Manager 搜 Impact 安装）
# 未装对应依赖时仅跳过这些节点，日志会打印缺什么，其余节点不受影响
(TrucyExcelReader, TrucyExcelReader6, TrucyExcelReader10) = _safe_import(
    "excel_nodes", ["TrucyExcelReader", "TrucyExcelReader6", "TrucyExcelReader10"],
)
(TrucyAnySwitch6, TrucyAnySwitch10, TrucyControlBridge, TrucyFrameSecondsConverter) = _safe_import(
    "trucy_switch",
    ["TrucyAnySwitch6", "TrucyAnySwitch10", "TrucyControlBridge", "TrucyFrameSecondsConverter"],
)

# LLM / ref2v 节点族（合并自 ComfyUI-TrucyLLM，2026-10-16）
#   trucy_skill_runner.py —— LLM Loader Trucy（三通道大脑装载，独立类目）；
#                          Skill Runner Trucy 家族（Skill Loader / Chat / Prompt / Unload）；
#                          VLM Runner Trucy（图片/视频推理，独立类目）
#   trucy_ref2v.py        —— H3 ref2v Trucy：H3参考编码 / H3提示词编码 / H3参考转视频（合并版）
#   trucy_dmad.py         —— H3 4 步加速采样器（DMAD 蒸馏 LoRA 专用推理步，替代 KSamplerSelect）
(TrucyLLMLoader, TrucySkillLoader, TrucyChat, TrucyPromptH3QWI, TrucyUnloadModel) = _safe_import(
    "trucy_skill_runner",
    ["TrucyLLMLoader", "TrucySkillLoader", "TrucyChat", "TrucyPromptH3QWI", "TrucyUnloadModel"],
)
(TrucyVLMRunner,) = _safe_import("trucy_skill_runner", ["TrucyVLMRunner"])
(TrucyH3RefEncode, TrucyH3PromptEncode, TrucyH3RefToVideo) = _safe_import(
    "trucy_ref2v",
    ["TrucyH3RefEncode", "TrucyH3PromptEncode", "TrucyH3RefToVideo"],
)
(TrucyDMADSampler,) = _safe_import("trucy_dmad", ["TrucyDMADSampler"])

NODE_CLASS_MAPPINGS = {
    "TrucyAudioLoaderIndex": TrucyAudioLoaderIndex,
    "AudioLengthDetector": AudioLengthDetector,
    "EmptyAudioGenerator": EmptyAudioGenerator,
    "TrucySaveAudio": TrucySaveAudio,
    "TrucyTxtBatchLoader": TrucyTxtBatchLoader,
    "TrucyTxtPreviewAndSave": TrucyTxtPreviewAndSave,
    "TrucySymbolSniffer": TrucySymbolSniffer,
    "TrucyTextToNumber": TrucyTextToNumber,
    "TrucyTextSlicerSmart": TrucyTextSlicerSmart,
    "TrucyTextCleaner": TrucyTextCleaner,
    "TrucyRemoteToggle6x6": TrucyRemoteToggle6x6,
    "TrucyMasterIntRouter": TrucyMasterIntRouter,
    "TrucyImageLoaderIndex": TrucyImageLoaderIndex,
    "TrucyImageLoader6": TrucyImageLoader6,
    "TrucyImageAdapter": TrucyImageAdapter,
    "TrucyAssetGrid6": TrucyAssetGrid6,
    "TrucyAssetGrid10": TrucyAssetGrid10,
    "TrucyImageBridge6": TrucyImageBridge6,
    "TrucyImageBridge10": TrucyImageBridge10,
    "TrucyImageLoaderString6": TrucyImageLoaderString6,
    "TrucyImageLoaderString10": TrucyImageLoaderString10,
    "TrucyFolderIterator": TrucyFolderIterator,
    "TrucyPromptSplitter6": TrucyPromptSplitter6,
    "TrucyPromptSplitter10": TrucyPromptSplitter10,
    "TrucyIDExtractor": TrucyIDExtractor,
    "TrucyStringSlicer": TrucyStringSlicer,
    "TrucyDatasetSaver": TrucyDatasetSaver,
    "TrucyForLoopStart9ch": TrucyForLoopStart9ch,
    "TrucyForLoopEnd9ch": TrucyForLoopEnd9ch,
    "TrucyForLoopStart2ch": TrucyForLoopStart2ch,
    "TrucyForLoopEnd2ch": TrucyForLoopEnd2ch,
}

optional_nodes = {
    "TrucyVideoLoaderIndex": TrucyVideoLoaderIndex,
    "TrucyDocLoader": TrucyDocLoader,
    "TrucyVideoCombine": TrucyVideoCombine,
    # 依赖 openpyxl（requirements.txt 已列）
    "TrucyExcelReader": TrucyExcelReader,
    "TrucyExcelReader6": TrucyExcelReader6,
    "TrucyExcelReader10": TrucyExcelReader10,
    # 依赖 ComfyUI-Impact-Pack 插件
    "TrucyAnySwitch6": TrucyAnySwitch6,
    "TrucyAnySwitch10": TrucyAnySwitch10,
    "TrucyControlBridge": TrucyControlBridge,
    "TrucyFrameSecondsConverter": TrucyFrameSecondsConverter,
    # LLM Loader Trucy（三通道大脑装载，独立类目）
    "TrucyLLMLoader": TrucyLLMLoader,
    # Skill Runner Trucy 节点族（Skill 执行器）
    "TrucySkillLoader": TrucySkillLoader,
    "TrucyChat": TrucyChat,
    "TrucyPromptH3QWI": TrucyPromptH3QWI,
    "TrucyUnloadModel": TrucyUnloadModel,
    # VLM Runner Trucy（图片/视频推理，不调用 Skill）
    "TrucyVLMRunner": TrucyVLMRunner,
    # H3 ref2v Trucy 节点族
    "TrucyH3RefEncode": TrucyH3RefEncode,
    "TrucyH3PromptEncode": TrucyH3PromptEncode,
    "TrucyH3RefToVideo": TrucyH3RefToVideo,
    # H3 4 步加速采样器（DMAD 蒸馏 LoRA 专用推理步）
    "TrucyDMADSampler": TrucyDMADSampler,
}
for name, cls in optional_nodes.items():
    if cls is not None:
        NODE_CLASS_MAPPINGS[name] = cls

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyAudioLoaderIndex": "🚀 Audio Loader by Index (Trucy)",
    "AudioLengthDetector": "🚀 Audio Detector & Padder (Trucy)",
    "EmptyAudioGenerator": "🚀 Empty Audio Generator (Trucy)",
    "TrucySaveAudio": "🚀 Save Audio (Trucy)",
    "TrucyTxtBatchLoader": "🚀 TXT Loader by Index (Trucy)",
    "TrucyTxtPreviewAndSave": "🚀 Text Preview & Save (Trucy)",
    "TrucySymbolSniffer": "🚀 Text Symbol Sniffer (Trucy)",
    "TrucyTextToNumber": "🚀 Text to Number Converter (Trucy)",
    "TrucyTextSlicerSmart": "🚀 Text Smart Slicer (Trucy)",
    "TrucyTextCleaner": "🚀 Text Cleaner (Trucy)",
    "TrucyAnySwitch6": "🚀 Any Switch (6ch) (Trucy)",
    "TrucyAnySwitch10": "🚀 Any Switch (10ch) (Trucy)",
    "TrucyControlBridge": "🚀 Control Bridge (Trucy)",
    "TrucyFrameSecondsConverter": "🚀 Frame & Seconds Converter (Trucy)",
    "TrucyRemoteToggle6x6": "🚀 Remote Toggle 6x6 (Trucy)",
    "TrucyMasterIntRouter": "🚀 5-way Mute/Bypass Nodes-Remote (Trucy)",
    "TrucyExcelReader": "🚀 Excel-Reader-Trucy",
    "TrucyExcelReader6": "🚀 Excel-Reader-6-Trucy",
    "TrucyExcelReader10": "🚀 Excel-Reader-10-Trucy",
    "TrucyImageLoaderIndex": "🚀 Image Loader by Index (Trucy)",
    "TrucyImageLoader6": "🚀 Image Loader (6 Channels) (Trucy)",
    "TrucyImageAdapter": "🚀 Image Size Adapter (Trucy)",
    "TrucyAssetGrid6": "🚀 Trucy Asset Grid (6)",
    "TrucyAssetGrid10": "🚀 Trucy Asset Grid (10)",
    "TrucyImageBridge6": "🚀 Image Bridge (6ch) (Trucy)",
    "TrucyImageBridge10": "🚀 Image Bridge (10ch) (Trucy)",
    "TrucyImageLoaderString6": "🚀 Trucy Image Loader (String 6)",
    "TrucyImageLoaderString10": "🚀 Trucy Image Loader (String 10)",
    "TrucyFolderIterator": "🚀 Trucy Folder Iterator",
    "TrucyPromptSplitter6": "🚀 Trucy Text Splitter (6)",
    "TrucyPromptSplitter10": "🚀 Trucy Text Splitter (10)",
    "TrucyIDExtractor": "🚀 Trucy ID Extractor",
    "TrucyStringSlicer": "🚀 Trucy String Slicer",
    "TrucyDatasetSaver": "🚀 Trucy Dataset Saver",
    "TrucyVideoLoaderIndex": "🚀 Video Loader by Index (Trucy)",
    "TrucyVideoCombine": "🚀 Video-Combine-Trucy",
    "TrucyDocLoader": "🚀 Doc-Loader-Trucy",
    "TrucyForLoopStart9ch": "🚀 Trucy For Loop Start (9ch)",
    "TrucyForLoopEnd9ch": "🚀 Trucy For Loop End (9ch)",
    "TrucyForLoopStart2ch": "🚀 Trucy For Loop Start (2ch)",
    "TrucyForLoopEnd2ch": "🚀 Trucy For Loop End (2ch)",
    # LLM Loader Trucy（三通道大脑装载，独立类目；端口名仍为 LLM）
    "TrucyLLMLoader": "🚀 LLM Loader Trucy",
    # Skill Runner Trucy 节点族（真正的 Skill 执行器）
    "TrucySkillLoader": "🚀 Skill Loader Trucy",
    "TrucyChat": "🚀 Skill Runner Trucy · Chat",
    "TrucyPromptH3QWI": "🚀 Skill Runner Trucy · Prompt (H3/QWI/MOSS)",
    "TrucyUnloadModel": "🚀 Skill Runner Trucy · Unload Model",
    # VLM Runner Trucy（图片/视频推理，独立类目）
    "TrucyVLMRunner": "🚀 VLM Runner Trucy",
    # H3 ref2v Trucy 节点族（H3 Ref2VA 编码/缓存）
    "TrucyH3RefEncode": "🚀 H3 ref2v Trucy · 参考编码（缓存层）",
    "TrucyH3PromptEncode": "🚀 H3 ref2v Trucy · 提示词编码（出口）",
    "TrucyH3RefToVideo": "🚀 H3 ref2v Trucy · 参考转视频（合并版）",
    "TrucyDMADSampler": "🚀 Trucy DMAD Sampler (H3 4步)",
}

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

# ---------------------------------------------------------------------------
# API 预设地址簿 HTTP 接口（供前端「＋ 保存为API预设」按钮增删查；
# 从 ComfyUI-TrucyLLM 迁入，路由路径保持不变，前端 JS 无需改动）
# ---------------------------------------------------------------------------
try:
    from aiohttp import web
    from server import PromptServer

    from .trucy_presets import 保存预设, 删除预设, 读取预设

    @PromptServer.instance.routes.get("/trucyllm/api_presets")
    async def _trucy_presets_get(request):
        return web.json_response({"presets": 读取预设()})

    @PromptServer.instance.routes.post("/trucyllm/api_presets")
    async def _trucy_presets_post(request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "请求体不是合法 JSON"}, status=400)
        try:
            record = 保存预设(
                body.get("name"), body.get("api_base"),
                body.get("api_key"), body.get("model"), body.get("timeout"),
            )
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        return web.json_response({"ok": True, "preset": record, "presets": 读取预设()})

    @PromptServer.instance.routes.post("/trucyllm/api_presets/delete")
    async def _trucy_presets_delete(request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "请求体不是合法 JSON"}, status=400)
        删除预设(body.get("name"))
        return web.json_response({"ok": True, "presets": 读取预设()})

    print("\033[36m[TrucyNodes]\033[0m API预设地址簿接口已注册（/trucyllm/api_presets）")
except Exception as _e:  # 非 ComfyUI 环境（单测直 import）时静默跳过，节点内路径仍可用
    print(f"\033[33m[TrucyNodes]\033[0m API预设接口未注册（{_e}），节点内「保存为预设」路径仍可用")

_LLM节点数 = sum(1 for k in NODE_CLASS_MAPPINGS
                 if k in ("TrucyLLMLoader", "TrucySkillLoader", "TrucyChat", "TrucyPromptH3QWI",
                          "TrucyUnloadModel", "TrucyVLMRunner", "TrucyH3RefEncode",
                          "TrucyH3PromptEncode", "TrucyH3RefToVideo"))
print("\033[36m[TrucyNodes]\033[0m "
      f"{len(NODE_CLASS_MAPPINGS)} nodes | LLM Loader Trucy + Skill Runner Trucy + VLM Runner Trucy"
      f" + H3 ref2v Trucy 已合并入本包"
      f"（LLM 节点 {_LLM节点数}/9；官方 MiniMax H3 参考转视频节点为视频参考备用通道）")
