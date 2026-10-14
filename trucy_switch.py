import math
import torch
import nodes
from server import PromptServer
import impact.utils as impact_utils

class AlwaysEqualProxy(str):
    def __eq__(self, _): return True
    def __ne__(self, _): return False

any_type = AlwaysEqualProxy("*")

def generate_safe_placeholder(output_type, string_val=""):
    if output_type in ["IMAGE", "VIDEO"]:
        return torch.zeros((1, 512, 512, 3), dtype=torch.float32)
    elif output_type == "LATENT":
        import comfy.model_management
        return {"samples": torch.zeros((1, 4, 64, 64), dtype=torch.float32, device=comfy.model_management.get_torch_device())}
    elif output_type == "AUDIO":
        return {"waveform": torch.zeros((1, 2, 48000)), "sample_rate": 48000}
    elif output_type == "STRING":
        return string_val
    elif output_type == "INT":
        return 0
    elif output_type == "FLOAT":
        return 0.0
    return None

def workflow_to_map(workflow):
    nodes_map, links_map = {}, {}
    for link in workflow.get('links', []): links_map[link[0]] = link[1:]
    for node in workflow.get('nodes', []): nodes_map[str(node['id'])] = node
    return nodes_map, links_map

# ==========================================
# 彻底正名为 6 路 Switch (TrucyAnySwitch6)
# ==========================================
class TrucyAnySwitch6:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"select_input": ("INT", {"default": 1, "min": 1, "max": 6})}, "optional": {f"input_{i}": (any_type,) for i in range(1, 7)}}
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = (any_type,), ("output",), "switch", "TrucyNodes/Logic"
    def switch(self, select_input, **kwargs): return (kwargs.get(f"input_{select_input}", None),)

class TrucyAnySwitch10:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"select_input": ("INT", {"default": 1, "min": 1, "max": 10})}, "optional": {f"input_{i}": (any_type,) for i in range(1, 11)}}
    RETURN_TYPES, RETURN_NAMES, FUNCTION, CATEGORY = (any_type,), ("output",), "switch", "TrucyNodes/Logic"
    def switch(self, select_input, **kwargs): return (kwargs.get(f"input_{select_input}", None),)

class TrucyControlBridge:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "output_type": (["AUTO/ANY", "IMAGE", "VIDEO", "LATENT", "AUDIO", "STRING", "INT", "FLOAT"], {"default": "STRING"}),
                "mode": ("BOOLEAN", {"default": True, "label_on": "Active", "label_off": "Stop/Mute/Bypass"}),
                "behavior": (["Stop", "Mute", "Bypass"], ),
                "string_value": ("STRING", {"default": "gpt-4o", "multiline": False}),
            },
            "optional": {
                "value": (any_type,),
            },
            "hidden": {"unique_id": "UNIQUE_ID", "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}
        }

    FUNCTION, CATEGORY, OUTPUT_NODE = "doit", "TrucyNodes/Logic", True
    RETURN_TYPES, RETURN_NAMES = (any_type,), ("output",)

    def doit(self, output_type, mode, behavior, string_value, value=None, unique_id=None, prompt=None, extra_pnginfo=None):
        try: from comfy_execution.graph import ExecutionBlocker
        except: ExecutionBlocker = None

        data_to_pass = value if value is not None else generate_safe_placeholder(output_type, string_value)

        # 模式 1：物理 Stop 阻断
        if behavior == "Stop": return (data_to_pass if mode else ExecutionBlocker(None) if ExecutionBlocker else None, )
        
        # 模式 2：拓扑控制 (Mute/Bypass)
        if extra_pnginfo is None: return (data_to_pass,)
        
        try:
            nodes_map, links_map = workflow_to_map(extra_pnginfo['workflow'])
            target_nodes = []
            if unique_id in nodes_map:
                for output in nodes_map[unique_id].get("outputs", []):
                    for link_id in output.get("links", []):
                        if link_id in links_map:
                            import impact.utils as impact_utils
                            impact_utils.collect_non_reroute_nodes(nodes_map, links_map, target_nodes, str(links_map[link_id][2]))
            
            target_nodes = list(set(target_nodes))
            if len(target_nodes) > 0:
                nodes_to_change, action_to_take = [], None
                
                # --- 关闭节点 (Mute/Bypass) ---
                if not mode:
                    for tid in target_nodes:
                        if nodes_map[tid].get('mode', 0) != (2 if behavior == "Mute" else 4):
                            nodes_to_change.append(tid)
                    if nodes_to_change: 
                        action_to_take = "mutes" if behavior == "Mute" else "bypasses"
                        print(f"[TrucyNodes] Bridging OFF: Silencing downstream nodes: {nodes_to_change}")
                        PromptServer.instance.send_sync("impact-bridge-continue", {"node_id": unique_id, action_to_take: nodes_to_change})
                        nodes.interrupt_processing()
                        return (data_to_pass,)

                # --- 唤醒节点 (Active) ---
                else:
                    for tid in target_nodes:
                        if nodes_map[tid].get('mode', 0) != 0: 
                            nodes_to_change.append(tid)
                    if nodes_to_change: 
                        action_to_take = "actives"
                        print(f"[TrucyNodes] Bridging ON: Reactivating downstream nodes: {nodes_to_change}")
                        PromptServer.instance.send_sync("impact-bridge-continue", {"node_id": unique_id, action_to_take: nodes_to_change})
                        pass 
                
        except Exception as e: 
            print(f"[TrucyNodes] Bridge Error: {str(e)}")
            
        return (data_to_pass, )

