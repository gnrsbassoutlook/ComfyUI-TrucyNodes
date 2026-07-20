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

class TrucyAnySwitch5:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"select_input": ("INT", {"default": 1, "min": 1, "max": 5})}, "optional": {f"input_{i}": (any_type,) for i in range(1, 6)}}
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
                        
                        # 只有在关闭 (杀节点) 的时候，才允许打断当前进程。
                        # 因为关闭操作必须立即生效，否则下游可能带着错误数据跑出垃圾图。
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
                        # 发送唤醒信号给网页前端
                        PromptServer.instance.send_sync("impact-bridge-continue", {"node_id": unique_id, action_to_take: nodes_to_change})
                        
                        # 【核心修复】：坚决不打断！不触发重跑！
                        # 允许数据直接流过去。只要数据到了，即使前端网页还没反应过来，底层的 Python 代码也会乖乖计算。
                        # 这样彻底消灭了多重循环环境下的死锁与卡排队问题！
                        pass 
                
        except Exception as e: 
            print(f"[TrucyNodes] Bridge Error: {str(e)}")
            
        return (data_to_pass, )

NODE_CLASS_MAPPINGS = {
    "TrucyAnySwitch5": TrucyAnySwitch5, "TrucyAnySwitch10": TrucyAnySwitch10, "TrucyControlBridge": TrucyControlBridge
}