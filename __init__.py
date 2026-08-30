# --- ComfyUI-TrucyNodes 初始化文件 (Master Unified Version) ---

# ========================================================
# 🚀 Windows 多国语言子进程编码防崩溃热补丁
# 解决部分插件因 GBK / UTF-8 字符冲突导致启动崩溃的问题
# ========================================================
import subprocess


_orig_Popen_init = subprocess.Popen.__init__


def _patched_Popen_init(self, *args, **kwargs):
    if kwargs.get("encoding") in ("utf-8", "utf8"):
        kwargs["errors"] = "replace"

    _orig_Popen_init(self, *args, **kwargs)


subprocess.Popen.__init__ = _patched_Popen_init


# ========================================================
# 1. 基础模块导入
# ========================================================
from .audio_nodes import (
    TrucyAudioLoaderIndex,
    AudioLengthDetector,
    EmptyAudioGenerator,
    TrucySaveAudio,
)

from .text_nodes import (
    TrucyTxtBatchLoader,
    TrucyTxtPreviewAndSave,
    TrucySymbolSniffer,
    TrucyTextToNumber,
    TrucyTextSlicerSmart,
    TrucyTextCleaner,
)

from .excel_nodes import (
    TrucyExcelReader,
    TrucyExcelReader5,
    TrucyExcelReader10,
)

from .klein_nodes import (
    TrucyKleinEncode,
    TrucyKleinEncode5,
)

from .image_adapter import (
    TrucyImageAdapter,
    TrucyAssetGrid5,
    TrucyAssetGrid10,
    TrucyImageBridge5,
    TrucyImageBridge10,
)


# ========================================================
# 2. 工业工具箱导入 (trucy_toolkit.py)
# ========================================================
from .trucy_toolkit import (
    TrucyImageLoaderString5,
    TrucyImageLoaderString10,
    TrucyFolderIterator,
    TrucyPromptSplitter5,
    TrucyPromptSplitter10,
    TrucyIDExtractor,
    TrucyStringSlicer,
    TrucyDatasetSaver,
)


# ========================================================
# 3. 万能切换器模块导入 (trucy_switch.py)
# ========================================================
from .trucy_switch import (
    TrucyAnySwitch5,
    TrucyAnySwitch10,
    TrucyControlBridge,
)


# ========================================================
# 4. 视频及 MiniMax H3 模块安全导入 (trucy_video.py)
# ========================================================
try:
    from .trucy_video import (
        TrucyVideoLoaderIndex,
        TrucyMiniMaxH3Prep,
        TrucyMiniMaxH3Prompt,
    )

except Exception as e:
    print(
        f"\n[TrucyNodes] ❌ 导入 trucy_video.py 失败！"
        f"错误信息：{e}"
    )

    import traceback
    traceback.print_exc()

    print(
        "[TrucyNodes] "
        "--------------------------------------------------\n"
    )

    TrucyVideoLoaderIndex = None
    TrucyMiniMaxH3Prep = None
    TrucyMiniMaxH3Prompt = None


# ========================================================
# 5. 高阶逻辑循环模块导入 (trucy_loop.py)
# ========================================================
from .trucy_loop import (
    TrucyForLoopStart9ch,
    TrucyForLoopEnd9ch,
    TrucyForLoopStart2ch,
    TrucyForLoopEnd2ch,
)


# ========================================================
# 6. 前端远程控制模块导入 (trucy_remote.py)
# ========================================================
from .trucy_remote import (
    TrucyRemoteToggle5x5,
    TrucyMasterIntRouter,
)


# ========================================================
# 7. 绝对路径文档加载器安全导入 (trucy_doc.py)
# ========================================================
try:
    from .trucy_doc import TrucyDocLoader

except Exception as e:
    print(
        f"\n[TrucyNodes] ❌ 导入 trucy_doc.py 失败！"
        f"错误信息：{e}"
    )

    import traceback
    traceback.print_exc()

    print(
        "[TrucyNodes] "
        "--------------------------------------------------\n"
    )

    TrucyDocLoader = None


