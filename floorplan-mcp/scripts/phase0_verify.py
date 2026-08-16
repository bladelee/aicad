#!/usr/bin/env python3
"""Phase 0 假设验证脚本：DWG round-trip + 房间识别准确率。

跑通需要（用户提供）：
  - samples/ 下放 2 个真实装修 DWG
  - 容器内或本机装好 FreeCAD（脚本会探测 importDXF / Arch）

两个 P0 假设 → 触发备选条件（见 方案-F2 §1.1）:

  R1 房间识别准确率:
    算法识别房间数 / 设计师人工房间数
    < 70% → 触发备选 A（ezdxf+shapely）

  R3 round-trip 实体保真度:
    DWG → DXF → DWG 各类实体不丢失
    丢 > 5% → 评估是否退到只支持 DXF

用法:
    # 容器内
    python3 /opt/floorplan/scripts/phase0_verify.py /data

    # 本机（开发者）
    python3 floorplan-mcp/scripts/phase0_verify.py samples/
"""

from __future__ import annotations
import os
import sys
import json
import subprocess
from pathlib import Path
from collections import Counter


def find_samples(root: str) -> list[Path]:
    root = Path(root)
    if not root.is_dir():
        return []
    return sorted(list(root.glob("*.dwg")) + list(root.glob("*.dxf")))


# ─── R3: round-trip 对照 ───

def count_entities(dxf_path: str) -> dict:
    """用 ezdxf 统计 DXF 各类实体数 + 图层数 + 标注/填充数。"""
    import ezdxf
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    cnt = Counter(e.dxftype() for e in msp)
    return {
        "entities": dict(cnt),
        "total": sum(cnt.values()),
        "layers": len(list(doc.layers)),
        "dims": len(msp.query("DIMENSION")),
        "hatches": len(msp.query("HATCH")),
        "blocks": len([b for b in doc.blocks if not b.is_layout]),
    }


def roundtrip_one(dwg: Path, workdir: Path) -> dict:
    """DWG → DXF（ODA）→ DWG（ODA）→ 重新统计。"""
    report = {"file": dwg.name, "before": None, "after": None, "delta": {}}
    try:
        # step 1: 转 DXF
        dxf1 = workdir / (dwg.stem + ".dxf")
        if dwg.suffix.lower() == ".dwg":
            subprocess.run(
                ["ODAFileConverter", str(dwg.parent), str(workdir),
                 "ACAD2018", "0", "1", "DXF"],
                check=True, capture_output=True, timeout=120,
            )
        else:
            dxf1 = dwg

        report["before"] = count_entities(str(dxf1))

        # step 2: DXF → DWG → DXF（round-trip）
        subprocess.run(
            ["ODAFileConverter", str(workdir), str(workdir),
             "ACAD2018", "0", "1", "DWG"],
            check=True, capture_output=True, timeout=120,
        )
        rt_dwg = workdir / (dxf1.stem + ".dwg")
        subprocess.run(
            ["ODAFileConverter", str(workdir), str(workdir),
             "ACAD2018", "0", "1", "DXF"],
            check=True, capture_output=True, timeout=120,
        )
        rt_dxf = workdir / (dxf1.stem + ".dxf")
        report["after"] = count_entities(str(rt_dxf))

        # step 3: delta
        b, a = report["before"], report["after"]
        if b and a:
            report["delta"] = {
                "total_lost": b["total"] - a["total"],
                "total_lost_pct": round((b["total"] - a["total"]) / max(b["total"], 1) * 100, 2),
                "layers_lost": b["layers"] - a["layers"],
                "dims_lost": b["dims"] - a["dims"],
                "hatches_lost": b["hatches"] - a["hatches"],
                "blocks_lost": b["blocks"] - a["blocks"],
            }
    except Exception as e:
        report["error"] = str(e)
    return report


# ─── R1: 房间识别准确率（FreeCAD 链路）───

