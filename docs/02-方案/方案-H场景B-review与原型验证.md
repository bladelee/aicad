# 方案 H 场景 B 评审 + 原型验证

> 评审日期：2026-08-09
> 评审范围：`方案-H-视觉验证与语义对齐层.md` §1.2 场景 B（改后视觉验收）
> 评审方法：可实现性 / 正确性 / 精益 / KISS 四维度
> 评审后行动：每个高/中风险 → 一个原型验证（半小时内可跑完），验证结果决定是否进入正式实现

---

## 1. 风险登记表（5 项，1 项低风险仅文档修订）

| ID | 风险 | 等级 | 关联设计决策 | 关联原型 |
|----|------|------|-------------|---------|
| R1 | **场景 B 的 VLM 验收能力未经验证** | 🔴 高 | 决策 1A + 决策 2 | **P1**（4 维打分反证） |
| R2 | **change_record 格式未定义**，move_wall 不返回结构化 record | 🔴 高 | 决策 1A 的"结构化版"维度 | **P2**（跑 move_wall 看实际产出） |
| R3 | **决策 4C 回滚链路模糊**，"AI 询问触发"无明确接口 | 🔴 高 | 决策 4C（半自动） | **P3**（restore_from_bak 骨架） |
| R4 | **LineCollection 渲染对几何细节不足**（看不见墙厚、门窗联动） | 🟡 中 | 决策 1A 路径本身 | **P1 已包含**（同一原型同时打分 4 维） |
| R5 | **DXF→PDF 升级路径 C 未实测**（PyMuPDF AGPL 规避后 svglib 链路是否可行） | 🟡 中 | 决策 1A→C 升级路径 | **P4**（svglib+reportlab 实测） |
| R6 | **决策矩阵 3 级抽象过度**（先 A 后 D 不够再 C） | 🟢 低 | 文档结构 | **无原型**（文档修订即可） |

---

## 2. 详细评审

### 2.1 R1（🔴 高）：场景 B VLM 验收能力未验证

**问题**：
- Phase H-0 的方案 A（视觉对账）已实测有价值（M3 看 PDF + DXF JSON 给出 9 房间 + 6 家具 + 11 尺寸）
- **但场景 B 的"改前后骨架图对比"和方案 A 的"PDF 全保真视觉对账"是不同难度**：
  - A 给 VLM 看的是设计师原 PDF（含 TEXT/INSERT/HATCH）→ 高保真
  - B 给 VLM 看的是 LineCollection 自渲 PNG（仅 LINE 骨架）→ 低保真
- 反证实验下，骨架图能否让 VLM 给出有意义的"4 维验收意见"，**未知**

**可能失败模式**：
- 几何完整性：✅ 应能（VLM 看骨架图能数线段）
- 几何位置：🟡 部分能（500mm 移动在 1.0 scale 渲染下 = 500-1000 像素，VLM 能粗略判断）
- 关联保持：❌ 难能（VLM 看不见门窗、家具细节，"关联"语义不可见）
- 副作用：🟡 部分能（多线/漏线可见，但"该联动没联动"看不见）

**最坏情况**：VLM 4 维只有 1 维有效，场景 B 价值崩塌。

### 2.2 R2（🔴 高）：change_record 格式未定义

**问题**：
- `tools/dxf_edit/move_wall.py` 的 `move_wall()` 当前返回 `{'ok': bool, 'backup_path': str}`
- **没有"动了哪些 handle、每个 handle 之前/之后的坐标"清单**
- verify_change 拿不到声明要改的内容，4 维验收的"几何位置"维度（对照声明）失效

**当前影响**：
- 验收退化为"纯视觉差异发现"（VLM 自己看图发现哪儿不一样）
- 没有"声明 vs 实际"的对照能力
- 不能区分"故意改的"和"误改的"

**修复方向**：
- 改 `move_wall.py` 返回结构化 record（`{action: move, handle, before_geom, after_geom, dx, dy}`）
- 或 verify_change 自己跑 diff 推断 record（更脆弱）

### 2.3 R3（🔴 高）：决策 4C 回滚链路模糊

**问题**：
- 我设计的"半自动——AI 询问可触发回滚"是模糊描述
- 没说清：触发接口是什么？回滚命令是哪个？LLM 在哪一层做决定？
- 现有的 `.bak` 机制有，但**没有暴露给 LLM 调用的工具**

**修复方向（KISS 拆分）**：
- **verify_change.py 只做只读审计**，输出结构化报告 + `auto_rollback_recommended: bool`
- **新增 `tools/dxf_edit/restore_from_bak.py`** 作为只写执行器
- LLM 在对话里：读 verify_change 报告 → 自己决定 → 显式调 restore_from_bak
- **决策与执行分离**：verify_change 是审计员，restore_from_bak 是执行者，LLM 在中间

### 2.4 R4（🟡 中）：LineCollection 渲染细节不足

**问题**：
- LineCollection 是单线条宽度，无法表达墙厚变化
- 看不见门窗、家具、HATCH 填充、TEXT 标注

**已在 R1 的原型 P1 中评估**（同一原型打分 4 维就能体现这个限制）

