import torch
from nodes import NODE_CLASS_MAPPINGS as ALL_NODE_CLASS_MAPPINGS

try:
    from comfy_execution.graph_utils import GraphBuilder, is_link
    from comfy_execution.graph import ExecutionBlocker
except Exception:
    GraphBuilder = None
    ExecutionBlocker = None

class AlwaysEqualProxy(str):
    def __eq__(self, _): return True
    def __ne__(self, _): return False

any_type = AlwaysEqualProxy("*")
MAX_FLOW_NUM = 10 

# ========================================================
# 万能解包工具
# ========================================================
def safe_int(val):
    if isinstance(val, list):
        val = val[0] if len(val) > 0 else 0
    if isinstance(val, torch.Tensor):
        try: return int(val.item())
        except: return 0
    try: return int(val)
    except: return 0

# ========================================================
# 核心解析器
# ========================================================
def parse_trucy_sequence(loop_range, index_mode, step):
    if isinstance(loop_range, list): loop_range = loop_range[0]
    if isinstance(index_mode, list): index_mode = index_mode[0]
    step = safe_int(step)
    if step == 0: step = 1
    
    s = str(loop_range).replace('，', ',')
    seq = []
    for part in s.split(','):
        part = part.strip()
        if not part: continue
        if '-' in part:
            try:
                start_str, end_str = part.split('-')
                start_val, end_val = int(start_str), int(end_str)
                dir_step = step if start_val <= end_val else -step
                if dir_step == 0: dir_step = 1
                seq.extend(list(range(start_val, end_val + (1 if start_val <= end_val else -1), dir_step)))
            except: pass
        else:
            try: seq.append(int(part))
            except: pass
    
    if len(seq) == 1 and str(loop_range).strip().isdigit() and "-" not in str(loop_range):
        val = seq[0]
        seq = list(range(1, val + 1, step))
        
    if not seq:
        seq = [0]
        
    if index_mode == "0-based":
        seq = [x - 1 for x in seq]
        
    return seq

# ========================================================
# 用户节点：一体化 For 循环结构
# ========================================================
class TrucyForLoopStart:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "loop_range": ("STRING", {"default": "2-3, 8"}),
                "index_mode": (["0-based", "1-based"], {"default": "0-based"}),
                "step": ("INT", {"default": 1, "min": 1, "max": 1000}),
            },
            "optional": {},
            # 内部隐藏计次器，默认从 0 开始
            "hidden": {"iteration": ("INT", {"default": 0})}
        }
        for i in range(1, MAX_FLOW_NUM):
            inputs["optional"]["initial_value%d" % i] = (any_type,)
        return inputs

    RETURN_TYPES = tuple(["FLOW_CONTROL", "INT"] + [any_type] * (MAX_FLOW_NUM - 1))
    RETURN_NAMES = tuple(["flow", "index"] + ["value%d" % i for i in range(1, MAX_FLOW_NUM)])
    FUNCTION = "start_loop"
    CATEGORY = "TrucyNodes/Logic"

    def start_loop(self, loop_range, index_mode, step, iteration=0, **kwargs):
        seq = parse_trucy_sequence(loop_range, index_mode, step)
        iteration = safe_int(iteration)
        condition = iteration < len(seq)
        
        # 如果循环结束，发出 ExecutionBlocker 彻底阻断下游执行
        if not condition:
            values = [ExecutionBlocker(None) for _ in range(MAX_FLOW_NUM - 1)]
            return tuple(["stub", ExecutionBlocker(None)] + values)
            
        # 提取真正的数组索引并传给下游
        index_val = seq[iteration]
        values = [kwargs.get("initial_value%d" % i, None) for i in range(1, MAX_FLOW_NUM)]
        return tuple(["stub", index_val] + values)


