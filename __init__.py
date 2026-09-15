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
from .audio_nodes import TrucyAudioLoaderIndex, AudioLengthDetector, EmptyAudioGenerator, TrucySaveAudio
from .text_nodes import TrucyTxtBatchLoader, TrucyTxtPreviewAndSave, TrucySymbolSniffer, TrucyTextToNumber, TrucyTextSlicerSmart, TrucyTextCleaner
from .excel_nodes import TrucyExcelReader, TrucyExcelReader5, TrucyExcelReader10
from .klein_nodes import TrucyKleinEncode, TrucyKleinEncode5
from .image_adapter import TrucyImageLoaderIndex, TrucyImageAdapter, TrucyAssetGrid5, TrucyAssetGrid10, TrucyImageBridge5, TrucyImageBridge10
from .trucy_toolkit import TrucyImageLoaderString5, TrucyImageLoaderString10, TrucyFolderIterator, TrucyPromptSplitter5, TrucyPromptSplitter10, TrucyIDExtractor, TrucyStringSlicer, TrucyDatasetSaver
from .trucy_switch import TrucyAnySwitch5, TrucyAnySwitch10, TrucyControlBridge
from .trucy_loop import TrucyForLoopStart9ch, TrucyForLoopEnd9ch, TrucyForLoopStart2ch, TrucyForLoopEnd2ch
from .trucy_remote import TrucyRemoteToggle5x5, TrucyMasterIntRouter

# 可选模块安全导入
def _safe_import(module_name, class_names):
    try:
        mod = __import__(f"{__name__}.{module_name}", fromlist=class_names)
        return [getattr(mod, c, None) for c in class_names]
    except Exception as e:
        print(f"[TrucyNodes] ❌ 导入 {module_name} 失败: {e}")
        return [None] * len(class_names)

TrucyVideoLoaderIndex, TrucyMiniMaxH3Prep, TrucyMiniMaxH3Prompt = _safe_import("trucy_video", ["TrucyVideoLoaderIndex", "TrucyMiniMaxH3Prep", "TrucyMiniMaxH3Prompt"])
(TrucyVideoCombine,) = _safe_import("trucy_video_combine", ["TrucyVideoCombine"])
(TrucyDocLoader,) = _safe_import("trucy_doc", ["TrucyDocLoader"])

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
    "TrucyAnySwitch5": TrucyAnySwitch5,
    "TrucyAnySwitch10": TrucyAnySwitch10,
    "TrucyControlBridge": TrucyControlBridge,
    "TrucyRemoteToggle5x5": TrucyRemoteToggle5x5,
    "TrucyMasterIntRouter": TrucyMasterIntRouter,
    "TrucyExcelReader": TrucyExcelReader,
    "TrucyExcelReader5": TrucyExcelReader5,
    "TrucyExcelReader10": TrucyExcelReader10,
    "TrucyKleinEncode": TrucyKleinEncode,
    "TrucyKleinEncode5": TrucyKleinEncode5,
    "TrucyImageLoaderIndex": TrucyImageLoaderIndex,
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
    "TrucyForLoopEnd2ch": TrucyForLoopEnd2ch,
}

optional_nodes = {
    "TrucyVideoLoaderIndex": TrucyVideoLoaderIndex,
    "TrucyMiniMaxH3Prep": TrucyMiniMaxH3Prep,
    "TrucyMiniMaxH3Prompt": TrucyMiniMaxH3Prompt,
    "TrucyDocLoader": TrucyDocLoader,
    "TrucyVideoCombine": TrucyVideoCombine,
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
    "TrucyAnySwitch5": "🚀 Any Switch (6ch) (Trucy)",
    "TrucyAnySwitch10": "🚀 Any Switch (10ch) (Trucy)",
    "TrucyControlBridge": "🚀 Control Bridge (Trucy)",
    "TrucyRemoteToggle5x5": "🚀 Remote Toggle 6x6 (Trucy)",
    "TrucyMasterIntRouter": "🚀 5-way Mute/Bypass Nodes-Remote (Trucy)",
    "TrucyExcelReader": "🚀 Excel-Reader-Trucy",
    "TrucyExcelReader5": "🚀 Excel-Reader-6-Trucy",
    "TrucyExcelReader10": "🚀 Excel-Reader-10-Trucy",
    "TrucyKleinEncode": "🚀 Klein-Model Text Encode (10ch) (Trucy)",
    "TrucyKleinEncode5": "🚀 Klein-Model Text Encode (6ch) (Trucy)",
    "TrucyImageLoaderIndex": "🚀 Image Loader by Index (Trucy)",
    "TrucyImageAdapter": "🚀 Image Size Adapter (Trucy)",
    "TrucyAssetGrid5": "🚀 Trucy Asset Grid (6)",
    "TrucyAssetGrid10": "🚀 Trucy Asset Grid (10)",
    "TrucyImageBridge5": "🚀 Image Bridge (6ch) (Trucy)",
    "TrucyImageBridge10": "🚀 Image Bridge (10ch) (Trucy)",
    "TrucyImageLoaderString5": "🚀 Trucy Image Loader (String 6)",
    "TrucyImageLoaderString10": "🚀 Trucy Image Loader (String 10)",
    "TrucyFolderIterator": "🚀 Trucy Folder Iterator",
    "TrucyPromptSplitter5": "🚀 Trucy Text Splitter (6)",
    "TrucyPromptSplitter10": "🚀 Trucy Text Splitter (10)",
    "TrucyIDExtractor": "🚀 Trucy ID Extractor",
    "TrucyStringSlicer": "🚀 Trucy String Slicer",
    "TrucyDatasetSaver": "🚀 Trucy Dataset Saver",
    "TrucyVideoLoaderIndex": "🚀 Video Loader by Index (Trucy)",
    "TrucyMiniMaxH3Prep": "🚀 MiniMax H3 Multi-Ref Data Prep (Trucy)",
    "TrucyMiniMaxH3Prompt": "🚀 MiniMax H3 Prompt & Conditioning (Trucy)",
    "TrucyVideoCombine": "🚀 Video-Combine-Trucy",
    "TrucyDocLoader": "🚀 Doc-Loader-Trucy",
    "TrucyForLoopStart9ch": "🚀 Trucy For Loop Start (9ch)",
    "TrucyForLoopEnd9ch": "🚀 Trucy For Loop End (9ch)",
    "TrucyForLoopStart2ch": "🚀 Trucy For Loop Start (2ch)",
    "TrucyForLoopEnd2ch": "🚀 Trucy For Loop End (2ch)",
}

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]