# ========================================================
# 节点类名映射（ComfyUI 内部识别名称）
# ========================================================
NODE_CLASS_MAPPINGS = {
    # ----------------------------------------------------
    # 音频工具组
    # ----------------------------------------------------
    "TrucyAudioLoaderIndex": TrucyAudioLoaderIndex,
    "AudioLengthDetector": AudioLengthDetector,
    "EmptyAudioGenerator": EmptyAudioGenerator,
    "TrucySaveAudio": TrucySaveAudio,

    # ----------------------------------------------------
    # 文本工具组
    # ----------------------------------------------------
    "TrucyTxtBatchLoader": TrucyTxtBatchLoader,
    "TrucyTxtPreviewAndSave": TrucyTxtPreviewAndSave,
    "TrucySymbolSniffer": TrucySymbolSniffer,
    "TrucyTextToNumber": TrucyTextToNumber,
    "TrucyTextSlicerSmart": TrucyTextSlicerSmart,
    "TrucyTextCleaner": TrucyTextCleaner,

    # ----------------------------------------------------
    # 万能切换器与桥接控制
    # ----------------------------------------------------
    "TrucyAnySwitch5": TrucyAnySwitch5,
    "TrucyAnySwitch10": TrucyAnySwitch10,
    "TrucyControlBridge": TrucyControlBridge,

    # ----------------------------------------------------
    # 远程控制器
    # ----------------------------------------------------
    "TrucyRemoteToggle5x5": TrucyRemoteToggle5x5,
    "TrucyMasterIntRouter": TrucyMasterIntRouter,

    # ----------------------------------------------------
    # Excel、核心溶图与分辨率适配
    # ----------------------------------------------------
    "TrucyExcelReader": TrucyExcelReader,
    "TrucyExcelReader5": TrucyExcelReader5,
    "TrucyExcelReader10": TrucyExcelReader10,
    "TrucyKleinEncode": TrucyKleinEncode,
    "TrucyKleinEncode5": TrucyKleinEncode5,
    "TrucyImageAdapter": TrucyImageAdapter,
    "TrucyAssetGrid5": TrucyAssetGrid5,
    "TrucyAssetGrid10": TrucyAssetGrid10,
    "TrucyImageBridge5": TrucyImageBridge5,
    "TrucyImageBridge10": TrucyImageBridge10,

    # ----------------------------------------------------
    # Trucy Toolkit 工业工具箱
    # ----------------------------------------------------
    "TrucyImageLoaderString5": TrucyImageLoaderString5,
    "TrucyImageLoaderString10": TrucyImageLoaderString10,
    "TrucyFolderIterator": TrucyFolderIterator,
    "TrucyPromptSplitter5": TrucyPromptSplitter5,
    "TrucyPromptSplitter10": TrucyPromptSplitter10,
    "TrucyIDExtractor": TrucyIDExtractor,
    "TrucyStringSlicer": TrucyStringSlicer,
    "TrucyDatasetSaver": TrucyDatasetSaver,

    # ----------------------------------------------------
    # 逻辑循环（9 通道版与 2 通道版）
    # ----------------------------------------------------
    "TrucyForLoopStart9ch": TrucyForLoopStart9ch,
    "TrucyForLoopEnd9ch": TrucyForLoopEnd9ch,
    "TrucyForLoopStart2ch": TrucyForLoopStart2ch,
    "TrucyForLoopEnd2ch": TrucyForLoopEnd2ch,
}


# ========================================================
# 动态挂载可能受环境影响的视频、MiniMax H3 和文档节点
# ========================================================
if TrucyVideoLoaderIndex is not None:
    NODE_CLASS_MAPPINGS[
        "TrucyVideoLoaderIndex"
    ] = TrucyVideoLoaderIndex

if TrucyMiniMaxH3Prep is not None:
    NODE_CLASS_MAPPINGS[
        "TrucyMiniMaxH3Prep"
    ] = TrucyMiniMaxH3Prep

if TrucyMiniMaxH3Prompt is not None:
    NODE_CLASS_MAPPINGS[
        "TrucyMiniMaxH3Prompt"
    ] = TrucyMiniMaxH3Prompt

if TrucyDocLoader is not None:
    NODE_CLASS_MAPPINGS[
        "TrucyDocLoader"
    ] = TrucyDocLoader


