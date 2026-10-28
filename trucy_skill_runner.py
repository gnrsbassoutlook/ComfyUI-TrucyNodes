"""TrucyNodes · Skill Runner / LLM Loader / VLM Runner 节点族（合并自 ComfyUI-TrucyLLM）。

六个节点，三个类目：
    LLM Loader      —— 装载三种大脑：局域网LM Studio / 远程API（OpenAI 兼容）/ 本地GGUF。
                      独立类目 TrucyNodes/LLM Loader；输出端口名仍为 LLM，
                       可同时喂给 Skill Runner 家族与 VLM Runner（上游只管装载，不管执行）。
    Skill Loader    —— 扫描 skills 目录，选择或自动匹配 Skill
    Chat            —— LLM + Skill + 提示词 → 文本（支持参考图/音频输入）
    Prompt (H3/QWI) —— 官方提示词 Skill（H3 视频 / Qwen-Image-2.1 图像）→ 结构化提示词
    Unload Model    —— 释放本地 GGUF 占用的显存（放工作流末尾、出图前）
    VLM Runner      —— LLM + 提示词 + 图片（8 槽）或视频（1 个）→ 文本，不调用 Skill；
                      图片/视频模式互斥（独立类目 TrucyNodes/VLM Runner）。

LLM Loader 与各执行节点之间的连接端口名为 LLM（输出/输入均为此名）。
质量层 trucy_quality：检查只记日志、确定性修复只动格式、LLM 纠正可选且全自动——
连续性优先，任何手段都不会中断 ComfyUI 批处理流水线。
传统节点写法（INPUT_TYPES / RETURN_TYPES），方便自行修改。
"""
import re
import sys

# 双上下文导入兼容：ComfyUI 里本模块是插件包子模块，相对导入可解析；
# 单测以裸模块导入（无父包）时相对导入必失败，退回裸导入——调用方需已把
# 插件根目录放上 sys.path（各测试脚本均如此）。
try:
    from .trucy_llm import TrucyBrain, TrucyBrainError, TrucyLocalBrain, 扫描gguf文件
    from .trucy_quality import (
        检查H3, 检查QWI, 检查MOSS, 检查通用, 修复H3, 修复QWI, 修复MOSS, 汇总, 提取引号文字,
    )
    from .trucy_skills import (
        自动选择, 发现skills, 获取skill, 规范化内联文件, 构建skill系统提示词, 读取reference,
    )
    from .trucy_media import (
        图片槽输入, 音频槽输入, 收集图片, 收集音频,
        构建素材清单, 构建媒体部分, 已连接音频, 解析标签家族, 标签逻辑选项,
        通用标签模式,
        视频槽输入, 解析视频源, 视频信息, 视频数据URI, 视频帧条目, ffmpeg可用,
        _输入被静音 as 输入被静音,
        _张量可用 as _张量可用,
        _视频可用 as _视频可用,
    )
    from .trucy_presets import 保存预设, 取预设, 预设选项
    from .trucy_llm import KV缓存类型选项, FlashAttention模式选项
except ImportError:
    import os as _os

    _here = _os.path.dirname(_os.path.abspath(__file__))
    if _here not in sys.path:
        sys.path.insert(0, _here)
    from trucy_llm import TrucyBrain, TrucyBrainError, TrucyLocalBrain, 扫描gguf文件  # noqa: E402
    from trucy_llm import KV缓存类型选项, FlashAttention模式选项  # noqa: E402
    from trucy_quality import (  # noqa: E402
        检查H3, 检查QWI, 检查MOSS, 检查通用, 修复H3, 修复QWI, 修复MOSS, 汇总, 提取引号文字,
    )
    from trucy_skills import (  # noqa: E402
        自动选择, 发现skills, 获取skill, 规范化内联文件, 构建skill系统提示词, 读取reference,
    )
    from trucy_media import (  # noqa: E402
        图片槽输入, 音频槽输入, 收集图片, 收集音频,
        构建素材清单, 构建媒体部分, 已连接音频, 解析标签家族, 标签逻辑选项,
        通用标签模式,
        视频槽输入, 解析视频源, 视频信息, 视频数据URI, 视频帧条目, ffmpeg可用,
        _输入被静音 as 输入被静音,
        _张量可用 as _张量可用,
        _视频可用 as _视频可用,
    )
    from trucy_presets import 保存预设, 取预设, 预设选项  # noqa: E402

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
H3技能ID = "h3-prompt-writing"           # 内置官方 H3 Skill 目录名
基础模式任务 = ("T2VA", "I2VA", "FL2VA", "L2VA")   # 使用 references/base-en.txt
H3任务选项 = ["Auto", "T2VA", "I2VA", "FL2VA", "L2VA", "Ref2VA"]
H3任务说明 = {
    "Auto": "Auto（请根据创意描述与参考素材自行判断 T2VA / I2VA / FL2VA / L2VA / Ref2VA）",
    "T2VA": "T2VA（文生视频：从文本构建完整视听时间线）",
    "I2VA": "I2VA（首帧图生视频：以首帧为锚点向前发展）",
    "FL2VA": "FL2VA（首尾帧图生视频：描述首帧到尾帧的连续路径）",
    "L2VA": "L2VA（尾帧图生视频：推断开局并收敛到给定尾帧）",
    "Ref2VA": "Ref2VA（全参考模式：按六段式结构改写）",
}

QWI技能ID = "qwen-image-2-1-prompter"    # 内置官方 Qwen-Image-2.1 Skill 目录名
QWI任务选项 = ["T2I", "Edit"]
QWI任务说明 = {
    "T2I": "T2I（文生图：英文观察者视角单段长描述，另输出 wh_ratio）",
    "Edit": "Edit（图像编辑/多图合成：属性解耦 + <imageN> 标记 + ratio_follow）",
}

MOSS技能ID = "moss-image-prompt-enhancer"   # 官方 MOSS-Image Skill 目录名
MOSS任务选项 = ["Caption", "Layout"]
MOSS任务说明 = {
    "Caption": "Caption（散文式图像长描述：主体/动作/环境/镜头/光线/材质/色调，可直接生图）",
    "Layout": "Layout（像素布局：画布 16 倍数 + 扁平 items + 绝对像素 bbox，编译为一行 "
              "yxyx 中心化 JSON，适合海报/多面板/精确文字排版）",
}

# 内置三家的 references 按任务精选加载；其余（第三方 / 自建）走全量兜底自动加载
内置skillIDs = frozenset({H3技能ID, QWI技能ID, MOSS技能ID})
第三方附录最多文件 = 6          # 单次最多注入的附录个数
第三方附录单文件上限 = 24000     # 单个附录超过此字符数则整份跳过（避免半截规则误导模型）
第三方附录总量上限 = 48000       # 一次注入的全部附录合计字符上限
技能预设选项 = ["H3（MiniMax 视频提示词）", "Qwen-Image-2.1（图像提示词）", "MOSS-Image（提示词增强）"]

# 节点拆分（2026-10-29）：按「这次要不要吃素材」把提示词节点一分为二，
# 各自的下拉只留本节点用得着的值，避免十几项混在一起。
#   老节点 TrucyPromptH3QWI（Prompt · Ref2V/I2I）：12 个媒体槽在身，只管带素材的任务
#   新节点 TrucyPromptPure （Prompt · T2V/T2I） ：零媒体槽，只管纯文本任务
# 老节点的值保留家族前缀（历史工作流里存的就是这种写法，去掉会出现空白项）；
# 新节点下拉不带前缀，节点内按当前预设补前缀后交给同一套执行逻辑。
素材任务选项 = (
    ["Auto"]
    + [f"H3·{t}" for t in ("I2VA", "FL2VA", "L2VA", "Ref2VA")]
    + ["QWI·Edit"]
)
纯文本任务选项 = ["Auto", "T2VA", "T2I", "Caption", "Layout"]

# 质量模式（连续性优先：默认只检查并记录日志，零打断；纠正为可选）
质量模式选项 = ["检查并记录（推荐）", "检查+自动纠正一次", "关闭检查"]
镜头数选项 = ["Auto"] + [str(i) for i in range(1, 21)]
画面比例选项 = ["不指定", "横屏（16:9）", "竖屏（9:16）"]
LLM类型选项 = ["局域网LM Studio", "远程API", "本地GGUF"]


# ---------------------------------------------------------------------------
# 公共工具
# ---------------------------------------------------------------------------
def _日志(msg):
    print(f"\033[36m[TrucyLLM]\033[0m {msg}")


def _清洗输出(text, 保留思考过程=False):
    """清理 LLM 输出里的思考块 / 代码围栏 / 常见废话前缀。

    保留思考过程=True 时只去首尾空白，思考块（<think>…</think>）原样保留
    （仅本地 GGUF 思考型模型有内联思考块；远程推理模型的思考在 API 侧
    单独返回，本开关对它们无效）。
    """
    if not text:
        return ""
    result = str(text).strip()

    if not 保留思考过程:
        # 1. 思考块
        result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL | re.IGNORECASE).strip()
        if "<think>" in result.lower() and "</think>" not in result.lower():
            result = re.sub(r"<think>.*", "", result, flags=re.DOTALL | re.IGNORECASE).strip()
        # 1.5 思考型本地模型（如 Qwen3.8）：输出形如「思考过程</think>\n\n正式回答」——
        #     按最后一个闭合标签切分
        if "</think>" in result:
            tail = result.rsplit("</think>", 1)[-1].strip()
            if tail:
                result = tail

    # 2. markdown 代码围栏
    fence = re.search(r"^```(?:text|json|plaintext|plain|markdown)?\s*\n(.*?)\n```\s*$", result, re.DOTALL)
    if fence:
        result = fence.group(1).strip()
    else:
        result = re.sub(r"^```[\w]*\s*\n", "", result)
        result = re.sub(r"\n```\s*$", "", result)

    # 3. {"prompt": "..."} 包裹
    wrapper = re.match(r'^\s*\{\s*"(?:prompt|output|result|text)"\s*:\s*"(.*?)"\s*\}\s*$', result, re.DOTALL)
    if wrapper:
        result = wrapper.group(1).strip().replace("\\n", "\n").replace('\\"', '"')

    # 4. 常见前缀
    for pattern in (
        r"^Here(?:'s| is) (?:the|your) (?:generated |rewritten |final )?(?:H3 )?prompt:?\s*\n",
        r"^(?:Sure|Okay|Of course)[!,.]?\s*(?:Here(?:'s| is).*?:)?\s*\n",
        r"^Output:?\s*\n",
    ):
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)

    return result.strip()


