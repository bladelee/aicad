# 🗄️ 归档文档说明（99-归档/）

> 本目录存放**已被取代的历史方案**和**已废弃的实验残骸**，仅作回溯用，不再维护。
> 当前权威文档清单见 [`../README.md`](../README.md)。

---

## 📂 目录结构

```
99-归档/
├── 方案演进/                    # v1 → v2 → … → F 的方案演进史
│   ├── 方案-v1.md               （最早 v1 方案）
│   ├── 方案-v2.md               （v1 + 系统性 review）
│   ├── 方案-v2-review.md        （v2 的自我 review + FreeCAD MCP 调研）
│   ├── 方案-v3-final.md         （v2.1 收敛 + FloorplanBackend 抽象）
│   ├── 方案-C-BIM.md            （IFC + SketchUp 第三套对比方案）
│   ├── 方案-D-决策.md           （锁定实施路径，但跨平台 transport 误判）
│   └── 方案-E-混合架构.md       （Linux 服务器 + Windows 客户端，被 F 取代）
│
├── 方案-G-多模态双视角.md        （VLM 看图猜结构，反证实验 0 分，被 H 取代）
├── 研究方案总览.md               （最早 6 大方案综述，已被方案演进覆盖）
└── oda-experiments/             （ODA File Converter 27.x CLI 失败实验残骸）
```

---

## 📋 归档原因一览

### `方案演进/`（7 份，全部已被 F 取代）

| 文档 | 归档日期 | 归档原因 |
|---|---|---|
| `方案-v1.md` | 2026-08-08 | ⚠️ 房间识别算法地基不成立（详见 v1 顶部 §三 P0） |
| `方案-v2.md` | 2026-08-08 | ⚠️ 漏掉了 MCP 这层（现代 Chat→CAD 集成范式） |
| `方案-v2-review.md` | 2026-08-08 | ⚠️ 自我 review，freecad-ai 结论已并入 v3 + memory |
| `方案-v3-final.md` | 2026-08-08 | ⚠️ design 抽象被 F 继承，但 transport/平台判断被 F 覆盖 |
| `方案-C-BIM.md` | 2026-08-08 | ⏸️ Phase 3 参考保留，非 MVP；当前不实施 IFC 路径 |
| `方案-D-决策.md` | 2026-08-08 | ⚠️ "freecad-ai 是 Linux entry = B 在 Windows 不可用"误判 |
| `方案-E-混合架构.md` | 2026-08-08 | ⚠️ 混合思路被 F 容器化吸收并超越 |

**演进链**：v1 → v2 → v2-review(v2.1) → v3-final → D（锁定）→ E（混合）→ **F（当前权威）**

### `方案-G-多模态双视角.md`（独立归档）

| 文档 | 归档日期 | 归档原因 |
|---|---|---|
| 方案 G | 2026-08-09 | 🗄️ 试图用 ezdxf 自渲 PNG 让 VLM 推断结构，反证实验 0 分；**方向错误**。真正的视觉价值在 PDF 对照校验 + 改后验收（继承者：方案 H）|

### `研究方案总览.md`

最早 6 大技术方案综述（FreeCAD / OpenSCAD / AutoCAD / Docker / 等），后续 v1~F 方案完全覆盖了里面的分析，仅留作历史回溯。

### `oda-experiments/`（实验残骸）

ODA File Converter 27.x CLI 8 个调试脚本 + deb/AppImage 包。**结论已沉淀**：

- **ODA 27.x 不支持 CLI**（虽然官方文档说支持，实际已坏）
- **LibreDWG 是当前唯一可行路径**（详见 [`../06-工程实操/格式转换-实战记录.md`](../06-工程实操/格式转换-实战记录.md)）

文件包括：
- `run_oda*.sh` / `run_appimage*.sh` / `convert_all_to_dxf.sh` — 8 个失败的 ODA 调用脚本
- `Dockerfile.test` — ODA 容器实验残骸
- `test_libredwg.sh` — libredwg 早期实验（弃用）
- `oda_pkg/` — 早期下载的 oda.AppImage + oda.deb

---

## 🔍 何时查看本目录？

- **想理解为什么当前是方案 F 而不是其他**：看 `方案演进/` 里 v1~E 的取舍
- **想了解 VLM/多模态方向的死路**：看 `方案-G-多模态双视角.md`
- **想了解原始 6 大技术选型分析**：看 `研究方案总览.md`
- **想验证"为什么不用 ODA"**：看 `oda-experiments/` 的失败脚本 + `格式转换-实战记录.md`

---

## ⚠️ 注意

- 本目录文档**不维护**，链接可能是失效的路径（早期写到根目录的链接）
- 如需权威信息，请回到 [`../README.md`](../README.md) 找当前文档
