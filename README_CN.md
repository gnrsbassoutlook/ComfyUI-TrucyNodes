# 🎬 ComfyUI-TrucyNodes (翠西节点包)
**专为 AI 影视工业化、分镜创作、逻辑循环、生产力与 LLM 提示词驱动设计的终极套件**

---

## 📖 简介
TrucyNodes 是一套为 AI 影视工作流量身定制的专业节点包。它打通了从剧本资产读取（Excel/TXT/DOCX）、按索引加载素材（图/音/视频）、高阶逻辑循环（For-Loop）到后期视频合成的全流程；并通过 **LLM Loader Trucy**（三种大脑装载器）→ **Skill Runner Trucy**（skill 执行器）/ **VLM Runner Trucy**（图文推理）与 **ref2v Trucy**（MiniMax H3 参考生视频）等模块，把「本地大模型出提示词 → 参考素材编码 → 采样出片」整条链收进一个节点包。它强调“导演思维”，通过精准的参数控制和算力优化，让 AI 创作从“抽卡”进化为“生产”。

**[🇺🇸 English Version](./README.md)**

---

### [2026-10-17] 执行节点大清整：VLM 通用标签 + 采样微调 + llama.cpp 提速控件
🏷️ **VLM Runner 标签改通用口径**——接入的图片在节点内部按 **图片1…图片8** 指代、视频按 **视频1** 指代，提示词要求模型分别描述每张图片。该节点的 H3/QWI 标签下拉已删除（它压根不进 Skill 家族工作流）；Chat / Prompt 的 Skill 家族标签逻辑保留不动。
🛡️ **媒体输入空值不崩全覆盖**——8 个图槽 + 1 个视频口，空置 / 上游被静音 / 零尺寸 / 坏路径 / 认不出的对象一律跳过记日志（视频模式下无可用的东西时报设计内的清晰错误），绝不抛原始异常、绝不发空提示词。
🎚️ **三个执行节点新增采样微调**（Chat / Prompt / VLM Runner）：`top_p` / `top_k` / `重复惩罚` / `seed` / `保留思考过程`——每项默认「不指定、不发」，老工作零行为变化。`top_p`/`seed` 是 OpenAI 标准请求字段（本地 + LM Studio + 远程都生效）；`top_k`/`重复惩罚` 是 llama.cpp 专有字段（本地 + LM Studio 生效，严格 API 没有，被拒自动去掉重试）。
⚡ **LLM Loader 新增 llama.cpp 提速控件**（参考社区最快的 llama-TE，仅本地 GGUF 生效）：KV 缓存 K/V 量化（`q8_0` 等，默认「不指定」= 原生 f16 不动）+ Flash Attention 三态开关（默认「不开启」= 不碰 llama.cpp 默认）。
🧹 Chat / Prompt 的旧版通用「图片」端口已删除（9 个编号图槽全覆盖，老工作流里连它的线需改一次）。

### [2026-10-16] 「大脑与参考」更新：LLM Loader + Skill Runner + VLM Runner + MiniMax H3 ref2v
🧠 **LLM Loader Trucy**（自 ComfyUI-TrucyLLM 合并）：大脑装载器——一个节点三种大脑（局域网LM Studio / 远程API / 本地GGUF）。它只装载大脑、本身不执行任何 Skill；**LLM** 输出端口同时喂给 **Skill Runner Trucy** 家族与 **VLM Runner Trucy** 节点。
🛠️ **Skill Runner Trucy**：真正的 skill 执行器家族——Skill Loader → Chat / Prompt (H3·QWI) → 卸载模型，附带 API预设地址簿与零打断质量层。
👁️ **VLM Runner Trucy**：无 skill 机制的图文推理——**最多 8 张图片或 1 个视频，图文互斥**。本地 GGUF 大脑直接收**视频文件本体**（Qwen-VL 经 llama.cpp mtmd + ffmpeg 原生读视频，带时间戳）；远程大脑 / 缺 ffmpeg / 原生发送失败时**自动退化为等距抽帧**。设计上**没有文本模式**——纯文本对话是 Chat 节点的活。
🎬 **ref2v Trucy**：MiniMax H3 Ref2VA 参考编码双形态——缓存层双节点（参考编码刻意不接提示词，只改提示词时蹭 ComfyUI 内置缓存跳过 VAE 重编码）+ 合并版单节点（提示词必失效，改节点内 LRU 自管缓存）。
🧹 清理：移除早已废弃的 Klein 编码节点与两个过时的 H3 预处理/提示词节点；README 按实际在册节点全量重写。

