# cad_tools.archived（已归档，不再使用）

> ⚠️ 本目录是 v1 阶段代码的归档，**已被 `floorplan-mcp/` 完全替代**。
> 归档日期：2026-08-08（Phase 0 准备阶段，详见 `../复盘-2026-08-08-Phase0准备.md`）

## 为什么归档

v1 的 `cad_tools/` 6 个模块（converter/reader/writer/renderer/geometry/blocks）整体被
`floorplan-mcp/` 重构覆盖：

| v1 模块 | 命运 | 现位置 |
|---------|-----|--------|
| `blocks.py::FURNITURE_KEYWORDS` | bake 进单一真源 | `floorplan-mcp/backends/freecad_backend.py`（顶部 FURNITURE_KEYWORDS）|
| `geometry.py`（纯函数） | 算法上与 shapely 重叠，弃用 | — |
| `converter.py` | 简化为 `floorplan-mcp/backends/_safety.py + _oda_convert` | 同左 |
| `reader.py::_detect_rooms` | 🔴 算法地基错（"闭合多段线=房间"），换 shapely polygonize | `floorplan-mcp/backends/rooms_detect.py` |
| `writer.py`（13 家具块工厂） | 砍掉（真实图纸自带块库） | — |
| `renderer.py` | 🔴 破图层 bug（`layer.off()` 永久改图层），换 RenderContext 副本 | `floorplan-mcp/backends/{freecad,ezdxf}_backend.py::render_preview` |

## 已知 v1 问题（不用再 review，已修）

- 房间识别算法不成立（合成 3 房间图得 0 个房间，详见 `../复盘-2026-08-08-Phase0准备.md §三 P0`）
- renderer `layer.off()` 破坏图层状态
- DOOR_KEYWORDS 含 `D_` 把 `BED_1800` 误判为门

## 还要查 v1 关键词怎么办

打开 `floorplan-mcp/backends/freecad_backend.py`，顶部 `FURNITURE_KEYWORDS` 是单一真源。
要补类别/关键词就在那里改，并同步更新 `floorplan-mcp/tests/test_safety_and_backend.py::test_classify_block_name_full_keywords`。

**别在 cad_tools.archived/ 里改**——它不会被引用，改了也不会进 floorplan-mcp。
