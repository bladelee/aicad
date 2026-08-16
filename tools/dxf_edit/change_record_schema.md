# change_record JSON Schema（P2 产出）

> 用途：move_wall / apply_material_rename 等写工具**统一返回的结构化 record**，供 verify_change.py 验收
> 当前状态：move_wall **部分实现**，缺关键字段（`before_geom`, `after_geom`, `handle` 列表）

---

## Schema 定义

```jsonc
{
  "schema_version": "1.0",
  "tool": "move_wall",                    // 工具名（move_wall / apply_material_rename / ...）
  "timestamp": "2026-08-09T13:30:00Z",   // ISO 8601 时间戳
  "input_file": "/abs/path/file.dxf",    // 输入 DXF（改前）
  "output_file": "/abs/path/file.dxf",   // 输出 DXF（改后）
  "backup_file": "/abs/path/file.dxf.bak1.dxf",  // 自动备份路径，null = 无备份

  "actions": [                            // 改动作清单（数组支持批量）
    {
      "type": "translate",                // move_wall: translate / extend-end
                                         // apply_material_rename: replace
      "entity_handle": "1A2",            // 主被改实体（墙/门等）的 ezdxf handle
      "entity_type": "LINE",             // 实体类型
      "layer": "A原建筑墙体",            // 所属图层
      "before_geom": {                    // 几何改前坐标（依赖实体类型字段不同）
        "start": [x, y, z],               // LINE 用
        "end": [x, y, z]
      },
      "after_geom": {                     // 几何改后坐标
        "start": [x, y, z],
        "end": [x, y, z]
      },
      "delta": {                          // 改动量
        "dx": 500.0,
        "dy": 0.0
      }
    }
  ],

  "synced_actions": [                    // 因 sync_layers=True 联动的同族图层实体
    {
      "type": "synced_translate",
      "entity_handles": ["3F", "4B", ...],  // 所有联动平移的实体 handle 列表
      "layer": "A原建筑墙体填充",
      "delta": {"dx": 500.0, "dy": 0.0},
      "count": 200                          // 该图层被平移的实体数
    }
  ],

  "round_trip": {                         // 写后 round-trip 健康度（写入文件再读回来）
    "before_entity_count": 9471,
    "after_entity_count": 9471,
    "type_diff": {}                        // {LINE: (2698, 2698), ...} 改前/改后类型计数
  },

  "warnings": [...]                       // 可选：执行中的警告（如某实体几何更新失败）
}
```

---

## 当前 move_wall 实现 vs Schema 差距

| Schema 字段 | move_wall 当前返回 | 缺口 |
|------------|------------------|------|
| `schema_version` | 无 | 需加 |
| `tool` | 无 | 需加 |
| `timestamp` | 无 | 需加 |
| `input_file` | ✅ `input` | 改名 |
| `output_file` | ✅ `output` | 改名 |
| `backup_file` | ✅ `backup` | 改名 |
| `actions[].type` | ✅ `shift.mode` | 嵌套路径改 |
| `actions[].entity_handle` | ✅ `wall_handle`（顶层） | 移到 actions 里 |
| `actions[].entity_type` | 无 | 需加 |
| `actions[].layer` | 打印在 stdout（未返回） | 需收集 |
| `actions[].before_geom` | 打印在 stdout（未返回） | 🔴 **必须加**（verify_change 关键） |
| `actions[].after_geom` | 打印在 stdout（未返回） | 🔴 **必须加**（verify_change 关键） |
| `actions[].delta` | ✅ `shift` | 移到 actions 里 |
| `synced_actions[]` | ⚠️ `synced_layers: {layer: count}` | 需升级为 handle 列表 |
| `round_trip` | ✅ | 一致 |
| `warnings` | 无 | 可选补 |

**核心缺口**：`before_geom` / `after_geom` 必须是结构化坐标，不能只 print。
**次要缺口**：`synced_actions` 应返回具体 handle 列表而不是只 count。

---

## 修复方案（不在 P2 范围，记录供后续）

`tools/dxf_edit/move_wall.py` 的 `move_wall()` 函数需要：
1. 在改前抓 `wall.dxf.start/end` 存为 `before_geom`
2. 改后再抓一次存为 `after_geom`
3. `shift_layer_entities()` 在返回 count 同时收集所有被平移的实体 handle
4. 把所有字段按 schema 重新组装返回

预估改动：~30 行代码，不影响 `move_wall` 主流程。

---

## verify_change.py 怎么用这个 schema

```python
# 伪代码
record = move_wall(...)  # 返回 schema 化的 record
report = verify_change(
    dxf_before=record["input_file"],
    dxf_after=record["output_file"],
    change_record=record,                  # 直接传
    mode="inline" | "http",
    out="verify_change_p00.json",
)

# report 包含：
# - 几何完整性：VLM 数 line 数 vs record.round_trip.before/after
# - 几何位置：record.actions[].delta vs VLM 视觉确认位移量
# - 关联保持：相邻实体的相对位置是否仍保持
# - 副作用：除 actions[] 外的图层是否变化
```

---

## 验证（已完成）

- ✅ `move_wall()` 当前返回结构有 60% 字段
- ⚠️ 缺 `before_geom` / `after_geom` / `synced_actions[].entity_handles`
- 🔴 verify_change.py 在补齐 move_wall schema 前不能完整工作（几何位置维度失效）

**结论**：P2 已发现真实缺口，但**修复不在 P2 范围**（不重写 move_wall）。verify_change.py 实现前必须先升级 move_wall 到完整 schema。
