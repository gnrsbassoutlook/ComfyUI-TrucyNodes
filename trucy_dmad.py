# -*- coding: utf-8 -*-
"""H3 四步加速采样器（DMAD / DMD 蒸馏 LoRA 专用推理格式）

背景
----
MiniMax-H3 社区（Spark-H3 项目）用 DMD（Distribution Matching Distillation）
蒸出了一棵「4 步学生」——`minimax_h3_dmad_full_dareties_v4_step600` 之类的
LoRA（safetensors 元数据里写着 ``converted_from:
dmad_minimax_h3_4step_full_critic``，纯 ``diffusion_model.*`` DiT 补丁，
约 208 对 lora_A/B）。

关键点：**它不是普通 turbo LoRA，不能直接配 res_multistep 用**。DMD 学生的
权重是按它自己的推理格式训的——每步先预测 x0，再按下一个 sigma 重新加噪
（renoise），和 Euler/Heun 之类的一阶递推数学上是两回事。配错采样器，4 步
出来的是糊的。

标准配方（Spark-H3 官方工作流 `spark_h3_dmad_4step_lora_*.json`）：
    UNETLoader(H3 int8)
      → LoraLoaderModelOnly(dmad LoRA, strength=1.0)
      → MiniMaxH3SigmaShift(video=12, audio=2)      ← 官方节点，F 盘已在册
      → BasicScheduler(scheduler="simple", steps=4, denoise=1.0)
      → MiniMaxH3DMADSampler                        ← 本节点替代 KSamplerSelect
      → BasicGuider → SamplerCustomAdvanced

本节点 = Spark-H3 包 `comfyui_dmad.py` 里 `MiniMaxH3DMADSampler` 的等价实现
（算法是公开的 DMD renoise 步骤）。之所以在我们自己的包里复刻一份，是因为
F 盘测试实例没装 Spark-H3 那个重包（带稀疏注意力内核/补丁），不想为一个小
采样器把测试床搞不稳。E 盘主环境已装 Spark-H3，用官方节点效果相同。

注意：官方参考链的底模是 ``minimax_h3_fl2va_pruned_int8_convrot``（首尾帧
模式），全参考链用的是 ``minimax_h3_ref2va_pruned_int8_convrot``——同一 DiT
家族的不同训练变体，dmad LoRA 跨变体是否等效需要实跑验证。
"""

from __future__ import annotations

try:
    import comfy.samplers
    import comfy.k_diffusion.sampling
    _依赖齐全 = True
except Exception:  # 非 ComfyUI 环境（单测/静态检查）下静默降级
    _依赖齐全 = False


def _dmad_renoise_sampler(model, x, sigmas, extra_args=None, callback=None,
                          disable=None, **kwargs):
    """DMD 学生的单步推理：预测 x0 → 按下一档 sigma 重新加噪。

    与 Spark-H3 的 dmad_renoise_sampler 逐行等价：
        denoised = model(x, sigma)
        x_next   = denoised                         （最后一步，sigma_next=0）
        x_next   = (1 - sigma_next) * denoised + sigma_next * noise
    噪声来自 ``default_noise_sampler(x, seed)``——和 ComfyUI 自带的所有
    ancestral 采样器同一套取噪机制，seed 经 extra_args 正常穿透
    （comfy/samplers.py: ``extra_args = {..., "seed": seed}``）。
    """
    extra_args = {} if extra_args is None else extra_args
    noise_sampler = comfy.k_diffusion.sampling.default_noise_sampler(
        x, seed=extra_args.get("seed"))
    s_in = x.new_ones((x.shape[0],))
    for index in range(len(sigmas) - 1):
        sigma = sigmas[index]
        sigma_next = sigmas[index + 1]
        denoised = model(x, sigma * s_in, **extra_args)
        if float(sigma_next) == 0.0:
            x = denoised
        else:
            noise = noise_sampler(sigma, sigma_next)
            x = (1.0 - sigma_next) * denoised + sigma_next * noise
        if callback is not None:
            callback({
                "i": index,
                "denoised": denoised,
                "x": x,
                "sigma": sigma,
                "sigma_hat": sigma,
            })
    return x


class TrucyDMADSampler:
    """输出 DMAD 4 步专用 SAMPLER，替换 KSamplerSelect(res_multistep)。

    无输入控件——配什么 sigma 档位由上游 BasicScheduler 决定，本节点只负责
    「每一步怎么走」。必须搭配：dmad LoRA + MiniMaxH3SigmaShift(12, 2) +
    BasicScheduler(simple, 4 步)。换到底模没蒸过的普通 H3 上会出来糊片，
    这是 DMD 学生的预期行为，不是 bug。
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    RETURN_TYPES = ("SAMPLER",)
    FUNCTION = "取采样器"
    CATEGORY = "sampling/custom_sampling/samplers"
    DESCRIPTION = (
        "DMAD/DMD 4 步蒸馏学生的专用推理步（预测 x0 后按下一档 sigma 重新加噪）。"
        "配方：dmad LoRA(strength=1.0) + MiniMaxH3SigmaShift(video=12, audio=2) "
        "+ BasicScheduler(simple, 4 步)。请勿与普通 turbo LoRA 混用。"
    )
    SEARCH_ALIASES = ["dmad", "dmd", "4step", "minimax h3", "sampler"]

    def 取采样器(self):
        if not _依赖齐全:
            raise RuntimeError(
                "TrucyDMADSampler 需要 ComfyUI 运行时环境（comfy.samplers / "
                "comfy.k_diffusion.sampling 不可用）。")
        return (comfy.samplers.KSAMPLER(_dmad_renoise_sampler),)


NODE_CLASS_MAPPINGS = {"TrucyDMADSampler": TrucyDMADSampler}
NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyDMADSampler": "🚀 Trucy DMAD Sampler (H3 4步)",
}