# ========================================================
# 节点显示名称映射（ComfyUI 菜单显示名称）
# ========================================================
NODE_DISPLAY_NAME_MAPPINGS = {
    # ----------------------------------------------------
    # 音频工具组
    # ----------------------------------------------------
    "TrucyAudioLoaderIndex":
        "🚀 Audio Loader by Index (Trucy)",

    "AudioLengthDetector":
        "🚀 Audio Detector & Padder (Trucy)",

    "EmptyAudioGenerator":
        "🚀 Empty Audio Generator (Trucy)",

    "TrucySaveAudio":
        "🚀 Save Audio (Trucy)",

    # ----------------------------------------------------
    # 文本工具组
    # ----------------------------------------------------
    "TrucyTxtBatchLoader":
        "🚀 TXT Loader by Index (Trucy)",

    "TrucyTxtPreviewAndSave":
        "🚀 Text Preview & Save (Trucy)",

    "TrucySymbolSniffer":
        "🚀 Text Symbol Sniffer (Trucy)",

    "TrucyTextToNumber":
        "🚀 Text to Number Converter (Trucy)",

    "TrucyTextSlicerSmart":
        "🚀 Text Smart Slicer (Trucy)",

    "TrucyTextCleaner":
        "🚀 Text Cleaner (Trucy)",

    # ----------------------------------------------------
    # 万能切换器与桥接控制
    # ----------------------------------------------------
    "TrucyAnySwitch5":
        "🚀 Any Switch (5ch) (Trucy)",

    "TrucyAnySwitch10":
        "🚀 Any Switch (10ch) (Trucy)",

    "TrucyControlBridge":
        "🚀 Control Bridge (Trucy)",

    # ----------------------------------------------------
    # 远程控制器
    # ----------------------------------------------------
    "TrucyRemoteToggle5x5":
        "🚀 Remote Toggle 5x5 (Trucy)",

    "TrucyMasterIntRouter":
        "🚀 5-way Mute/Bypass Nodes-Remote (Trucy)",

    # ----------------------------------------------------
    # Excel、核心溶图与图像适配
    # ----------------------------------------------------
    "TrucyExcelReader": 
        "🚀 Excel-Reader-Trucy",
        
    "TrucyExcelReader5": 
        "🚀 Excel-Reader-5-Trucy",
        
    "TrucyExcelReader10":
        "🚀 Excel-Reader-10-Trucy",

    "TrucyKleinEncode":
        "🚀 Klein-Model Text Encode (10ch) (Trucy)",

    "TrucyKleinEncode5":
        "🚀 Klein-Model Text Encode (5ch) (Trucy)",

    "TrucyImageAdapter":
        "🚀 Image Size Adapter (Trucy)",

    "TrucyAssetGrid5":
        "🚀 Trucy Asset Grid (5)",

    "TrucyAssetGrid10":
        "🚀 Trucy Asset Grid (10)",

    "TrucyImageBridge5":
        "🚀 Image Bridge (5ch) (Trucy)",

    "TrucyImageBridge10":
        "🚀 Image Bridge (10ch) (Trucy)",

    # ----------------------------------------------------
    # Trucy Toolkit 工业工具箱
    # ----------------------------------------------------
    "TrucyImageLoaderString5":
        "🚀 Trucy Image Loader (String 5)",

    "TrucyImageLoaderString10":
        "🚀 Trucy Image Loader (String 10)",

    "TrucyFolderIterator":
        "🚀 Trucy Folder Iterator",

    "TrucyPromptSplitter5":
        "🚀 Trucy Text Splitter (5)",

    "TrucyPromptSplitter10":
        "🚀 Trucy Text Splitter (10)",

    "TrucyIDExtractor":
        "🚀 Trucy ID Extractor",

    "TrucyStringSlicer":
        "🚀 Trucy String Slicer",

    "TrucyDatasetSaver":
        "🚀 Trucy Dataset Saver",

    # ----------------------------------------------------
    # 视频与 MiniMax H3
    # ----------------------------------------------------
    "TrucyVideoLoaderIndex":
        "🚀 Video Loader by Index (Trucy)",

    "TrucyMiniMaxH3Prep":
        "🚀 MiniMax H3 Multi-Ref Data Prep (Trucy)",

    "TrucyMiniMaxH3Prompt":
        "🚀 MiniMax H3 Prompt & Conditioning (Trucy)",

    # ----------------------------------------------------
    # 文档加载器
    # ----------------------------------------------------
    "TrucyDocLoader":
        "🚀 Doc-Loader-Trucy",

    # ----------------------------------------------------
    # 逻辑循环节点
    # ----------------------------------------------------
    "TrucyForLoopStart9ch":
        "🚀 Trucy For Loop Start (9ch)",

    "TrucyForLoopEnd9ch":
        "🚀 Trucy For Loop End (9ch)",

    "TrucyForLoopStart2ch":
        "🚀 Trucy For Loop Start (2ch)",

    "TrucyForLoopEnd2ch":
        "🚀 Trucy For Loop End (2ch)",
}


# ========================================================
# 前端目录
# ========================================================
WEB_DIRECTORY = "./web"


# ========================================================
# 对外导出
# ========================================================
__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]