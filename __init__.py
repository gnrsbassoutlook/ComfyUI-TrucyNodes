# --- ComfyUI-TrucyNodes 初始化文件 (Master Unified Version) ---

# 1. 基础模块导入
from .audio_nodes import TrucyAudioLoaderIndex, AudioLengthDetector, EmptyAudioGenerator, TrucySaveAudio
from .text_nodes import TrucyTxtBatchLoader, TrucyTxtPreviewAndSave, TrucySymbolSniffer, TrucyTextToNumber, TrucyTextSlicerSmart
from .excel_nodes import TrucyExcelReader
from .klein_nodes import TrucyKleinEncode, TrucyKleinEncode5
from .image_adapter import TrucyImageAdapter, TrucyAssetGrid5, TrucyAssetGrid10, TrucyImageBridge5, TrucyImageBridge10

# 2. 工业工具箱导入
from .trucy_toolkit import (
    TrucyImageLoaderString5, TrucyImageLoaderString10, 
    TrucyFolderIterator, TrucyPromptSplitter5, TrucyPromptSplitter10,
    TrucyIDExtractor, TrucyStringSlicer, TrucyDatasetSaver
)

# 3. 万能切换器模块
from .trucy_switch import TrucyAnySwitch5, TrucyAnySwitch10, TrucyControlBridge

# 4. 视频与流媒体模块安全导入
try:
    from .trucy_video import TrucyVideoCombine, TrucyLTXMSR, TrucyVideoLoaderIndex
except ImportError as e:
    print(f"\n[TrucyNodes] ❌ 导入 trucy_video.py 失败！错误信息: {e}")
    TrucyVideoCombine = None
    TrucyLTXMSR = None
    TrucyVideoLoaderIndex = None

# 5. 高阶逻辑循环模块
from .trucy_loop import (
    TrucyForLoopStart9ch, TrucyForLoopEnd9ch,
    TrucyForLoopStart2ch, TrucyForLoopEnd2ch
)

# ========================================================
# 节点类名映射 (ComfyUI 内部逻辑识别)
# ========================================================
NODE_CLASS_MAPPINGS = {
    # 音频工具组
    "TrucyAudioLoaderIndex": TrucyAudioLoaderIndex,
    "AudioLengthDetector": AudioLengthDetector,
    "EmptyAudioGenerator": EmptyAudioGenerator,
    "TrucySaveAudio": TrucySaveAudio,
    
    # 文本工具组
    "TrucyTxtBatchLoader": TrucyTxtBatchLoader,
    "TrucyTxtPreviewAndSave": TrucyTxtPreviewAndSave,
    "TrucySymbolSniffer": TrucySymbolSniffer,
    "TrucyTextToNumber": TrucyTextToNumber,
    "TrucyTextSlicerSmart": TrucyTextSlicerSmart,
    
    # 切换与桥接
    "TrucyAnySwitch5": TrucyAnySwitch5,
    "TrucyAnySwitch10": TrucyAnySwitch10,
    "TrucyControlBridge": TrucyControlBridge,
    
    # 核心溶图与适配
    "TrucyExcelReader": TrucyExcelReader,
    "TrucyKleinEncode": TrucyKleinEncode,       
    "TrucyKleinEncode5": TrucyKleinEncode5,     
    "TrucyImageAdapter": TrucyImageAdapter,
    "TrucyAssetGrid5": TrucyAssetGrid5,
    "TrucyAssetGrid10": TrucyAssetGrid10,
    "TrucyImageBridge5": TrucyImageBridge5,     
    "TrucyImageBridge10": TrucyImageBridge10,   
    
    # 工具箱
    "TrucyImageLoaderString5": TrucyImageLoaderString5,
    "TrucyImageLoaderString10": TrucyImageLoaderString10,
    "TrucyFolderIterator": TrucyFolderIterator,
    "TrucyPromptSplitter5": TrucyPromptSplitter5,
    "TrucyPromptSplitter10": TrucyPromptSplitter10,
    "TrucyIDExtractor": TrucyIDExtractor,
    "TrucyStringSlicer": TrucyStringSlicer,
    "TrucyDatasetSaver": TrucyDatasetSaver,
    
    # 逻辑循环
    "TrucyForLoopStart9ch": TrucyForLoopStart9ch,
    "TrucyForLoopEnd9ch": TrucyForLoopEnd9ch,
    "TrucyForLoopStart2ch": TrucyForLoopStart2ch,
    "TrucyForLoopEnd2ch": TrucyForLoopEnd2ch
}

# 动态挂载视频节点
if TrucyVideoCombine:
    NODE_CLASS_MAPPINGS["TrucyVideoCombine"] = TrucyVideoCombine
    NODE_CLASS_MAPPINGS["TrucyLTXMSR"] = TrucyLTXMSR
    NODE_CLASS_MAPPINGS["TrucyVideoLoaderIndex"] = TrucyVideoLoaderIndex

# ========================================================
# 节点显示名称映射 (菜单 UI 显示)
# ========================================================
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
    
    "TrucyAnySwitch5": "🚀 Any Switch (5ch) (Trucy)",
    "TrucyAnySwitch10": "🚀 Any Switch (10ch) (Trucy)",
    "TrucyControlBridge": "🚀 Control Bridge (Trucy)",
    
    "TrucyExcelReader": "🚀 Excel Cell Reader (Trucy)",
    "TrucyKleinEncode": "🚀 Klein-Model Text Encode (10ch) (Trucy)",
    "TrucyKleinEncode5": "🚀 Klein-Model Text Encode (5ch) (Trucy)",
    "TrucyImageAdapter": "🚀 Image Size Adapter (Trucy)",
    "TrucyAssetGrid5": "🚀 Trucy Asset Grid (5)",
    "TrucyAssetGrid10": "🚀 Trucy Asset Grid (10)",
    "TrucyImageBridge5": "🚀 Image Bridge (5ch) (Trucy)",
    "TrucyImageBridge10": "🚀 Image Bridge (10ch) (Trucy)",
    
    "TrucyImageLoaderString5": "🚀 Trucy Image Loader (String 5)",
    "TrucyImageLoaderString10": "🚀 Trucy Image Loader (String 10)",
    "TrucyFolderIterator": "🚀 Trucy Folder Iterator",
    "TrucyPromptSplitter5": "🚀 Trucy Text Splitter (5)",
    "TrucyPromptSplitter10": "🚀 Trucy Text Splitter (10)",
    "TrucyIDExtractor": "🚀 Trucy ID Extractor",
    "TrucyStringSlicer": "🚀 Trucy String Slicer",
    "TrucyDatasetSaver": "🚀 Trucy Dataset Saver",
    
    "TrucyVideoCombine": "🚀 Trucy Video Combine",
    "TrucyLTXMSR": "🚀 Trucy LTX MSR (Video Prep)",
    "TrucyVideoLoaderIndex": "🚀 Video Loader by Index (Trucy)", # 显示名称
    
    "TrucyForLoopStart9ch": "🚀 Trucy For Loop Start (9ch)",
    "TrucyForLoopEnd9ch": "🚀 Trucy For Loop End (9ch)",
    "TrucyForLoopStart2ch": "🚀 Trucy For Loop Start (2ch)",
    "TrucyForLoopEnd2ch": "🚀 Trucy For Loop End (2ch)"
}

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]