import math
import torch
import torch.nn.functional as F
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
                "main_prompt_ratio": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "base_target": (["all"] + [f"img{i}" for i in range(1, 11)], {"default": "img5"}),
                "reference_sq_area": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 16}),
            },
            "optional": {
                "vae": ("VAE",),
                "base_mask": ("MASK",),  
            }
        }
        
        for i in range(1, 11):
            inputs["optional"][f"img{i}"] = ("IMAGE",)
            inputs["optional"][f"img{i}_strength"] = ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.05})
            
        return inputs

    RETURN_TYPES = ("CONDITIONING", "CONDITIONING", "LATENT")
    RETURN_NAMES = ("positive", "negative", "latent")
    FUNCTION = "encode_klein_ultimate"
    CATEGORY = "TrucyNodes/Conditioning"

    def encode_klein_ultimate(self, clip, prompt, width, height, main_prompt_ratio, base_target, reference_sq_area, vae=None, base_mask=None, **kwargs):
        
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

        base_influence = 8 * main_prompt_ratio * (main_prompt_ratio - 1) - 6 * main_prompt_ratio + 6

        for loop_idx, (image, strength, asset_idx) in enumerate(assets):
            samples = image.movedim(-1, 1)
            
            is_full_canvas = (base_target == "all" or base_target == f"img{asset_idx}")
            is_primary_output = (base_target == f"img{asset_idx}") or (base_target == "all" and loop_idx == 0)

            # --- 1. Vision Encoder ---
            current_total = samples.shape[3] * samples.shape[2]
            vl_scale_by = math.sqrt((384 * 384) / current_total)
            vl_width, vl_height = round(samples.shape[3] * vl_scale_by), round(samples.shape[2] * vl_scale_by)
            s_vl = comfy.utils.common_upscale(samples, vl_width, vl_height, "area", "center")
            images_vl.append(s_vl.movedim(1, -1))

            # --- 2. VAE 潜空间处理 ---
            if is_full_canvas:
                vae_input_canvas = torch.zeros((samples.shape[0], height, width, 3), dtype=samples.dtype, device=samples.device)
                resized_img = comfy.utils.common_upscale(samples, width, height, "lanczos", "center").movedim(1, -1)
                img_h, img_w = resized_img.shape[1], resized_img.shape[2]
                vae_input_canvas[:, :img_h, :img_w, :] = resized_img
                encoded = vae.encode(vae_input_canvas)
                
                pure_latent_tensor = encoded["samples"] if isinstance(encoded, dict) else encoded
                
                if is_primary_output:
                    base_output_latent = pure_latent_tensor.clone()
                    if base_mask is not None:
                        mask = base_mask.unsqueeze(0).unsqueeze(0) if base_mask.dim() == 2 else base_mask.unsqueeze(1)
                        noise_mask = comfy.utils.common_upscale(mask, width // 8, height // 8, "area", "center").squeeze(1)
            else:
                scale_by = math.sqrt((reference_sq_area * reference_sq_area) / current_total)
                vae_w, vae_h = round(samples.shape[3] * scale_by / 8.0) * 8, round(samples.shape[2] * scale_by / 8.0) * 8
                s_vae = comfy.utils.common_upscale(samples, vae_w, vae_h, "area", "disabled")
                encoded = vae.encode(s_vae.movedim(1, -1)[:, :, :, :3])
                pure_latent_tensor = encoded["samples"] if isinstance(encoded, dict) else encoded
            
            ref_latents.append(pure_latent_tensor * (base_influence * strength))
            image_prompt_accumulated += f"img{asset_idx}: <|vision_start|><|image_pad|><|vision_end|> "

        # --- 3. 正面与负面条件组装 ---
        full_text = image_prompt_accumulated + prompt
        try:
            tokens = clip.tokenize(full_text, images=images_vl, llama_template=llama_template)
            positive_cond = clip.encode_from_tokens_scheduled(tokens)
            
            # 【极致优化点】：生成完全空白的负面条件，不含任何图像数据！
            negative_cond = clip.encode_from_tokens_scheduled(clip.tokenize(""))
        except:
            positive_cond = clip.encode_from_tokens(clip.tokenize(full_text), return_pooled=True)
            negative_cond = clip.encode_from_tokens(clip.tokenize(""), return_pooled=True)

        # 【极致优化点】：只给正面条件注入参考图特征。负面条件保持“裸奔”！
        # 这一步直接将 KSampler 的处理负担砍掉一半，瞬间提速！
        if len(ref_latents) > 0:
            positive_cond = node_helpers.conditioning_set_values(positive_cond, {"reference_latents": ref_latents}, append=True)
            # 坚决不给 negative_cond 注入 reference_latents

        # --- 4. Latent 输出 ---
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