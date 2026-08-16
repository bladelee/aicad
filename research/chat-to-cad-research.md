# Chat-to-CAD & 自然语言驱动 CAD 开源项目调研报告

> 调研日期: 2026-08-08
> 数据来源: GitHub API, Hacker News (Algolia), 项目官网

---

## 目录

1. [GitHub 上的 Text-to-CAD / Chat-to-CAD 项目](#1-github-上的-text-to-cad--chat-to-cad-项目)
2. [OpenSCAD 方案](#2-openscad-方案)
3. [AutoCAD AutoLISP / Script 方案](#3-autocad-autolisp--script-方案)
4. [CAD API as a Service](#4-cad-api-as-a-service)
5. [Python CAD 库](#5-python-cad-库)
6. [MCP (Model Context Protocol) CAD 项目](#6-mcp-model-context-protocol-cad-项目新兴趋势)
7. [学术/研究项目](#7-学术研究项目)
8. [Hacker News 讨论热度](#8-hacker-news-讨论热度)
9. [技术路线对比总结](#9-技术路线对比总结)

---

## 1. GitHub 上的 Text-to-CAD / Chat-to-CAD 项目

### 1.1 核心项目（按 Star 数排序）

| 项目 | ★ Stars | 语言 | License | 最后更新 | 特点 |
|------|---------|------|---------|----------|------|
| **earthtojake/text-to-cad** | 13,067 | JavaScript | MIT | 2026-08-08 | CAD/CAE/CAM agent skills 库，最活跃项目 |
| **Adam-CAD/CADAM** | 4,950 | TypeScript | GPL v3 | 2026-08-07 | 开源 text-to-CAD Web 应用，使用 OpenSCAD+WASM |
| **SadilKhan/Text2CAD** | 456 | Python | Other | 2026-08-07 | NeurIPS'24 Spotlight，从文本生成顺序 CAD 设计 |
| **Pan-Chera/Multi-Agent-CAD** | 449 | Python | MIT | 2026-08-08 | 多智能体框架，使用 build123d + langgraph |
| **KittyCAD/text-to-cad-ui** | 295 | Svelte | MIT | 2026-07-27 | Zoo Text-to-CAD API 的轻量 UI |
| **forgent3d/forgent3d-desktop** | 229 | TypeScript | - | 2026-08-01 | AI 生成 3D 模型的桌面应用 |
| **EESJGong/Graph-CAD** | 136 | Python | - | 2026-07-20 | 图表示学习的 Text-to-CAD |
| **Text-to-CadQuery/Text-to-CadQuery** | 111 | Python | - | 2026-08-04 | 文本生成 CadQuery Python 代码 |

#### 详细分析

**① earthtojake/text-to-cad** ★13,067
- **描述**: A library of agent skills for CAD, CAE and CAM
- **语言**: JavaScript
- **主页**: https://www.texttocad.dev
- **活跃度**: 极高（2026年8月仍在更新，1378 forks，14 open issues）
- **创建时间**: 2026-04-22
- **特点**: 这是目前 star 数最高的 text-to-CAD 项目，定位为 CAD/CAE/CAM 的 agent skills 库
- **HN 热度**: 186 points, 48 comments (2026-05-01)

**② Adam-CAD/CADAM** ★4,950
- **描述**: CADAM is the open source text-to-CAD web application
- **语言**: TypeScript
- **Topics**: agents, ai, ai-agents, cad, llms, openscad, react, robotics, stl, text-to-cad, wasm
- **主页**: https://adam.new/cadam
- **License**: GPL v3
- **创建时间**: 2025-09-01
- **特点**: 
  - YC W25 公司 (Adam) 的开源项目
  - 使用 OpenSCAD 作为后端 CAD 引擎，通过 WASM 在浏览器运行
  - 完整的 Web 应用，支持文本到 3D 模型生成
  - HN 上有两次热门帖子：开源公告 (179pts) 和 Launch HN (215pts, 97 comments)

**③ SadilKhan/Text2CAD** ★456
- **描述**: [NeurIPS'24 Spotlight] Text2CAD: Generating Sequential CAD Designs from Beginner-to-Expert Level Text Prompts
- **语言**: Python
- **Topics**: 3d, brep, cad, dataset, deepcad, generation, neurips, transformer
- **主页**: https://sadilkhan.github.io/text2cad-project/
- **特点**: 学术项目，NeurIPS 2024 Spotlight 论文，从文本提示生成顺序 CAD 操作序列

**④ Pan-Chera/Multi-Agent-CAD (MAC)** ★449
- **描述**: A decoupled multi-agent framework for text-to-CAD generation via constrained test-time compute
- **语言**: Python
- **Topics**: build123d, cad, langgraph, llm-agent, multi-agent, opencascade, qwen, step, text-to-cad
- **创建时间**: 2026-07-30 (非常新)
- **特点**: 
  - 使用 **build123d** (Python CAD 库) 作为后端
  - 基于 **LangGraph** 的多智能体架构
  - 使用 **Qwen** 模型
  - 输出 STEP 文件
  - 通过约束测试时计算实现可控生成

**⑤ KittyCAD/text-to-cad-ui** ★295
- **描述**: A lightweight UI for interacting with the Zoo Text-to-CAD API
- **语言**: Svelte/SvelteKit
- **License**: MIT
- **创建时间**: 2023-10-18
- **特点**: Zoo (zoo.dev) 官方的 Text-to-CAD API 前端 UI

### 1.2 LLM + CAD 生成工具

| 项目 | ★ Stars | 语言 | 特点 |
|------|---------|------|------|
| **ghbalf/freecad-ai** | 420 | Python | FreeCAD AI 工作台，自然语言生成 3D 模型，支持 OpenAI/Anthropic/Ollama/MCP |
| **FreedomIntelligence/BlenderLLM** | 280 | Python | 专为 CAD 脚本生成设计的 LLM，在 Blender 中渲染 |
| **filaPro/cad-recode** | 251 | Python | ICCV2025，从点云逆向工程 CAD 代码，使用 CadQuery + Qwen2 |
| **OpenOrion/CQAsk** | 185 | Python | 开源 LLM CAD 生成工具，使用 CadQuery |
| **col14m/cadrille** | 169 | Python | ICLR2026，多模态 CAD 重建，使用 CadQuery + Qwen2-VL |
| **NiJingzhe/SimpleCADAPI** | 80 | Python | 命令式 CAD API，专为 LLM 设计 |
| **dimitrismallis/CAD-Assistant** | 77 | Python | ICCV2025，工具增强 VLLM 作为通用 CAD 任务求解器 |

#### 重点分析

**ghbalf/freecad-ai** ★420
- **描述**: AI-powered assistant workbench for FreeCAD — generate 3D models from natural language
- **Topics**: addon, ai, anthropropic, cad, freecad, freecad-addon, llm, mcp, ollama, openai, python
- **创建时间**: 2026-02-20
- **License**: LGPL v2.1
- **特点**: 
  - FreeCAD 插件形式，直接集成到 FreeCAD 工作台
  - 支持 OpenAI, Anthropic (Claude), Ollama (本地模型)
  - 支持 MCP (Model Context Protocol)
  - 从自然语言生成 3D 模型

**OpenOrion/CQAsk** ★185
- **描述**: the open source llm cad generation tool
- **语言**: Python
- **License**: MIT
- **特点**: 使用 CadQuery 作为 CAD 后端，LLM 生成 CadQuery Python 代码

**NiJingzhe/SimpleCADAPI** ★80
- **描述**: A command style api to build CAD model, LLM friendly
- **特点**: 专门为 LLM 友好设计的命令式 CAD API，降低 LLM 生成 CAD 代码的难度

---

## 2. OpenSCAD 方案

### 2.1 OpenSCAD 基础能力

OpenSCAD 是纯脚本驱动的 3D CAD 软件，非常适合 LLM 生成代码。

**DXF 导出能力** (来自 OpenSCAD README):
> OpenSCAD 支持两种建模方式：1) 实体几何 (CSG)；2) 2D 轮廓拉伸。DXF 文件用作 2D 轮廓的数据交换格式。除了用于拉伸的 2D 路径外，还可以从 DXF 文件读取设计参数。OpenSCAD 还可以读取和创建 STL 和 OFF 格式的 3D 模型。

- ✅ **支持 DXF 导入/导出** (2D 轮廓)
- ✅ **支持 STL 导出** (3D 模型)
- ✅ **支持 SVG 导出** (2D)
- ✅ **纯脚本驱动**，LLM 友好
- ✅ **开源免费** (GPL v3)
- ⚠️ 不支持直接 DWG 格式
- ⚠️ 2D 功能有限，主要用于 2D 轮廓拉伸为 3D

### 2.2 OpenSCAD + AI 项目

| 项目 | ★ Stars | 语言 | 特点 |
|------|---------|------|------|
| **zacharyfmarion/openscad-studio** | 192 | TypeScript | AI 辅助 OpenSCAD 编辑器 (macOS)，支持 2D/3D 设计 |
| **KrishKrosh/ScadLM** | 22 | Jupyter | 开源 agentic AI CAD 生成，基于 OpenSCAD |
| **format37/openscad-mcp** | 12 | Python | OpenSCAD MCP 服务器，LLM 组合和渲染 OpenSCAD 脚本 |
| **levkropp/ClawSCAD** | 12 | JavaScript | OpenSCAD + Claude Code，带检查点分支 |
| **caseyhartnett/Torrify** | 9 | TypeScript | AI 辅助桌面应用，参数化 3D CAD |
| **Kevoyuan/AgentSCAD** | 6 | TypeScript | AI 原生 CAD agent，自然语言转 OpenSCAD |
| **jabberjabberjabber/openscad-mcp** | 2 | Python | LLM 创建 OpenSCAD 模型的 MCP 服务器 |
| **atx/OpenSCAD-Bench** | 1 | OpenSCAD | OpenSCAD LLM 基准测试 |
| **zion379/openscad-agent** | 0 | OpenSCAD | LLM-to-CAD agent，英文转 OpenSCAD |

#### 重点分析

**zacharyfmarion/openscad-studio** ★192
- **描述**: Create 2D and 3D designs with AI
- **语言**: TypeScript
- **Topics**: 3d, 3d-printing, ai, ide, mac-app, openscad, wasm
- **主页**: https://openscad-studio.pages.dev/
- **License**: GPL v2
- **特点**: macOS 原生应用，使用 WASM 运行 OpenSCAD，AI 辅助 2D/3D 设计

**KrishKrosh/ScadLM** ★22
- **描述**: Open source agentic AI CAD generation built on OpenSCAD
- **特点**: 使用 AI agent 自动生成和迭代 OpenSCAD 代码

**levkropp/ClawSCAD** ★12
- **描述**: AI-powered 3D CAD — OpenSCAD + Claude Code with checkpoint branching
- **特点**: 结合 Claude Code，支持检查点分支（版本管理）

### 2.3 OpenSCAD 作为 LLM CAD 后端的优势

1. **语法简单**: 函数式 DSL，比 Python CAD 库更简洁
2. **确定性**: 纯函数式，相同输入相同输出
3. **可验证**: 代码可直接编译渲染验证
4. **轻量**: 无需 GUI，命令行即可运行
5. **WASM 支持**: 可在浏览器中运行 (openscad-wasm)
6. **DXF 支持**: 可导出 2D DXF 文件

---

## 3. AutoCAD AutoLISP / Script 方案

### 3.1 相关项目

| 项目 | ★ Stars | 特点 |
|------|---------|------|
| **Psalmustrack/lambdacad-mcp** | 0 | λ MCP 服务器，支持任何 AutoLISP CAD，100 个工具，2D+3D |
| **rusliksu/autolisp-bot** | 1 | AI 驱动的 AutoLISP 脚本生成器（结构工程师） |
| **Rtoony/AutoLISP-Architect-AI** | 0 | AutoLISP Architect AI |
| **ethanaggor/draft-cad-generator** | 0 | 图片转 AutoCAD-ready AutoLISP 代码 |
| **avb-git-gm/autolisp-codex-env** | 0 | AutoLISP 编程环境，集成 Codex (ChatGPT) |
| **FuxuanNet/CADx** | 0 | AI 辅助 AutoCAD 工作流工具包，集成 OpenAI |

### 3.2 AutoCAD 脚本方案分析

**AutoCAD .scr 脚本文件格式**:
- `.scr` 文件是纯文本命令序列，每行一个 AutoCAD 命令
- 可通过 `AutoCAD.exe /b script.scr` 批处理执行
- 支持所有 AutoCAD 命令（LINE, CIRCLE, ARC, POLYLINE 等）
- 适合简单的自动化操作，不适合复杂逻辑

**AutoLISP 编程**:
- AutoCAD 内置的 Lisp 方言
- 功能强大，可访问几乎所有 AutoCAD API
- 可创建自定义命令、对话框
- 支持 DXF/DWG 文件操作
- LLM 可以生成 AutoLISP 代码

**通过脚本控制 AutoCAD 的方式**:
1. `.scr` 脚本文件 → 最简单，LLM 友好
2. AutoLISP (.lsp) → 功能强大，LLM 可生成
3. .NET API (C#/VB.NET) → 功能最全
4. COM Automation → 外部程序控制
5. ObjectARX (C++) → 底层开发

### 3.3 lambdacad-mcp（值得关注）

**Psalmustrack/lambdacad-mcp**
- **描述**: λ MCP server for any AutoLISP-capable CAD — AI drafting with 100 tools, 2D + 3D solids. BricsCAD on Linux is the reference adapter. No COM, no SDK.
- **Topics**: ai, autocad, autolisp, bricscad, cad, claude, dwg, linux, lisp, mcp, mcp-server
- **特点**:
  - MCP 服务器，支持任何 AutoLISP 兼容的 CAD（AutoCAD, BricsCAD 等）
  - 100 个工具，覆盖 2D + 3D
  - 无需 COM, 无需 SDK
  - Linux 上以 BricsCAD 为参考适配器
  - 刚创建 (2026-08-07)，非常新

---

## 4. CAD API as a Service

### 4.1 Zoo / KittyCAD (zoo.dev)

**KittyCAD/modeling-app** ★1,271
- **描述**: The Zoo Design Studio app
- **主页**: https://zoo.dev/design-studio/download
- **License**: MIT
- **Topics**: electron, playwright, react, tailwind, vitest, wasm
- **特点**:
  - Zoo (前身为 KittyCAD) 提供云端 CAD 引擎
  - **KCL (KittyCAD Configuration Language)**: 专为参数化 CAD 设计的编程语言
  - **Text-to-CAD API**: 接受自然语言提示，返回 KCL 代码并生成 3D 模型
  - Zoo Design Studio: 桌面应用 (Electron)，支持 KCL 编程
  - 开源引擎 + 商业 API 服务模式
  - 支持 STL, STEP, OBJ, PLY 等格式导出

**Zoo Text-to-CAD API 特点**:
- HN 上的原始发布帖获得 119 points, 95 comments (2023-12-20)
- 是最早商业化 Text-to-CAD API 的公司之一
- API 接受自然语言，返回 KCL 代码
- KCL 代码可在 Zoo Design Studio 中编辑和修改
- 支持参数化建模

**KittyCAD 组织其他相关仓库**:
- text-to-cad-ui (★295) - Text-to-CAD API 前端
- text-to-cad-blender-addon (★36) - Blender 插件
- viewer (★2) - 轻量 KCL 查看器

### 4.2 Onshape API

- **Onshape** 是全云端 CAD 平台 (PTC 旗下)
- 提供 REST API，支持：
  - 创建/读取/更新/删除 CAD 文档
  - 参数化建模操作
  - Part Studio 和 Assembly 操作
  - 导出 STL, STEP, DXF, DWG 等格式
- API 文档: https://onshape-public.github.io/onshape-clients/
- 支持 Python, JavaScript, C# 等多语言 SDK
- **特点**: 完整的云原生 CAD API，但商业授权

### 4.3 其他云 CAD API

| 服务 | 特点 |
|------|------|
| **Zoo API (zoo.dev)** | KCL 语言 + Text-to-CAD API，开源引擎，商业 API |
| **Onshape API** | 全云端 CAD，REST API，PTC 旗下 |
| **Autodesk Platform Services (APS)** | 原 Forge API，支持 AutoCAD/Fusion 360 数据 |
| **Trimble SketchUp API** | Ruby API + Cloud API |

---

## 5. Python CAD 库

### 5.1 核心库

| 库 | ★ Stars | 语言 | License | 特点 |
|----|---------|------|---------|------|
| **CadQuery/cadquery** | 5,571 | Python | Apache 2.0 | 参数化 CAD 脚本框架，基于 OCCT，支持 DXF/STEP/STL |
| **gumyr/build123d** | 2,813 | Python | Apache 2.0 | Python CAD 编程库，CadQuery 的改进版 |
| **mozman/ezdxf** | 1,397 | Python | MIT | DXF 读写接口，纯 Python |
| **partcad/partcad** | 483 | Python | Apache 2.0 | 硬件包管理器，AI 增强，支持 CadQuery/build123d/OpenSCAD |

### 5.2 详细分析

**CadQuery** ★5,571
- **主页**: https://cadquery.org
- **描述**: A python parametric CAD scripting framework based on OCCT
- **Topics**: 3d, brep, cad, dxf, modeling, occt, opencascade, parametric, python, step, stl
- **特点**:
  - 基于 OpenCASCADE (OCCT) 内核
  - 支持 DXF, STEP, STL, IGES 导出
  - 参数化建模，Python 脚本驱动
  - **LLM 友好**: 多个项目使用 LLM 生成 CadQuery 代码
  - 活跃维护（2026-08-08 更新）

**build123d** ★2,813
- **描述**: A python CAD programming library
- **Topics**: 3d, brep, cad, opencascade, python
- **特点**:
  - CadQuery 作者的新项目，改进 API 设计
  - 更 Pythonic 的 API
  - 同样基于 OpenCASCADE
  - 被 Multi-Agent-CAD 项目采用

**ezdxf** ★1,397
- **描述**: Python interface to DXF
- **主页**: https://ezdxf.mozman.at
- **特点**:
  - 纯 Python DXF 读写库
  - 不依赖任何 CAD 软件
  - 可创建/修改/导出 DXF 文件
  - **2D 绘图专用**，适合生成工程图纸
  - LLM 可直接生成 ezdxf Python 代码

**PartCAD** ★483
- **描述**: Package manager for things. Start designing modular hardware!
- **主页**: https://partcad.org
- **特点**:
  - 硬件设计的"包管理器"（类似 npm for hardware）
  - 支持 CadQuery, build123d, OpenSCAD
  - AI 增强工作流
  - 数字孪生/TDP 文档管理
  - 支持 STEP, STL, IGES 格式

### 5.3 LLM 生成 Python CAD 代码的项目

| 项目 | 后端库 | 特点 |
|------|--------|------|
| OpenOrion/CQAsk | CadQuery | LLM 生成 CadQuery 代码 |
| Text-to-CadQuery/Text-to-CadQuery | CadQuery | 文本到 CadQuery 代码 |
| Pan-Chera/Multi-Agent-CAD | build123d | 多智能体 + build123d |
| filaPro/cad-recode | CadQuery | 点云逆向工程为 CadQuery 代码 |
| col14m/cadrille | CadQuery | 多模态 CAD 重建为 CadQuery 代码 |
| NiJingzhe/SimpleCADAPI | 自研 | LLM 友好的命令式 CAD API |
| stevenleeRNC/cadasu | CadQuery | Claude 生成 3D 模型 |

---

## 6. MCP (Model Context Protocol) CAD 项目（新兴趋势）

MCP 是 Anthropic 推出的模型上下文协议，正在成为 LLM-CAD 集成的主流方式。

| 项目 | ★ Stars | CAD 软件 | 特点 |
|------|---------|----------|------|
| **mixelpixx/KiCAD-MCP-Server** | 1,797 | KiCAD | PCB 设计 MCP，LLM 直接交互 KiCAD |
| **ghbalf/freecad-ai** | 420 | FreeCAD | FreeCAD AI 工作台，支持 MCP |
| **ndoo/fusion360-mcp-bridge** | 20 | Fusion 360 | Claude Code 连接 Fusion 360 |
| **asmith26/jupytercad-mcp** | 20 | JupyterCAD | LLM 控制 JupyterCAD |
| **NeonGlay/inventor-mcp** | 14 | Autodesk Inventor | 参数化 3D 建模 MCP |
| **format37/openscad-mcp** | 12 | OpenSCAD | OpenSCAD MCP 服务器 |
| **codeofaxel/Kiln** | 43 | OpenSCAD | 3D 打印 MCP，设计+切片+打印 |
| **proximile/FreeCAD-MCP** | 3 | FreeCAD | FreeCAD + AI 模型 MCP 服务器 |
| **sandraschi/qcad-mcp** | 7 | QCAD Pro | 建筑 CAD MCP |
| **Psalmustrack/lambdacad-mcp** | 0 | AutoCAD/BricsCAD | AutoLISP MCP，100 个工具 |

---

## 7. 学术/研究项目

| 项目 | ★ Stars | 会议/期刊 | 特点 |
|------|---------|-----------|------|
| **SadilKhan/Text2CAD** | 456 | NeurIPS'24 Spotlight | 文本生成顺序 CAD 设计，数据集 |
| **filaPro/cad-recode** | 251 | ICCV2025 | 点云逆向工程为 CAD 代码 |
| **col14m/cadrille** | 169 | ICLR2026 | 多模态 CAD 重建 + 在线强化学习 |
| **dimitrismallis/CAD-Assistant** | 77 | ICCV2025 | 工具增强 VLLM 通用 CAD 求解 |
| **huggingface/cadgenbench** | 100 | - | AI CAD 生成基准测试 (HuggingFace) |
| **EESJGong/Graph-CAD** | 136 | - | 图表示学习 Text-to-CAD |
| **JasonShiii/STEP-LLM** | 31 | - | 从自然语言生成 CAD STEP 模型 |
| **gudo7208/awesome-ai4cad** | 19 | - | AI+CAD 论文列表 (700+ 篇) |

---

## 8. Hacker News 讨论热度

| 帖子标题 | Points | Comments | 日期 | 链接 |
|----------|--------|----------|------|------|
| Launch HN: Adam (YC W25) – Open-Source AI CAD | 215 | 97 | 2026-06-17 | github.com/Adam-CAD/CADAM |
| Text-to-CAD (earthtojake) | 186 | 48 | 2026-05-01 | github.com/earthtojake/text-to-cad |
| Show HN: Open-sourcing our text-to-CAD app | 179 | 23 | 2025-09-05 | github.com/Adam-CAD/CADAM |
| Text-to-CAD (Zoo) | 119 | 95 | 2023-12-20 | zoo.dev/blog/introducing-text-to-cad |
| Text-to-CAD: Risks and Opportunities | 66 | 51 | 2023-10-19 | thegradient.pub/text-to-cad/ |
| Unified Controllable Text-to-CAD with LLMs | 63 | 22 | 2026-06-09 | arxiv.org/abs/2604.19773 |
| Show HN: ChatToSTL – AI text-to-CAD for 3D printing | 52 | 6 | 2025-06-12 | huggingface.co/spaces/flowfulai/ChatToSTL |
| Show HN: Vibe Code your 3D Models (synaps-cad) | 61 | 20 | 2026-02-27 | github.com/ierror/synaps-cad |
| Hardware Builders Need More Than Text-to-CAD | 6 | 0 | 2026-07-15 | opuslabs.substack.com |

---

## 9. 技术路线对比总结

### 9.1 LLM → CAD 的主要技术路线

| 路线 | 代表项目 | 优势 | 劣势 | DXF 支持 |
|------|----------|------|------|----------|
| **LLM → OpenSCAD 代码** | CADAM, ScadLM, openscad-studio | 语法简单，LLM 友好，WASM 可浏览器运行 | 功能有限，无 BREP | ✅ (2D 轮廓) |
| **LLM → CadQuery/build123d (Python)** | CQAsk, Multi-Agent-CAD, cad-recode | 功能强大，基于 OCCT，支持 BREP | 需 Python 环境，代码较复杂 | ✅ |
| **LLM → KCL (Zoo)** | Zoo Text-to-CAD API, text-to-cad-ui | 商业 API，云端运行，KCL 专为 CAD 设计 | 依赖 Zoo 服务 | ✅ |
| **LLM → AutoLISP/.scr** | lambdacad-mcp, autolisp-bot | 直接控制 AutoCAD，行业标准 | AutoCAD 商业软件，Lisp 学习曲线 | ✅ (原生) |
| **LLM → ezdxf (Python)** | (尚无知名项目) | 纯 Python，无需 CAD 软件，直接写 DXF | 仅 2D，无 3D 建模 | ✅ (原生) |
| **MCP Server → CAD 软件** | KiCAD-MCP, freecad-ai, Kiln | 直接控制真实 CAD 软件，实时交互 | 需要安装对应 CAD 软件 | 取决于 CAD 软件 |
| **LLM → 专有 CAD API** | Text-to-CadQuery, SimpleCADAPI | 针对 LLM 优化 API 设计 | 需自建后端 | 取决于实现 |

### 9.2 关键发现

1. **最热门方向**: LLM 生成 OpenSCAD 代码（CADAM ★4,950）和 CadQuery Python 代码（CQAsk ★185, Multi-Agent-CAD ★449）

2. **MCP 是新兴趋势**: 2025-2026 年大量项目采用 MCP 协议连接 LLM 和 CAD 软件，KiCAD-MCP-Server 已达 ★1,797

3. **Zoo/KittyCAD 是先行者**: 2023年12月推出 Text-to-CAD API，开创了商业化 Text-to-CAD 服务

4. **CADAM (Adam, YC W25)** 是目前最活跃的开源 text-to-CAD 项目，使用 OpenSCAD + WASM 在浏览器运行

5. **学术研究活跃**: NeurIPS, ICCV, ICLR 均有相关论文，HuggingFace 推出了 cadgenbench 基准测试

6. **2D DXF 生成**: ezdxf 是纯 Python DXF 库，OpenSCAD 支持 DXF 2D 轮廓导出，CadQuery 支持 DXF 导出

7. **AutoLISP 方向较冷**: 目前 star 数都很低，但 lambdacad-mcp 提供了 MCP 方案值得关注

### 9.3 推荐技术路线

根据调研结果，如果目标是**自然语言驱动 CAD 生成**，推荐以下路线：

**方案 A: LLM → OpenSCAD → DXF/STL**
- 适合: 快速原型、3D 打印、简单零件
- 优势: 语法简单，LLM 容易生成，可浏览器运行
- 工具: OpenSCAD + openscad-wasm

**方案 B: LLM → CadQuery/build123d → STEP/DXF/STL**
- 适合: 工程级零件，需要 BREP 和精确几何
- 优势: 功能强大，基于 OCCT 工业级内核
- 工具: CadQuery 或 build123d

**方案 C: LLM → ezdxf → DXF**
- 适合: 纯 2D 工程图纸生成
- 优势: 无需 CAD 软件，纯 Python，直接生成 DXF
- 工具: ezdxf

**方案 D: MCP → AutoCAD/FreeCAD**
- 适合: 需要直接控制专业 CAD 软件
- 优势: 实时交互，利用现有 CAD 功能
- 工具: lambdacad-mcp (AutoCAD) 或 freecad-ai (FreeCAD)

**方案 E: Zoo Text-to-CAD API**
- 适合: 快速集成，无需自建 CAD 后端
- 优势: 商业级 API，KCL 语言专为 CAD 设计
- 劣势: 依赖第三方服务

---

## 附录: 完整项目列表

### A. 所有调研到的项目 (按 Star 排序)

| # | 项目 | ★ Stars | 类别 | URL |
|---|------|---------|------|-----|
| 1 | earthtojake/text-to-cad | 13,067 | Agent Skills | github.com/earthtojake/text-to-cad |
| 2 | Adam-CAD/CADAM | 4,950 | Text-to-CAD Web App | github.com/Adam-CAD/CADAM |
| 3 | CadQuery/cadquery | 5,571 | Python CAD 库 | github.com/CadQuery/cadquery |
| 4 | gumyr/build123d | 2,813 | Python CAD 库 | github.com/gumyr/build123d |
| 5 | mixelpixx/KiCAD-MCP-Server | 1,797 | MCP (KiCAD) | github.com/mixelpixx/KiCAD-MCP-Server |
| 6 | mozman/ezdxf | 1,397 | DXF 库 | github.com/mozman/ezdxf |
| 7 | KittyCAD/modeling-app | 1,271 | CAD App (Zoo) | github.com/KittyCAD/modeling-app |
| 8 | SadilKhan/Text2CAD | 456 | 学术 (NeurIPS'24) | github.com/SadilKhan/Text2CAD |
| 9 | Pan-Chera/Multi-Agent-CAD | 449 | 多智能体 CAD | github.com/Pan-Chera/Multi-Agent-CAD |
| 10 | ghbalf/freecad-ai | 420 | FreeCAD AI | github.com/ghbalf/freecad-ai |
| 11 | timschmidt/synaps-cad | 349 | AI CAD IDE (Rust) | github.com/timschmidt/synaps-cad |
| 12 | KittyCAD/text-to-cad-ui | 295 | Zoo API UI | github.com/KittyCAD/text-to-cad-ui |
| 13 | forgent3d/forgent3d-desktop | 229 | AI 3D 模型 | github.com/forgent3d/forgent3d-desktop |
| 14 | FreedomIntelligence/BlenderLLM | 280 | LLM for Blender | github.com/FreedomIntelligence/BlenderLLM |
| 15 | filaPro/cad-recode | 251 | 学术 (ICCV'25) | github.com/filaPro/cad-recode |
| 16 | zacharyfmarion/openscad-studio | 192 | OpenSCAD AI IDE | github.com/zacharyfmarion/openscad-studio |
| 17 | OpenOrion/CQAsk | 185 | LLM + CadQuery | github.com/OpenOrion/CQAsk |
| 18 | col14m/cadrille | 169 | 学术 (ICLR'26) | github.com/col14m/cadrille |
| 19 | EESJGong/Graph-CAD | 136 | 图表示学习 | github.com/EESJGong/Graph-CAD |
| 20 | huggingface/cadgenbench | 100 | 基准测试 | github.com/huggingface/cadgenbench |
| 21 | Text-to-CadQuery/Text-to-CadQuery | 111 | Text→CadQuery | github.com/Text-to-CadQuery/Text-to-CadQuery |
| 22 | NiJingzhe/SimpleCADAPI | 80 | LLM 友好 CAD API | github.com/NiJingzhe/SimpleCADAPI |
| 23 | dimitrismallis/CAD-Assistant | 77 | 学术 (ICCV'25) | github.com/dimitrismallis/CAD-Assistant |
| 24 | islamnurdin/Artifex | 62 | CAD Copilot | github.com/islamnurdin/Artifex |
| 25 | armpro24-blip/cad-cae-copilot | 46 | CAD/CAE Copilot | github.com/armpro24-blip/cad-cae-copilot |
| 26 | codeofaxel/Kiln | 43 | MCP 3D 打印 | github.com/codeofaxel/Kiln |
| 27 | JasonShiii/STEP-LLM | 31 | 自然语言→STEP | github.com/JasonShiii/STEP-LLM |
| 28 | jabarkle/CADSmith | 28 | 多智能体验证 | github.com/jabarkle/CADSmith |
| 29 | KrishKrosh/ScadLM | 22 | OpenSCAD Agent | github.com/KrishKrosh/ScadLM |
| 30 | ndoo/fusion360-mcp-bridge | 20 | MCP (Fusion 360) | github.com/ndoo/fusion360-mcp-bridge |
| 31 | asmith26/jupytercad-mcp | 20 | MCP (JupyterCAD) | github.com/asmith26/jupytercad-mcp |
| 32 | NeonGlay/inventor-mcp | 14 | MCP (Inventor) | github.com/NeonGlay/inventor-mcp |
| 33 | format37/openscad-mcp | 12 | MCP (OpenSCAD) | github.com/format37/openscad-mcp |
| 34 | levkropp/ClawSCAD | 12 | OpenSCAD+Claude | github.com/levkropp/ClawSCAD |
| 35 | caseyhartnett/Torrify | 9 | AI 参数化 CAD | github.com/caseyhartnett/Torrify |
| 36 | Kevoyuan/AgentSCAD | 6 | OpenSCAD Agent | github.com/Kevoyuan/AgentSCAD |
| 37 | Psalmustrack/lambdacad-mcp | 0 | MCP (AutoLISP) | github.com/Psalmustrack/lambdacad-mcp |

---

*报告生成时间: 2026-08-08 16:33 CST*
*数据来源: GitHub Search API, HN Algolia API, 项目官方文档*
