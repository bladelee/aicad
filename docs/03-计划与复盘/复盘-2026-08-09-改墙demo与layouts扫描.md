# 复盘：要求 #1 改墙链路 + Layouts 扫描升级（2026-08-09）

> 创建：2026-08-09 03:23
> 关联：`docs/05-知识沉淀/DXF扫描报告.md`、`docs/07-目录整理/目录整理方案-dwg目录整理草案.md`、`复盘-2026-08-09-DWG转换与图纸摸底.md`
> 摘要：完成 3 个遗留任务（XData 解析 / move_wall demo / scan 升级 layouts），**推翻了"天正自定义对象"假设**——墙就是普通 LINE，可直接改。

---

## TL;DR

| 任务 | 结论 | 关键数字 |
|------|------|---------|
| 1. 解析天正 XData → 改墙 | ✅ **完全不需要解析！** XData/PROXY 实体数都 = 0 | 推翻假设 |
| 2. move_wall 最小 demo | ✅ **打通**全链路（含绕过 ezdxf materials bug）| 9471→9461 实体（仅丢 10 个 REGION）|
| 3. scan_dxf.py 升级扫 layouts | ✅ **解锁 0 实体问题** | 1-封面 0→522，2-材料表 0→4 |

## 一、关键认知更新（推翻昨天假设）

| 昨天认为（错的） | 今天实测（对的） |
|------------------|------------------|
| 图纸是天正画的，墙是自定义对象，需 XData 解码 | `_TCH` 只是 APPID 注册元数据，**未被任何实体使用** |
| PROXY 实体需要复杂解析 | **PROXY 实体数 = 0**（6 张全空）|
| 改墙任务阻塞天正对象解析 | **可直接开工**：墙 = LINE（`A原建筑墙体` 图层）|

证据源：`tools/dxf_scan/probe_xdata.py`
```
3-19-102平面系统图：
  业务相关 APPID: ['_TCH', 'switchboard', 'switch']
  Top 实体类型: [('LINE', 2698), ('LWPOLYLINE', 1630), ('INSERT', 1406), ...]
  PROXY 实体数: 0
  XData APPID 命中 top10: []
```

## 二、move_wall demo 完整链路

### 2.1 选材
- 输入：`workdir/19-102/dxf/3-19-102平面系统图.dxf`（22 MB, 9471 实体）
- 目标图层：`A原建筑墙体`（含 244 条 LINE）
- 目标墙：水平最长的一条，handle=`E6037`，从 (201902, -908615) 到 (211902, -908615)，**长 10 米**

### 2.2 改造
1. ✅ 备份原文件 → `.bak1.dxf`（用 `shutil.copy2`）
2. ✅ `target.dxf.end = (end[0] + 500, end[1], end[2])` — end 端点水平 +500mm
3. ✅ 保存到新 DXF（不动原件）

### 2.3 关键 bug + 规避

**bug**：ezdxf 1.4.4 对 libredwg 转出的 DXF 调 `doc.saveas()` 触发：
```
File "ezdxf/document.py", line 690, in _update_header_vars
    handle = self.materials.get("ByLayer").dxf.handle
AttributeError: 'str' object has no attribute 'dxf'
```
libredwg 转出的 DXF 中 `materials` 表里 "ByLayer" 是 str 而非对象。

**规避（monkey-patch）**：
```python
original_update = type(doc)._update_header_vars
def safe_update_header(self):
    try:
        original_update(self)
    except AttributeError as e:
        print(f"  [warn] 跳过 header materials 更新: {e}")
type(doc)._update_header_vars = safe_update_header
doc.saveas(str(OUTPUT_DXF))
```

### 2.4 round-trip 验证结果

| 检查项 | 结果 |
|--------|------|
| 改造保持 | ✅ handle=E6037 的 end.x **211902.1 → 212402.1** |
| 实体数 | ⚠️ **9471 → 9461**（丢 10 个） |
| 类型变化 | ⚠️ 仅 `REGION: 10 → 0` |
| 文件大小 | 22M → 16M（缩 26.4%） |

→ **对 2D 业务无影响**（墙/门窗/标注都不依赖 REGION）。REGION 是 3D 边界表示（ACIS），ezdxf 文档明确不写。

## 三、Layouts 扫描升级结果

`tools/dxf_scan/scan_dxf.py` 升级为遍历 `doc.layouts`（含 paper space），各图实体数变化：

| 文件 | 旧（仅 Model）| 新（含 layouts）| 新增在哪个 layout |
|------|---:|---:|------|
| 1-封面/目录 | 0 | **522** | Layout1（即 paper space）|
| 2-材料表 | 0 | **4**（3 attribs）| 布局1 |
| 3-平面系统图 | 9,471 | 10,332 | Model + 布局1（+861）|
| 4-立面图 | 19,775 | 19,776 | Model + Layout1（+1，仅图框）|
| 5-节点 | 22,723 | 23,549 | Model + Layout1（+826）|
| XINLU-A2 | 85 | 85 | Model |

新增 ST 编号发现：**ST-08**（在 5-节点 的 *U1631/1620/1621 块属性 tag=ST-01 里）。

## 四、4 个新工具沉淀

| 脚本 | 用途、调用方式 |
|------|--------------|
| `tools/dxf_scan/probe_xdata.py` | 探查 PROXY/XData 分布 |
| `tools/dxf_scan/scan_dxf.py`（升级）| 扫所有 layouts 出跨图分析报告 |
| `tools/dxf_scan/demo_move_wall.py` | 改墙 demo 主程序 |
| `tools/dxf_scan/verify_roundtrip.py` | 改造前后实体数/handle 对比 |

容器内统一调用模板：
```bash
docker run --rm -v "$PWD:/data" \
    -e PYTHONHOME=/opt/FreeCAD/usr \
    -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
    -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
    --entrypoint=/bin/bash \
    floorplan-mcp:latest \
    -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_scan/<script>.py"
```

## 五、5 条新教训

1. **探针证实假设**：天正块名前缀 ≠ 实体是真天正对象。`$TCHSYS$WIN2D` 只是块命名风格，内容可能是普通 LINE。
2. **先看实体类型再决定算法**：`Counter(e.dxftype() for e in msp)` 一行就看清。
3. **不要假设 libredwg 转换丢字段**：实测 6 张图所有几何实体（LINE/POLYLINE/INSERT/DIMENSION）全部保留，仅 REGION 等不常见 ACIS 实体写回时丢。
4. **ezdxf 1.4.4 在含变种 DXF 时几次坑**：
   - materials 表 update bug（这次撞到）
   - POLYLINE 容器迭代 bug（v2 时期撞过）
   - 解决思路统一：**monkey-patch + try/except，而不是 fork ezdxf**
5. **DXF 文件大小骤减不一定是 bug**：libredwg 转换保留所有 ACIS 文本（占体积），ezdxf 写回压缩了。