def detect_rooms_freecad(dwg: Path, workdir: Path) -> dict:
    """走 FreeCAD：DXF→draftify→makeWall→makeSpace，返回识别出的房间数。

    ⚠️ 修正 v2 §11.2：不能直接 makeSpace(裸 LINE)，
       先 importDXF + 按 WALL 关键词 draftify 成 Arch Wall。
    """
    # 先确保有 DXF
    dxf = workdir / (dwg.stem + ".dxf")
    if not dxf.exists():
        if dwg.suffix.lower() == ".dwg":
            subprocess.run(
                ["ODAFileConverter", str(dwg.parent), str(workdir),
                 "ACAD2018", "0", "1", "DXF"],
                check=True, capture_output=True, timeout=120,
            )
        else:
            dxf = dwg

    # FreeCAD 脚本（与 freecad-ai conftest 同模式：subprocess + offscreen）
    script = f"""
import sys, json
sys.path.insert(0, "/opt/floorplan")
import FreeCAD as App
import importDXF, Draft, Arch

App.newDocument("P0")
doc = App.ActiveDocument
importDXF.insert(u"{dxf}", doc.Name)
doc.recompute()

# 关键：仅对含 WALL 关键词的对象 draftify 成墙
WALL_KW = ("WALL", "WALLS", "W-WALL", "墙")
walls = []
for obj in list(doc.Objects):
    label = (getattr(obj, "Label", "") or obj.Name).upper()
    if any(k in label for k in WALL_KW):
        try:
            # draftify 把 LINE/DWire 转 Draft 线 + 再 Arch.makeWall
            Draft.draftify(obj, delete=False)
            aw = Arch.makeWall(obj)
            if aw:
                walls.append(aw)
        except Exception as e:
            pass

doc.recompute()
n_rooms = 0
total_area = 0.0
if walls:
    try:
        space = Arch.makeSpace(walls)
        space.removeShape()
        doc.recompute()
        total_area = float(getattr(space, "Area", 0) or 0)
        if total_area > 1e5:
            n_rooms = 1
    except Exception as e:
        print("makeSpace error:", e)

print(json.dumps({{"walls_found": len(walls), "rooms_detected": n_rooms,
                   "space_area_m2": round(total_area/1e6, 2)}}))
App.closeDocument("P0")
sys.exit(0)
"""
    try:
        r = subprocess.run(
            ["FreeCAD", "-c", "/dev/stdin"],
            input=script, capture_output=True, text=True, timeout=120,
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        )
        # 解析最后一行 JSON
        for line in reversed(r.stdout.strip().split("\n")):
            if line.strip().startswith("{"):
                return json.loads(line)
        return {"error": "no JSON in stdout", "stderr_tail": r.stderr[-500:]}
    except Exception as e:
        return {"error": str(e)}


def detect_rooms_shapely(dxf_path: str) -> dict:
    """走 shapely（共享算法）：读 DXF → 抽 WALL 线段 → detect_rooms。

    不依赖 FreeCAD 容器，本机 miniconda Python 也能跑。
    这是 MVP 主路径，比 FreeCAD 链路更稳。
    """
    try:
        import sys as _sys
        # 让脚本能 import rooms_detect（容器/本机都能跑）
        _root = str(Path(__file__).resolve().parent.parent)
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        from backends.rooms_detect import detect_rooms
        from backends.freecad_backend import WALL_KEYWORDS

        import ezdxf
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        segs = []
        for ent in msp.query("LWPOLYLINE LINE"):
            layer = ent.dxf.layer.upper()
            if any(k in layer for k in WALL_KEYWORDS):
                if ent.dxftype() == "LWPOLYLINE":
                    pts = [(p[0], p[1]) for p in ent.get_points()]
                else:
                    pts = [(ent.dxf.start.x, ent.dxf.start.y),
                           (ent.dxf.end.x, ent.dxf.end.y)]
                for i in range(len(pts) - 1):
                    segs.append((pts[i], pts[i + 1]))
        furniture = []
        for ent in msp.query("INSERT"):
            furniture.append({
                "block": ent.dxf.name,
                "position_xy": [ent.dxf.insert.x, ent.dxf.insert.y],
            })
        rooms = detect_rooms(segs, furniture=furniture)
        return {
            "walls_found": len(segs),
            "rooms_detected": len(rooms),
            "rooms_area_m2": [r["area_m2"] for r in rooms],
            "rooms_detail": rooms,
        }
    except Exception as e:
        return {"error": str(e)}