### [2026-07-03] 工业级生产管线整合：性能与稳定性里程碑
🎬 智能代理视频加载器 (TrucyVideoLoaderIndex)：新增专业级“代理媒体”流程。
降维打击：引入 FPS 抽帧（支持 4/8/12 关键帧抽样）与分辨率代理缩放（支持 128p-1280p），大幅降低视频输入对显存的冲击，完美适应 AI 推理负载。
智能冗余保护：加入索引越界防御——当索引超出范围时自动生成 1kHz 提示音，确保工作流永不中断。
🚀 增强版 LTX MSR 视频预处理：新增背景图智能识别逻辑，可自由选择任一 img 插槽作为空间锚点（Base Target），不仅适配 41 帧标准，同时兼容多种帧数分布，不再被原作者的硬编码所束缚。
🛠️ 生产级鲁棒性：所有桥接与逻辑节点全线集成 ExecutionBlocker 机制。现已实现下游节点的网页级 Mute/Bypass 主动干预，调试阶段彻底告别卡顿与报错。
🏗️ 架构大一统：完成了 Trucy 命名空间的全量升级与 Matrix 遗留代码清理。全套代码已实现模块化物理隔离。

### [2026-06-26] 导演剪辑版更新：极致的流程控制与性能榨取
🛡️ 全新节点：Trucy 图像直通桥接器 (6路/10路)：专为复杂影视分镜工作流设计的“理线神器”与“流程路由器”。
零显存开销：采用指针传递，不对图像张量做任何多余操作，不占用 1 字节额外内存。
物理级算力阻断：保留 disable_out 开关。开启“禁用输出”时，节点会在底层抛出 ExecutionBlocker 信号。所有连接在此通道后方的 KSampler 或视频合成节点将被直接物理阻断（不再报错或计算假图像），极大节省调试期的算力和时间！
🔢 文字转数字节点优化 (Text To Number)：去除了强制连线 (forceInput) 限制。现在你可以直接在节点上手打输入文字，节点依然会智能地为你同步输出 String、Int 和 Float。
✨ 代码洁癖级梳理：持续精简 image_adapter.py，确保界面清爽、逻辑硬核。

## 🚀 核心模块详述

**共 50 个节点。** ComfyUI 菜单分类：`TrucyNodes/Logic`、`/Image`、`/Toolkit`、`/Text`、`/Excel`、`/Audio`、`/Video`、`/LLM Loader`、`/Skill Runner`、`/VLM Runner`、`/ref2v`。

### 1. 逻辑与流程控制 (Logic 系列)
*   **Trucy For Loop (Start / End, 9路 / 2路)**: 逻辑核心。
    *   9路版支持 **9路同步变量通道**（value1-value9）+ 1路 Flow + 1路 Index；2路版为轻量场景准备。
    *   强大的范围解析：支持 `1-3, 5, 10-12` 这种复杂序列，带索引模式与步进。
    *   高效递归：在 ComfyUI 内部实现真正的图扩展循环。
*   **Trucy Any Switch (6路/10路)**: 任意类型多路选择器——LATENT / IMAGE / AUDIO / STRING / INT / FLOAT 通吃，一个节点收束所有类型分歧。
*   **Trucy Control Bridge**: 布尔控制桥。disable_out 触发 ComfyUI 原生 ExecutionBlocker，下游节点被物理阻断（不产假图、不烧算力）。
*   **Trucy Remote Toggle 6x6**: 按节点 ID 远程成组 Mute/Bypass——填 A/B 两组 ID 清单即可批量开关，不用满画布找节点。
*   **🚀 5-way Mute/Bypass Nodes-Remote**: 一个 master 整数按取值把执行分流到五个节点组。
*   **Trucy Frame & Seconds Converter**: 帧 ↔ 秒换算，多种舍入模式，INT + FLOAT 双输出。

### 2. 图像管线 (Image 系列)
*   **Trucy Image Loader by Index / Image Loader (6路)**: 目录 + 索引加载，越界有兜底；6路版一次装入排序连续的 6 张图。
*   **🚀 字符加载器 (String 6/10)**: 直接输入 ID（如 "X1"）或文件名，支持智能模糊匹配；空槽位自动占位，资产管理不再痛苦。
*   **🚀 图像直通桥接器 (6路/10路)**: 指针传递、零显存开销；每通道独立 disable_out 物理阻断。
*   **Trucy Image Size Adapter**: “分辨率桥梁”。专为 **1088p 转 1080p** 无损居中裁切/拉伸设计。
*   **🚀 资产网格拼图 (6/10)**: 极低显存占用的资产缩略图网格，支持标签与空位占位图。