def _推理后自动卸载(LLM, 开启=False):
    """执行节点「推理后自动卸载」的落地：仅本地 GGUF 大脑有效。

    为什么不放在 LLM Loader：Loader 在工作流最上游执行，「推理何时结束」
    只有执行节点知道；且多个执行节点共用一个 Loader 时，只在最后一个
    执行节点上开，可避免中途卸载导致下一个节点重新加载模型。
    远程API / 局域网LM Studio 的模型不在本机显存，无需卸载。
    """
    if not 开启:
        return
    卸载 = getattr(LLM, "卸载", None)
    if not callable(卸载):
        _日志("推理后自动卸载: 当前大脑为远程API/局域网LM Studio（模型不在本机显存），无需卸载")
        return
    try:
        数量 = 卸载()
        if 数量:
            _日志(f"推理后自动卸载: 本地模型已卸载（{数量} 个实例），显存已释放"
                  "（下次推理会重新加载模型，略慢）")
        else:
            _日志("推理后自动卸载: 没有已加载的本地模型实例")
    except Exception as e:
        _日志(f"推理后自动卸载失败（不影响本次输出）: {e}")


def _采样微调端口():
    """执行节点（Chat / Prompt / VLM Runner）共用的采样微调控件。

    铁律：全部默认值 = 「不指定、不发」——老工作流零行为变化。
    两类字段分开标注（tooltip 说清生效面）：
      top_p / seed     —— OpenAI 标准请求字段：本地 GGUF 与 远程API/LM Studio 都按请求生效；
      top_k / 重复惩罚 —— llama.cpp 专有字段：本地 GGUF 与 LM Studio 生效；
                          严格 OpenAI 兼容 API 无此字段（被拒时自动去掉重试，不打断流水线）；
      保留思考过程     —— 仅本地 GGUF 思考型模型（保留内联 <think> 块）。
    远程大脑的等效调优（temperature/top_p 之外的）请在 LM Studio / API 界面设置。
    """
    return {
        "top_p": ("FLOAT", {
            "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.05,
            "tooltip": "核采样：只从概率前 top_p 的候选里抽，越小越保守。"
                       "0 = 不指定（用大脑自己的默认）。"
                       "OpenAI 标准字段，本地GGUF / 远程API / LM Studio 都按请求生效。"
                       "Qwen3.8 参考：思考模式 0.95、非思考 0.80。",
        }),
        "top_k": ("INT", {
            "default": 0, "min": 0, "max": 200, "step": 1,
            "tooltip": "每步只保留概率前 k 的候选，治天马行空。0 = 不指定。"
                       "llama.cpp 专有字段：本地GGUF 与 LM Studio 生效；"
                       "严格 OpenAI 兼容 API 没有这个字段（设了多被忽略，被拒时自动去掉重试）。"
                       "Qwen 系参考值 20。",
        }),
        "重复惩罚": ("FLOAT", {
            "default": 1.0, "min": 0.5, "max": 2.0, "step": 0.05,
            "tooltip": "重复惩罚（llama.cpp repeat_penalty）：>1 抑制复读机，1.0 = 不指定。"
                       "llama.cpp 专有字段：本地GGUF 与 LM Studio 生效；严格 API 无此字段。",
        }),
        "seed": ("INT", {
            "default": 0, "min": 0, "max": 0xFFFFFFFF, "step": 1,
            "control_after_generate": True,
            "tooltip": "随机种子：固定后同样输入结果可复现。0 = 不指定（端点默认随机行为）。"
                       "OpenAI 标准字段，本地GGUF / 远程API / LM Studio 都按请求生效。",
        }),
        "保留思考过程": ("BOOLEAN", {
            "default": False,
            "tooltip": "开启 = 输出里保留模型的 <think> 思考块（默认剥掉只留正式回答）。"
                       "仅本地 GGUF 思考型模型（如 Qwen3.8）生效；"
                       "远程推理模型的思考由 API 单独返回，本开关无效。",
        }),
    }


def _自动选择skill(LLM, skills, user_text):
    """让 LLM 从 Skill 目录中挑选唯一最匹配的 Skill（移植自 llama-TE）。"""
    if not skills:
        return None
    catalogue = "\n".join(
        f'- {s["id"]}: {s["name"]}；{str(s.get("description") or "")[:500]}' for s in skills
    )
    messages = [
        {"role": "system", "content": "根据用户任务选择唯一最匹配的 Skill。只输出 Skill ID，不解释，不添加标点。"},
        {"role": "user", "content": f"可用 Skills：\n{catalogue}\n\n用户任务：\n{user_text}"},
    ]
    content, _ = LLM.chat(messages, temperature=0.0, max_tokens=256)
    selected = content.strip().strip("`'\".,，。 ")
    valid_ids = {str(s.get("id") or "") for s in skills}
    if selected in valid_ids:
        return 获取skill(selected)
    for sid in valid_ids:
        if sid and sid in selected:
            return 获取skill(sid)
    raise ValueError(f"自动选择 Skill 失败，模型返回：{selected[:120]}。请手动选择 Skill。")


def _解析skill加载器(skill加载器, LLM, 用户文本):
    """把 Skill Loader 节点的输出解析为一个 skill 记录（或 None）。"""
    if not isinstance(skill加载器, dict):
        return None

    inline = skill加载器.get("inline_file")
    if isinstance(inline, dict) and str(inline.get("content") or "").strip():
        return inline

    selected_id = str(skill加载器.get("selected") or "").strip()
    if selected_id:
        skill = 获取skill(selected_id)
        if skill is None:
            raise ValueError("Skill 已不存在，请刷新 Skill Loader 并重新选择。")
        return skill

    return _自动选择skill(LLM, skill加载器.get("skills") or [], 用户文本)


def _自动加载第三方附录(skill, 已选):
    """第三方 / 自建 Skill 的 references 全量兜底加载。

    内置三家（h3-prompt-writing / qwen-image-2-1-prompter / moss-image-prompt-enhancer）
    各有按任务精选的附录表，不在此列——它们的附录大（ref-en 24KB），全量注入只会撑爆上下文。

    第三方 Skill 则相反：SKILL.md 里常写「see references/xxx.md」，但单次推理没有文件系统，
    不注入就等于模型永远看不到。这里按文件名顺序全量注入，并设三道闸：

      - 最多 第三方附录最多文件 个（.md / .txt，yaml/json 等配置档跳过）
      - 单个超过 第三方附录单文件上限 字符 → 整份跳过（不截断，避免半截规则误导模型）
      - 合计超过 第三方附录总量上限 字符 → 停止后续文件

    任何跳过都写日志，不打断流水线。
    """
    if "inline_content" in skill:
        return []
    if str(skill.get("id") or "") in 内置skillIDs:
        return []

    已选 = {str(x).replace("\\", "/").strip("/") for x in (已选 or [])}
    候选 = [
        p for p in skill.get("references", [])
        if str(p).lower().endswith((".md", ".txt"))
        and str(p).replace("\\", "/").strip("/") not in 已选
    ]
    if not 候选:
        return []

    块们 = []
    总量 = 0
    已装 = []
    跳过 = []
    for rel in 候选:
        if len(已装) >= 第三方附录最多文件:
            跳过.append(f"{rel}（已达 {第三方附录最多文件} 个文件上限）")
            continue
        try:
            正文 = 读取reference(skill, rel)
        except Exception as e:  # 缺文件 / 越界 / 编码问题都不该中断出稿
            跳过.append(f"{rel}（读取失败：{e}）")
            continue
        if not str(正文 or "").strip():
            跳过.append(f"{rel}（空文件）")
            continue
        if len(正文) > 第三方附录单文件上限:
            跳过.append(f"{rel}（{len(正文)} 字符 > 单文件上限 {第三方附录单文件上限}）")
            continue
        if 总量 + len(正文) > 第三方附录总量上限:
            跳过.append(f"{rel}（累计将超总量上限 {第三方附录总量上限} 字符）")
            continue
        总量 += len(正文)
        已装.append(rel)
        块们.append(f"===== {rel} =====\n{正文}")

    if 已装:
        _日志(f"提示词节点: 第三方 Skill「{skill.get('id')}」自动加载附录 {len(已装)} 份"
              f"（{总量} 字符）：{', '.join(已装)}")
    if 跳过:
        _日志(f"提示词节点: 第三方 Skill 附录跳过 {len(跳过)} 份（不打断）："
              f"{'; '.join(跳过)}")
    return 块们


