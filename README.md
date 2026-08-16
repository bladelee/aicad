# floorplan-mcp — 装修师傅的自然语言 CAD 助手

> 通过桌面 Chat 客户端（[Goose](https://github.com/aaif-goose/goose) / [OpenWork](https://github.com/different-ai/openwork)）+ 本项目提供的 Docker 镜像，
> 让设计师用自然语言**读改查装修 DWG/DXF**——UI 即所得，不必写 Python 也不必学 FreeCAD API。

[![status](https://img.shields.io/badge/status-MVP%20Phase%200-yellow)](docs/03-计划与复盘/计划-工作.md)
[![license](https://img.shields.io/badge/license-See%20NOTICE-important)](#license)

---

## 📦 这是什么

| 输入 | 输出 |
|---|---|
| 一套装修工程 DWG 图纸（5+ 张）+ 改造需求（自然语言或参数 JSON）| 改好的 DXF 图纸（保留原图所有未改实体，仅改指定处） |

**典型场景**：改一堵墙的位置 → 自动同步关联图层（填充/天花/地坪）+ 自动重算相关尺寸 + 高保真 PDF 改前后对比图。

---

## 🚀 快速开始

### 客户/实施工程师
- 部署手册：[`docs/01-产品/客户部署使用手册.md`](docs/01-产品/客户部署使用手册.md)
- 发布与上线方案：[`docs/06-工程实操/发布与部署完整方案.md`](docs/06-工程实操/发布与部署完整方案.md)

### 开发者
1. 架构与方案：[`docs/02-方案/方案-F-容器化.md`](docs/02-方案/方案-F-容器化.md) → [`方案-F2-产品-风险-验证.md`](docs/02-方案/方案-F2-产品-风险-验证.md) → [`产品Spec.md`](docs/01-产品/产品Spec.md)
2. 跑测试：`cd floorplan-mcp && python -m pytest tests/`
3. 工具脚本（独立于 MCP）：`tools/dwg_to_dxf/`, `tools/dxf_scan/`, `tools/dxf_edit/`, `tools/visual/`

---

## 🗂️ 仓库结构

```
.
├── docs/                    # 📚 全部项目文档（按主题分层）
│   ├── README.md            # 文档总导航 ← 先看这里
│   ├── 01-产品/             # 产品定义 + 客户部署手册
│   ├── 02-方案/             # 当前权威架构方案
│   ├── 03-计划与复盘/        # 时间序列过程记录
│   ├── 04-任务执行/          # 10 项联动改造任务执行链
│   ├── 05-知识沉淀/          # 领域知识 + SOP + 借鉴
│   ├── 06-工程实操/          # 实战记录、实施日志
│   ├── 07-目录整理/          # 整理元文档
│   └── 99-归档/              # 历史已取代方案（v1~E、G 等）
│
├── floorplan-mcp/           # 🐳 主代码：MCP server + Docker 镜像
├── tools/                   # 🛠️ 独立工具脚本（DWG→DXF / scan / edit / visual）
├── samples/19-102/          # 📐 原始样本数据（**只读**，客户别墅工程图）
├── workdir/19-102/          # 🗂️ 运行期产物（DXF / reports / backups，多数 .gitignore 掉）
├── ops/                     # 🔧 工程运维（Docker/Hombrew 排错手册）
├── research/                # 🔍 早期调研笔记
└── cad_tools.archived/      # 🗄️ 已归档的 v1 代码（保留作历史）
```

> 📖 完整文档导航见 [`docs/README.md`](docs/README.md)。

---

## ⚖️ License / NOTICE

本仓库源代码按 **Apache-2.0** 协议开源，但**运行期依赖以下强 copyleft 库**，商业分发需单独评估：

| 依赖 | License | 用途 | 处理方式 |
|---|---|---|---|
| [LibreDWG](https://www.gnu.org/software/libredwg/) | **GPL-3.0-or-later** | DWG → DXF 转换 | 仅在容器内调用，不直接链入 |
| [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) | **AGPL-3.0** | DXF → 高保真 PDF 渲染 | 仅在容器内调用，不直接链入 |
| [ezdxf](https://ezdxf.mozman.at/) | MIT | DXF 读写核心 | 直接 import |

容器镜像分发请阅读 [`docs/06-工程实操/发布与部署完整方案.md`](docs/06-工程实操/发布与部署完整方案.md) 的合规章节。

---

## 🧪 当前进度（2026-08-09）

- ✅ DWG→DXF 链路打通（LibreDWG 容器内编译）
- ✅ 改墙 + 材料编号替换（任务 #1 #6 生产就绪）
- ✅ 跨图关联图谱建立（DE-XX / 1EA-XX 编号指针体系）
- 🚧 10 项联动改造中 6 项阻塞（详见 `docs/04-任务执行/剩余事项总览.md`）

更多见 [`docs/03-计划与复盘/计划-工作.md`](docs/03-计划与复盘/计划-工作.md)。
