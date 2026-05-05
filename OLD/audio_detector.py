import math
import torch
import torch.nn.functional as F

class AudioLengthDetector:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO", ),
                "fps": ("INT", {"default": 24, "min": 1, "max": 120, "step": 1}),
                "enable_padding": ("BOOLEAN", {"default": True, "label_on": "ON (打开补偿)", "label_off": "OFF (关闭补偿)"}),
                "padding_level": (["250ms", "500ms", "750ms", "1000ms"], {"default": "250ms"}),
            }
        }

    RETURN_TYPES = ("AUDIO", "FLOAT", "INT")
    RETURN_NAMES = ("audio (音频)", "length_sec (时长)", "total_frames (总帧数)")
    FUNCTION = "process_audio"
    CATEGORY = "Audio/Processing"
    OUTPUT_NODE = True  # 必须设为True，前端UI才会接收到文字数据

    def process_audio(self, audio, fps, enable_padding, padding_level):
        waveform = audio["waveform"]
        sample_rate = audio["sample_rate"]
        
        # ComfyUI 中的 waveform 结构通常是 [batch, channels, samples]
        # 获取原始样本总数并计算原始秒数
        samples = waveform.shape[-1]
        original_length_sec = samples / sample_rate
        
        if enable_padding:
            # 提取补偿等级的毫秒数值，并转为秒
            step_ms = int(padding_level.replace("ms", ""))
            step_sec = step_ms / 1000.0
            
            # math.ceil 保证只能入不能舍，向上取到最近的步长边界
            # 例如 1.27s / 0.25 = 5.08 -> ceil(5.08) = 6 -> 6 * 0.25 = 1.50s
            target_length_sec = math.ceil(original_length_sec / step_sec) * step_sec
            target_samples = int(target_length_sec * sample_rate)
            
            # 计算需要补齐的样本数量
            pad_length = target_samples - samples
            if pad_length > 0:
                # 使用 PyTorch 原生的 pad 函数在最后一维（样本数）末尾补齐 0（绝对静音）
                padded_waveform = F.pad(waveform, (0, pad_length), "constant", 0)
            else:
                padded_waveform = waveform
                
            final_length_sec = target_length_sec
            final_audio = {"waveform": padded_waveform, "sample_rate": sample_rate}
        else:
            final_length_sec = original_length_sec
            final_audio = audio
            
        # 根据最终时长计算总帧数（采用经典的四舍五入）
        total_frames = round(final_length_sec * fps)
        
        # 准备要在节点界面直接显示的文字信息
        text_out = f"【检测结果】\n"
        text_out += f"原始时长: {original_length_sec:.3f} 秒\n"
        if enable_padding:
            text_out += f"补偿后时长: {final_length_sec:.3f} 秒\n"
        text_out += f"帧速率 (FPS): {fps}\n"
        text_out += f"输出总帧数: {total_frames} 帧"
        
        # 将信息装入 "ui" 中回传给前端，同时正常输出 result
        return {"ui": {"text": [text_out]}, "result": (final_audio, final_length_sec, total_frames)}