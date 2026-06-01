import math
import torch
import comfy.utils
import node_helpers
import comfy.model_management

class TrucyKleinEncode:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "clip": ("CLIP",),
                "prompt": ("STRING", {"multiline": True, "default": "img1 and img4 fighting on img5..."}),
                "width": ("INT", {"default": 1920, "min": 512, "max": 4096, "step": 8}),
                "height": ("INT", {"default": 1088, "min": 512, "max": 4096, "step": 8}),
                # 核心控制：非基准图是跟随全局 W/H 还是使用 RSA 缩放
                "non_base_alignment": (["Follow Node (W/H)", "Use RSA Scaling"], {"default": "Follow Node (W/H)"}),
                "rsa_value": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 16}),
                "base_target": (["None"] + [f"img{i}" for i in range(1, 11)], {"default": "img5"}),
            },
            "optional": {
                "vae": ("VAE",),
                "base_mask": ("MASK",),  
            }
        }
        
        # 统一命名为 img，避免 UI 与逻辑错位
        for i in range(1, 11):
            inputs["optional"][f"img{i}"] = ("IMAGE",)
            inputs["optional"][f"img{i}_strength"] = ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.05})
            
        return inputs

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT")
    RETURN_NAMES = ("positive", "negative", "latent")
    FUNCTION = "encode_klein_professional"
    CATEGORY = "TrucyNodes/Conditioning"

    def encode_klein_professional(self, clip, prompt, width, height, non_base_alignment, rsa_value, base_target, vae=None, base_mask=None, **kwargs):
        
        if vae is None:
            raise RuntimeError("TrucyKleinEncode requires a VAE.")

        images_vl = []
        ref_latents = []
        noise_mask = None
        base_output_latent = None

        llama_template = (
            "<|im_start|>system\n"
            "Describe the key features of the input image (color, shape, "
            "size, texture, objects, background), then explain how the "
            "user's text instruction should alter or modify the image. "
            "Generate a new image that meets the user's requirements while "
            "maintaining consistency with the original input where "
            "appropriate.<|im_end|>\n"
            "<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n"
        )

        image_prompt_accumulated = ""
        assets = []
        for i in range(1, 11):
            img = kwargs.get(f"img{i}", None)
            strength = kwargs.get(f"img{i}_strength", 1.0)
            if img is not None and strength > 0:
                assets.append((img, strength, i))

        for loop_idx, (image, strength, asset_idx) in enumerate(assets):
            samples = image.movedim(-1, 1)
            is_base = (base_target == f"img{asset_idx}")
            
            # --- 1. Vision Encoder (始终使用 384 面积保持语义识别) ---
            current_total = samples.shape[3] * samples.shape[2]
            vl_scale_by = math.sqrt((384 * 384) / current_total)
            vl_w, vl_h = round(samples.shape[3] * vl_scale_by), round(samples.shape[2] * vl_scale_by)
            s_vl = comfy.utils.common_upscale(samples, vl_w, vl_h, "area", "center")
            images_vl.append(s_vl.movedim(1, -1))

            # --- 2. VAE 潜空间处理 (决定画质和速度的核心逻辑) ---
            # 如果是基准图，或者是用户选了"Follow Node"模式，则执行全画幅黑底对齐
            if is_base or non_base_alignment == "Follow Node (W/H)":
                vae_input_canvas = torch.zeros((samples.shape[0], height, width, 3), dtype=samples.dtype, device=samples.device)
                resized_img = comfy.utils.common_upscale(samples, width, height, "lanczos", "center").movedim(1, -1)
                img_h, img_w = resized_img.shape[1], resized_img.shape[2]
                vae_input_canvas[:, :img_h, :img_w, :] = resized_img
                encoded = vae.encode(vae_input_canvas)
                
                pure_latent_tensor = encoded["samples"] if isinstance(encoded, dict) else encoded
                
                # 基准图特权：输出底图和遮罩
                if is_base:
                    base_output_latent = pure_latent_tensor.clone()
                    if base_mask is not None:
                        mask = base_mask.unsqueeze(0).unsqueeze(0) if base_mask.dim() == 2 else base_mask.unsqueeze(1)
                        noise_mask = comfy.utils.common_upscale(mask, width // 8, height // 8, "area", "center").squeeze(1)
            else:
                # 只有在 Use RSA Scaling 模式下，非基准图才会缩小
                scale_by = math.sqrt((rsa_value * rsa_value) / current_total)
                vae_w, vae_h = round(samples.shape[3] * scale_by / 8.0) * 8, round(samples.shape[2] * scale_by / 8.0) * 8
                s_vae = comfy.utils.common_upscale(samples, vae_w, vae_h, "area", "disabled")
                encoded = vae.encode(s_vae.movedim(1, -1)[:, :, :, :3])
                pure_latent_tensor = encoded["samples"] if isinstance(encoded, dict) else encoded
            
            # 应用强度滑块
            ref_latents.append(pure_latent_tensor * strength)
            # 统一命名标签
            image_prompt_accumulated += f"img{asset_idx}: <|vision_start|><|image_pad|><|vision_end|> "

        # --- 3. 正负面组装 ---
        full_text = image_prompt_accumulated + prompt
        try:
            tokens = clip.tokenize(full_text, images=images_vl, llama_template=llama_template)
            positive_cond = clip.encode_from_tokens_scheduled(tokens)
            negative_cond = clip.encode_from_tokens_scheduled(clip.tokenize(""))
        except:
            positive_cond = clip.encode_from_tokens(clip.tokenize(full_text), return_pooled=True)
            negative_cond = clip.encode_from_tokens(clip.tokenize(""), return_pooled=True)

        if len(ref_latents) > 0:
            positive_cond = node_helpers.conditioning_set_values(positive_cond, {"reference_latents": ref_latents}, append=True)
            negative_cond = node_helpers.conditioning_set_values(negative_cond, {"reference_latents": ref_latents}, append=True)

        # --- 4. Latent 输出兜底 ---
        if base_output_latent is None:
            base_output_latent = vae.encode(torch.zeros(1, height, width, 3, device=comfy.model_management.get_torch_device()))
            if isinstance(base_output_latent, dict):
                base_output_latent = base_output_latent["samples"]

        latent_out = {"samples": base_output_latent}
        if noise_mask is not None: 
            latent_out["noise_mask"] = noise_mask

        return (positive_cond, negative_cond, latent_out)

NODE_CLASS_MAPPINGS = {"TrucyKleinEncode": TrucyKleinEncode}
NODE_DISPLAY_NAME_MAPPINGS = {"TrucyKleinEncode": "Klein-Model Text Encode (Trucy)"}