import torch
import nodes
from server import PromptServer
import impact.utils as impact_utils

# ========================================================
# 魔法工具：万能类型代理 (AnyType)
# ========================================================
class AlwaysEqualProxy(str):
    def __eq__(self, _): return True
    def __ne__(self, _): return False

any_type = AlwaysEqualProxy("*")

# ========================================================
# 辅助函数：生成安全的兜底空对象，防止强类型节点无输入时崩溃
# ========================================================
def generate_safe_placeholder(output_type):
    if output_type == "IMAGE":
        return torch.zeros((1, 512, 512, 3), dtype=torch.float32)
    elif output_type == "LATENT":
        import comfy.model_management
        device = comfy.model_management.get_torch_device()
        return {"samples": torch.zeros((1, 4, 64, 64), dtype=torch.float32, device=device)}
    elif output_type == "AUDIO":
        return {"waveform": torch.zeros((1, 2, 48000)), "sample_rate": 48000}
    elif output_type == "STRING":
        return ""
    elif output_type == "INT":
        return 0
    elif output_type == "FLOAT":
        return 0.0
    return None

# ========================================================
# 辅助函数：解析工作流网络拓扑结构
# ========================================================
def workflow_to_map(workflow):
    nodes_map = {}
    links_map = {}
    for link in workflow.get('links', []):
        links_map[link[0]] = link[1:]
    for node in workflow.get('nodes', []):
        nodes_map[str(node['id'])] = node
    return nodes_map, links_map


# ======================================================================
# 1. 🚀 Trucy AnySwitch (5通道/10通道)
# ======================================================================
class TrucyAnySwitch5:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"select_input": ("INT", {"default": 1, "min": 1, "max": 5, "step": 1})},
            "optional": {f"input_{i}": (any_type,) for i in range(1, 6)}
        }
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    FUNCTION = "switch"
    CATEGORY = "TrucyNodes/Logic"
    def switch(self, select_input, **kwargs):
        return (kwargs.get(f"input_{select_input}", None),)

class TrucyAnySwitch10:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"select_input": ("INT", {"default": 1, "min": 1, "max": 10, "step": 1})},
            "optional": {f"input_{i}": (any_type,) for i in range(1, 11)}
        }
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    FUNCTION = "switch"
    CATEGORY = "TrucyNodes/Logic"
    def switch(self, select_input, **kwargs):
        return (kwargs.get(f"input_{select_input}", None),)


# ======================================================================
# 2. 🚀 Trucy Control Bridge (双向独立控制桥接器)
# ======================================================================
class TrucyControlBridge:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "output_type": (["AUTO/ANY", "IMAGE", "LATENT", "AUDIO", "STRING", "INT", "FLOAT"], {"default": "IMAGE"}),
                "mode": ("BOOLEAN", {"default": True, "label_on": "Active", "label_off": "Stop/Mute/Bypass"}),
                "behavior": (["Stop", "Mute", "Bypass"], ),
            },
            "optional": {
                "value": (any_type,),
            },
            "hidden": {"unique_id": "UNIQUE_ID", "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}
        }

    FUNCTION = "doit"
    CATEGORY = "TrucyNodes/Logic"
    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("output",)
    OUTPUT_NODE = True

    def doit(self, output_type, mode, behavior="Stop", value=None, unique_id=None, prompt=None, extra_pnginfo=None):
        try:
            from comfy_execution.graph import ExecutionBlocker
        except ImportError:
            ExecutionBlocker = None

        # 如果没有连入真实数据，生成一个对应类型的安全空对象
        data_to_pass = value if value is not None else generate_safe_placeholder(output_type)

        # 模式一：Stop (物理阻断，没有复活机制，因为它是直接把变量变成毒药)
        if behavior == "Stop":
            if mode:
                return (data_to_pass,)
            else:
                return (ExecutionBlocker(None) if ExecutionBlocker else None,)
        
        # 模式二：Mute / Bypass (网页拓扑级控制，具备复活能力)
        if extra_pnginfo is None:
            return (data_to_pass,)
        
        try:
            workflow = extra_pnginfo['workflow']
            nodes_map, links_map = workflow_to_map(workflow)
            
            target_nodes = []
            
            # 精准寻找连接在当前桥接器输出口的所有下游节点
            if unique_id in nodes_map:
                my_node = nodes_map[unique_id]
                for output in my_node.get("outputs", []):
                    for link_id in output.get("links", []):
                        if link_id in links_map:
                            next_node_id = str(links_map[link_id][2])
                            impact_utils.collect_non_reroute_nodes(nodes_map, links_map, target_nodes, next_node_id)
            
            target_nodes = list(set(target_nodes)) # 去重
            
            if len(target_nodes) > 0:
                nodes_to_change = []
                action_to_take = None
                
                # 情况 A: 开关关闭 -> 下去杀人 (Mute/Bypass)
                if not mode:
                    for tid in target_nodes:
                        current_mode = nodes_map[tid].get('mode', 0)
                        target_mode = 2 if behavior == "Mute" else 4
                        # 只有当它还醒着，或者状态不对时，我们才发信号
                        if current_mode != target_mode:
                            nodes_to_change.append(tid)
                            
                    if nodes_to_change:
                        action_to_take = "mutes" if behavior == "Mute" else "bypasses"

                # 情况 B: 开关打开 -> 下去救人 (Active 唤醒)
                else:
                    for tid in target_nodes:
                        current_mode = nodes_map[tid].get('mode', 0)
                        # 如果它处于沉睡状态 (2=Mute, 4=Bypass, 3=Never, 等)，我们强行将其唤醒 (0=Active)
                        if current_mode != 0:
                            nodes_to_change.append(tid)
                            
                    if nodes_to_change:
                        action_to_take = "actives"
                
                # 如果确实有需要改变状态的节点，立刻发送广播并打断当前线程
                if action_to_take and nodes_to_change:
                    print(f"[TrucyNodes] Control Bridge '{action_to_take}' downstream nodes: {nodes_to_change}")
                    PromptServer.instance.send_sync("impact-bridge-continue", {"node_id": unique_id, action_to_take: nodes_to_change})
                    nodes.interrupt_processing()
                    return (data_to_pass,)
                
        except Exception as e:
            print(f"[TrucyNodes] Control Bridge routing error: {e}")
            
        return (data_to_pass, )

NODE_CLASS_MAPPINGS = {
    "TrucyAnySwitch5": TrucyAnySwitch5,
    "TrucyAnySwitch10": TrucyAnySwitch10,
    "TrucyControlBridge": TrucyControlBridge
}