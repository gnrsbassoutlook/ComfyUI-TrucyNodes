# 🎬 ComfyUI-TrucyNodes (翠西节点包)
**专为 AI 影视工业化、分镜创作、逻辑循环、生产力与 LLM 提示词驱动设计的终极套件**

---

## 📖 简介
TrucyNodes 是一套为 AI 影视工作流量身定制的专业节点包。它打通了从剧本资产读取（Excel/TXT/DOCX）、按索引加载素材（图/音/视频）、高阶逻辑循环（For-Loop）到后期视频合成的全流程；并通过 **Skill Runner Trucy**（三种大脑 + Skill 执行器）与 **ref2v Trucy**（MiniMax H3 参考生视频）两大模块，把「本地大模型出提示词 → 参考素材编码 → 采样出片」整条链收进一个节点包。它强调“导演思维”，通过精准的参数控制和算力优化，让 AI 创作从“抽卡”进化为“生产”。

**[🇺🇸 English Version](./README.md)**

---

### [2026-10-16] 「大脑与参考」更新：LLM Skill Runner + MiniMax H3 ref2v
🧠 **Skill Runner Trucy**（自 ComfyUI-TrucyLLM 合并）：技能执行器节点族——LLM（局域网LM Studio / 远程API / 本地GGUF）→ Skill加载器 → 对话 / 提示词（H3·QWI）→ 卸载本地模型。大脑输出端口更名为 **LLM**。附带 API预设地址簿与零打断质量层。
🎬 **ref2v Trucy**：MiniMax H3 Ref2VA 参考编码双形态——缓存层双节点（参考编码刻意不接提示词，改提示词时蹭 ComfyUI 内置缓存零重算）+ 合并版单节点（提示词必失效，改节点内 LRU 自管缓存）。
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

**共 49 个节点。** ComfyUI 菜单分类：`TrucyNodes/Logic`、`/Image`、`/Toolkit`、`/Text`、`/Excel`、`/Audio`、`/Video`、`/Skill Runner`、`/ref2v`。

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

### 6. Skill Runner Trucy（LLM + Skill 执行器）
把任何 OpenAI 兼容大脑变成节点驱动的提示词工厂。大脑节点的输出端口叫 **LLM**，直插各 Skill 执行节点。

*   **🚀 Skill Runner Trucy · LLM**：三种大脑一个下拉切换——
    *   **局域网LM Studio**（`http://<Mac-IP>:1234/v1`，默认 `gemma-4-e4b-it`）
    *   **远程API**：DeepSeek / OpenAI / 任何 OpenAI 兼容服务（`api_base` + `api_key` + `model`；只写域名如 `https://api.deepseek.com` 自动补 `/v1`）。**`model` 是必填自由文本框**——任意模型 ID 随手填，含中转站模型名（如 `gemini-3.1-flash-lite-preview`）；「API预设」选中只帮填、不锁死，之后随便改
    *   **本地GGUF**：本机显卡跑 `ComfyUI/models/LLM`（含子文件夹）下的 gguf，带 mmproj 视觉投影、`n_ctx` / `n_gpu_layers` / `n_batch` 与 Qwen3.8 系思考控制
*   **🚀 Skill Runner Trucy · Skill Loader**：扫描内置 `skills/`（及 `comfyUI-llama-TE/skills`，存在时自动兼容）；可固定选一个，也可交给大脑自动匹配。
*   **🚀 Skill Runner Trucy · Chat**：大脑 + Skill + 提示词 → 文本，带 **12 个参考素材槽位**（🖼️ 图1-9 / 🎵 音1-3）。空槽位跳过并记日志，绝不卡流水线。
*   **🚀 Skill Runner Trucy · Prompt (H3/QWI)**：两套官方提示词 Skill 一个节点搞定——**H3**（MiniMax 视频提示词，`[Shot N]` 分镜 + 音效/配乐）与 **Qwen-Image-2.1**（图像提示词重写）。质量层只检查记日志、**零打断**（可选一次自动纠正，默认关）。
*   **🚀 Skill Runner Trucy · Unload Model**：采样前释放本地 GGUF 显存；把「上游」通配输入接到提示词节点输出即可固定执行顺序。

**API预设地址簿**：LLM 节点带「API预设」下拉 + 「＋ 保存为API预设」按钮，存于插件目录 `api_presets.json`（**本地明文含 Key，切勿外发整个插件目录**）。

### 7. Vision Trucy（图像推理）
纯**系统提示词 + 用户提示词 + 图片 → 文本**——**不经过 Skill Loader**（与 Skill Runner 家族的唯一区别即此）。形态对标 `comfyUI-llama-TE` 的 `QwenTE图像推理`，同样 **8 个图片输入**。

*   **🚀 Vision Trucy · 图像推理**：LLM（三种大脑任意）+「输入模式」（图片/文本）+ 系统/用户提示词 + 🖼️ 参考图1-8（+ 🎵 参考音频1-3）→ 文本。适合批量图片打标/描述、参考素材分析（如把三视图/场景图喂给 H3 ref2v 管线前先过一遍）、或任何视觉问答——提示词框直达，零 Skill 机制。
*   复用整套媒体层：槽位空值安全、`<Picture N>` / `<imageN>` 标签（自动识别，H3 兜底）、质量层只记日志不打断。
*   **注意**：图片能否真到模型取决于大脑——本地 GGUF 需选 mmproj 投影；DeepSeek API 现已支持图片（返回模型名为 `deepseek-flash`）；纯文本模型在图片模式下会报错，把「输入模式」切到文本即可。

### 8. H3 ref2v Trucy（MiniMax H3 参考生视频）
官方 MiniMax H3 Ref2VA 管线的参考 conditioning，双形态任意选（参考编码数学逐位一致，单测对冲）：

*   **🚀 ref2v Trucy · 参考编码（缓存层）**：参考图/音频 + 双 VAE → AV latent + ref_data。**刻意没有 prompt 输入**——只改提示词时 ComfyUI 内置缓存直接跳过 VAE 重编码。
*   **🚀 ref2v Trucy · 提示词编码（出口）**：clip + prompt + 上游 ref_data → positive conditioning；提示词变动时只有它重跑。
*   **🚀 ref2v Trucy · 参考转视频（合并版）**：单框形态，连线同官方 `MiniMaxH3ReferenceToVideo`；因含 prompt 缓存必失效，改**节点内 LRU 自管缓存**（每槽位内容 sha1 + VAE 实例身份 + 弱引用存活校验）。

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

## 📄 License
MIT License
