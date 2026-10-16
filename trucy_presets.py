"""TrucyLLM · API 预设地址簿（常用远程 LLM 地址一键存取）。

存于插件目录 api_presets.json（本地明文含 API Key，切勿外发目录）。
三条路径：下拉选中即套用 / 前端按钮保存 / 「保存为预设」文本框跑一次即存。
底线：预设只帮填远程字段，绝不改大脑类型；本地 GGUF 模式整条忽略。
RLock：保存/删除时会持锁调用读取（同线程重入），必须可重入否则自死锁。
"""
import json
import os
import threading

# RLock：保存/删除预设时会持有锁再调用读取预设（同线程重入），必须可重入，否则自死锁
_锁 = threading.RLock()


def _预设文件():
    here = os.path.dirname(os.path.abspath(__file__))  # .../ComfyUI-TrucyNodes
    return os.path.join(here, "api_presets.json")


def 读取预设():
    """返回 [{name, api_base, api_key, model, timeout}, ...]；无文件/损坏返回 []。"""
    with _锁:
        try:
            with open(_预设文件(), "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []
    items = data.get("presets") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    return [p for p in items if isinstance(p, dict) and str(p.get("name") or "").strip()]


def 保存预设(name, api_base, api_key="", model="", timeout=300):
    """新增或同名覆盖。返回保存后的记录；名称/地址为空抛 ValueError。"""
    name = str(name or "").strip()
    if not name:
        raise ValueError("预设名称不能为空。")
    api_base = str(api_base or "").strip()
    if not api_base:
        raise ValueError("api_base 地址不能为空，没什么可保存的。")
    try:
        timeout = int(timeout)
    except Exception:
        timeout = 300
    record = {
        "name": name,
        "api_base": api_base,
        "api_key": str(api_key or "").strip(),
        "model": str(model or "").strip(),
        "timeout": max(10, timeout),
    }
    with _锁:
        items = [p for p in 读取预设() if str(p.get("name") or "") != name]
        items.append(record)
        items.sort(key=lambda p: str(p.get("name") or "").casefold())
        with open(_预设文件(), "w", encoding="utf-8") as f:
            json.dump({"presets": items}, f, ensure_ascii=False, indent=2)
    return record


def 删除预设(name):
    """按名称删除。返回是否删掉过。"""
    name = str(name or "").strip()
    with _锁:
        items = 读取预设()
        剩余 = [p for p in items if str(p.get("name") or "") != name]
        if len(剩余) == len(items):
            return False
        with open(_预设文件(), "w", encoding="utf-8") as f:
            json.dump({"presets": 剩余}, f, ensure_ascii=False, indent=2)
    return True


def 取预设(name):
    """按名称取单条；不存在返回 None。"""
    name = str(name or "").strip()
    for p in 读取预设():
        if str(p.get("name") or "") == name:
            return p
    return None


def 预设选项():
    """给节点下拉用：[（不使用预设）, 各预设名...]。"""
    return ["（不使用预设）"] + [str(p.get("name") or "") for p in 读取预设()]