### 3. 文本与数据工具箱 (Toolkit / Text 系列)
*   **🚀 文本拆分器 (6/10)**: 括号 + 分隔符拆分，或 **None (Direct Split)** 直拆模式。
*   **🚀 ID 提取器**: 从文本中“嗅探”ID（如 `X1`），支持搜索模式与剩余文本输出。
*   **🚀 字符切割刀 / 智能文本切割**: 文本手术刀。自定义左右符号，精确截取中间内容。
*   **🚀 文本符号嗅探器**: 从多槽位文本中提取符号与编号。
*   **🚀 文本清洗器**: 关键词移除 + 模糊清理，专治 LLM / Excel 的脏输出。
*   **🚀 文字转数字节点**: 手打输入文字，同步输出 String、Int、Float、Boolean。
*   **🚀 Doc-Loader-Trucy**: 绝对路径加载 TXT / MD / DOCX，编码自动识别。
*   **🚀 TXT Loader by Index**: 按索引批量读取 TXT 剧本，完美适配循环节点。
*   **🚀 Text Preview & Save**: 文本预览与智能保存。支持**自动编号递增**（防止覆盖）和**路径失效自动重定向**。
*   **🚀 Trucy Folder Iterator**: 按过滤模式遍历文件夹，把文件路径喂给下游。
*   **🚀 Trucy Dataset Saver**: 图像 + 文案配对存盘，数据集构建一条龙。

### 4. Excel 驱动分镜 (Excel 系列)
*   **TrucyExcelReader**: Excel 单格读取器。内置**智能数字提取**（正则逻辑），能从复杂的备注中抓取数值。
*   **TrucyExcelReader6 / TrucyExcelReader10**: 按行批量读 6/10 列——Excel 一行 = 循环里一个镜头。

### 5. 音视频合成 (Media 系列)
*   **TrucyAudioLoaderIndex**: 高效音频加载。支持 **自动重采样** (44.1k/48k) 和 **1kHz 提示音兜底**。
*   **🚀 Audio Detector & Padder**: 音频长度检测（秒/帧双输出）与补齐到目标长度。
*   **🚀 Empty Audio Generator**: 按秒或帧合成静音音频（conditioning 占位救星）。
*   **🚀 Save Audio**: 音频多格式落盘，支持重采样。
*   **TrucyVideoLoaderIndex**: 专业代理视频流程——FPS 抽帧、分辨率代理缩放、越界保护。
*   **TrucyVideoCombine**: FFmpeg 管道直通编码（注册在 VHS 分类下）。不产生垃圾文件，支持 MP4/WebP/GIF 及音频自动混流。

### 6. LLM Loader Trucy（大脑装载器）
装载三种大脑之一，从 **LLM** 端口输出。它本身不执行任何 Skill——同一个大脑既喂给 **Skill Runner Trucy** 家族（第 7 节），也喂给 **VLM Runner Trucy** 节点（第 8 节）。

*   **🚀 LLM Loader Trucy**：三种大脑一个下拉切换——
    *   **局域网LM Studio**（`http://<Mac-IP>:1234/v1`，默认 `gemma-4-e4b-it`）
    *   **远程API**：DeepSeek / OpenAI / 任何 OpenAI 兼容服务（`api_base` + `api_key` + `model`；只写域名如 `https://api.deepseek.com` 自动补 `/v1`）。**`model` 是必填自由文本框**——任意模型 ID 随手填，含中转站模型名（如 `gemini-3.1-flash-lite-preview`）；「API预设」选中只帮填、不锁死，之后随便改
    *   **本地GGUF**：本机显卡跑 `ComfyUI/models/LLM`（含子文件夹）下的 gguf，带 mmproj 视觉投影、`n_ctx` / `n_gpu_layers` / `n_batch` 与 Qwen3.8 系思考控制
    *   **本地专用提速控件（llama.cpp，参考社区最快的 llama-TE）**：「KV缓存K类型 / KV缓存V类型」（默认「不指定」= 不动 llama.cpp 原生 f16；`q8_0` 省显存，大模型+长上下文常常还更快）+「Flash Attention」三态开关（「不开启」= 不碰 llama.cpp 默认行为；「开启 / 关闭」= 显式覆盖）。**这两个是加载期参数，只对本地 GGUF 有意义**——LM Studio / 远程API 的等效调优请在各自界面设置

