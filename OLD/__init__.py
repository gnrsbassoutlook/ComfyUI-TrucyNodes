# 分别从两个文件中导入类
from .audio_detector import AudioLengthDetector
from .EmptyAudioGenerator import EmptyAudioGenerator

NODE_CLASS_MAPPINGS = {
    "AudioLengthDetector": AudioLengthDetector,
    "EmptyAudioGenerator": EmptyAudioGenerator
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AudioLengthDetector": "Audio Detector & Padder (音频检测与补齐)",
    "EmptyAudioGenerator": "Empty Audio Generator (空音频生成)"
}

# 保持 JS 目录注册
WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]