# ---------------------------------------------------------------------------
# 节点 1：LLM Loader（三种大脑装载）
# ---------------------------------------------------------------------------
class TrucyLLMLoader:
    """三种大脑装载器（下拉切换）：
    局域网LM Studio —— 填 http://<Mac-IP>:1234/v1 与模型 ID；
    远程API        —— 任何 OpenAI 兼容服务（ChatGPT / DeepSeek 等），填 api_base + api_key + model；
    本地GGUF       —— 用本机显卡跑 ComfyUI/models/LLM（含子文件夹）下的 gguf，主模型/投影各自下拉选择。

    本节点只负责装载大脑，不执行任何 Skill；输出端口 LLM 可同时接给
    Skill Runner 家族（Skill Loader/Chat/Prompt）与 VLM Runner。
    """

    @classmethod
    def INPUT_TYPES(cls):
        主模型, 投影模型, _roots = 扫描gguf文件()
        if 主模型:
            gguf选项 = list(主模型)
        else:
            gguf选项 = ["（未找到 GGUF，请放入 ComfyUI/models/LLM 后刷新页面）"]
        if 投影模型:
            proj选项 = ["(无)"] + list(投影模型)
        else:
            proj选项 = ["(无)"]
        return {
            "required": {
                "model": ("STRING", {
                    "default": "gemma-4-e4b-it",
                    "tooltip": "【模型名·可自由填写】任意 OpenAI 兼容模型 ID：LM Studio 用 /v1/models 列表里的 id；"
                               "DeepSeek 用 deepseek-chat；中转站/第三方用其模型名，如 gemini-3.1-flash-lite-preview。"
                               "「API预设」选中只会帮填此框，之后可随手改成任何模型名（本地GGUF 模式下忽略）。",
                }),
            },
            "optional": {
                "LLM类型": (LLM类型选项, {
                    "default": "局域网LM Studio",
                    "tooltip": "只选LLM类型（三选一，本栏不填任何地址）："
                               "局域网LM Studio=Mac 上的 LM Studio；远程API=DeepSeek/OpenAI 等（需 api_key）；"
                               "本地GGUF=本机显卡跑 models/LLM 下的 gguf（主模型+投影下拉）。"
                               "地址请填在下方独立的 api_base 地址栏（本地GGUF 时该栏无效），"
                               "或在「API预设」下拉一键选用常用地址。",
                }),
                "API预设": (预设选项(), {
                    "default": "（不使用预设）",
                    "tooltip": "常用远程LLM地址簿：选中即自动套用该预设的 api_base/api_key/model/超时"
                               "（只帮填远程字段，不改LLM类型；本地GGUF 模式下忽略）。"
                               "用「＋ 保存为API预设」按钮或「保存为预设」文本框增存；"
                               "存于插件目录 api_presets.json（本地明文含密钥，切勿外发目录）。",
                }),
                "api_base": ("STRING", {
                    "default": "",
                    "placeholder": "http://192.168.1.112:1234/v1",
                    "tooltip": "【地址栏】远程LLM的 OpenAI 兼容地址，只对「局域网LM Studio」「远程API」有效，"
                               "本地GGUF 模式下此栏无效（自动忽略）。"
                               "局域网LM Studio 填 http://<Mac-IP>:1234/v1；"
                               "DeepSeek 填 https://api.deepseek.com/v1（只写域名不写 /v1 也能自动兼容）。"
                               "留空 = 用默认局域网地址 http://192.168.1.112:1234/v1（Mac Studio）。",
                }),
                "api_key": ("STRING", {
                    "default": "lm-studio",
                    "tooltip": "API Key。LM Studio 不校验（任意非空）；DeepSeek/OpenAI 填真实 key（sk- 开头）。本地模式忽略。",
                }),
                "请求超时秒": ("INT", {
                    "default": 300, "min": 30, "max": 3600, "step": 10,
                    "tooltip": "远程LLM请求超时（秒）。推理型模型建议 >= 300。",
                }),
                "保存为预设": ("STRING", {
                    "default": "",
                    "placeholder": "填个名字，跑一次即存入地址簿",
                    "tooltip": "填名称后跑一次工作流：把当前 api_base/api_key/model/超时 存进插件目录 "
                               "api_presets.json，刷新页面后出现在 API预设 下拉里"
                               "（本地明文含 API Key，切勿外发插件目录）。同名覆盖。",
                }),
                "gguf主模型": (gguf选项, {
                    "default": gguf选项[0],
                    "tooltip": "本地模式：ComfyUI/models/LLM（含子文件夹）下的 gguf 主模型。放入新文件后刷新浏览器即可在此下拉看到。",
                }),
                "mmproj投影": (proj选项, {
                    "default": proj选项[0],
                    "tooltip": "本地模式：视觉投影模型（mmproj）。选了本地模型才能看图片；纯文本任务可选(无)省显存。",
                }),
                "n_ctx": ("INT", {
                    "default": 8192, "min": 2048, "max": 131072, "step": 1024,
                    "tooltip": "本地模式：上下文长度。H3 大 skill 建议 >= 8192；调大更吃显存。",
                }),
                "n_gpu_layers": ("INT", {
                    "default": -1, "min": -1, "max": 200, "step": 1,
                    "tooltip": "本地模式：卸载到 GPU 的层数。-1=全部；0=纯 CPU；显存不够时调小（如 20）。",
                }),
                "n_batch": ("INT", {
                    "default": 512, "min": 128, "max": 2048, "step": 64,
                    "tooltip": "本地模式：提示词处理批量，越大越快越吃显存。",
                }),
                "思考模式": (["开启", "关闭"], {
                    "default": "开启",
                    "tooltip": "本地模式：Qwen3.8 等思考型模型的思考开关。开启质量更高但更慢；"
                               "关闭可大幅提速（格式严格的提示词任务可关）。",
                }),
                "推理强度": (["xhigh", "medium", "low"], {
                    "default": "medium",
                    "tooltip": "本地模式：思考开启时的推理强度（xhigh 最慢最细 / low 最快）。关闭思考时无效。",
                }),
                "KV缓存K类型": (list(KV缓存类型选项), {
                    "default": KV缓存类型选项[0],
                    "tooltip": "本地模式（llama.cpp 专有，参考 llama-TE）：KV 缓存 K 的量化精度。"
                               "默认(不指定)=保持 llama.cpp 原生 f16；q8_0 明显省显存，"
                               "大模型+长上下文下常常还更快。远程API/LM Studio 无此概念"
                               "（等效调优请在各自界面设置）。",
                }),
                "KV缓存V类型": (list(KV缓存类型选项), {
                    "default": KV缓存类型选项[0],
                    "tooltip": "本地模式（llama.cpp 专有，参考 llama-TE）：KV 缓存 V 的量化精度。"
                               "默认(不指定)=保持 llama.cpp 原生 f16；q8_0 明显省显存，"
                               "大模型+长上下文下常常还更快。远程API/LM Studio 无此概念。",
                }),
                "FlashAttention": (list(FlashAttention模式选项), {
                    "default": FlashAttention模式选项[0],
                    "tooltip": "本地模式（llama.cpp 专有，参考 llama-TE）：Flash Attention 三态开关。"
                               "不开启=不碰 llama.cpp 默认行为（老工作流零变化）；"
                               "开启/关闭=显式覆盖。开了通常更快更省显存，个别环境有兼容问题可关。"
                               "远程API/LM Studio 无此概念。",
                }),
            },
        }

    RETURN_TYPES = ("TRUCY_BRAIN",)
    RETURN_NAMES = ("LLM",)
    FUNCTION = "run"
    CATEGORY = "TrucyNodes/LLM Loader"

    def run(self, LLM类型="局域网LM Studio",
            api_base="http://192.168.1.112:1234/v1", api_key="lm-studio",
            model="gemma-4-e4b-it", 请求超时秒=300,
            gguf主模型="", mmproj投影="(无)", n_ctx=8192, n_gpu_layers=-1, n_batch=512,
            思考模式="开启", 推理强度="medium",
            KV缓存K类型=KV缓存类型选项[0], KV缓存V类型=KV缓存类型选项[0],
            FlashAttention=FlashAttention模式选项[0],
            API预设="（不使用预设）", 保存为预设=""):
        类型 = str(LLM类型)

        # API 预设地址簿：选中预设 = 用预设的地址/密钥/模型/超时帮填（只动远程字段）
        预设名 = str(API预设 or "").strip()
        if 预设名 and 预设名 != "（不使用预设）":
            记录 = 取预设(预设名)
            if 记录 is None:
                _日志(f"LLM: API预设「{预设名}」不存在（可能已删除），刷新页面后重新选择")
            else:
                if str(记录.get("api_base") or "").strip():
                    api_base = 记录["api_base"]
                if str(记录.get("api_key") or "").strip():
                    api_key = 记录["api_key"]
                if str(记录.get("model") or "").strip():
                    model = 记录["model"]
                if 记录.get("timeout"):
                    请求超时秒 = int(记录["timeout"])
                _日志(f"LLM: 已套用 API预设「{预设名}」→ {记录.get('api_base')} "
                      f"| model={记录.get('model') or model}")

        # 「保存为预设」填了名：把当前远程字段存进插件目录 api_presets.json
        保存名 = str(保存为预设 or "").strip()
        if 保存名:
            try:
                保存预设(保存名, api_base, api_key, model, 请求超时秒)
                _日志(f"LLM: 已保存 API预设「{保存名}」→ api_presets.json"
                      f"（刷新页面后可在 API预设 下拉选中）")
            except ValueError as e:
                _日志(f"LLM: 保存 API预设 失败 - {e}")

        # 地址栏（api_base）规范化：界面上默认留空，是独立待填行；
        # 留空时：局域网LM Studio 用默认 Mac 地址；远程API 必须显式填（禁止猜）；
        # 本地GGUF 模式压根不走这里（地址栏无效）。
        if not str(api_base or "").strip():
            if 类型.startswith("远程"):
                raise ValueError(
                    "远程API 模式必须在 api_base 地址栏填写地址"
                    "（如 https://api.deepseek.com/v1，只写域名不写 /v1 也能自动兼容）。"
                )
            api_base = "http://192.168.1.112:1234/v1"
            _日志("LLM: 地址栏(api_base)留空，使用默认局域网地址 "
                  "http://192.168.1.112:1234/v1（Mac Studio LM Studio）")
        if 类型.startswith("本地"):
            if not gguf主模型 or gguf主模型.startswith("（"):
                raise ValueError(
                    "未选择 GGUF 文件。请把 .gguf 模型放入 ComfyUI/models/LLM"
                    "（或其子文件夹），然后刷新浏览器页面重新加载节点下拉。"
                )
            _主模型, _投影模型, roots = 扫描gguf文件()
            brain = TrucyLocalBrain(
                gguf路径=gguf主模型, mmproj路径=mmproj投影,
                n_ctx=n_ctx, n_gpu_layers=n_gpu_layers, n_batch=n_batch,
                模型根目录=roots,
                enable_thinking=(str(思考模式) != "关闭"),
                reasoning_effort=推理强度,
                kv缓存k类型=KV缓存K类型, kv缓存v类型=KV缓存V类型,
                flash_attention=FlashAttention,
            )
            _日志(f"LLM就绪: {brain.describe()}（首次推理时加载模型；"
                  f"本地模式下 api_base 地址栏无效）")
        else:
            if 类型.startswith("远程") and not str(api_key or "").strip():
                _日志("提示：远程API 通常需要填写 api_key（sk- 开头）")
            brain = TrucyBrain(api_base=api_base, api_key=api_key, model=model, timeout=请求超时秒)
            _日志(f"LLM就绪: {brain.describe()}")
        return (brain,)