def write_manual_template(samples, workdir, results_by_sample):
    """写人工标注模板 Markdown，设计师照填再回读。"""
    lines = ["# Phase 0 人工标注模板",
             "",
             "> 用法：对照原始 DWG（用任意 CAD viewer 打开），数清每个样本的真实房间数，",
             ">      填到下面表格，再把同份内容写成 .phase0/manual_answers.json。",
             ">      重跑 phase0_verify.py 即可算出 R1 房间识别准确率。",
             "",
             "| 文件 | 算法识别房间数 | 算法识别总面积(m²) | **人工真实房间数** | **人工真实面积(m²)** | 算法备注 |",
             "|------|--------------|------------------|------------------|---------------------|---------|"]
    for s in samples:
        r = results_by_sample.get(s.name, {})
        rooms = r.get("rooms_shapely", {})
        det = rooms.get("rooms_detected", "?")
        areas = rooms.get("rooms_area_m2", [])
        total = round(sum(areas), 2) if areas else "?"
        err = rooms.get("error", "")
        lines.append(f"| {s.name} | {det} | {total} | **__**  | **__** | {err} |")
    lines += ["",
              "## 填好后在 .phase0/ 下建 manual_answers.json：",
              "```json",
              "{",
              '  "sample1.dwg": {"real_room_count": 3, "real_total_area_m2": 95.0},',
              '  "sample2.dwg": {"real_room_count": 4, "real_total_area_m2": 120.0}',
              "}",
              "```",
              "然后重跑：python scripts/phase0_verify.py /data"]
    out = workdir / "manual_template.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def compute_accuracy(report, workdir):
    """回读 manual_answers.json 算 R1 准确率 + 出最终 verdict。"""
    ans_path = workdir / "manual_answers.json"
    if not ans_path.exists():
        return None  # 未填，跳过
    answers = json.loads(ans_path.read_text(encoding="utf-8"))
    rows = []
    for s in report["samples"]:
        name = s["file"]
        ans = answers.get(name)
        if not ans:
            continue
        det = s["rooms_shapely"].get("rooms_detected", 0)
        real = ans.get("real_room_count", 0)
        ok = det == real
        rows.append({
            "file": name,
            "detection": det,
            "real": real,
            "match": ok,
            "detected_area": round(sum(s["rooms_shapely"].get("rooms_area_m2", [])), 2),
            "real_area": ans.get("real_total_area_m2"),
        })
    if not rows:
        return None
    match_rate = sum(1 for r in rows if r["match"]) / len(rows)
    area_err = []
    for r in rows:
        if r["real_area"] and r["detected_area"]:
            err = abs(r["detected_area"] - r["real_area"]) / max(r["real_area"], 1)
            area_err.append(err)
    avg_area_err = round(sum(area_err) / len(area_err) * 100, 2) if area_err else None
    return {
        "rows": rows,
        "room_match_rate_pct": round(match_rate * 100, 1),
        "room_match_pass": match_rate >= 0.7,
        "area_avg_err_pct": avg_area_err,
        "area_pass": (avg_area_err is None) or (avg_area_err < 5),
    }


def main(samples_dir: str):
    samples = find_samples(samples_dir)
    if not samples:
        print(f"❌ 未在 {samples_dir} 找到 .dwg/.dxf 样本")
        print("   请把 2 个真实装修 DWG 放到 samples/（或容器内 /data）后重跑。")
        sys.exit(1)

    workdir = Path(samples_dir) / ".phase0"
    workdir.mkdir(exist_ok=True)

    report = {"samples": [], "verdict": {}}
    results_by_sample = {}
    for s in samples:
        print(f"\n==> 处理 {s.name}")
        rt = roundtrip_one(s, workdir)
        # 优先 shapely（不依赖 FreeCAD，更稳）
        shp = detect_rooms_shapely(str(workdir / (s.stem + ".dxf"))
                                   if (workdir / (s.stem + ".dxf")).exists()
                                   else str(s))
        fc = detect_rooms_freecad(s, workdir)  # 备用对照
        sample = {
            "file": s.name,
            "roundtrip": rt,
            "rooms_shapely": shp,
            "rooms_freecad": fc,
        }
        report["samples"].append(sample)
        results_by_sample[s.name] = sample

    # ─── 判定 roundtrip ───
    avg_loss = sum(s["roundtrip"].get("delta", {}).get("total_lost_pct", 0)
                   for s in report["samples"]) / max(len(report["samples"]), 1)
    report["verdict"] = {
        "roundtrip_avg_loss_pct": round(avg_loss, 2),
        "roundtrip_pass": avg_loss < 5,
    }

    # ─── 写人工标注模板 ───
    tmpl = write_manual_template(samples, workdir, results_by_sample)

    # ─── 若设计师已填 manual_answers.json，算 R1 ───
    acc = compute_accuracy(report, workdir)
    if acc:
        report["verdict"]["room_detection"] = acc
    else:
        report["verdict"]["room_detection"] = "待人工标注（模板已写）"

    # ─── 最终建议 ───
    rec = []
    if avg_loss >= 5:
        rec.append("⚠️ R3 round-trip 失败（>5% 实体丢失）→ 评估是否只支持 DXF")
    else:
        rec.append(f"✅ R3 round-trip 通过（{round(avg_loss,2)}% 丢失）")
    if acc:
        if acc["room_match_pass"] and acc["area_pass"]:
            rec.append(f"✅ R1 房间识别通过（匹配率 {acc['room_match_rate_pct']}%，面积误差 {acc['area_avg_err_pct']}%）")
        else:
            rec.append(f"⚠️ R1 不达标 → 排查墙体关键词匹配，必要时加映射表")
    else:
        rec.append(f"📋 R1 待人工标注：打开 {tmpl} 填 → .phase0/manual_answers.json → 重跑")
    report["verdict"]["recommendation"] = "\n".join(rec)

    out = workdir / "phase0_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    print(f"\n==> 报告已写 {out}")
    print("==> " + "\n==> ".join(rec))

    if avg_loss >= 5:
        sys.exit(2)


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SAMPLES_DIR", "/data")
    main(src)
