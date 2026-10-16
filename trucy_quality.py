"""TrucyLLM · 输出质量模块（连续性优先设计，合并自 ComfyUI-TrucyLLM）。

原则（对应用户底线：连续输出不可中断）：检查全是纯 Python 毫秒级、不调 LLM、
不弹窗、不等待人工；发现问题只记日志，输出照常流向下游；确定性修复只动格式
（时间码零填充/首镜时间码/越界钳制），修了什么必记日志；LLM 纠正由节点层在
同一次执行内自动完成，失败保底第一稿，默认关闭。
"""
import re

# ---------------------------------------------------------------------------
# 公共工具
# ---------------------------------------------------------------------------
def 去引号内容(text):
    """去掉引号 span，返回剩余文本（用于"比例是否混进正文"这类检查时豁免画面文字）。"""
    result = str(text or "")
    result = re.sub(r'"(?:\\.|[^"\\])*"', " ", result)
    result = re.sub(r"“[^”]*”", " ", result)
    result = re.sub(r"‘[^’]*’", " ", result)
    return result


def 提取引号文字(brief, 上限=60):
    """从用户创意里提取引号内的文字（用户要求逐字保留的画面文字候选）。"""
    lits = []
    for groups in re.findall(
        r'"([^"\n]{1,%d})"|“([^”\n]{1,%d})”|‘([^’\n]{1,%d})’' % (上限, 上限, 上限),
        str(brief or ""),
    ):
        lit = next((g for g in groups if g), "")
        if lit.strip():
            lits.append(lit.strip())
    return lits


def 检查空话(text):
    """QWI 规范明令禁止的"空话质量词"。"""
    issues = []
    prose = 去引号内容(text)
    for word in ("8K", "4K", "masterpiece", "highly detailed", "award-winning", "best quality"):
        if re.search(r"\b%s\b" % re.escape(word), prose, flags=re.IGNORECASE):
            issues.append(f"正文含空话质量词「{word}」（官方规范禁用）")
    return issues


# ---------------------------------------------------------------------------
# H3：协议检查 + 确定性修复
# ---------------------------------------------------------------------------
def _解析shots(text):
    """返回 [(shot_no, time_seconds|None, span)], time 为该镜后的 At MM:SS.mmm 切点。"""
    shots = []
    for m in re.finditer(r"\[Shot\s+(\d+)\]", str(text or "")):
        no = int(m.group(1))
        tail = text[m.end():]
        # 窗口截断到下一个 [Shot 标记，避免吞掉下一镜的时间码
        next_shot = tail.find("[Shot")
        if next_shot >= 0:
            tail = tail[:next_shot]
        tm = re.search(r"At\s+(\d+):(\d+(?:\.\d+)?)", tail)
        seconds = None
        if tm:
            seconds = int(tm.group(1)) * 60 + float(tm.group(2))
        shots.append((no, seconds, m.span()))
    return shots