class TrucyUnloadModel:
    """释放本地 GGUF LLM占用的显存。

    典型用法：工作流末尾、出图节点之前（本地大模型和出图会抢显存）。
    通过「上游」通配输入挂在提示词节点后面，确保最后执行。
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "optional": {
                "上游": ("*", {
                    "tooltip": "接入任意上游输出，固定执行顺序（确保提示词生成完之后才卸载）。",
                }),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "run"
    CATEGORY = "TrucyNodes/Skill Runner"
    OUTPUT_NODE = True

    def run(self, 上游=None):
        count = TrucyLocalBrain.卸载全部()
        if count:
            _日志(f"本地模型已卸载（{count} 个实例），显存已释放")
        else:
            _日志("没有已加载的本地模型，无需卸载")
        return ()


# ---------------------------------------------------------------------------
# 节点 2：Skill Loader
# ---------------------------------------------------------------------------
class TrucySkillLoader:
    """扫描 skills 目录（本插件 + comfyUI-llama-TE），选择或自动匹配 Skill。"""

    @classmethod
    def INPUT_TYPES(cls):
        skills = 发现skills()
        choices = [自动选择] + [s["label"] for s in skills]
        return {
            "required": {
                "skill": (choices, {
                    "default": 自动选择,
                    "tooltip": "自动选择 = 用LLM按任务匹配 Skill；也可固定选一个。",
                }),
            },
            "optional": {
                "加载文件名": ("STRING", {"default": "", "multiline": False}),
                "加载文件内容": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("TRUCY_SKILL",)
    RETURN_NAMES = ("skill加载器",)
    FUNCTION = "run"
    CATEGORY = "TrucyNodes/Skill Runner"

    def run(self, skill, 加载文件名="", 加载文件内容="", **kwargs):
        skills = 发现skills()
        selected = ""
        if skill != 自动选择:
            hit = next((s for s in skills if s["label"] == skill or s["id"] == skill), None)
            if hit is None:
                raise ValueError(f"找不到 Skill：{skill}，请刷新节点后重新选择。")
            selected = hit["id"]
        inline = 规范化内联文件(加载文件名, 加载文件内容)
        if inline is not None:
            _日志(f"Skill加载器: 使用临时文件 {inline['name']}")
        elif selected:
            _日志(f"Skill加载器: 固定 Skill {selected}")
        else:
            _日志(f"Skill加载器: 自动选择（{len(skills)} 个可用 Skill）")
        return ({"selected": selected, "skills": skills, "inline_file": inline},)


# ---------------------------------------------------------------------------
# 节点 3：Chat
# ---------------------------------------------------------------------------
class TrucyChat:
    """LLM + Skill + 提示词 → 文本。可选接入多参考素材（图片1-9 / 音频1-3）。"""

    @classmethod
    def INPUT_TYPES(cls):
        optional = {
            "skill加载器": ("TRUCY_SKILL",),
            "输入媒体标签逻辑": (标签逻辑选项, {
                "default": 标签逻辑选项[0],
                "tooltip": "参考素材标签用哪套规范（严格对应官方 Skill）："
                           "自动识别 = 按已加载 Skill 查登记册严格匹配，只有 h3-prompt-writing / "
                           "qwen-image-* 系 Skill 能判定，内联文件/第三方 Skill/未接 Skill 时按 H3 兜底并记日志；"
                           "H3 = <Picture N>/<Audio N>；"
                           "Qwen-Image-2.1 = <imageN>（多图必须用，单图不加标签）。",
            }),
            "参考图最长边": ("INT", {
                "default": 0, "min": 0, "max": 2048, "step": 64,
                "tooltip": "发给 LLM 前参考图的缩放边长，0 = 标准 1280。"
                           "小上下文LLM（如 LM Studio 8192）建议 768 或 512，防止视觉 token 挤爆上下文。",
            }),
            "推理后自动卸载": ("BOOLEAN", {
                "default": False,
                "tooltip": "仅本地 GGUF 生效：本次推理完成后自动卸载模型、释放显存"
                           "（下次推理会重新加载模型，略慢）。多个执行节点共用一个 LLM Loader 时，"
                           "建议只挂在最后一个执行节点上；也可继续用专用的「卸载模型」节点。"
                           "远程API / 局域网LM Studio 下本选项无效（模型不在本机）。",
            }),
        }
        optional.update(_采样微调端口())
        optional.update(图片槽输入())
        optional.update(音频槽输入())
        return {
            "required": {
                "LLM": ("TRUCY_BRAIN",),
                "系统提示词": ("STRING", {
                    "default": "你是一个乐于助人的助手。",
                    "multiline": True,
                    "tooltip": "接入 Skill加载器 时，Skill 正文会追加在这段系统提示词之后。",
                }),
                "提示词": ("STRING", {"default": "", "multiline": True}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.05}),
                "max_tokens": ("INT", {"default": 4096, "min": 256, "max": 32768, "step": 256}),
            },
            "optional": optional,
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("文本",)
    FUNCTION = "run"
    CATEGORY = "TrucyNodes/Skill Runner"

    def run(self, LLM, 系统提示词, 提示词, temperature, max_tokens,
            skill加载器=None, 输入媒体标签逻辑=标签逻辑选项[0],
            参考图最长边=0, 推理后自动卸载=False,
            top_p=0.0, top_k=0, 重复惩罚=1.0, seed=0, 保留思考过程=False, **kwargs):
        if 输入被静音(LLM):
            _日志("对话节点: 上游 LLM 节点被静音（ExecutionBlocker），返回空输出——"
                  "取消静音或改接 LLM 后重跑")
            return ("",)
        # 多参考素材收集（空值安全：None/零尺寸/坏槽位/被静音跳过不报错，也不发给 LLM）
        图片条目 = 收集图片(kwargs, 最长边=参考图最长边 or None)
        视频条目 = []  # 视频参考端口已摘除（99.99% 不用）；媒体层后端保留，加一行即复活
        音频条目 = 收集音频(kwargs)
        skill = _解析skill加载器(skill加载器, LLM, "\n".join(
            p for p in (系统提示词, 提示词) if str(p or "").strip()))

        system_text = (系统提示词 or "").strip()
        if skill is not None:
            if "inline_content" in skill:
                system_text = "\n\n".join(p for p in (
                    system_text,
                    f"当前加载文件：{skill['name']}\n===== {skill['name']} =====\n{skill['inline_content']}",
                ) if p)
            else:
                system_text = 构建skill系统提示词(system_text, skill)

        # 标签家族：下拉手动指定优先；否则按 Skill 登记册严格匹配（猜不出就按 H3 兜底+记日志）
        有素材 = bool(图片条目 or 音频条目)
        图像标签模式 = 解析标签家族(输入媒体标签逻辑, skill, 有素材=有素材)

        messages = []
        if system_text:
            messages.append({"role": "system", "content": system_text})
        user_text = str(提示词 or "").strip()
        if not user_text and not (图片条目 or 音频条目):
            raise ValueError("提示词不能为空（也未接入任何参考素材）。")
        if not user_text:
            user_text = "请分析提供的输入。"
        if 图片条目 or 音频条目:
            user_text += "\n\n" + 构建素材清单(图片条目, 视频条目, 音频条目, 图像标签模式)
        messages.append({"role": "user", "content": user_text})

        媒体部分 = 构建媒体部分(图片条目, 视频条目, 音频条目, 图像标签模式)
        _日志(f"对话 → {LLM.describe()} | skill={'有' if skill else '无'} | "
              f"输入媒体标签={'QWI(<imageN>)' if 图像标签模式 else 'H3(<Picture N>)'} | "
              f"images={len(图片条目)} audios={len(音频条目)}")
        content, usage = LLM.chat(
            messages, temperature=temperature, max_tokens=max_tokens, 媒体部分=媒体部分,
            top_p=top_p, top_k=top_k, repeat_penalty=重复惩罚, seed=seed,
        )
        _日志(f"对话 ← {len(content)} chars | tokens={usage.get('total_tokens', '?')}")
        result = _清洗输出(content, 保留思考过程=保留思考过程)
        # 基础质量检查：只记日志，不打断（毫秒级纯 Python）
        问题 = 检查通用(result)
        if 问题:
            _日志(f"质量模块: {汇总(问题)}")
        _推理后自动卸载(LLM, 推理后自动卸载)
        return (result,)


# ---------------------------------------------------------------------------
# 节点 3.5：VLM Runner（图片 / 视频推理）
#   —— 对标 comfyUI-llama-TE 的 QwenTE图像推理并扩展视频：LLM + 系统/用户提示词
#      + 图片（8 槽）或视频（1 个）→ 文本，不经过 Skill Loader（区别于 Chat/Prompt 的
#      skill 通道）。图片/视频按「输入模式」互斥，不会同时发给大脑。
#      视频双通道：本地 GGUF 大脑发原生视频文件（Qwen-VL 经 mtmd+ffmpeg 直接读视频，
#      带时间戳）；远程大脑 / PATH 缺 ffmpeg / 原生发送失败 → 自动退化为等距抽帧。
# ---------------------------------------------------------------------------
class TrucyVLMRunner:
    """LLM + 系统提示词 + 用户提示词 + 图片（8 槽）或视频（1 个）→ 文本。不调用 Skill。"""

    @classmethod
    def INPUT_TYPES(cls):
        optional = {
            "参考图最长边": ("INT", {
                "default": 0, "min": 0, "max": 2048, "step": 64,
                "tooltip": "发给 LLM 前参考图/视频采样帧的缩放边长，0 = 标准 1280。"
                           "小上下文LLM（如 LM Studio 8192）建议 768 或 512，防止视觉 token 挤爆上下文。",
            }),
            "视频抽帧数": ("INT", {
                "default": 8, "min": 2, "max": 32, "step": 1,
                "tooltip": "视频退化通道用：按等距时间点抽这么多帧发给大脑。仅在原生视频不可用"
                           "（远程大脑 / PATH 缺 ffmpeg / 原生发送失败）时生效。帧越多越细节，越占上下文。",
            }),
            "推理后自动卸载": ("BOOLEAN", {
                "default": False,
                "tooltip": "仅本地 GGUF 生效：本次推理完成后自动卸载模型、释放显存"
                           "（下次推理会重新加载模型，略慢）。多个执行节点共用一个 LLM Loader 时，"
                           "建议只挂在最后一个执行节点上；也可继续用专用的「卸载模型」节点。"
                           "远程API / 局域网LM Studio 下本选项无效（模型不在本机）。",
            }),
        }
        optional.update(_采样微调端口())
        optional.update(图片槽输入(数量=8))   # 与 llama-TE 的 QwenTE图像推理 对齐：8 个图片输入
        optional.update(视频槽输入())          # 1 个视频输入（与图片槽按「输入模式」互斥）
        return {
            "required": {
                "LLM": ("TRUCY_BRAIN",),
                "输入模式": (["图片", "视频"], {
                    "default": "图片",
                    "tooltip": "图片 = 分析「🖼️ 参考图1-8」槽位接入的图片；"
                               "视频 = 分析「🎬 视频」端口接入的 1 个视频。"
                               "两种模式互斥、不会同时发送；两边都接时按本下拉取舍并记日志。",
                }),
                "系统提示词": ("STRING", {
                    "default": "你是一个专业的视觉分析助手。请仔细观察用户提供的图片或视频，"
                               "给出准确、详细、结构清晰的描述与分析。",
                    "multiline": True,
                }),
                "提示词": ("STRING", {
                    "default": "请详细描述输入的内容。",
                    "multiline": True,
                }),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.05}),
                "max_tokens": ("INT", {"default": 2048, "min": 256, "max": 32768, "step": 256}),
            },
            "optional": optional,
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("文本",)
    FUNCTION = "run"
    CATEGORY = "TrucyNodes/VLM Runner"

    def run(self, LLM, 输入模式, 系统提示词, 提示词, temperature, max_tokens,
            参考图最长边=0, 视频抽帧数=8, 推理后自动卸载=False,
            top_p=0.0, top_k=0, 重复惩罚=1.0, seed=0, 保留思考过程=False, **kwargs):
        if 输入被静音(LLM):
            _日志("VLM Runner: 上游 LLM 节点被静音（ExecutionBlocker），返回空输出——"
                  "取消静音或改接 LLM 后重跑")
            return ("",)
        模式 = str(输入模式)
        视频对象 = kwargs.get("🎬 视频")
        有视频输入 = _视频可用(视频对象)
        有图片输入 = any(_张量可用(kwargs.get(f"🖼️ 参考图{i}")) for i in range(1, 9))

        if 模式 == "视频":
            if 有图片输入:
                _日志("VLM Runner: 已连接参考图槽位，但当前为视频模式——图片已忽略"
                      "（切到「图片」模式即可分析图片）")
            if not 有视频输入:
                if 视频对象 is not None:
                    _日志("VLM Runner: 「🎬 视频」端口接了东西但不可用"
                          "（空输入/上游被静音/无法识别的视频对象），按未连接处理")
                raise ValueError(
                    "视频模式：请在「🎬 视频」端口连接 1 个视频（LoadVideo 节点的输出）；"
                    "若想分析图片，请把「输入模式」改回「图片」并连接参考图槽位。")
            return self._跑视频(LLM, 系统提示词, 提示词, temperature, max_tokens,
                               视频对象, 视频抽帧数, 推理后自动卸载,
                               top_p, top_k, 重复惩罚, seed, 保留思考过程)

        # 图片模式
        if 有视频输入:
            _日志("VLM Runner: 已连接视频端口，但当前为图片模式——视频已忽略"
                  "（切到「视频」模式即可分析视频）")
        # 多参考素材收集（空值安全：None/零尺寸/坏槽位/被静音跳过不报错，也不发给 LLM；
        # 编号保留槽位号从 1 起，按 图片1…图片8 通用标签发给模型，不挂靠任何 Skill 家族）
        图片条目 = 收集图片(kwargs, 最长边=参考图最长边 or None)
        if not 图片条目:
            raise ValueError(
                "图片模式：请在「🖼️ 参考图1-8」槽位至少连接 1 张图片；"
                "若想分析视频，请把「输入模式」改为「视频」并连接「🎬 视频」端口。")
        return self._跑图片(LLM, 系统提示词, 提示词, temperature, max_tokens,
                           图片条目, 推理后自动卸载,
                           top_p, top_k, 重复惩罚, seed, 保留思考过程)

    # ---- 图片模式 ----
    def _跑图片(self, LLM, 系统提示词, 提示词, temperature, max_tokens, 图片条目,
                推理后自动卸载=False, top_p=0.0, top_k=0, 重复惩罚=1.0, seed=0,
                保留思考过程=False):
        messages, 媒体部分 = self._组装(系统提示词, 提示词, 图片条目, [], 通用标签模式)
        _日志(f"VLM Runner → {LLM.describe()} | 模式=图片 | 通用标签(图片1-图片{len(图片条目)}) | "
              f"images={len(图片条目)}")
        content, usage = LLM.chat(
            messages, temperature=temperature, max_tokens=max_tokens, 媒体部分=媒体部分,
            top_p=top_p, top_k=top_k, repeat_penalty=重复惩罚, seed=seed,
        )
        return self._收尾(LLM, content, usage, 保留思考过程, 推理后自动卸载)

    # ---- 视频模式 ----
    def _跑视频(self, LLM, 系统提示词, 提示词, temperature, max_tokens,
               视频对象, 抽帧数, 推理后自动卸载=False, top_p=0.0, top_k=0,
               重复惩罚=1.0, seed=0, 保留思考过程=False):
        try:
            路径, 需清理 = 解析视频源(视频对象, "视频")
        except Exception as e:
            # 空值不崩：连了却不可用的视频按「未连接」走设计内报错，不把原始异常抛上流水线
            _日志(f"VLM Runner: 视频源解析失败（{e}），按未连接处理")
            raise ValueError(
                "视频模式：「🎬 视频」端口连接的视频无法读取（文件不存在/已移动/不是有效视频）。"
                "请重新连接 LoadVideo 的输出；若想分析图片，请把「输入模式」改回「图片」。")
        try:
            信息 = 视频信息(路径) or {}
            原生 = False
            url = ""
            if isinstance(LLM, TrucyLocalBrain):
                if ffmpeg可用():
                    原生, url = True, 路径
                else:
                    _日志("VLM Runner: 本地大脑原生视频需要 PATH 上的 ffmpeg + ffprobe"
                          "（llama.cpp 以子进程调用解码），未找到——本次自动抽帧发送")
            else:
                _日志("VLM Runner: 远程大脑不走原生视频通道（兼容性优先）——本次自动抽帧发送")
            if 原生:
                视频条目 = [{"kind": "视频", "slot": 1, "n": 1, "label": "视频",
                          "原生": True, "url": url, "path": 路径,
                          "duration": 信息.get("duration", 0.0),
                          "fps": 信息.get("fps", 0.0),
                          "width": 信息.get("width", 0), "height": 信息.get("height", 0),
                          "frames": []}]
            else:
                try:
                    视频条目 = [视频帧条目(视频对象, 采样帧数=抽帧数)]
                except Exception as e:
                    _日志(f"VLM Runner: 视频抽帧失败（{e}）")
                    raise ValueError(
                        "视频模式：无法从连接的视频中抽取帧（文件损坏/编码不支持/OpenCV 读取失败）。"
                        "请更换视频文件，或把「输入模式」改回「图片」分析图片。")
            messages, 媒体部分 = self._组装(系统提示词, 提示词, [], 视频条目, 通用标签模式)
            _日志(f"VLM Runner → {LLM.describe()} | 模式=视频 | "
                  f"{'原生视频文件' if 原生 else '抽帧×%d' % len(视频条目[0]['frames'])} | "
                  f"{信息.get('width', 0)}x{信息.get('height', 0)}，"
                  f"约{信息.get('duration', 0.0):.1f}秒")
            try:
                content, usage = LLM.chat(
                    messages, temperature=temperature, max_tokens=max_tokens, 媒体部分=媒体部分,
                    top_p=top_p, top_k=top_k, repeat_penalty=重复惩罚, seed=seed,
                )
            except Exception as e:
                if not 原生:
                    raise
                _日志(f"VLM Runner: 原生视频发送失败（{e}），自动改为抽帧重试")
                try:
                    视频条目 = [视频帧条目(视频对象, 采样帧数=抽帧数)]
                except Exception as e2:
                    raise ValueError(
                        f"视频模式：原生发送失败（{e}），抽帧兜底也失败（{e2}）。"
                        "请更换视频文件，或把「输入模式」改回「图片」。")
                messages, 媒体部分 = self._组装(系统提示词, 提示词, [], 视频条目, 通用标签模式)
                _日志(f"VLM Runner → {LLM.describe()} | 模式=视频 | "
                      f"抽帧×{len(视频条目[0]['frames'])}（重试）")
                content, usage = LLM.chat(
                    messages, temperature=temperature, max_tokens=max_tokens, 媒体部分=媒体部分,
                    top_p=top_p, top_k=top_k, repeat_penalty=重复惩罚, seed=seed,
                )
            return self._收尾(LLM, content, usage, 保留思考过程, 推理后自动卸载)
        finally:
            if 需清理:
                from pathlib import Path

                Path(路径).unlink(missing_ok=True)

    # ---- 公共组装 / 收尾 ----
    def _组装(self, 系统提示词, 提示词, 图片条目, 视频条目, 标签模式):
        messages = []
        system_text = (系统提示词 or "").strip()
        if system_text:
            messages.append({"role": "system", "content": system_text})
        user_text = str(提示词 or "").strip()
        if not user_text:
            user_text = "请分析提供的输入。"
        if 图片条目 or 视频条目:
            user_text += "\n\n" + 构建素材清单(图片条目, 视频条目, [], 标签模式)
        messages.append({"role": "user", "content": user_text})
        媒体部分 = 构建媒体部分(图片条目, 视频条目, [], 标签模式)
        return messages, 媒体部分

    def _收尾(self, LLM, content, usage, 保留思考过程=False, 推理后自动卸载=False):
        _日志(f"VLM Runner ← {len(content)} chars | tokens={usage.get('total_tokens', '?')}")
        result = _清洗输出(content, 保留思考过程=保留思考过程)
        # 基础质量检查：只记日志，不打断（毫秒级纯 Python）
        问题 = 检查通用(result)
        if 问题:
            _日志(f"质量模块: {汇总(问题)}")
        _推理后自动卸载(LLM, 推理后自动卸载)
        return (result,)


# ---------------------------------------------------------------------------
# 节点 4：Prompt (H3/QWI)
# ---------------------------------------------------------------------------
class TrucyPromptH3QWI:
    """官方提示词 Skill + LLM → 结构化提示词。

    skill_preset 下拉同时支持三套官方 Skill 家族：
      - H3（MiniMax H3 视频提示词，分镜/音效/配乐结构化输出）
      - Qwen-Image-2.1（阿里官方图像提示词重写，T2I / Edit）
      - MOSS-Image（MOSS 官方 Prompt Enhancer：caption 长描述 / layout 像素排版）
    """

    @classmethod
    def INPUT_TYPES(cls):
        optional = {
            "skill加载器": ("TRUCY_SKILL", {
                "tooltip": "不接：用内置的当前预设 Skill（H3 / Qwen-Image-2.1 / MOSS 三家官方规范）。\n"
                           "接了：按家族前缀换书——H3 预设任意 Skill 都能挂；图像预设只认同家族"
                           "（qwen-image* / moss*），跨家族会忽略并回退内置；"
                           "第三方 / 自建 Skill 的 references 会自动全量注入。",
            }),
            "vision_context": ("STRING", {
                "force_input": True, "default": "",
                "tooltip": "可接入 llama-TE 的 Qwen3.8-VL 图像推理输出，作为参考素材的视觉分析。",
            }),
            "aspect_ratio": ("STRING", {
                "default": "",
                "tooltip": "目标宽高比（仅 Qwen-Image-2.1 用），如 16:9 / 1:1 / 9:16 / 3:2。留空由模型自行判断。"
                           "H3 视频模式请使用下方「画面比例」下拉，本参数在 H3 下无效。",
            }),
            "参考图最长边": ("INT", {
                "default": 0, "min": 0, "max": 2048, "step": 64,
                "tooltip": "发给 LLM 前参考图的缩放边长，0 = 标准 1280。"
                           "小上下文LLM（如 LM Studio 8192）建议 768 或 512，防止视觉 token 挤爆上下文。",
            }),
            "推理后自动卸载": ("BOOLEAN", {
                "default": False,
                "tooltip": "仅本地 GGUF 生效：本次推理（含可选的一次自动纠正）完成后自动卸载模型、"
                           "释放显存（下次推理会重新加载模型，略慢）。多个执行节点共用一个 LLM Loader 时，"
                           "建议只挂在最后一个执行节点上；也可继续用专用的「卸载模型」节点。"
                           "远程API / 局域网LM Studio 下本选项无效（模型不在本机）。",
            }),
            "上游约束生效": ("BOOLEAN", {
                "default": False,
                "tooltip": "总闸（仅 H3 视频模式）：关闭时，「指定时长」「强制单镜」等外接输入一律无效，"
                           "Skill 完全按官方原版方式执行；开启后，外接的时长与切镜约束才会真正影响本次生成。",
            }),
            "指定时长": ("FLOAT", {
                "default": 0.0, "min": 0.0, "max": 120.0, "step": 0.5,
                "tooltip": "仅 H3 用：上游指定的单次生成时长（秒）。总闸开启且本值 >0 时覆盖 duration 控件；"
                           "0=不指定。超出健康区（单镜 4-10s / 多镜 4-15s）自动钳制并记日志，不报错。"
                           "帧数请由上级节点先换算成秒——H3 世界只有秒。",
            }),
            "强制单镜": ("BOOLEAN", {
                "default": False,
                "tooltip": "仅 H3 用：总闸开启且本项=True 时，强制单镜不切（只允许 [Shot 1]、无 At 切点时间码、"
                           "单一连续镜头运动）；False=按 shot_count / Auto 由模型自裁。",
            }),
            "画面比例": (画面比例选项, {
                "default": 画面比例选项[0],
                "tooltip": "仅 H3 视频模式：目标画幅。横屏/竖屏按画幅语法注入镜头约束（竖屏：中近景/单主体/"
                           "纵向构图/慎用大全景；横屏：可用全景与双人并置）；「不指定」=不注入，保持官方原版行为。"
                           "节点自身控件，不受总闸管。",
            }),
            "quality_mode": (质量模式选项, {
                "default": 质量模式选项[0],
                "tooltip": "检查并记录：输出后跑纯 Python 检查，有问题只记日志，输出照常流向下游（零打断）；"
                           "检查+自动纠正一次：检查不过时在同一次运行内自动多打一次模型修改，不等人工、队列不停、"
                           "失败保底第一稿（坏输出时该节点耗时约翻倍）；关闭检查：不检查。",
            }),
            "shot_count": (镜头数选项, {
                "default": "Auto",
                "tooltip": "仅 H3 用：指定 [Shot N] 数量；Auto 由模型结合时长与节奏自定。",
            }),
            "constraints": ("STRING", {
                "default": "", "multiline": True,
                "tooltip": "硬性要求：必须保留或禁止添加的内容（如：不许改变人物服装；对白必须是原文）。会写进调用规则。",
            }),
            "reference_context": ("STRING", {
                "default": "", "multiline": True,
                "tooltip": "参考素材补充事实：人物身份/关系/场景设定等，帮助模型理解接入的图片或素材。",
            }),
            "max_chars": ("INT", {
                "default": 0, "min": 0, "max": 20000, "step": 100,
                "tooltip": "提示词正文字数上限，0 = 不限制。超出时 Repair 模式会尝试压缩。",
            }),
        }
        # 多参考素材槽位（optional；未连接=None，空值安全，不发给 LLM）
        # 视频参考端口已按用户决定摘除（99.99% 不用），只保留图片与音频
        optional.update(图片槽输入())
        optional.update(音频槽输入())
        optional.update(_采样微调端口())
        return {
            "required": {
                "LLM": ("TRUCY_BRAIN",),
                "skill_preset": (技能预设选项, {
                    "default": 技能预设选项[0],
                    "tooltip": "H3 = MiniMax H3 视频提示词（分镜/音效/配乐）；"
                               "Qwen-Image-2.1 = 阿里官方图像提示词重写（T2I/Edit）；"
                               "MOSS-Image = MOSS 官方 Prompt Enhancer（caption 长描述 / layout 像素排版，"
                               "坐标由模型自行中心化编译）。",
                }),
                "task_type": (素材任务选项, {
                    "default": "Auto",
                    "tooltip": "带素材的任务：H3·I2VA 首帧 / FL2VA 首尾帧 / L2VA 尾帧 / Ref2VA 全参考、"
                               "QWI·Edit 图生图。\n"
                               "纯文本任务（T2VA 文生视频 / T2I 文生图 / MOSS 长描述与版面）在另一个节点"
                               "「Prompt (T2V/T2I)」里，那个节点没有媒体槽、下拉也不参杂这些。\n"
                               "选了与本预设不匹配的任务会自动纠正为 Auto 并记日志。",
                }),
                "scene_direction": ("STRING", {
                    "default": "", "multiline": True,
                    "tooltip": "导演指令 / 创意描述，一句话就能跑。例如: 镜头从窗外缓慢推入，角色转身说“时间到了”。\n"
                               "纯文本任务（H3·T2VA / QWI·T2I / MOSS·Caption）不需要连接任何素材，"
                               "9 个参考图与 3 个参考音频槽位全部可选、留空即可。",
                }),
                "duration": ("FLOAT", {
                    "default": 5.0, "min": 4.0, "max": 15.0, "step": 0.5,
                    "tooltip": "目标时长（秒）= 单次生成单元时长，非全片总长（全片多单元拆分后到达芬奇等剪辑台拼接）。"
                               "仅 H3 视频模式有效，Qwen-Image-2.1 模式下忽略。",
                }),
                "output_language": (["English", "Chinese"], {"default": "English"}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.05}),
                "max_tokens": ("INT", {"default": 4096, "min": 1024, "max": 16384, "step": 256}),
            },
            "optional": optional,
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "run"
    CATEGORY = "TrucyNodes/Skill Runner"

    def run(self, LLM, skill_preset, task_type, scene_direction, duration, output_language,
            temperature, max_tokens, skill加载器=None, vision_context="", aspect_ratio="",
            quality_mode="检查并记录（推荐）", shot_count="Auto", constraints="",
            reference_context="", max_chars=0, 上游约束生效=False, 指定时长=0.0,
            强制单镜=False, 画面比例="不指定", 参考图最长边=0, 推理后自动卸载=False,
            top_p=0.0, top_k=0, 重复惩罚=1.0, seed=0, 保留思考过程=False, **kwargs):
        if 输入被静音(LLM):
            _日志("提示词节点: 上游 LLM 节点被静音（ExecutionBlocker），返回空输出——"
                  "取消静音或改接 LLM 后重跑")
            return ("",)
        预设 = str(skill_preset or "")
        图像模式 = 预设.startswith("Qwen")          # Qwen-Image-2.1 家族
        MOSS模式 = 预设.startswith("MOSS")          # MOSS-Image 家族
        图像类模式 = 图像模式 or MOSS模式           # 非 H3：不吃时长/分镜/画幅约束
        镜头数 = int(shot_count) if str(shot_count).isdigit() else 0
        质量模式 = str(quality_mode or 质量模式选项[0])
        try:
            上游时长 = float(指定时长 or 0.0)
        except (TypeError, ValueError):
            上游时长 = 0.0

        # —— 上游约束总闸（仅 H3 视频模式）——
        # 关：外接输入全是空气，官方 skill 原版执行；开：指定时长(>0)覆盖控件时长，
        # 强制单镜锁 1 镜；超健康区只记日志钳制，绝不报错不打断。
        生效时长 = float(duration)
        单镜模式 = False
        if not 图像类模式:
            if bool(上游约束生效):
                if 上游时长 > 0:
                    生效时长 = 上游时长
                    _日志(f"上游约束: 指定时长 {上游时长:.2f}s 覆盖控件值 {float(duration):.2f}s")
                if bool(强制单镜):
                    单镜模式 = True
                    镜头数 = 1
                    _日志("上游约束: 强制单镜生效（不切镜，分镜数锁定 1）")
                下限, 上限 = (4.0, 10.0) if 单镜模式 else (4.0, 15.0)
                if 生效时长 < 下限:
                    _日志(f"上游约束: 时长 {生效时长:.2f}s 低于{'单镜' if 单镜模式 else '多镜'}健康下限 {下限:.1f}s，已钳制")
                    生效时长 = 下限
                elif 生效时长 > 上限:
                    _日志(f"上游约束: 时长 {生效时长:.2f}s 超出{'单镜' if 单镜模式 else '多镜'}健康上限 {上限:.1f}s，已钳制")
                    生效时长 = 上限
            elif 上游时长 > 0 or bool(强制单镜):
                _日志("上游约束: 总闸关闭，指定时长/强制单镜不生效，按官方 skill 原版执行")

        # 多参考素材收集（空值安全：None/零尺寸/坏槽位跳过不报错，也不发给 LLM；
        # 编号保留槽位号从 1 起，与下游多参 text encoder 一一对应，不重编号）
        图片条目 = 收集图片(kwargs, 最长边=参考图最长边 or None)
        视频条目 = []  # 视频参考端口已摘除（99.99% 不用）；媒体层后端保留，加一行即复活
        if 图像类模式:
            家族名 = "Qwen-Image-2.1" if 图像模式 else "MOSS-Image"
            音频条目 = []
            if 已连接音频(kwargs):
                _日志(f"提示词节点: {家族名} 为图像提示词 Skill，参考音频槽位已忽略")
            if bool(上游约束生效) or 上游时长 > 0 or bool(强制单镜) \
                    or str(画面比例 or 画面比例选项[0]) != 画面比例选项[0]:
                _日志("提示词节点: 上游约束（总闸/指定时长/强制单镜）与画面比例均为 H3 视频模式参数，"
                      f"{家族名} 模式下已忽略（只认参考图输入）")
        else:
            音频条目 = 收集音频(kwargs)
        素材清单 = 构建素材清单(图片条目, 视频条目, 音频条目, 图像类模式)
        媒体部分 = 构建媒体部分(图片条目, 视频条目, 音频条目, 图像类模式)

        # 0. 任务类型规范化：剥离家族前缀；跨家族选择时纠正为 Auto
        任务 = str(task_type or "Auto").strip()
        当前家族 = "QWI" if 图像模式 else ("MOSS" if MOSS模式 else "H3")
        for 前缀, 家族 in (("H3·", "H3"), ("QWI·", "QWI"), ("MOSS·", "MOSS")):
            if 任务.startswith(前缀):
                任务 = 任务[len(前缀):]
                if 家族 != 当前家族:
                    _日志(f"提示词节点: 预设为 {当前家族} 家族，任务 {task_type} 不适用，改用 Auto")
                    任务 = "Auto"
                break
        合法任务 = {
            "H3": H3任务选项,
            "QWI": QWI任务选项 + ["Auto"],
            "MOSS": MOSS任务选项 + ["Auto"],
        }[当前家族]
        if 任务 not in 合法任务:
            任务 = "Auto"

        # 0.1 纯文本任务提示：T2VA / T2I / Caption 三类不依赖任何素材，
        # 素材槽位本就全部可选；若手上仍连着图或音频，只记一行日志说明去向，
        # 既不改变行为也不打断流水线。
        纯文本任务 = (
            (当前家族 == "H3" and 任务 == "T2VA")
            or (当前家族 == "QWI" and 任务 == "T2I")
            or (当前家族 == "MOSS" and 任务 == "Caption")
        )
        if 纯文本任务 and (图片条目 or 音频条目):
            _日志(f"提示词节点: 任务 {当前家族}·{任务} 属纯文本任务，但仍检测到 "
                  f"{len(图片条目)} 张参考图 / {len(音频条目)} 段音频，已按素材一并发送；"
                  "如需纯文本效果请断开对应槽位")
        elif 纯文本任务:
            _日志(f"提示词节点: 纯文本任务 {当前家族}·{任务}（零素材输入）")

        # 1. 确定 Skill
        if 图像类模式:
            # 图像家族：只接受同家族 Skill（前缀匹配，含自装/第三方）或临时内联文件；
            # 跨家族（H3 风格或另一图像家族）不适用，自动忽略并回退内置
            内置ID = QWI技能ID if 图像模式 else MOSS技能ID
            内置名 = "Qwen-Image-2.1" if 图像模式 else "MOSS-Image"
            家族前缀 = "qwen-image" if 图像模式 else "moss"
            家族任务说明 = QWI任务说明 if 图像模式 else MOSS任务说明
            skill = None
            if skill加载器:
                loaded = _解析skill加载器(
                    skill加载器, LLM,
                    f"{家族任务说明.get(任务, 任务)} {scene_direction}".strip()
                )
                # 家族匹配用前缀而非精确 id：同家族的自装/第三方 Skill 也能直接选用
                # （如 qwen-image-edit-system-prompt / qwen-image-t2i-system-prompt），
                # 只有跨家族（H3 风格 skill 塞进图像模式）才忽略
                if loaded is not None and (
                    "inline_content" in loaded
                    or str(loaded.get("id") or "").lower().startswith(家族前缀)
                ):
                    skill = loaded
                elif loaded is not None:
                    _日志(f"提示词节点: Skill「{loaded.get('id')}」不属于 {内置名} 家族"
                          f"（需以 {家族前缀} 开头），改用内置 {内置ID}")
            if skill is None:
                skill = 获取skill(内置ID)
            if skill is None:
                raise ValueError(
                    f"未找到 {内置ID} Skill。请确认本插件 skills/ 目录存在。"
                )
        else:
            # H3 模式：优先 skill加载器（可换 llama-TE 风格 Skill），其次内置 h3-prompt-writing
            skill = _解析skill加载器(
                skill加载器, LLM,
                f"{H3任务说明.get(任务, 任务)} {scene_direction}".strip()
            )
            if skill is None:
                skill = 获取skill(H3技能ID)
            if skill is None:
                raise ValueError(
                    "未找到 h3-prompt-writing Skill。请确认本插件 skills/ 目录或 "
                    "comfyUI-llama-TE/skills/ 目录存在。"
                )

        # 2. 组装系统提示词：Skill 正文 + 按任务类型按需加载的 reference
        extra_blocks = []
        want_refs = []
        if "inline_content" not in skill:
            if 图像模式:
                # Auto 时按「有没有参考图」替模型判定模式——节点本来就知道，比让模型
                # 从措辞里猜更可靠，也让 Auto 与显式选 T2I/Edit 拿到同样的附录支持
                附录任务 = 任务
                if 任务 == "Auto":
                    附录任务 = "Edit" if 图片条目 else "T2I"
                    _日志(f"提示词节点: QWI 任务 Auto → 按素材判定为 {附录任务}"
                          f"（{len(图片条目)} 张参考图），预加载对应附录")
                want_refs = {
                    "T2I": ["references/t2i_rules.md", "references/cheat_sheet.md"],
                    "Edit": ["references/edit_rules.md", "references/cheat_sheet.md"],
                }.get(附录任务, [])
            elif MOSS模式:
                # Layout/Auto 才需要坐标系与字段白名单；Caption 全靠 SKILL.md 自足
                want_refs = ["references/compile-rules.md", "references/layout.md"] \
                    if 任务 in ("Layout", "Auto") else []
            else:
                want_refs = []
                if 任务 == "Ref2VA":
                    want_refs = ["references/ref-en.txt"]
                elif 任务 in 基础模式任务 or 任务 == "Auto":
                    want_refs = ["references/base-en.txt"]
            for wr in want_refs:
                if wr in skill.get("references", []):
                    extra_blocks.append(f"===== {wr} =====\n{读取reference(skill, wr)}")
        # 第三方 / 自建 Skill：references 全量兜底注入（内置三家不在此列）
        第三方块 = _自动加载第三方附录(skill, want_refs)
        extra_blocks.extend(第三方块)
        if 图像模式:
            base_system = ("你是阿里巴巴 Qwen-Image-2.1 官方图像提示词重写专家，严格按照当前 Skill 及其 "
                           "references 的规则输出，最终提示词必须可直接用于 Qwen-Image-2.1 生图/编辑。")
        elif MOSS模式:
            base_system = ("你是 MOSS-Image 官方提示词增强（Prompt Enhancer）专家，严格按当前 Skill 的"
                           "字段白名单、画布规则与输出契约作答。Layout 的方框中心化换算必须由你自己完成"
                           "（减去 W//2、H//2，顺序 y1,x1,y2,x2），最终结果要能直接粘贴给 MOSS-Image。")
        else:
            base_system = ("你是 MiniMax H3 官方视频提示词编写专家，严格按照当前 Skill 及其 references 的 "
                           "字段名、章节顺序、标签与时间格式输出。")
        system_text = 构建skill系统提示词(base_system, skill, extra_blocks)

        # 3. 组装用户消息（含显式硬性规则块：把本次调用的约束写成明条，纯提示词工程，不多一次调用）
        parts = []
        if 图像模式:
            parts.append(f"任务类型：{QWI任务说明.get(任务, 任务)}")
            ratio = str(aspect_ratio or "").strip()
            parts.append(f"目标宽高比：{ratio}（wh_ratio 必须取该值，比例不要写进提示词正文）" if ratio
                         else "目标宽高比：未指定，请根据画面内容自行判断并给出 wh_ratio。")
            rule_lines = [
                "【本次调用硬性规则】",
                "1. 宽高比只出现在首行「宽高比：」字段，禁止以任何形式写进 PROMPT 正文"
                "（宽高比/分辨率是下游生成参数，不属于提示词内容）。",
                "2. 用户引号内的文字必须逐字保留在画面文字描述中，不翻译、不改写、不增删标点。",
                "3. 禁止使用 8K / 4K / masterpiece / highly detailed / award-winning 一类空话质量词。",
            ]
            if 任务 == "Edit" or (任务 == "Auto" and 图片条目):
                tags = "、".join(f"<image{e['n']}>" for e in 图片条目)
                rule_lines.append(
                    f"4. 共 {len(图片条目)} 张参考图（{tags}）：多图必须使用上述 <imageN> 规范标记指代，"
                    "禁止用「第一张图」等自然语言编号；各图属性解耦，未要求修改的属性保持不动。")
            if str(constraints or "").strip():
                rule_lines.append(f"5. 硬性要求（必须遵守）：{str(constraints).strip()}")
            parts += rule_lines
            parts += ["", "创意描述 / 用户需求：", str(scene_direction or "").strip() or "（未提供，请自行发挥）"]
            if str(reference_context or "").strip():
                parts += ["", "参考素材补充（身份/关系等事实）：", str(reference_context).strip()]
            if str(vision_context or "").strip():
                parts += ["", "以下是对参考图片的视觉分析（vision context）：", str(vision_context).strip()]
            if 图片条目:
                parts += ["", 素材清单]
            parts += [
                "",
                "输出格式要求（ComfyUI 流水线模式）：",
                "第一行输出「宽高比：<wh_ratio 或 ratio_follow>」，",
                "空一行后输出「===== PROMPT =====」，",
                "之后只放最终提示词纯文本（单段，无 JSON、无解释、无微调建议）。",
            ]
        elif MOSS模式:
            parts.append(f"任务类型：{MOSS任务说明.get(任务, 任务)}")
            ratio = str(aspect_ratio or "").strip()
            if ratio:
                parts.append(f"目标宽高比：{ratio}（Layout 据此选择 16 倍数的像素画布；"
                             "比例字样禁止写进 JSON 或 caption）")
            elif 任务 in ("Layout", "Auto"):
                parts.append("目标画布：未指定，按 Skill 里的常见画布表选合适尺寸（宽高均为 16 倍数）。")
            规则 = ["只输出最终提示词：不解释过程、不给备选方案、不写 draft 文件、不调用任何脚本。"]
            if 任务 in ("Layout", "Auto"):
                规则.append(
                    "Layout 的坐标换算必须由你完成：v1=floor(y1)-H//2、v2=floor(x1)-W//2、"
                    "v3=ceil(y2)-H//2、v4=ceil(x2)-W//2，输出顺序 [v1,v2,v3,v4]（y 在前、x 在后）；"
                    "负值表示位于画面中心左上，属正常结果，严禁钳到 0 或改成正数。")
                规则.append(
                    "Layout 根字段只允许 summary / items / bbox_coord_space / bbox_format，"
                    "bbox_coord_space=\"abs_centralized\"、bbox_format=\"yxyx\"；"
                    "画布宽高为 16 的正整数倍，且不得写进 JSON 内部。")
            规则.append("用户引号内的文字逐字保留（text 字段或 caption 引用），不翻译、不改写、不增删标点。")
            规则.append("禁止 8K / 4K / masterpiece / highly detailed / award-winning 一类空话质量词。")
            if str(constraints or "").strip():
                规则.append(f"硬性要求（必须遵守）：{str(constraints).strip()}")
            parts.append("【本次调用硬性规则】")
            parts += [f"{i}. {r}" for i, r in enumerate(规则, 1)]
            parts += ["", "创意描述 / 用户需求：", str(scene_direction or "").strip() or "（未提供，请自行发挥）"]
            if str(reference_context or "").strip():
                parts += ["", "参考素材补充（身份/关系等事实）：", str(reference_context).strip()]
            if str(vision_context or "").strip():
                parts += ["", "以下是对参考图片的视觉分析（vision context）：", str(vision_context).strip()]
            if 图片条目:
                parts += ["", 素材清单]
            parts += [
                "",
                "输出格式：Caption 直接给散文长描述（无标题、无前缀、无 JSON）；",
                "Layout 第一行「尺寸：WxH」，空一行后给分隔行（五个等号 + 空格 + PROMPT + 空格 + 五个等号，"
                "与 Skill 的 Output contract 完全一致），之后只放一行紧凑 JSON"
                "（summary/items/bbox_coord_space/bbox_format）。",
            ]
        else:
            lang_line = "输出语言：英文（对话、歌词、画面文字保留原文）。" if output_language == "English" \
                else "输出语言：中文（保留字段名与结构为英文）。"
            if 单镜模式:
                分镜规则 = (
                    "2. 分镜数量：1（强制单镜，全程不切镜）：全文只允许出现 [Shot 1] 这一个镜头标记，"
                    "禁止出现 [Shot 2] 及任何后续镜头标记，禁止任何 At 切点时间码；"
                    "镜头运动必须是单一连续运动（如持续推近 / 横移 / 跟随），"
                    "动作与对白都在这一个镜头内连续完成，禁止使用 <scenetrans> 等跨镜标记。"
                )
            else:
                分镜规则 = f"2. 分镜数量：{镜头数 if 镜头数 else '由你结合时长与节奏自行决定'} 个 [Shot N]。"
            rule_lines = [
                "【本次调用硬性规则】",
                f"1. 目标时长 {生效时长:.2f} 秒：所有 [Shot N] 的切点时间（At MM:SS.mmm）严格递增，"
                f"且全部落在 0–{生效时长:.2f} 秒内，最后一个镜头必须覆盖到时长末尾。",
                分镜规则,
                "3. 画面文字 / 对白 / 歌词逐字保留用户原文，不翻译、不改写、不增删标点。",
                "4. 宽高比 / 帧率 / 总帧数是下游生成参数，禁止以任何形式写入提示词。",
            ]
            规则号 = 5
            if str(画面比例 or 画面比例选项[0]) != 画面比例选项[0]:
                画幅指导 = {
                    "横屏（16:9）": "横屏 16:9 画幅的镜头语法：可用大全景建立镜头与环境叙事；"
                                   "双人对话可用侧面并置或过肩正反打；充分利用画面宽度组织横向构图与遮挡关系。",
                    "竖屏（9:16）": "竖屏 9:16 画幅的镜头语法：优先中近景与特写、单主体聚焦；"
                                   "慎用大全景（画面容易被天空/地面浪费、信息效率低）；"
                                   "双人对话用正反打而非并置；利用前景-中景-背景的纵向层次构图；动作动势以纵向为主。",
                }.get(str(画面比例), "")
                rule_lines.append(
                    f"{规则号}. 目标画幅：{画面比例}。{画幅指导}"
                    "画幅比例本身是下游生成参数，禁止把比例字样写进输出正文。")
                规则号 += 1
            if str(constraints or "").strip():
                rule_lines.append(f"{规则号}. 硬性要求（必须遵守）：{str(constraints).strip()}")
            parts = [f"任务类型：{H3任务说明.get(任务, 任务)}", f"目标时长：{生效时长:.2f} 秒", lang_line]
            parts += rule_lines
            parts += ["", "创意描述 / 导演指令：", str(scene_direction or "").strip() or "（未提供，请自行发挥）"]
            if str(reference_context or "").strip():
                parts += ["", "参考素材补充（身份/关系等事实）：", str(reference_context).strip()]
            if str(vision_context or "").strip():
                parts += ["", "以下是对参考素材的视觉分析（vision context）：", str(vision_context).strip()]
            if 图片条目 or 音频条目:
                parts += ["", 素材清单]
        user_text = "\n".join(parts)

        # 4. 调用 LLM
        messages = [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text},
        ]
        预设名 = "QWI" if 图像模式 else ("MOSS" if MOSS模式 else "H3")
        _日志(f"提示词节点 → {LLM.describe()} | preset={预设名}"
              f" | skill={skill['id']} | task={任务} | images={len(图片条目)}"
              f" audios={len(音频条目)}")
        content, usage = LLM.chat(
            messages, temperature=temperature, max_tokens=max_tokens, 媒体部分=媒体部分,
            top_p=top_p, top_k=top_k, repeat_penalty=重复惩罚, seed=seed,
        )
        prompt = _清洗输出(content, 保留思考过程=保留思考过程)
        _日志(f"提示词节点 ← {len(prompt)} chars | tokens={usage.get('total_tokens', '?')}")
        if not prompt:
            raise TrucyBrainError(
                "LLM返回了空内容。推理型模型可能把 token 预算都用在了思考上，请调大 max_tokens。"
            )

        # 5. 质量层（连续性优先：检查只记日志；纠正为可选且全自动、不等人工、队列不停）
        if 质量模式 != "关闭检查":
            if 图像模式:
                问题 = 检查QWI(prompt, aspect_ratio=str(aspect_ratio or "").strip(),
                            is_edit=(任务 == "Edit" or (任务 == "Auto" and bool(图片条目))),
                            image_count=len(图片条目), 必须保留文字=提取引号文字(scene_direction))
                prompt, notes = 修复QWI(prompt)
            elif MOSS模式:
                # 先确定性修复再检查：小模型常忘做中心化，纯算术不该指望它算准
                prompt, notes = 修复MOSS(prompt, mode=任务 if 任务 in MOSS任务选项 else "Auto")
                问题 = 检查MOSS(prompt, mode=任务 if 任务 in MOSS任务选项 else "Auto")
            else:
                问题 = 检查H3(prompt, duration=生效时长, shot_count=镜头数,
                           task_type=任务, 图片数=len(图片条目),
                           视频数=0, 音频数=len(音频条目), 强制单镜=单镜模式)
                prompt, notes = 修复H3(prompt, duration=生效时长)
            问题 = list(问题) + 检查通用(prompt)
            for n in notes:
                _日志(f"质量模块: 确定性修复 - {n}")
            if 问题:
                _日志(f"质量模块: 检查发现 {len(问题)} 个问题（输出照常流向下游）- {汇总(问题)}")
            else:
                _日志("质量模块: 检查通过")

            # 可选：一次有界 LLM 纠正。自动完成、不弹窗、不等待人工、失败保底第一稿。
            if 质量模式 == "检查+自动纠正一次" and 问题:
                _日志(f"质量模块: 触发一次自动纠正（同一次运行内完成，队列不停止）")
                correction = list(messages) + [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": (
                        "你上一条输出未通过格式检查，问题如下：\n"
                        + "\n".join(f"- {i}" for i in 问题)
                        + "\n请在这一次回复中重新完整输出：遵守既定输出格式与全部硬性规则，"
                          "修正上述问题；不要只解释，不要输出差异，不要追加说明。"
                    )},
                ]
                try:
                    content2, _ = LLM.chat(
                        correction, temperature=temperature, max_tokens=max_tokens, 媒体部分=媒体部分,
                        top_p=top_p, top_k=top_k, repeat_penalty=重复惩罚, seed=seed,
                    )
                    prompt2 = _清洗输出(content2, 保留思考过程=保留思考过程)
                    if 图像模式:
                        问题2 = 检查QWI(prompt2, aspect_ratio=str(aspect_ratio or "").strip(),
                                     is_edit=(任务 == "Edit" or (任务 == "Auto" and bool(图片条目))),
                                     image_count=len(图片条目), 必须保留文字=提取引号文字(scene_direction))
                        prompt2, notes2 = 修复QWI(prompt2)
                    elif MOSS模式:
                        prompt2, notes2 = 修复MOSS(prompt2, mode=任务 if 任务 in MOSS任务选项 else "Auto")
                        问题2 = 检查MOSS(prompt2, mode=任务 if 任务 in MOSS任务选项 else "Auto")
                    else:
                        问题2 = 检查H3(prompt2, duration=生效时长, shot_count=镜头数,
                                     task_type=任务, 图片数=len(图片条目),
                                     视频数=0, 音频数=len(音频条目), 强制单镜=单镜模式)
                        prompt2, notes2 = 修复H3(prompt2, duration=生效时长)
                    问题2 = list(问题2) + 检查通用(prompt2)
                    if prompt2 and len(问题2) < len(问题):
                        for n in notes2:
                            _日志(f"质量模块: 确定性修复 - {n}")
                        _日志(f"质量模块: 纠正改善（{len(问题)} → {len(问题2)} 个问题），采用纠正稿")
                        prompt = prompt2
                    else:
                        _日志(f"质量模块: 纠正未改善（{len(问题2)} 个问题），保留第一稿")
                except Exception as e:
                    _日志(f"质量模块: 纠正请求失败（{e}），保留第一稿")

        _推理后自动卸载(LLM, 推理后自动卸载)
        return (prompt,)


# ---------------------------------------------------------------------------
# 节点 4b：Prompt (T2V/T2I) —— 纯文本形态
# ---------------------------------------------------------------------------
class TrucyPromptPure(TrucyPromptH3QWI):
    """纯文本提示词节点：零媒体槽，只吃一句话创意。

    与带素材的 TrucyPromptH3QWI 共用同一套执行逻辑，差别只在形态：
      - 没有 9 个参考图 / 3 个参考音频槽位（节点宽度和控件数直接砍半）
      - 任务下拉只留纯文本任务（T2VA / T2I / Caption / Layout），值不带家族前缀，
        由节点按当前 skill_preset 补上前缀后交给父类；跨家族选择由父类自动纠正为 Auto

    老节点的类名、端口顺序、任务选项一律不动，所以历史工作流不会红框。
    """

    @classmethod
    def INPUT_TYPES(cls):
        完整 = super().INPUT_TYPES()
        optional = {
            名: 定义 for 名, 定义 in 完整.get("optional", {}).items()
            if not (名.startswith("🖼️") or 名.startswith("🎵"))
        }
        required = dict(完整["required"])
        required["task_type"] = (纯文本任务选项, {
            "default": "Auto",
            "tooltip": "纯文本任务：T2VA 文生视频 / T2I 文生图 / Caption 长描述 / Layout 像素版面。\n"
                       "Auto 交给 Skill 自己判断——本节点没有素材槽，H3 自然落到 T2VA、"
                       "Qwen 落到 T2I、MOSS 落到 Caption。\n"
                       "选了跟当前预设不匹配的任务会自动纠正为 Auto 并记日志。",
        })
        return {"required": required, "optional": optional}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "run"
    CATEGORY = "TrucyNodes/Skill Runner"

    def run(self, LLM, skill_preset, task_type, scene_direction, duration, output_language,
            temperature, max_tokens, **kwargs):
        预设 = str(skill_preset or "")
        家族 = "QWI" if 预设.startswith("Qwen") else ("MOSS" if 预设.startswith("MOSS") else "H3")
        任务 = str(task_type or "Auto")
        if 任务 != "Auto":
            # 无前缀的值 = 用户按「任务」而不是「家族」在选，先确认这任务归当前家族，
            # 不归就明说并退回 Auto（不能靠父类的前缀纠正——那层看到的已经是带前缀的值，
            # 会误判成同家族，然后静默改 Auto，用户不知道为什么）
            家族任务 = {"H3": {"T2VA"}, "QWI": {"T2I"}, "MOSS": {"Caption", "Layout"}}[家族]
            纯任务 = 任务.split("·")[-1]
            if 纯任务 not in 家族任务:
                _日志(f"提示词节点: 任务 {任务} 不属于 {家族} 家族（{预设}），改用 Auto")
                任务 = "Auto"
            elif "·" not in 任务:
                # 补前缀后复用父类同一套执行逻辑；已带前缀（从老图抄过来）不再套一层
                任务 = f"{家族}·{任务}"
        return super().run(
            LLM, skill_preset, 任务, scene_direction, duration, output_language,
            temperature, max_tokens, **kwargs,
        )


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS = {
    "TrucyLLMLoader": TrucyLLMLoader,
    "TrucySkillLoader": TrucySkillLoader,
    "TrucyChat": TrucyChat,
    "TrucyPromptH3QWI": TrucyPromptH3QWI,
    "TrucyPromptPure": TrucyPromptPure,
    "TrucyUnloadModel": TrucyUnloadModel,
    "TrucyVLMRunner": TrucyVLMRunner,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "TrucyLLMLoader": "🚀 LLM Loader Trucy",
    "TrucySkillLoader": "🚀 Skill Loader Trucy",
    "TrucyChat": "🚀 Skill Runner Trucy · Chat",
    "TrucyPromptH3QWI": "🚀 Skill Runner Trucy · Prompt (Ref2V/I2I)",
    "TrucyPromptPure": "🚀 Skill Runner Trucy · Prompt (T2V/T2I)",
    "TrucyUnloadModel": "🚀 Skill Runner Trucy · Unload Model",
    "TrucyVLMRunner": "🚀 VLM Runner Trucy",
}
