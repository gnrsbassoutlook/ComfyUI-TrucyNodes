# --- ComfyUI-TrucyNodes 初始化文件 ---

from .audio_detector import AudioLengthDetector
from .EmptyAudioGenerator import EmptyAudioGenerator
from .excel_nodes import TrucyExcelReader
from .klein_nodes import TrucyKleinEncode
from .image_adapter import TrucyImageAdapter # 文件名和类名现在对齐了

NODE_CLASS_MAPPINGS = {
    "AudioLengthDetector": AudioLengthDetector,
    "EmptyAudioGenerator": EmptyAudioGenerator,
    "TrucyExcelReader": TrucyExcelReader,
    "TrucyKleinEncode": TrucyKleinEncode,
    "TrucyImageAdapter": TrucyImageAdapter
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AudioLengthDetector": "Audio Detector & Padder (Trucy)",
    "EmptyAudioGenerator": "Empty Audio Generator (Trucy)",
    "TrucyExcelReader": "Excel Cell Reader (Trucy)",
    "TrucyKleinEncode": "Klein-Model Text Encode (Trucy)",
    "TrucyImageAdapter": "Image Size Adapter (Trucy)"
}

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]