**API预设地址簿**：LLM 节点带「API预设」下拉 + 「＋ 保存为API预设」按钮，存于插件目录 `api_presets.json`（**本地明文含 Key，切勿外发整个插件目录**）。

### 7. Skill Runner Trucy（skill 执行器）
真正的 skill 执行器家族：**LLM Loader → Skill Loader → Chat / Prompt → 卸载模型**。

*   **🚀 Skill Loader Trucy**：扫描内置 `skills/`（及 `comfyUI-llama-TE/skills`，存在时自动兼容）；可固定选一个，也可交给大脑自动匹配。
*   **🚀 Skill Runner Trucy · Chat**：大脑 + Skill + 提示词 → 文本，带 **12 个参考素材槽位**（🖼️ 图1-9 / 🎵 音1-3）。空槽位跳过并记日志，绝不卡流水线。（旧版通用「图片」端口已删除——9 个编号图槽全覆盖，老工作流里连它的线需改一次。）
*   **🚀 Skill Runner Trucy · Prompt (H3/QWI)**：两套官方提示词 Skill 一个节点搞定——**H3**（MiniMax 视频提示词，`[Shot N]` 分镜 + 音效/配乐）与 **Qwen-Image-2.1**（图像提示词重写）。质量层只检查记日志、**零打断**（可选一次自动纠正，默认关）。
*   **🚀 Skill Runner Trucy · Unload Model**：采样前释放本地 GGUF 显存；把「上游」通配输入接到提示词节点输出即可固定执行顺序。
*   **采样微调**（Chat / Prompt / VLM Runner 三个执行节点都有，每项默认 = 「不指定、不发」，老工作流零行为变化）：`top_p` / `seed` 是 OpenAI 标准请求字段（本地 GGUF / LM Studio / 远程API 都按请求生效）；`top_k` / `重复惩罚` 是 llama.cpp 专有字段（本地 GGUF 与 LM Studio 生效，严格 OpenAI 兼容 API 没有这俩字段——被 400 拒绝时自动去掉重试，不打断流水线）；`保留思考过程` 仅本地 GGUF 思考型模型生效。详见第 8 节。
*   **推理后自动卸载**（Chat / Prompt / VLM Runner 三个执行节点都有，默认关）：仅本地 GGUF 生效，本次推理完成后自动卸载模型释放显存（下次推理重新加载，略慢）。多个执行节点共用一个 LLM Loader 时建议只挂在最后一个上；也可以继续用专用的「卸载模型」节点。远程API / 局域网LM Studio 下无效（模型不在本机）。

### 8. VLM Runner Trucy（图像 / 视频推理）
纯**系统提示词 + 用户提示词 + 图片或视频 → 文本**——**不经过 Skill Loader**（与 Skill Runner 家族的唯一区别即此）。形态对标 `comfyUI-llama-TE` 的 `QwenTE图像推理`，并扩展了视频输入。

*   **🚀 VLM Runner Trucy**：LLM（三种大脑任意）+「输入模式」（**图片 / 视频——互斥，绝不并用**）+ 系统/用户提示词 → 文本：
    *   **图片模式**：🖼️ 参考图1-8。节点内部用**通用标签 图片1…图片8** 指代（本节点不进任何 Skill 家族工作流，H3/QWI 标签规范与它无关），并在提示词里要求模型**分别描述每张图片**。槽位号保留——空置/被静音/损坏的槽位跳过并记日志，绝不重排编号
    *   **视频模式**：🎬 一个视频（接 LoadVideo 输出），内部标签 **视频1**。本地 GGUF 大脑直接收**视频文件本体**——llama.cpp 的 mtmd 通过 ffmpeg 子进程解码（需 PATH 里有 `ffmpeg` + `ffprobe`，常见 ComfyUI 整合包都自带），Qwen-VL 以约 4 fps 原生读视频并带时间戳。远程大脑、缺 ffmpeg 或原生发送失败时**自动退化为等距抽帧**（「视频抽帧数」，默认 8）按图片发送——每帧保留时间戳，时间维度的分析在退化通道下依然成立
    *   两边都接了？由模式下拉决定发给大脑的内容，另一边忽略并记一行日志
