# tools/dxf_scan

## 它是什么

扫描 DXF 文件结构，建立"跨图纸关联图谱"。基于 ezdxf。

## 包含

- `scan_dxf.py` —— 扫描入口脚本
- `doc_to_shapes.py` —— DXF → 内部 shape 列表（"局部图形可重放包"），借鉴 wheel-drawing-tools 的 `_doc_to_shapes`，扩展支持 HATCH。`python doc_to_shapes.py <file.dxf> --layer NAME` 即可导出 JSON（详见 `docs/借鉴-wheel-drawing-tools-参数化模式.md` §五 A2）
- `test_doc_to_shapes.py` —— 19 个单测（`python test_doc_to_shapes.py` 直接跑，无 pytest 依赖）

## 用法

在 floorplan-mcp 容器内跑（需要 ezdxf + shapely）：

```bash
docker run --rm -v "$PWD:/data" \
    -e PYTHONHOME=/opt/FreeCAD/usr \
    -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
    -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
    --entrypoint=/bin/bash \
    floorplan-mcp:latest \
    -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_scan/scan_dxf.py"
```

输出：
- 控制台：每张图的实体数、图层数、公共图层、公共块、ST-XX 材料编号
- `workdir/19-102/scan_report.json`：完整报告（含所有 attribs / text_strings）

## 改进方向

⚠️ **当前版本只扫 modelspace**。下面 2 张图扫出 0 实体是因为内容全在 paper space：
- `1-封面、目录、设计说明.dxf`
- `2-材料表.dxf`

下一步需要升级扫描循环：

```python
# 当前
for ent in msp:
    ...

# 升级后
for layout in doc.layouts:
    for ent in layout:
        # 同时记录 layout_name
        ...
```

否则扫不到用户最关心的「目录编号表 + 完整 ST 材料表」。
