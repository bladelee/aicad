"""
extract_dimensions — 从 DXF 抽 DIMENSION 实体（19-102 复盘发现的工程缺口）

背景：docs/DXF扫描报告.md 当前只统计实体类型和图层，**1367 个 DIMENSION 实体里的尺寸数字未被解析**。
本工具补这个缺口。

输出 JSON 结构（每条）:
    {
        "handle": "1F0",                # ezdxf 实体 handle，可用于后续 edit/校验
        "layer": "A原建筑尺寸",          # 所属图层
        "actual_mm": 4000.0,             # ezdxf get_measurement() 算出的实际值（mm）
        "override_text": "",             # 显式覆盖文字（空表示用 actual）
        "block_name": "*D0",             # DIMENSION 的匿名块名
        "geom": {                        # 几何关键点（用于回溯到图上位置）
            "definition_point": [x, y, z],
            "insert": [x, y, z],         # 文本插入点
            "text_mid": [x, y, z],
        }
    }

用法：
    python tools/dxf_scan/extract_dimensions.py \\
        workdir/19-102/dxf/3-19-102平面系统图.dxf \\
        --out tmp_vision/phase_h0/dimensions_plan.json

设计依据：方案-H §3 Phase H-0 交付清单
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from collections import Counter

import ezdxf


def extract(doc_path: str) -> dict:
    doc = ezdxf.readfile(doc_path)
    items: list[dict] = []
    by_layer: Counter = Counter()
    by_layer_value: dict[str, list[float]] = {}
    err_count = 0

    for e in doc.modelspace():
        try:
            if e.dxftype() != "DIMENSION":
                continue
            actual = e.get_measurement() if hasattr(e, "get_measurement") else 0.0
            override = e.dxf.get("text", "") or ""
            layer = e.dxf.layer or ""
            by_layer[layer] += 1
            if isinstance(actual, (int, float)) and actual > 0:
                by_layer_value.setdefault(layer, []).append(float(actual))
            geom: dict = {}
            for k in ("definition_point", "insert", "text_mid"):
                try:
                    p = getattr(e.dxf, k)
                    geom[k] = [p.x, p.y, p.z]
                except (AttributeError, KeyError):
                    pass
            items.append({
                "handle": e.dxf.handle,
                "layer": layer,
                "actual_mm": float(actual) if actual is not None else None,
                "override_text": str(override),
                "block_name": e.dxf.get("geometry", None) and "",  # 简化
                "geom": geom,
            })
        except Exception:
            err_count += 1

    # 摘要
    summary = {
        "file": os.path.basename(doc_path),
        "total_dimensions": len(items),
        "by_layer": dict(by_layer),
        "by_layer_value_stats": {
            layer: {
                "n": len(vals),
                "min": min(vals),
                "max": max(vals),
                "avg": sum(vals) / len(vals),
            }
            for layer, vals in by_layer_value.items()
            if vals
        },
        "errors": err_count,
    }
    return {"summary": summary, "items": items}


def _cli() -> int:
    p = argparse.ArgumentParser(description="从 DXF 抽 DIMENSION 实体为 JSON")
    p.add_argument("dxf", help="DXF 文件路径")
    p.add_argument("--out", required=True, help="输出 JSON 路径")
    args = p.parse_args()

    data = extract(args.dxf)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    s = data["summary"]
    print(f"✅ {s['file']}: {s['total_dimensions']} DIMENSION, "
          f"{len(s['by_layer'])} 图层, errors={s['errors']}")
    print(f"   written: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