*   **所有媒体输入都有空值不崩保护**：8 个图槽 + 1 个视频口，空置 / 上游被静音 / 零尺寸 / 坏路径 / 认不出的对象一律跳过并记日志（视频模式下无可用的东西时报设计内的清晰错误），绝不把原始异常抛上流水线，更绝不发空提示词
*   **设计上没有文本模式**——纯文本对话请用 Skill Runner 的 Chat 节点。某模式下什么都没接时报错说清楚，绝不发空提示词。
*   **采样微调**（三个执行节点同款，每项默认 = 「不指定、不发」，老工作流零行为变化）：
    *   `top_p` / `seed`——**OpenAI 标准请求字段**：本地 GGUF、LM Studio、远程API 都按请求生效
    *   `top_k` / `重复惩罚`——**llama.cpp 专有字段**：本地 GGUF 与 LM Studio 生效；严格 OpenAI 兼容 API 没有这俩字段（设了多被忽略；被 400 拒绝时节点自动去掉再重试一次，流水线不中断）
    *   `保留思考过程`——仅本地 GGUF 思考型模型：输出里保留 `<think>` 思考块（默认剥掉只留正式回答）。远程推理模型的思考由 API 单独返回，本开关无效
    *   远程大脑除 temperature / top_p 之外的等效调优，请在 LM Studio / API 提供方界面设置
*   **推理后自动卸载**（默认关）：仅本地 GGUF 生效，推理完成后自动卸载模型释放显存（下次推理重新加载，略慢）；远程大脑下无效。
*   **注意**：媒体能否真到模型取决于大脑——本地 GGUF 需选 mmproj 投影；DeepSeek API 现已支持图片（返回模型名为 `deepseek-flash`），视频模式走抽帧退化。

### 8. H3 ref2v Trucy（MiniMax H3 参考生视频）
官方 MiniMax H3 Ref2VA 管线的参考 conditioning，双形态任意选（参考编码数学逐位一致，单测对冲）：

*   **🚀 H3 ref2v Trucy · 参考编码（缓存层）**：参考图/音频 + 双 VAE → AV latent + ref_data。**刻意没有 prompt 输入**——只改提示词时 ComfyUI 内置缓存直接跳过 VAE 重编码。
*   **🚀 H3 ref2v Trucy · 提示词编码（出口）**：clip + prompt + 上游 ref_data → positive conditioning；提示词变动时只有它重跑。
*   **🚀 H3 ref2v Trucy · 参考转视频（合并版）**：单框形态，连线同官方 `MiniMaxH3ReferenceToVideo`；因含 prompt 缓存必失效，改**节点内 LRU 自管缓存**（每槽位内容 sha1 + VAE 实例身份 + 弱引用存活校验）。

两种形态都复用官方 helper（`_resize` / `_encode_ref_audio` / `_empty_av_latent`），遵循官方 `<Picture N>` / `<Audio N>` 标签规范（我们槽位 1 起编号 vs 官方 `ref_image_0` 0 起——端口名只是 kwargs 键，对结果零影响），全链路空值安全。视频参考端口已按决定摘除（确需时用官方 `MiniMaxH3ReferenceToVideo`，仍在册；收集后端休眠于 `trucy_media.py`）。

---

## 🛠️ 安装与推送

1. 在 `custom_nodes` 目录下运行：
   `git clone https://github.com/gnrsbassoutlook/ComfyUI-TrucyNodes.git`
2. 重启 ComfyUI。
3. 推送本地更新：
   ```bash
   git add .
   git commit -m "feat: complete rebranding and feature integration"
   git push origin main
   ```

> ⚠️ push 前注意：`api_presets.json`（本地预设地址簿，含明文 API Key）与
> `__pycache__/` 已被 `.gitignore` 排除，不会误推上仓库。

### 依赖

推荐用 **ComfyUI Manager** 安装——安装时会自动执行
`pip install -r requirements.txt`；手动安装则在 ComfyUI 的 python
环境下执行同一命令。

| 依赖 | 是否必需 | 说明 |
|---|---|---|
| `requests` | ✅ 自动 | 远程 LLM / API 预设 |
| `openpyxl` | ✅ 自动 | Excel 读取节点 |
| ComfyUI-Impact-Pack | 可选 | Any-Switch / Control Bridge 节点依赖；未装仅跳过这 4 个节点，其余节点不受影响 |
| `llama-cpp-python`（CUDA/Metal） | 可选 | 仅「本地 GGUF」LLM 模式需要 |

