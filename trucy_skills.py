"""TrucyLLM · Skill 系统（移植自 comfyUI-llama-TE，合并入 ComfyUI-TrucyNodes）。

扫描根目录 = 本插件 skills/ + comfyUI-llama-TE/skills/（存在则自动兼容）；
SKILL.md 正文整体注入系统提示词，references 按需读取（带目录穿越防护）。
"""
import os
import re

自动选择 = "自动选择"
内联文件最大字节数 = 4 * 1024 * 1024


def _读取文本(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read()


def _插件根目录():
    # 本文件位于 <plugin>/trucy_skills.py
    return os.path.dirname(os.path.realpath(__file__))


def _skill根目录列表():
    """返回去重后的 skills 扫描根目录（本插件优先，其次 comfyUI-llama-TE）。"""
    roots = [os.path.join(_插件根目录(), "skills")]
    custom_nodes = os.path.dirname(_插件根目录())
    for name in ("comfyUI-llama-TE", "comfyui-llama-TE", "ComfyUI-llama-TE"):
        candidate = os.path.join(custom_nodes, name, "skills")
        if os.path.isdir(candidate):
            real = os.path.realpath(candidate)
            if real not in [os.path.realpath(r) for r in roots]:
                roots.append(candidate)
    return [r for r in roots if os.path.isdir(r)]


def _解析前置信息(text):
    """解析 SKILL.md 顶部的 YAML front-matter（name/description）。"""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    values = {}
    for line in text[3:end].splitlines():
        m = re.match(r"^([\w-]+):\s*(.*)$", line)
        if m:
            key, value = m.groups()
            values[key] = value.strip().strip("\"'")
    return values


def _读取meta值(skill_dir, key):
    path = os.path.join(skill_dir, "meta.yaml")
    if not os.path.isfile(path):
        return ""
    for line in _读取文本(path).splitlines():
        m = re.match(rf"^{re.escape(key)}:\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip().strip("\"'")
    return ""


def _列出references(skill_dir):
    ref_dir = os.path.join(skill_dir, "references")
    if not os.path.isdir(ref_dir):
        return []
    files = []
    for root, _, names in os.walk(ref_dir):
        for name in names:
            if os.path.splitext(name)[1].lower() not in (".md", ".txt", ".yaml", ".yml", ".json"):
                continue
            rel = os.path.relpath(os.path.join(root, name), skill_dir).replace("\\", "/")
            files.append(rel)
    return sorted(files)


def _支持的skill文件(name):
    return os.path.splitext(name)[1].lower() in (".md", ".txt")


def _创建skill记录(file_path, root, skill_id=None, skill_dir=None, legacy_label=False):
    file_path = os.path.realpath(file_path)
    skill_dir = os.path.realpath(skill_dir or os.path.dirname(file_path))
    relative_file = os.path.relpath(file_path, root).replace("\\", "/")
    relative_dir = os.path.relpath(skill_dir, root).replace("\\", "/")
    if relative_dir == ".":
        relative_dir = ""

    content = _读取文本(file_path)
    metadata = _解析前置信息(content)
    meta_name = _读取meta值(skill_dir, "display-name-zh")
    meta_desc = _读取meta值(skill_dir, "summary-cn")
    fallback_name = os.path.splitext(os.path.basename(file_path))[0]
    name = meta_name or metadata.get("name") or fallback_name
    description = meta_desc or metadata.get("description") or ""
    entry_id = skill_id or relative_file
    if legacy_label:
        label = f"{name} [{entry_id}]" if name != entry_id else entry_id
    else:
        label = f"{name} [{relative_file}]"
    return {
        "id": entry_id,
        "name": name,
        "label": label,
        "description": description,
        "skill_file": os.path.basename(file_path),
        "skill_path": relative_file,
        "skill_dir": relative_dir,
        "root": root,
        "references": _列出references(skill_dir),
    }


def 发现skills():
    """扫描所有根目录，返回 Skill 记录列表（本插件目录优先，按 label 排序）。"""
    skills = []
    seen_ids = set()
    for root in _skill根目录列表():
        for dir_root, dirnames, filenames in os.walk(root):
            # references 由父 Skill 按需加载，不单独列为 Skill
            dirnames[:] = sorted(d for d in dirnames if d != "references")
            filenames = sorted(f for f in filenames if _支持的skill文件(f))
            if not filenames:
                continue

            relative_dir = os.path.relpath(dir_root, root).replace("\\", "/")
            legacy_dir = relative_dir != "." and re.fullmatch(r"[A-Za-z0-9._-]+", relative_dir or "")
            default_name = "SKILL.md"
            chinese_name = "SKILL.cn.md"
            primary_name = chinese_name if chinese_name in filenames else (
                default_name if default_name in filenames else None
            )

            if legacy_dir and primary_name:
                record = _创建skill记录(
                    os.path.join(dir_root, primary_name),
                    root=root,
                    skill_id=relative_dir,
                    skill_dir=dir_root,
                    legacy_label=True,
                )
                # 多根目录下去重：本插件目录优先
                if record["id"] not in seen_ids:
                    seen_ids.add(record["id"])
                    skills.append(record)

            for filename in filenames:
                if filename in (default_name, chinese_name) and primary_name and legacy_dir:
                    continue
                file_path = os.path.join(dir_root, filename)
                relative_file = os.path.relpath(file_path, root).replace("\\", "/")
                record = _创建skill记录(file_path, root=root, skill_id=relative_file)
                if record["id"] not in seen_ids:
                    seen_ids.add(record["id"])
                    skills.append(record)

    return sorted(skills, key=lambda item: (item["label"].casefold(), item["id"].casefold()))


def 获取skill(skill_id):
    return next((s for s in 发现skills() if s["id"] == skill_id), None)


def 读取skill正文(skill):
    return _读取文本(os.path.join(skill["root"], skill["skill_path"]))


def 读取reference(skill, relative_path):
    """按需读取 Skill 的 references 文件（带目录穿越防护）。"""
    normalized = str(relative_path or "").replace("\\", "/").strip("/")
    if normalized not in skill.get("references", []):
        raise ValueError(f"Skill reference 不存在：{normalized}")
    skill_dir = os.path.realpath(os.path.join(skill["root"], skill["skill_dir"] or skill["id"]))
    path = os.path.realpath(os.path.join(skill_dir, normalized))
    if os.path.commonpath([skill_dir, path]) != skill_dir:
        raise ValueError("Skill reference 路径超出 Skill 目录。")
    return _读取文本(path)


def 构建skill系统提示词(base_system, skill, extra_blocks=None):
    """
    把 Skill 正文注入系统提示词（移植自 llama-TE 的 _构建图像skill系统提示词）。

    extra_blocks: 额外文本块列表（例如按需读取的 references 内容）。
    """
    references = "\n".join(f"- {p}" for p in skill.get("references", [])) or "- 无"
    parts = [
        str(base_system or "").strip(),
        f"当前 Skill：{skill['name']} ({skill['id']})\n"
        f"可用 references（单次推理不会自动加载，请按任务需要取用）：\n{references}\n\n"
        f"===== {skill['skill_file']} =====\n{读取skill正文(skill)}",
    ]
    if extra_blocks:
        parts.extend(str(b) for b in extra_blocks if str(b or "").strip())
    parts.append("这是一次单次推理。请直接根据当前 Skill 完成用户任务，不要输出思考过程，不要输出与任务无关的解释。")
    return "\n\n".join(p for p in parts if p)


def 规范化内联文件(file_name, content):
    """把临时加载的 .md/.txt 内容包装为 inline skill 记录。"""
    import hashlib

    name = os.path.basename(str(file_name or "").strip())
    text = str(content or "")
    if not text.strip():
        return None
    if not name:
        name = "loaded_skill.txt"
    if os.path.splitext(name)[1].lower() not in (".md", ".txt"):
        raise ValueError("加载 Skill/提示词只支持 .md 或 .txt 文件。")
    if len(text.encode("utf-8")) > 内联文件最大字节数:
        raise ValueError("加载 Skill/提示词文件不能超过 4 MB。")
    file_id = hashlib.sha256((name + "\0" + text).encode("utf-8")).hexdigest()[:16]
    return {
        "id": file_id,
        "name": name,
        "label": f"{name} [{file_id}]",
        "description": "临时加载的文件",
        "skill_file": name,
        "skill_path": "",
        "skill_dir": "",
        "root": "",
        "references": [],
        "inline_content": text,
    }
