import torch

# ==========================================
# 1. 保留你原来的 5x5 开关节点 (防止报错)
# ==========================================
class TrucyRemoteToggle5x5:
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
                "Toggle_A": ("BOOLEAN", {"default": True}),
                "Toggle_B": ("BOOLEAN", {"default": True}),
                "Toggle_C": ("BOOLEAN", {"default": True}),
                "Toggle_D": ("BOOLEAN", {"default": True}),
                "Toggle_E": ("BOOLEAN", {"default": True}),
            }
        }
    RETURN_TYPES = ()
    FUNCTION = "dummy_pass"
    CATEGORY = "TrucyNodes/Logic"
    OUTPUT_NODE = True
    
    def dummy_pass(self, **kwargs):
        # 纯前端逻辑，后端直接透传
        return ()

# ==========================================
# 2. 这是为你全新打造的：4通道主控矩阵路由
# ==========================================
class TrucyMasterIntRouter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # 【修改点】：max 从 4 改成了 5
                "master_int": ("INT", {"default": 1, "min": 1, "max": 5, "step": 1}),
                "off_behavior": (["Bypass", "Mute"],),
                "Mode_1_Node_IDs": ("STRING", {"default": "", "multiline": False}),
                "Mode_2_Node_IDs": ("STRING", {"default": "", "multiline": False}),
                "Mode_3_Node_IDs": ("STRING", {"default": "", "multiline": False}),
                "Mode_4_Node_IDs": ("STRING", {"default": "", "multiline": False}),
                # 【修改点】：增加了第五个输入框
                "Mode_5_Node_IDs": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("workflow_int",)
    FUNCTION = "route_int"
    CATEGORY = "TrucyNodes"

    # 【修改点】：函数接收参数增加 Mode_5_Node_IDs
    def route_int(self, master_int, off_behavior, Mode_1_Node_IDs, Mode_2_Node_IDs, Mode_3_Node_IDs, Mode_4_Node_IDs, Mode_5_Node_IDs):
        # Python 后端只需要透传这个数字给下游即可，实际变灰控制由 JS 完成
        return (master_int,)