class TrucyForLoopEnd:
    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "flow": ("FLOW_CONTROL", {"rawLink": True}),
            },
            "optional": {},
            "hidden": {"dynprompt": "DYNPROMPT", "unique_id": "UNIQUE_ID"}
        }
        for i in range(1, MAX_FLOW_NUM):
            inputs["optional"]["initial_value%d" % i] = (any_type,)
        return inputs

    RETURN_TYPES = tuple([any_type] * (MAX_FLOW_NUM - 1))
    RETURN_NAMES = tuple(["value%d" % i for i in range(1, MAX_FLOW_NUM)])
    FUNCTION = "end_loop"
    CATEGORY = "TrucyNodes/Logic"

    def explore_dependencies(self, node_id, dynprompt, upstream, parent_ids):
        node_info = dynprompt.get_node(node_id)
        if "inputs" not in node_info: return
        for k, v in node_info["inputs"].items():
            if is_link(v):
                parent_id = v[0]
                display_id = dynprompt.get_display_node_id(parent_id)
                display_node = dynprompt.get_node(display_id)
                class_type = display_node["class_type"]
                # ！！！极其关键的修复：类名判定必须跟随修改！！！
                if class_type not in ['TrucyForLoopEnd']:
                    parent_ids.append(display_id)
                if parent_id not in upstream:
                    upstream[parent_id] = []
                    self.explore_dependencies(parent_id, dynprompt, upstream, parent_ids)
                upstream[parent_id].append(node_id)

    def explore_output_nodes(self, dynprompt, upstream, output_nodes, parent_ids):
        for parent_id in upstream:
            display_id = dynprompt.get_display_node_id(parent_id)
            for output_id in output_nodes:
                id = output_nodes[output_id][0]
                if id in parent_ids and display_id == id and output_id not in upstream[parent_id]:
                    if '.' in parent_id:
                        arr = parent_id.split('.')
                        arr[len(arr)-1] = output_id
                        upstream[parent_id].append('.'.join(arr))
                    else:
                        upstream[parent_id].append(output_id)

    def collect_contained(self, node_id, upstream, contained):
        if node_id not in upstream: return
        for child_id in upstream[node_id]:
            if child_id not in contained:
                contained[child_id] = True
                self.collect_contained(child_id, upstream, contained)

    def end_loop(self, flow, dynprompt=None, unique_id=None, **kwargs):
        # 1. 直接获取与之配对的 Start 节点的信息
        open_node = flow[0]
        start_node_info = dynprompt.get_node(open_node)
        
        inputs = start_node_info.get("inputs", {})
        loop_range = inputs.get("loop_range", "1-10")
        index_mode = inputs.get("index_mode", "0-based")
        step = inputs.get("step", 1)
        iteration = safe_int(inputs.get("iteration", 0))
        
        # 2. 判断是否满足下一次循环的条件
        seq = parse_trucy_sequence(loop_range, index_mode, step)
        next_iteration = iteration + 1
        condition = next_iteration < len(seq)
        
        # 如果不再满足条件，直接抛出结果，循环结束！
        if not condition:
            return tuple([kwargs.get("initial_value%d" % i, None) for i in range(1, MAX_FLOW_NUM)])

        # 3. 如果需要继续循环，则克隆出被包裹在循环体内的所有用户节点
        upstream = {}
        parent_ids = []
        self.explore_dependencies(unique_id, dynprompt, upstream, parent_ids)
        parent_ids = list(set(parent_ids))
        
        prompts = dynprompt.get_original_prompt()
        output_nodes = {}
        
        for id in prompts:
            node = prompts[id]
            if "inputs" not in node: continue
            class_type = node["class_type"]
            class_def = ALL_NODE_CLASS_MAPPINGS.get(class_type)
            if class_def and hasattr(class_def, 'OUTPUT_NODE') and class_def.OUTPUT_NODE == True:
                for k, v in node['inputs'].items():
                    if is_link(v): output_nodes[id] = v

        graph = GraphBuilder()
        self.explore_output_nodes(dynprompt, upstream, output_nodes, parent_ids)
        contained = {}
        self.collect_contained(open_node, upstream, contained)
        contained[unique_id] = True
        contained[open_node] = True

        for node_id in contained:
            original_node = dynprompt.get_node(node_id)
            node = graph.node(original_node["class_type"], "Recurse" if node_id == unique_id else node_id)
            node.set_override_display_id(node_id)
            
        for node_id in contained:
            original_node = dynprompt.get_node(node_id)
            node = graph.lookup_node("Recurse" if node_id == unique_id else node_id)
            for k, v in original_node["inputs"].items():
                if is_link(v) and v[0] in contained:
                    parent = graph.lookup_node(v[0])
                    node.set_input(k, parent.out(v[1]))
                else:
                    node.set_input(k, v)

        # ====================================================
        # 最核心修复：亲自给新克隆出来的 Start 节点硬编码打上递增后的 iteration
        # ====================================================
        new_start = graph.lookup_node(open_node)
        new_start.set_input("iteration", next_iteration)
        for i in range(1, MAX_FLOW_NUM):
            key = "initial_value%d" % i
            new_start.set_input(key, kwargs.get(key, None))
            
        my_clone = graph.lookup_node("Recurse")
        result = [my_clone.out(i) for i in range(MAX_FLOW_NUM - 1)]
            
        return {"result": tuple(result), "expand": graph.finalize()}


# ========================================================
# 兼容空壳层 (防止报找不到模块导致全红)
# ========================================================
class TrucyWhileLoopStart:
    @classmethod
    def INPUT_TYPES(cls): return {"required": {}}
    RETURN_TYPES = ()
    FUNCTION = "func"
    CATEGORY = "TrucyNodes/Hidden"
    def func(self): return ()

class TrucyWhileLoopEnd:
    @classmethod
    def INPUT_TYPES(cls): return {"required": {}}
    RETURN_TYPES = ()
    FUNCTION = "func"
    CATEGORY = "TrucyNodes/Hidden"
    def func(self): return ()

class TrucyLoopController:
    @classmethod
    def INPUT_TYPES(cls): return {"required": {}}
    RETURN_TYPES = ()
    FUNCTION = "func"
    CATEGORY = "TrucyNodes/Hidden"
    def func(self): return ()

class TrucyIndexMapper:
    @classmethod
    def INPUT_TYPES(cls): return {"required": {}}
    RETURN_TYPES = ()
    FUNCTION = "func"
    CATEGORY = "TrucyNodes/Hidden"
    def func(self): return ()

# ========================================================
# 节点注册导出
# ========================================================
NODE_CLASS_MAPPINGS = {
    "TrucyForLoopStart": TrucyForLoopStart,
    "TrucyForLoopEnd": TrucyForLoopEnd,
    "TrucyWhileLoopStart": TrucyWhileLoopStart,
    "TrucyWhileLoopEnd": TrucyWhileLoopEnd,
    "TrucyLoopController": TrucyLoopController,
    "TrucyIndexMapper": TrucyIndexMapper,
}