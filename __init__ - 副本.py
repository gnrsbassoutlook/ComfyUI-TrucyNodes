# --- ComfyUI-TrucyNodes 初始化文件 ---

from .audio_detector import AudioLengthDetector
from .EmptyAudioGenerator import EmptyAudioGenerator
from .excel_nodes import TrucyExcelReader
from .klein_nodes import TrucyKleinEncode

NODE_CLASS_MAPPINGS = {
    "AudioLengthDetector": AudioLengthDetector,
    "EmptyAudioGenerator": EmptyAudioGenerator,
    "TrucyExcelReader": TrucyExcelReader,
    "TrucyKleinEncode": TrucyKleinEncode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AudioLengthDetector": "Audio Detector & Padder (Trucy)",
    "EmptyAudioGenerator": "Empty Audio Generator (Trucy)",
    "TrucyExcelReader": "Excel Cell Reader (Trucy)",
    "TrucyKleinEncode": "Klein-Model Text Encode (Trucy)"
}

# 保持 WEB 目录注册
WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]