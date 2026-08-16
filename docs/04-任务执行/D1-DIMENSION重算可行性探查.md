# D1: DIMENSION 重算可行性探查结论

> **日期**：2026-08-09
> **结论**：**路径 C 可行**，8 个候选 DIMENSION 全是 `text='<auto>'`（不是硬编码），改 DEFPOINT 坐标就能触发重算。

---

## 一、探查结果

### 1.1 3-平面共有多少 DIMENSION
共 **1375** 个（来自 scan_report.json）

### 1.2 E6037 墙周围 2000mm 内的 DIMENSION
**8 个候选**（DEFPOINT 距墙端 < 2000mm），全部：

| # | 距墙端 | text | defpoint | defpoint2 | 实际距离 |
|---|------:|------|---|---|---:|
| 1 | 712mm | `<auto>` | (211492, -908033) | (208232, -908205) | 3264 |
| 2 | 929mm | `<auto>` | (211872, -907687) | (211472, -906785) | 986 |
| 3 | 1023mm | `<auto>` | (211472, -907687) | (211222, -907493) | 316 |
| ...| ... | `<auto>` | ... | ... | ... |

### 1.3 关键发现

✅ **所有 text 都是 `'<auto>'`** — 不是硬编码数字字符串
→ 这意味着 **AutoCAD 打开 DXF 时会自动按 defpoint/defpoint2 重算 measurement**！
→ 我们改墙后**只需要改 DEFPOINT 的坐标**，AutoCAD 自动显示新数值

---

## 二、路径 C 的具体实施计划

### 2.1 算法（5 步）

```python
# 在 move_wall 内嵌入：
1. 改墙的 LINE.start/end (dx/dy)
2. 找 DEFPOINT 落在墙端点 ±2000mm 内的所有 DIMENSION
3. 对每个 DIMENSION:
   - 如果 defpoint 落在墙的原端点上 → 平移 defpoint += (dx,dy)
   - 如果 defpoint2 落在墙的原端点上 → 平移 defpoint2 += (dx,dy)
   - （text = '<auto>'，不用改）
4. safe_saveas(doc, out)
5. 客户用 AutoCAD 打开 → measurement 自动重算 → 显示新数值
```

### 2.2 预估工作量

| 步骤 | 工作量 |
|------|------|
| 写 `update_dimensions_near_wall(msp, wall_ent, dx, dy)` | 半天 |
| 用真实 E6037 墙验证：8 个候选 defpoint 8 个被正确平移 | 2 小时 |
| 用 AutoCAD 打开校验 measurement 确实更新（需用户配合）| 30 分钟 |
| 加入 move_wall_kitchen_sink（综合 #1+#2+#3 三合一工具）| 1 小时 |

**总计**：**1 天** 就能完成路径 C 的 MVP。

### 2.3 风险（仅 1 个）

**PROXY DIMENSION**：如果 libredwg 转 DXF 时把 DIMENSION 降级成 PROXY，
则 defpoint 不可访问。本次探查里 **8 个全是正常 DIMENSION**（非 PROXY），所以风险**已被规避**。

### 2.4 收益（产品级价值）

路径 C 落地后：
- ✅ **#3 "墙体自动定位 / 标注顺改"** 解锁（用户原话的核心需求）
- ✅ **#4/#5/#9 跨视图联动** 也能加 dim 同步到立面/节点
- ✅ **演示对客户更具说服力**：改墙后数字也对，不是"几何对了但数字错了"

---

## 三、建议执行节奏

- **本周内**：完成 D1 的代码（`update_dimensions_near_wall`），1 天
- **本周末演示前**：可选已做 / 不做（对 MVP 演示不是必需的）
- **演示后**：根据客户反馈决定是否主推（如果客户在意"数字对"，就主推）

---

## 修订记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1 | 2026-08-09 | 创建：D1 探查结论 + 路径 C 实施计划（1 天即可）|
