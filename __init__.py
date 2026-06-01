# --- ComfyUI-TrucyNodes 初始化文件 (最终统合版) ---

# 1. 基础模块导入
from .audio_nodes import TrucyAudioLoaderIndex, AudioLengthDetector, EmptyAudioGenerator
# 核心修改：这里加入了新节点 TrucyTextSlicerSmart
from .text_nodes import TrucyTxtBatchLoader, TrucyTxtPreviewAndSave, TrucySymbolSniffer, TrucyTextSlicerSmart
from .excel_nodes import TrucyExcelReader
from .klein_nodes import TrucyKleinEncode, TrucyKleinEncode5
from .image_adapter import TrucyImageAdapter

# 2. 工业工具箱导入
from .trucy_toolkit import (
    TrucyImageLoaderString5, TrucyImageLoaderString10, 
    TrucyFolderIterator, TrucyPromptSplitter5, TrucyPromptSplitter10,
    TrucyIDExtractor, TrucyStringSlicer, TrucyAssetGrid5, TrucyAssetGrid10, TrucyDatasetSaver
)

# 3. 视频合成模块安全导入
try:
    from .trucy_video import TrucyVideoCombine
except ImportError:
    TrucyVideoCombine = None

# 4. 高阶逻辑循环模块导入 (2ch/9ch)
from .trucy_loop import (
    TrucyForLoopStart9ch, TrucyForLoopEnd9ch,
    TrucyForLoopStart2ch, TrucyForLoopEnd2ch
)

# ========================================================
# 节点类名映射
# ========================================================
NODE_CLASS_MAPPINGS = {
    # 音频工具组
    "TrucyAudioLoaderIndex": TrucyAudioLoaderIndex,
    "AudioLengthDetector": AudioLengthDetector,
    "EmptyAudioGenerator": EmptyAudioGenerator,
    
    # 文本工具组
    "TrucyTxtBatchLoader": TrucyTxtBatchLoader,
    "TrucyTxtPreviewAndSave": TrucyTxtPreviewAndSave,
    "TrucySymbolSniffer": TrucySymbolSniffer,
    "TrucyTextSlicerSmart": TrucyTextSlicerSmart, # 新增
    
    # 核心溶图与分辨率适配
    "TrucyExcelReader": TrucyExcelReader,
    "TrucyKleinEncode": TrucyKleinEncode,
    "TrucyKleinEncode5": TrucyKleinEncode5,
    "TrucyImageAdapter": TrucyImageAdapter,
    
    # Trucy Toolkit 工业工具箱
    "TrucyImageLoaderString5": TrucyImageLoaderString5,
    "TrucyImageLoaderString10": TrucyImageLoaderString10,
    "TrucyFolderIterator": TrucyFolderIterator,
    "TrucyPromptSplitter5": TrucyPromptSplitter5,
    "TrucyPromptSplitter10": TrucyPromptSplitter10,
    "TrucyIDExtractor": TrucyIDExtractor,
    "TrucyStringSlicer": TrucyStringSlicer,
    "TrucyAssetGrid5": TrucyAssetGrid5,
    "TrucyAssetGrid10": TrucyAssetGrid10,
    "TrucyDatasetSaver": TrucyDatasetSaver,
    
    # 逻辑循环 (9通道版与2通道版)
    "TrucyForLoopStart9ch": TrucyForLoopStart9ch,
    "TrucyForLoopEnd9ch": TrucyForLoopEnd9ch,
    "TrucyForLoopStart2ch": TrucyForLoopStart2ch,
    "TrucyForLoopEnd2ch": TrucyForLoopEnd2ch
}

if TrucyVideoCombine:
    NODE_CLASS_MAPPINGS["TrucyVideoCombine"] = TrucyVideoCombine

# ========================================================
# 节点显示名称映射
# ========================================================
NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyAudioLoaderIndex": "🚀 Audio Loader by Index (Trucy)",
    "AudioLengthDetector": "🚀 Audio Detector & Padder (Trucy)",
    "EmptyAudioGenerator": "🚀 Empty Audio Generator (Trucy)",
    "TrucyTxtBatchLoader": "🚀 TXT Loader by Index (Trucy)",
    "TrucyTxtPreviewAndSave": "🚀 Text Preview & Save (Trucy)",
    "TrucySymbolSniffer": "🚀 Text Symbol Sniffer (Trucy)",
    "TrucyTextSlicerSmart": "🚀 Text Smart Slicer (Trucy)", # 新增
    "TrucyExcelReader": "🚀 Excel Cell Reader (Trucy)",
    "TrucyKleinEncode": "🚀 Klein-Model Text Encode (10ch) (Trucy)",
    "TrucyKleinEncode5": "🚀 Klein-Model Text Encode (5ch) (Trucy)",
    "TrucyImageAdapter": "🚀 Image Size Adapter (Trucy)",
    "TrucyImageLoaderString5": "🚀 Trucy Image Loader (String 5)",
    "TrucyImageLoaderString10": "🚀 Trucy Image Loader (String 10)",
    "TrucyFolderIterator": "🚀 Trucy Folder Iterator",
    "TrucyPromptSplitter5": "🚀 Trucy Text Splitter (5)",
    "TrucyPromptSplitter10": "🚀 Trucy Text Splitter (10)",
    "TrucyIDExtractor": "🚀 Trucy ID Extractor",
    "TrucyStringSlicer": "🚀 Trucy String Slicer",
    "TrucyAssetGrid5": "🚀 Trucy Asset Grid (5)",
    "TrucyAssetGrid10": "🚀 Trucy Asset Grid (10)",
    "TrucyDatasetSaver": "🚀 Trucy Dataset Saver",
    "TrucyVideoCombine": "🚀 Trucy Video Combine",
    "TrucyForLoopStart9ch": "🚀 Trucy For Loop Start (9ch)",
    "TrucyForLoopEnd9ch": "🚀 Trucy For Loop End (9ch)",
    "TrucyForLoopStart2ch": "🚀 Trucy For Loop Start (2ch)",
    "TrucyForLoopEnd2ch": "🚀 Trucy For Loop End (2ch)"
}

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]