其余依赖（torch / numpy / PIL / torchaudio）均为 ComfyUI 环境自带。

**本地 GGUF 模式**需要 `llama-cpp-python`——无需本地编译，直接去
[JamePeng/llama-cpp-python releases](https://github.com/JamePeng/llama-cpp-python/releases)
下载预编译 wheel（CUDA 12.4 / 12.6 / 12.8 / 13.1，Python 3.10~3.14，
Windows / Linux x64，以 releases 页面实际发布为准），选对应 CUDA +
Python 版本 `pip install` 即可。也支持源码编译（见 `requirements.txt`
内注释）。

---

## 🧭 主流模型参数推荐

> **先记住一条分工**：`n_ctx`（上下文长度）、思考模式、推理强度、`n_gpu_layers`、`n_batch`、KV 缓存量化、Flash Attention、mmproj 投影——**只有「本地 GGUF」在节点里调**（它们是 llama.cpp 加载期参数）；LM Studio 与远程 API 的这些参数在服务端决定（LM Studio 加载界面 / API 提供商）。
> **请求级采样参数**（`temperature` / `max_tokens` / `top_p` / `seed`）是 OpenAI 标准请求字段，三种大脑都能按请求带；`top_k` / `重复惩罚` 是 llama.cpp 专有字段，本地 GGUF 与 LM Studio 生效，严格 OpenAI 兼容 API 没有（被拒自动忽略重试）。
> **Qwen 官方采样推荐**：思考开启 `temperature=1.0 / top_p=0.95 / top_k=20`；思考关闭 `temperature=0.7 / top_p=0.80 / top_k=20`。本地 GGUF 现在可直接在节点上精确设置；LM Studio / 远程 API 侧请在其界面同步。

### 本地 GGUF（LLM Loader 的「本地GGUF」区）

| 模型 | n_ctx | 思考模式 | 推理强度 | mmproj | 说明 |
|---|---|---|---|---|---|
| Qwen3.8-27B IQ2_XXS（16G 显卡，本项目实测配置） | 16384 | 开启 | medium | 看图必须 | 5060Ti 16G 日常档；xhigh 在 IQ2 量化下收益小、明显变慢 |
| Qwen3.8-27B Q4_K_M 以上（24G+ 显卡） | 32768 | 开启 | xhigh | 看图必须 | 量化保住后 xhigh 才划算 |
| Qwen3-VL / Qwen3.5-VL / Qwen3.6-VL 系列 | 16384~32768 | 按模型（Qwen3-VL 走 force_reasoning） | — | 必须 | VL 系不装 mmproj 看不了图 |
| 7B~14B 小模型 | 8192 | 关闭或 low | low | 可选 | 快但格式漂移多，适合打标/粗排，别碰 H3 大 skill |

本地通用规则：

- H3 大 skill 上下文至少 8192；每张 1280 边参考图约吃掉 1K+ token，3 张图 + skill 正文轻松过 8K——**n_ctx 开 16384 更稳**
- `n_gpu_layers=-1`（全上 GPU）；爆显存按这个顺序救：调小它 → 降 `n_ctx` → 把「参考图最长边」降到 768/512
- `n_batch` 512 是速度/显存平衡点，爆显存可降到 256
- **提速控件（学 llama-TE，仅本地 GGUF）**：「KV缓存K/V类型 = q8_0」省显存，大模型+长上下文常常还更快（质量代价很小；默认「不指定」保持 llama.cpp 原生 f16，零行为变化）；「Flash Attention」三态：不开启 = 不碰 llama.cpp 默认，开启/关闭 = 显式覆盖。两者都是加载期参数，改动会触发一次模型重载
- 推理完就让出显存：执行节点（Chat / Prompt / VLM Runner）开「**推理后自动卸载**」（默认关，仅本地 GGUF 生效；下次推理会重新加载模型，略慢），或继续用专用的「卸载模型」节点

### 局域网 LM Studio

| 模型 | 服务端 n_ctx | 节点 temperature | 节点 max_tokens | 说明 |
|---|---|---|---|---|
| gemma-4-e4b-it | ≥ 16384（8192 会思考爆量） | 0.7 | 4096 | 会读约束但不收敛思考；生产建议换 Qwen 系 |
| qwen3-vl / qwen3 系 | 16384 | 0.7（思考开则 1.0） | 4096 | 轻量看图/打标好用 |
| 其他 | 模型上限的 1/4~1/2 | 0.7 | 4096 | n_ctx 与思考开关在 LM Studio 加载界面设，不进 ComfyUI 节点 |

### 远程API

| 模型 | temperature | max_tokens | 说明 |
|---|---|---|---|
| deepseek-chat | 0.7（H3/QWI 结构化 0.3~0.5） | 4096~8192 | 已支持图片；上下文服务端管，节点只调采样 |
| deepseek-reasoner | 保持默认（思考型自控） | ≥ 8192 | 思考也占 max_tokens，给小了会被截断 |
| gpt-4o / gpt-4.1 等 | 0.7 | 4096~8192 | 通用；部分新模型只支持推理强度档位，按模型文档 |
| gemini-\*-flash-lite（中转） | 0.7 | 4096 | 轻量快；看图可用，细节偶有误判 |
| 中转站其他模型 | 0.7 | 4096 | 以站点文档为准；用「API预设」下拉一键切换 |

### 按任务选采样（三个执行节点通用）

| 任务 | temperature | max_tokens | 说明 |
|---|---|---|---|
| H3 视频提示词 | 0.3~0.5 | ≥ 4096 | 结构化输出要稳，低温防分镜乱跑 |
| QWI 图像提示词 | 0.5~0.7 | ≥ 4096 | — |
| VLM 图片/视频描述 | 0.3~0.5 | 2048~4096 | 描述要准，别让模型发挥 |
| Chat 创意对话 | 0.8~1.0 | 4096 | 越发散越有灵感，也越容易跑题 |

### 控件速查（补课向）

| 控件 | 大白话 | 什么时候调 |
|---|---|---|
| `n_ctx` | 模型的工作台：skill 正文 + 图片 token + 生成全摊在这块台面上 | 报 context exceeded 就加大，或缩图/缩 n_ctx |
| 思考模式 | 思考型模型的开关：开 = 质量高但慢 | H3 这种格式严的活建议开 |
| 推理强度 | 思考开启才有效：xhigh 最慢最细 / medium 均衡 / low 最快 | IQ2 量化用 medium 就够 |
| `n_gpu_layers` | 模型有多少层放显卡：-1 全放，0 纯 CPU | 爆显存往下调（如 20） |
| `n_batch` | 提示词一次吞多少 token：越大越快越吃显存 | 爆显存降到 256 |
| KV缓存K/V类型 | （仅本地 GGUF，llama.cpp）KV 缓存存多精细：q8_0 省显存常常还更快 | 大模型/长 ctx 上 q8_0；默认「不指定」= 原生 f16 |
| Flash Attention | （仅本地 GGUF，llama.cpp）注意力计算加速，开了通常更快更省 | 先试「开启」；环境别扭就「关闭」；默认「不开启」不动原生 |
| `temperature` | 越高越发散：0.3 稳定复现，1.0 创意发散 | 见上方任务表 |
| `max_tokens` | 一次最多吐多少 token；思考型模型的思考也占额度 | 输出被截断就加大 |
| `top_p` | 每步只从概率前 top_p 的候选里抽（OpenAI 标准字段，本地/LM Studio/远程都生效） | Qwen 参考：思考 0.95 / 非思考 0.80；0 = 不指定 |
| `top_k` | 每步只留概率前 k 个候选（llama.cpp 专有：本地 + LM Studio 生效） | Qwen 参考：20；0 = 不指定 |
| `重复惩罚` | >1 治复读机（llama.cpp 专有：本地 + LM Studio 生效） | 模型复读时试 1.05~1.15；1.0 = 不指定 |
| `seed` | 固定随机种子，同样输入结果可复现（OpenAI 标准字段） | A/B 对比提示词改动时固定；0 = 不指定（随机） |
| 保留思考过程 | 输出里保留模型的 `<think>` 思考块（仅本地 GGUF 思考型模型） | 想检查模型思路时开；默认关 |
| 参考图最长边 | 发图前缩到多小 | 小 ctx 时 768/512 防挤爆 |
| 推理后自动卸载 | 推理完把模型扔出显存（下次推理重新加载，略慢） | 后面要出图/采样抢显存时开；远程大脑下无效 |

## 📄 License
MIT License
