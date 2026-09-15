import torch

# ==========================================
# 6x6 远程开关控制节点 (TrucyRemoteToggle6x6)
# ==========================================
class TrucyRemoteToggle6x6:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "off_behavior": (["Bypass", "Mute"], {"default": "Bypass"}),
                "A_Node_IDs": ("STRING", {"default": "", "multiline": False}),
                "B_Node_IDs": ("STRING", {"default": "", "multiline": False}),
                "C_Node_IDs": ("STRING", {"default": "", "multiline": False}),
                "D_Node_IDs": ("STRING", {"default": "", "multiline": False}),
                "E_Node_IDs": ("STRING", {"default": "", "multiline": False}),
                "F_Node_IDs": ("STRING", {"default": "", "multiline": False}),
                "Toggle_A": ("BOOLEAN", {"default": True}),
                "Toggle_B": ("BOOLEAN", {"default": True}),
                "Toggle_C": ("BOOLEAN", {"default": True}),
                "Toggle_D": ("BOOLEAN", {"default": True}),
                "Toggle_E": ("BOOLEAN", {"default": True}),
                "Toggle_F": ("BOOLEAN", {"default": True}),
            }
        }
    RETURN_TYPES = ()
    FUNCTION = "dummy_pass"
    CATEGORY = "TrucyNodes/Logic"
    OUTPUT_NODE = True
    
    def dummy_pass(self, **kwargs):
        return ()

# ==========================================
# 5通道主控矩阵路由
# ==========================================
class TrucyMasterIntRouter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "master_int": ("INT", {"default": 1, "min": 1, "max": 5, "step": 1}),
                "off_behavior": (["Bypass", "Mute"],),
                "Mode_1_Node_IDs": ("STRING", {"default": "", "multiline": False}),
                "Mode_2_Node_IDs": ("STRING", {"default": "", "multiline": False}),
                "Mode_3_Node_IDs": ("STRING", {"default": "", "multiline": False}),
                "Mode_4_Node_IDs": ("STRING", {"default": "", "multiline": False}),
                "Mode_5_Node_IDs": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("workflow_int",)
    FUNCTION = "route_int"
    CATEGORY = "TrucyNodes"

    def route_int(self, master_int, off_behavior, Mode_1_Node_IDs, Mode_2_Node_IDs, Mode_3_Node_IDs, Mode_4_Node_IDs, Mode_5_Node_IDs):
        return (master_int,)