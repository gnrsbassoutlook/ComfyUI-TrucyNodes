# --- ComfyUI-TrucyNodes 初始化文件 ---

# 这里是关键：必须从整合后的 audio_nodes 导入，而不是旧的 audio_detector
from .audio_nodes import TrucyAudioLoaderIndex, AudioLengthDetector, EmptyAudioGenerator
from .text_nodes import TrucyTxtBatchLoader, TrucyTxtPreviewAndSave
from .excel_nodes import TrucyExcelReader
from .klein_nodes import TrucyKleinEncode
from .image_adapter import TrucyImageAdapter

NODE_CLASS_MAPPINGS = {
    "TrucyAudioLoaderIndex": TrucyAudioLoaderIndex,
    "AudioLengthDetector": AudioLengthDetector,
    "EmptyAudioGenerator": EmptyAudioGenerator,
    "TrucyTxtBatchLoader": TrucyTxtBatchLoader,
    "TrucyTxtPreviewAndSave": TrucyTxtPreviewAndSave,
    "TrucyExcelReader": TrucyExcelReader,
    "TrucyKleinEncode": TrucyKleinEncode,
    "TrucyImageAdapter": TrucyImageAdapter
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyAudioLoaderIndex": "Audio Loader by Index (Trucy)",
    "AudioLengthDetector": "Audio Detector & Padder (Trucy)",
    "EmptyAudioGenerator": "Empty Audio Generator (Trucy)",
    "TrucyTxtBatchLoader": "TXT Batch Loader (Trucy)",
    "TrucyTxtPreviewAndSave": "Text Preview & Save (Trucy)",
    "TrucyExcelReader": "Excel Cell Reader (Trucy)",
    "TrucyKleinEncode": "Klein-Model Text Encode (Trucy)",
    "TrucyImageAdapter": "Image Size Adapter (Trucy)"
}

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]