# --- ComfyUI-TrucyNodes 初始化文件 (最终统合版) ---

# 1. 基础模块导入
from .audio_nodes import TrucyAudioLoaderIndex, AudioLengthDetector, EmptyAudioGenerator
from .text_nodes import TrucyTxtBatchLoader, TrucyTxtPreviewAndSave
from .excel_nodes import TrucyExcelReader
from .klein_nodes import TrucyKleinEncode
from .image_adapter import TrucyImageAdapter

# 2. 工具箱导入
from .trucy_toolkit import (
    TrucyImageLoaderString5, TrucyImageLoaderString10, 
    TrucyFolderIterator, TrucyPromptSplitter5, TrucyPromptSplitter10,
    TrucyIDExtractor, TrucyStringSlicer, TrucyAssetGrid5, TrucyAssetGrid10, TrucyDatasetSaver
)

# 3. 视频与逻辑 (循环节点区分 9ch 和 2ch)
from .trucy_video import TrucyVideoCombine
from .trucy_loop import (
    TrucyForLoopStart9ch, TrucyForLoopEnd9ch,
    TrucyForLoopStart2ch, TrucyForLoopEnd2ch
)

NODE_CLASS_MAPPINGS = {
    # 音频工具
    "TrucyAudioLoaderIndex": TrucyAudioLoaderIndex,
    "AudioLengthDetector": AudioLengthDetector,
    "EmptyAudioGenerator": EmptyAudioGenerator,
    
    # 文本工具
    "TrucyTxtBatchLoader": TrucyTxtBatchLoader,
    "TrucyTxtPreviewAndSave": TrucyTxtPreviewAndSave,
    
    # 核心资产与适配
    "TrucyExcelReader": TrucyExcelReader,
    "TrucyKleinEncode": TrucyKleinEncode,
    "TrucyImageAdapter": TrucyImageAdapter,
    
    # 工业工具箱
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
    
    # 视频合成
    "TrucyVideoCombine": TrucyVideoCombine,
    
    # 逻辑循环 (9通道版)
    "TrucyForLoopStart9ch": TrucyForLoopStart9ch,
    "TrucyForLoopEnd9ch": TrucyForLoopEnd9ch,
    
    # 逻辑循环 (2通道版)
    "TrucyForLoopStart2ch": TrucyForLoopStart2ch,
    "TrucyForLoopEnd2ch": TrucyForLoopEnd2ch
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyAudioLoaderIndex": "🚀 Audio Loader by Index (Trucy)",
    "AudioLengthDetector": "🚀 Audio Detector & Padder (Trucy)",
    "EmptyAudioGenerator": "🚀 Empty Audio Generator (Trucy)",
    "TrucyTxtBatchLoader": "🚀 TXT Batch Loader (Trucy)",
    "TrucyTxtPreviewAndSave": "🚀 Text Preview & Save (Trucy)",
    "TrucyExcelReader": "🚀 Excel Cell Reader (Trucy)",
    "TrucyKleinEncode": "🚀 Klein-Model Text Encode (Trucy)",
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
    
    # 循环节点显示名
    "TrucyForLoopStart9ch": "🚀 Trucy For Loop Start (9ch)",
    "TrucyForLoopEnd9ch": "🚀 Trucy For Loop End (9ch)",
    "TrucyForLoopStart2ch": "🚀 Trucy For Loop Start (2ch)",
    "TrucyForLoopEnd2ch": "🚀 Trucy For Loop End (2ch)"
}

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]