**降级路径**：决策 1A → 决策 1C（DXF→PDF 全保真）由 P4 验证可行性

### 2.5 R5（🟡 中）：DXF→PDF 升级路径未实测

**问题**：
- PyMuPDF（AGPL 传染）已规避不装
- ezdxf SVG 后端 256MB 不可传输
- svglib + reportlab 已 `pip install` 但**未实测 DXF→PDF 整链路**
- 如果这条路也不通，决策 1A → C 的升级路径就不存在

**修复方向**：原型 P4 实测整链路（ezdxf SVG 后端 → svglib 解析 → reportlab 写 PDF），量大小和耗时。

### 2.6 R6（🟢 低）：决策矩阵 3 级抽象

**问题**：
- 文档写"先 A 后 D 不够再 C"的 3 级路径在实现阶段会增加复杂度
- 实际应该是 A 和 D 是两个**独立可选模式**，C 是待评估的第 3 个模式

**修复**：文档 §1.2 改"实现 1A + D 双模式（C 推迟到 Phase H-2 待评估）"。

---

## 3. 原型计划

### P1：反证实验——VLM 看改前后骨架图能不能给 4 维验收意见

**目标**：验证 R1 + R4

**做法**（半小时内）：
1. LineCollection 直渲 `3-平面系统图.dxf`（改前）→ `verify_p00_before.png`
2. LineCollection 直渲 `3-平面系统图_moved_500_0.dxf`（改后）→ `verify_p00_after.png`
3. 我（M3）作为 VLM，看两张图 + change_record（声明移动 500mm），按 4 维清单打分
4. 评分 ≥ 3 维有效 → 场景 B 值得做；≤ 2 维有效 → 升级到 C 路径

**预期产出**：`tmp_vision/phase_h1/p1_vlm_check.json` 含 M3 的 4 维打分

---

### P2：跑 move_wall.py 看实际返回，补 change_record 定义

**目标**：验证 R2

**做法**（半小时内）：
1. 读 `tools/dxf_edit/move_wall.py` 完整代码看实际返回
2. 跑一次 `move_wall.py` 看实际输出
3. 写出结构化 `change_record` 的 JSON schema
4. 给出"修复 move_wall 让它返回 record"的 diff（不一定要真改，先有 schema）

**预期产出**：`tools/dxf_edit/change_record_schema.json` + `docs/change_record_spec.md`

---

### P3：restore_from_bak.py 骨架

**目标**：验证 R3（决策 4C 的接口清晰化）

**做法**（半小时内）：
1. 写 `tools/dxf_edit/restore_from_bak.py`：
   - 输入：`--dxf <当前文件> --bak <.bak 路径>` 或 `--latest-bak`
   - 行为：恢复 → 自动 `.bak2`（防回滚错）
   - 输出：`{ok, restored_from, new_backup_path}`
2. 写 CLI 帮 LLM 直接调用
3. （可选）模拟一次回滚跑通

**预期产出**：`tools/dxf_edit/restore_from_bak.py` 可直接用

---

### P4：svglib+reportlab DXF→PDF 链路实测

**目标**：验证 R5（决策 1A → C 升级路径可行性）

**做法**（半小时内）：
1. ezdxf SVG 后端渲平面图
2. svglib 读 SVG → reportlab 写 PDF
3. 量 PDF 大小 + 是否能 pypdfium2 反读
4. 若 OK → 决策 1C 路径解锁；否则 → R5 升级路径不可行

**预期产出**：`tmp_vision/phase_h1/p4_dxf_to_pdf_test.pdf` + 测试结论

---

## 4. 验证矩阵

| 验证结果 | 下一步 |
|---------|--------|
| P1 ≥ 3 维有效 | 场景 B 进入正式实现（Phase H-1 实现 verify_change.py） |
| P1 ≤ 2 维有效 | 暂缓场景 B 实现，先做 P4 看 DXF→PDF 是否可行 |
| P2 schema 定义完成 | move_wall 升级（不在 Phase H-1 范围，列为后续） |
| P3 restore_from_bak 跑通 | 决策 4C 的 LLM 触发链路落地 |
| P4 DXF→PDF 链路 OK | 决策 1C 路径解锁，未来场景 B 可升级 |
| P4 DXF→PDF 链路失败 | 场景 B 暂不实现，或仅保留决策 1A 的有限场景 |

---

## 5. 时间预估

| 原型 | 预期耗时 | 卡住最坏情况 |
|------|---------|------------|
| P1 | 30 分钟（含 LineCollection 渲染 + M3 评分） | VLM 给不出答案 → 1 小时调试 prompt |
| P2 | 15 分钟 | move_wall 跑不起来 → 30 分钟 |
| P3 | 20 分钟 | 文件权限问题 → 30 分钟 |
| P4 | 30 分钟（含 ezdxf SVG + svglib + reportlab 链路） | svglib 解析 ezdxf SVG 出错 → 1 小时 |

**总计**：最长 4 小时（如果所有原型都卡最坏情况），最短 1.5 小时（如果都顺）。
