# 🎬 ComfyUI-TrucyNodes (翠西节点包)
**专为 AI 影视工业化、分镜创作、逻辑循环及生产力设计的终极套件**

---

## 📖 简介
TrucyNodes 是一套为 AI 影视工作流量身定制的专业节点包。它打通了从剧本资产读取（Excel/TXT）、高精度资产溶图（Flux2-Klein）、高阶逻辑循环（For-Loop）到后期视频合成的全流程。它强调“导演思维”，通过精准的参数控制和算力优化，让 AI 创作从“抽卡”进化为“生产”。

**[🇺🇸 English Version](./README.md)**

---

## 🚀 核心模块详述

### 1. 高精度视觉融合 (Klein 系列)
专为 **Flux2-Klein** 模型优化，支持最多 10 张图片（人物、道具、场景）同时注入。
*   **TrucyKleinEncode**: 
    *   **Follow Node (W/H)**: 🚀 **极致画质**。所有资产全画幅对齐，RSA 自动禁用，确保 1:1 物理坐标精度。
    *   **Use RSA Scaling**: ⚡ **加速模式**。仅基准图保持全分辨率，其余资产按 **RSA (参考图面积)** 缩放，采样速度翻倍。
    *   **基准目标 (Base Target)**: 自由指定任意 img 接口作为底图输出，支持接入 `base_mask` 精准控制站位。

### 2. 高阶递归循环 (Logic 系列)
*   **TrucyForLoop (Start / End)**: 逻辑核心。
    *   支持 **9路同步变量通道**（value1-value9）+ 1路 Flow + 1路 Index。
    *   强大的范围解析：支持 `1-3, 5, 10-12` 这种复杂序列。
    *   高效递归：在 ComfyUI 内部实现真正的图扩展循环。

### 3. 工业工具箱 (Toolkit 系列)
*   **🚀 字符加载器 (String 5/10)**: 直接输入 ID（如 "X1"）或文件名，支持智能模糊匹配，资产管理不再痛苦。
*   **🚀 文本拆分器 (5/10)**: 新增 **None (Direct Split)** 模式。不再强制要求括号，直接用分隔符（| - #）拆分文本。
*   **🚀 ID 提取器**: 从文本中“嗅探”ID。已升级支持 **2位字符 ID**（如 `X1`），兼容性更强。
*   **🚀 字符切割刀**: 文本手术刀。自定义左右符号，精确截取中间内容。
*   **🚀 资产网格拼图**: 生成极低显存占用的资产缩略图列表。

### 4. 智能数据处理 (Data 系列)
*   **TrucyExcelReader**: Excel 脚本加载器。内置**智能数字提取**（正则逻辑），能从复杂的备注中抓取数值。
*   **TrucyImageAdapter**: “分辨率桥梁”。专为 **1088p 转 1080p** 无损居中裁切设计。
*   **TrucyTxtBatchLoader**: 按索引批量读取 TXT 剧本，完美适配循环节点。
*   **TrucyTxtPreviewAndSave**: 文本预览与智能保存。支持**自动编号递增**（防止覆盖）和**路径失效自动重定向**（自动存入文档文件夹）。

### 5. 音视频合成 (Media 系列)
*   **TrucyAudioLoaderIndex**: 高效音频加载。支持 **自动重采样** (44.1k/48k) 和 **1kHz 提示音兜底**（索引超出时发出“哔”音提醒）。
*   **TrucyVideoCombine**: 采用 FFmpeg 管道技术。内存直通，不产生垃圾文件。支持 MP4/WebP/GIF 及音频自动混流。

---

## 🛠️ 安装与推送

1. 在 `custom_nodes` 目录下运行：
   `git clone https://github.com/gnrsbassoutlook/ComfyUI-TrucyNodes.git`
2. 推送本地更新：
   ```bash
   git add .
   git commit -m "feat: complete rebranding and feature integration"
   git push origin main