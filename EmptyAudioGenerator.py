import torch

class EmptyAudioGenerator:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (["按秒数 (Seconds)", "按帧数 (Frames)"], {"default": "按秒数 (Seconds)"}),
                "seconds": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3600.0, "step": 0.001}),
                "frames": ("INT", {"default": 24, "min": 0, "max": 1000000}),
                "fps": ("INT", {"default": 24, "min": 1, "max": 120}),
                "sample_rate": ([44100, 48000, 16000, 22050, 8000], {"default": 44100}),
                "channels": ("INT", {"default": 2, "min": 1, "max": 6, "step": 1}),
            }
        }

    RETURN_TYPES = ("AUDIO", "FLOAT", "INT")
    RETURN_NAMES = ("audio (音频)", "length_sec (时长)", "total_samples (总采样数)")
    FUNCTION = "generate_silence"
    CATEGORY = "Audio/Processing"

    def generate_silence(self, mode, seconds, frames, fps, sample_rate, channels):
        # 计算时长
        if mode == "按帧数 (Frames)":
            duration = frames / fps
        else:
            duration = seconds

        # 计算总采样数
        total_samples = int(duration * sample_rate)
        
        # 创建全零张量 [batch=1, channels, samples]
        waveform = torch.zeros((1, channels, total_samples), dtype=torch.float32)
        
        audio = {
            "waveform": waveform,
            "sample_rate": sample_rate
        }
        
        return (audio, duration, total_samples)