# ======================================================================
# 帧数与秒数双向互转器 (TrucyFrameSecondsConverter)
# ======================================================================
class TrucyFrameSecondsConverter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # 纯整数下拉菜单：只能点选固定帧率，无法随意手填文本
                "fps_select": (
                    [8, 12, 16, 24, 25, 30, 48, 50, 60],
                    {"default": 24}
                ),
                # 取整模式
                "round_mode": (
                    ["Round (四舍五入)", "Floor (全舍)", "Ceil (全入)"],
                    {"default": "Round (四舍五入)"}
                ),
            },
            "optional": {
                # 专属 INT 连线槽：支持直接拉 INT 线连入！接入时优先于下拉菜单
                "fps_opt": ("INT", {"forceInput": True}),
                "frames": ("INT", {"forceInput": True}),
                "seconds": ("FLOAT", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("INT", "FLOAT")
    RETURN_NAMES = ("frames", "seconds")
    FUNCTION = "convert"
    CATEGORY = "TrucyNodes/Logic"

    def convert(self, fps_select, round_mode="Round (四舍五入)", fps_opt=None, frames=None, seconds=None):
        # 兼容 ExecutionBlocker 空置
        if frames is not None and type(frames).__name__ == "ExecutionBlocker":
            frames = None
        if seconds is not None and type(seconds).__name__ == "ExecutionBlocker":
            seconds = None
        if fps_opt is not None and type(fps_opt).__name__ == "ExecutionBlocker":
            fps_opt = None

        # 严格检查：frames 与 seconds 必须且只能接入一个输入
        if frames is not None and seconds is not None:
            raise ValueError("❌ [TrucyNodes] 帧数 (frames) 与秒数 (seconds) 接口冲突！只允许接入其中一个输入。")
        if frames is None and seconds is None:
            raise ValueError("❌ [TrucyNodes] 未检测到输入！请接入【帧数 (frames)】或【秒数 (seconds)】其中之一。")

        # 确定最终帧率：若接入了外部 INT 连线则使用连线值，否则使用下拉框纯整型值
        final_fps = float(fps_opt) if fps_opt is not None else float(fps_select)
        if final_fps <= 0:
            final_fps = 24.0

        # 取整逻辑处理
        def _apply_rounding(val_float):
            if round_mode.startswith("Round"):
                return int(math.floor(val_float + 0.5)) if val_float >= 0 else int(math.ceil(val_float - 0.5))
            elif round_mode.startswith("Floor"):
                return int(math.floor(val_float))
            elif round_mode.startswith("Ceil"):
                return int(math.ceil(val_float))
            return int(val_float)

        # 情况 1：接入了帧数 -> 直出帧数，换算秒数
        if frames is not None:
            out_frames = _apply_rounding(float(frames))
            out_seconds = round(float(out_frames) / final_fps, 4)
            return (out_frames, out_seconds)

        # 情况 2：接入了秒数 -> 直出秒数，按所选模式换算帧数
        else:
            out_seconds = float(seconds)
            out_frames = _apply_rounding(out_seconds * final_fps)
            return (out_frames, out_seconds)

NODE_CLASS_MAPPINGS = {
    "TrucyAnySwitch6": TrucyAnySwitch6, 
    "TrucyAnySwitch10": TrucyAnySwitch10, 
    "TrucyControlBridge": TrucyControlBridge,
    "TrucyFrameSecondsConverter": TrucyFrameSecondsConverter,
}