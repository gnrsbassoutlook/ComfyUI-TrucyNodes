# --- ComfyUI-TrucyNodes 初始化文件 (Master Unified Version) ---

from .audio_nodes import TrucyAudioLoaderIndex, AudioLengthDetector, EmptyAudioGenerator
from .text_nodes import TrucyTxtBatchLoader, TrucyTxtPreviewAndSave, TrucySymbolSniffer, TrucyTextToNumber, TrucyTextSlicerSmart
from .excel_nodes import TrucyExcelReader
from .klein_nodes import TrucyKleinEncode, TrucyKleinEncode5
from .image_adapter import TrucyImageAdapter, TrucyAssetGrid5, TrucyAssetGrid10, TrucyImageBridge5, TrucyImageBridge10

from .trucy_toolkit import (
    TrucyImageLoaderString5, TrucyImageLoaderString10, 
    TrucyFolderIterator, TrucyPromptSplitter5, TrucyPromptSplitter10,
    TrucyIDExtractor, TrucyStringSlicer, TrucyDatasetSaver
)

try:
    from .trucy_video import TrucyVideoCombine, TrucyLTXMSR
except ImportError as e:
    # 打印详细错误方便排查
    print(f"\n[TrucyNodes] ❌ 导入 trucy_video.py 失败！错误信息: {e}")
    import traceback
    traceback.print_exc()
    print("[TrucyNodes] --------------------------------------------------\n")
    TrucyVideoCombine = None
    TrucyLTXMSR = None

from .trucy_loop import (
    TrucyForLoopStart9ch, TrucyForLoopEnd9ch,
    TrucyForLoopStart2ch, TrucyForLoopEnd2ch
)

# 【核心修改】：通过 try...except 尝试安全导入 TrucySaveAudio
try:
    from .audio_nodes import TrucySaveAudio
except ImportError:
    TrucySaveAudio = None


NODE_CLASS_MAPPINGS = {
    "TrucyAudioLoaderIndex": TrucyAudioLoaderIndex,
    "AudioLengthDetector": AudioLengthDetector,
    "EmptyAudioGenerator": EmptyAudioGenerator,
    
    "TrucyTxtBatchLoader": TrucyTxtBatchLoader,
    "TrucyTxtPreviewAndSave": TrucyTxtPreviewAndSave,
    "TrucySymbolSniffer": TrucySymbolSniffer,
    "TrucyTextToNumber": TrucyTextToNumber,
    "TrucyTextSlicerSmart": TrucyTextSlicerSmart,
    
    "TrucyExcelReader": TrucyExcelReader,
    "TrucyKleinEncode": TrucyKleinEncode,       
    "TrucyKleinEncode5": TrucyKleinEncode5,     
    "TrucyImageAdapter": TrucyImageAdapter,
    "TrucyAssetGrid5": TrucyAssetGrid5,
    "TrucyAssetGrid10": TrucyAssetGrid10,
    "TrucyImageBridge5": TrucyImageBridge5,     
    "TrucyImageBridge10": TrucyImageBridge10,   
    
    "TrucyImageLoaderString5": TrucyImageLoaderString5,
    "TrucyImageLoaderString10": TrucyImageLoaderString10,
    "TrucyFolderIterator": TrucyFolderIterator,
    "TrucyPromptSplitter5": TrucyPromptSplitter5,
    "TrucyPromptSplitter10": TrucyPromptSplitter10,
    "TrucyIDExtractor": TrucyIDExtractor,
    "TrucyStringSlicer": TrucyStringSlicer,
    "TrucyDatasetSaver": TrucyDatasetSaver,
    
    "TrucyForLoopStart9ch": TrucyForLoopStart9ch,
    "TrucyForLoopEnd9ch": TrucyForLoopEnd9ch,
    "TrucyForLoopStart2ch": TrucyForLoopStart2ch,
    "TrucyForLoopEnd2ch": TrucyForLoopEnd2ch
}

if TrucyVideoCombine:
    NODE_CLASS_MAPPINGS["TrucyVideoCombine"] = TrucyVideoCombine
    NODE_CLASS_MAPPINGS["TrucyLTXMSR"] = TrucyLTXMSR

# 【核心修改】：如果成功导入了 TrucySaveAudio，才注册它
if TrucySaveAudio:
    NODE_CLASS_MAPPINGS["TrucySaveAudio"] = TrucySaveAudio


NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyAudioLoaderIndex": "🚀 Audio Loader by Index (Trucy)",
    "AudioLengthDetector": "🚀 Audio Detector & Padder (Trucy)",
    "EmptyAudioGenerator": "🚀 Empty Audio Generator (Trucy)",
    "TrucyTxtBatchLoader": "🚀 TXT Loader by Index (Trucy)",
    "TrucyTxtPreviewAndSave": "🚀 Text Preview & Save (Trucy)",
    "TrucySymbolSniffer": "🚀 Text Symbol Sniffer (Trucy)",
    "TrucyTextToNumber": "🚀 Text to Number Converter (Trucy)",
    "TrucyTextSlicerSmart": "🚀 Text Smart Slicer (Trucy)",
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
    "TrucyForLoopStart9ch": "🚀 Trucy For Loop Start (9ch)",
    "TrucyForLoopEnd9ch": "🚀 Trucy For Loop End (9ch)",
    "TrucyForLoopStart2ch": "🚀 Trucy For Loop Start (2ch)",
    "TrucyForLoopEnd2ch": "🚀 Trucy For Loop End (2ch)"
}

if TrucySaveAudio:
    NODE_DISPLAY_NAME_MAPPINGS["TrucySaveAudio"] = "🚀 Save Audio (Trucy)"

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]