def 检查H3(text, duration=None, shot_count=0, task_type="", 图片数=0, 视频数=0, 音频数=0, 强制单镜=False):
    """H3 输出协议检查。返回问题列表（空 = 通过）。duration 单位秒，shot_count 0=Auto。

    task_type=Ref2VA（或 Auto 但输出呈六段全参考形态）走 检查Ref2VA；
    其余（T2VA/I2VA/FL2VA/L2VA）走基础模式检查。
    强制单镜=True（上游约束总闸开启时）：两种模式都追加单镜判定——
    全文只允许 [Shot 1]（按去重后的镜头编号计，retention 里重复引用 [Shot 1] 合法），
    禁止任何 At 切点时间码与 <scenetrans> 跨镜标记（不切镜 = 提示词内无切镜指令）。
    """
    issues = []
    text = str(text or "")
    if not text.strip():
        return ["输出为空"]

    # 强制单镜（上游约束总闸开启）：不切镜 = 提示词内无任何切镜指令
    if 强制单镜:
        镜头号 = sorted({s[0] for s in _解析shots(text)})
        if len(镜头号) > 1 or (镜头号 and 镜头号 != [1]):
            issues.append(f"强制单镜模式下出现多个镜头编号 {镜头号}（只允许 [Shot 1]）")
        if re.search(r"At\s+\d+:\d+(?:\.\d+)?", text):
            issues.append("强制单镜模式下出现 At 切点时间码（不切镜不应有任何切点）")
        if "<scenetrans>" in text:
            issues.append("强制单镜模式下出现跨镜标记 <scenetrans>")

    任务 = str(task_type or "").strip()
    呈全参考形态 = any(k in text for k in (
        "subject_definitions:", "retention_analysis:", "detailed_description:"))
    if 任务 == "Ref2VA" or (任务 in ("", "Auto") and 呈全参考形态):
        return issues + 检查Ref2VA(text, duration=duration, shot_count=shot_count,
                         图片数=图片数, 视频数=视频数, 音频数=音频数)

    shots = _解析shots(text)
    if not shots:
        issues.append("未找到 [Shot N] 分镜标记")
        return issues

    nums = [s[0] for s in shots]
    if nums != list(range(1, len(nums) + 1)):
        issues.append(f"分镜编号不连续或不从 1 开始: {nums[:12]}")

    if shot_count and isinstance(shot_count, int) and len(nums) != shot_count:
        issues.append(f"分镜数量为 {len(nums)}，与指定镜头数 {shot_count} 不符")

    # 首镜不应带时间码；后续镜必须带且严格递增
    prev = None
    for idx, (no, seconds, _span) in enumerate(shots):
        if idx == 0:
            if seconds is not None:
                issues.append(f"[Shot 1] 带了切点时间码（官方规范首镜不加时间码）")
            continue
        if seconds is None:
            issues.append(f"[Shot {no}] 缺少切点时间码（At MM:SS.mmm）")
            continue
        if prev is not None and seconds <= prev:
            issues.append(f"[Shot {no}] 切点 {seconds:.3f}s 未严格递增（上一镜 {prev:.3f}s）")
        if duration and seconds > float(duration) + 0.001:
            issues.append(f"[Shot {no}] 切点 {seconds:.3f}s 超出目标时长 {float(duration):.2f}s")
        prev = seconds

    # 时间线覆盖：最后一个切点是否靠近时长末尾
    timed = [s[1] for s in shots if s[1] is not None]
    if duration and timed:
        if timed[-1] < float(duration) * 0.5:
            issues.append(
                f"最后一个切点 {timed[-1]:.3f}s 远早于目标时长 {float(duration):.2f}s，时间线可能未覆盖全片")

    # 三大字段
    for field in ("integrated_multimodal_description", "overall_soundscape", "non_diegetic_music"):
        if field not in text:
            issues.append(f"缺少核心字段 {field}")

    return issues


# Ref2VA（全参考模式）六段结构，字段名与顺序依 skill references/ref-en.txt
_Ref2VA六段 = ("subject_definitions", "summary", "retention_analysis",
              "detailed_description", "overall_soundscape", "non_diegetic_music")
_Ref2VA合法任务前缀 = ("keyframe completion", "reference generation", "video editing",
                      "video continuation", "audio reuse", "audio reference")


def 检查Ref2VA(text, duration=None, shot_count=0, 图片数=0, 视频数=0, 音频数=0):
    """Ref2VA 全参考模式协议检查（依 references/ref-en.txt）。

    与基础模式的关键差异：
    - 主字段是 detailed_description（不是 integrated_multimodal_description）；
    - 分镜编号/时间码只在 detailed_description 内检查——retention_analysis 里
      合规地出现乱序镜头引用（如 (appears in [Shot 2], [Shot 1])）且不带时间码；
    - 额外检查六段结构/顺序、summary 任务类型前缀、参考标签、retention 关系标记。
    """
    issues = []
    text = str(text or "")
    if not text.strip():
        return ["输出为空"]

    # 1. 六段结构存在且顺序正确
    位置 = []
    for field in _Ref2VA六段:
        idx = text.find(field + ":")
        if idx < 0:
            issues.append(f"缺少核心字段 {field}")
        else:
            位置.append(idx)
    if len(位置) == len(_Ref2VA六段) and 位置 != sorted(位置):
        issues.append("六个 section 顺序不符合 ref-en.txt 规范")

    # 2. detailed_description  section 内的分镜检查
    m = re.search(r"\ndetailed_description:", text)
    if m:
        dd = text[m.end():]
        nxt = re.search(r"\n(?:overall_soundscape|non_diegetic_music):", dd)
        if nxt:
            dd = dd[:nxt.start()]
    else:
        dd = ""
    shots = _解析shots(dd)
    if not shots:
        issues.append("detailed_description 内未找到 [Shot N] 分镜标记")
    else:
        nums = [s[0] for s in shots]
        if nums != list(range(1, len(nums) + 1)):
            issues.append(f"分镜编号不连续或不从 1 开始: {nums[:12]}")
        if shot_count and isinstance(shot_count, int) and len(nums) != shot_count:
            issues.append(f"分镜数量为 {len(nums)}，与指定镜头数 {shot_count} 不符")
        prev = None
        for idx, (no, seconds, _span) in enumerate(shots):
            if idx == 0:
                if seconds is not None:
                    issues.append("[Shot 1] 带了切点时间码（官方规范首镜不加时间码）")
                continue
            if seconds is None:
                issues.append(f"[Shot {no}] 缺少切点时间码（At MM:SS.mmm）")
                continue
            if prev is not None and seconds <= prev:
                issues.append(f"[Shot {no}] 切点 {seconds:.3f}s 未严格递增（上一镜 {prev:.3f}s）")
            if duration and seconds > float(duration) + 0.001:
                issues.append(f"[Shot {no}] 切点 {seconds:.3f}s 超出目标时长 {float(duration):.2f}s")
            prev = seconds
        timed = [s[1] for s in shots if s[1] is not None]
        if duration and timed and timed[-1] < float(duration) * 0.5:
            issues.append(
                f"最后一个切点 {timed[-1]:.3f}s 远早于目标时长 {float(duration):.2f}s，时间线可能未覆盖全片")

    # 3. summary 的任务类型前缀（[reference generation + audio reference] 形式）
    sm = re.search(r"\nsummary:\s*\n?\s*(\[[^\]]+\])", text)
    if sm:
        for part in sm.group(1).strip("[]").split("+"):
            p = part.strip()
            if p and p not in _Ref2VA合法任务前缀:
                issues.append(f"summary 任务类型前缀含未知类型「{p}」")
    elif "summary:" in text:
        issues.append("summary 缺少 [任务类型] 前缀")

    # 4. 参考标签：接了什么素材就该出现对应标签（编号从 1 起，与槽位一致）
    if not re.search(r"<Subject \d+>", text):
        issues.append("未使用 <Subject N> 参考标签")
    if 图片数 and not re.search(r"<Picture \d+>", text):
        issues.append(f"接了 {图片数} 张参考图但未使用 <Picture N> 标签")
    if 视频数 and not re.search(r"<Video \d+>", text):
        issues.append(f"接了 {视频数} 段参考视频但未使用 <Video N> 标签")
    if 音频数 and not re.search(r"<Audio \d+>", text):
        issues.append(f"接了 {音频数} 个参考音频但未使用 <Audio N> 标签")

    # 5. retention_analysis 关系标记（视觉四选一 + 音频四选一）
    ra = re.search(r"\nretention_analysis:(.*?)(?=\n(?:detailed_description|overall_soundscape|non_diegetic_music):)",
                   text, re.S)
    if ra:
        if not re.search(r"fully_preserved|partially_preserved|attribute_transfer|weak_reference",
                         ra.group(1)):
            issues.append("retention_analysis 缺少视觉关系标记（fully_preserved 等）")
        if 音频数 and not re.search(r"fully_copy|partially_copy|reference|weak_reference", ra.group(1)):
            issues.append("retention_analysis 缺少音频关系标记（reference 等）")

    return issues


def 修复H3(text, duration=None):
    """确定性修复（只动格式，不动语义）。返回 (新文本, 修了什么列表)。"""
    notes = []
    text = str(text or "")
    if not text.strip():
        return text, notes

    shots = _解析shots(text)
    if not shots:
        return text, notes

    # 1. 零填充规范化：At 0:03.5 → At 00:03.500
    def _pad(m):
        return "At %02d:%06.3f" % (int(m.group(1)), float(m.group(2)))

    padded = re.sub(r"At\s+(\d+):(\d+(?:\.\d+)?)", _pad, text)
    if padded != text:
        notes.append("时间码格式规范化为 MM:SS.mmm 零填充")
        text = padded

    # 2. 首镜时间码剥离（官方规范：首镜不加时间码）
    first_no, first_seconds, _ = shots[0]
    if first_seconds is not None:
        pat = re.compile(r"(\[Shot\s+%d\]\s*)At\s+\d+:\d+(?:\.\d+)?\s*,?\s*" % first_no)
        stripped = pat.sub(r"\1", text, count=1)
        if stripped != text:
            notes.append(f"剥离 [Shot {first_no}] 首镜时间码")
            text = stripped

    # 3. 越界时间码钳制到时长内
    if duration:
        limit = float(duration)

        def _clamp(m):
            total = int(m.group(1)) * 60 + float(m.group(2))
            if total > limit:
                notes.append(f"切点 {total:.3f}s 超出时长，钳制到 {limit:.3f}s")
                total = max(limit - 0.001, 0.0)
            return "At %02d:%06.3f" % (int(total // 60), total % 60)

        text = re.sub(r"At\s+(\d+):(\d+(?:\.\d+)?)", _clamp, text)

    return text, notes


# ---------------------------------------------------------------------------
# QWI：契约检查 + 确定性修复
# ---------------------------------------------------------------------------
def 检查QWI(text, aspect_ratio="", is_edit=False, image_count=0, 必须保留文字=None):
    """QWI 输出契约检查。返回问题列表（空 = 通过）。"""
    issues = []
    text = str(text or "")
    if not text.strip():
        return ["输出为空"]

    lines = text.split("\n")
    first = lines[0].strip() if lines else ""
    if not first.startswith("宽高比："):
        issues.append("首行不是「宽高比：」行（ComfyUI 流水线格式要求）")
    if "===== PROMPT =====" not in text:
        issues.append("缺少 ===== PROMPT ===== 分隔行")

    prose = text.split("===== PROMPT =====", 1)[1].strip() if "===== PROMPT =====" in text else text

    ratio = str(aspect_ratio or "").strip()
    if ratio:
        unquoted = 去引号内容(prose)
        if ratio in unquoted:
            issues.append(f"宽高比 {ratio} 写进了提示词正文（应只在「宽高比：」行，正文禁出现）")

    issues.extend(检查空话(prose))

    if is_edit:
        if "\n\n" in prose:
            issues.append("Edit 模式正文应为单段（检测到空行分段）")
        if image_count > 1:
            tags = set(re.findall(r"<image(\d+)>", prose))
            missing = {str(i) for i in range(1, image_count + 1)} - tags
            if missing:
                issues.append(f"多图编辑缺少 <imageN> 标记: {sorted(missing, key=int)}")

    for lit in (必须保留文字 or []):
        if lit and lit not in text:
            issues.append(f"用户指定文字可能丢失: 「{lit[:40]}」")

    return issues


def 修复QWI(text):
    """确定性修复：剥离分隔行前的闲聊前缀、清理多余空行。返回 (新文本, 修了什么列表)。"""
    notes = []
    text = str(text or "")
    if "===== PROMPT =====\n" in text:
        head, _, tail = text.partition("===== PROMPT =====\n")
        # head 里只保留「宽高比：」行，其余视为闲聊前缀
        kept = [ln for ln in head.split("\n") if ln.strip().startswith("宽高比：")]
        dropped = [ln for ln in head.split("\n") if ln.strip() and not ln.strip().startswith("宽高比：")]
        if dropped:
            notes.append(f"剥离 PROMPT 分隔行前的 {len(dropped)} 行闲聊前缀")
        new_head = "\n".join(kept).strip()
        text = (new_head + "\n\n===== PROMPT =====\n" + tail) if new_head else ("===== PROMPT =====\n" + tail)
    # 正文尾部多余空行
    stripped = text.rstrip()
    if stripped != text:
        notes.append("清理尾部空行")
        text = stripped
    return text, notes


# ---------------------------------------------------------------------------
# 通用
# ---------------------------------------------------------------------------
def 检查通用(text):
    """两个家族都适用的基础检查。"""
    issues = []
    text = str(text or "")
    if "<think>" in text:
        issues.append("输出残留思考块标签（清洗未净）")
    low = text.lower()
    if "thinking process" in low or "thinking process:" in low:
        issues.append("输出残留英文思考过程（模型未收敛思考直接输出，如 Thinking Process:）")
    if text.count("```") >= 2:
        issues.append("输出残留 markdown 代码围栏")
    if text.strip() and len(text.strip()) < 20:
        issues.append(f"输出过短（{len(text.strip())} 字符），可能被截断")
    return issues


def 汇总(issues):
    """把问题列表压成一行日志文本。"""
    if not issues:
        return ""
    return "；".join(str(i) for i in issues)
