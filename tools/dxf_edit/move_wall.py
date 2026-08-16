"""任务 #1: 改一堵墙的正式函数封装。

把之前 demo_move_wall.py 升级成可参数化调用的模块，支持：
  - 通过 handle / 坐标点 / 序号 三种方式选墙
  - 平移整段墙（dx, dy）而不是单纯伸长端点
  - 自动备份 + 轮转命名（.bak1, .bak2...）
  - 可选同步联动图层（A原建筑墙体填充等）

封装入口：move_wall(dxf_path, wall_handle=None, point=None, idx=0,
                    dx=0, dy=0, mode='translate'/'extend-end',
                    sync_layers=True, backup_dir=None) -> dict

宿主机用：
    docker run --rm -v "$PWD:/data" \
        -e PYTHONHOME=/opt/FreeCAD/usr \
        -e LD_LIBRARY_PATH=/opt/FreeCAD/usr/lib \
        -e SSL_CERT_FILE=/opt/FreeCAD/usr/ssl/cacert.pem \
        --entrypoint=/bin/bash \
        floorplan-mcp:latest \
        -lc "/opt/FreeCAD/usr/bin/python /data/tools/dxf_edit/move_wall.py"
"""
from __future__ import annotations
import os
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

import ezdxf

# 借鉴 wheel-drawing-tools 的表达式引擎（docs/借鉴-wheel-drawing-tools-参数化模式.md A1）
# 允许 dx/dy 用表达式字符串，例如 dx="wall_length*0.1" 或 dx="PCD*sin(30*pi/180)"
try:
    # 同目录导入
    from param_expr import eval_expr, params_for_eval
except ImportError:  # pragma: no cover — 仅在没把 tools/dxf_edit/ 暴露到 sys.path 时退化
    eval_expr = None
    params_for_eval = None

WALL_LAYER = "A原建筑墙体"
# 改墙时希望联动的同族图层（hatch 边界 + 标注图层）
SYNC_LAYER_CANDIDATES = [
    "A原建筑墙体填充",
    # "A原建筑尺寸"  # 标注联动是 #3 的硬骨头，这里先不开
]


def _resolve_offset(value, params: Optional[dict] = None) -> float:
    """把 dx/dy 数值或表达式字符串解析为 float。

    - value 是 int/float → 直接 float
    - value 是 str（如 ``"W*0.1"``）→ 用 param_expr.eval_expr 求值
    - 没有 param_expr 可用、或表达式异常 → 退化为 float(value)，再退化则 0.0

    这样调用方既可以继续传 ``dx=500``（老调用方式 100% 向后兼容），
    也可以传 ``dx="W*0.1", params={"W": 5000}``。
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    # 字符串 / 其它
    if eval_expr is not None:
        try:
            return eval_expr(value, params_for_eval(params or {}) if params_for_eval else {})
        except Exception:
            pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def safe_saveas(doc, path: Path):
    """绕开 ezdxf 1.4.4 materials 字典 bug"""
    original = type(doc)._update_header_vars

    def patched(self):
        try:
            original(self)
        except AttributeError as e:
            print(f"  [warn] 跳过 header materials 更新: {e}")

    type(doc)._update_header_vars = patched
    try:
        doc.saveas(str(path))
    finally:
        type(doc)._update_header_vars = original


def backup_with_rotate(src: Path, backup_dir: Path) -> Path:
    """备份源文件到 backup_dir/<name>.bakN.dxf，N 自增轮转。
    首次执行：.bak1.dxf；第二次：.bak2.dxf ..."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    n = 1
    while True:
        bak = backup_dir / f"{src.stem}.bak{n}.dxf"
        if not bak.exists():
            shutil.copy2(src, bak)
            return bak
        n += 1


def find_wall(msp, handle: Optional[str] = None,
              point: Optional[tuple] = None, idx: int = 0):
    """三种方式选墙"""
    walls = [e for e in msp
             if e.dxftype() == "LINE" and e.dxf.layer == WALL_LAYER]
    if not walls:
        raise ValueError(f"在图层 {WALL_LAYER!r} 下没找到任何 LINE")

    if handle:
        for w in walls:
            if w.dxf.handle == handle:
                return w, walls
        raise ValueError(f"handle={handle} 未在墙体图层找到")

    if point:
        # 找距离 point 最近的墙（按端点距离）
        x, y = point[0], point[1]
        def dist(w):
            s, e = w.dxf.start, w.dxf.end
            return min((s[0]-x)**2 + (s[1]-y)**2,
                       (e[0]-x)**2 + (e[1]-y)**2)
        walls.sort(key=dist)
        return walls[0], walls

    return walls[idx], walls


def shift_line(ent, dx, dy, mode: str, params: Optional[dict] = None):
    """mode='translate': 整段平移
       mode='extend-end': 只动 end（伸长/缩短）

    dx/dy 可以是数字（float）或表达式字符串（如 ``"W*0.1"``）。
    表达式形式时需要传 params 提供参数字典。
    """
    dx = _resolve_offset(dx, params)
    dy = _resolve_offset(dy, params)
    s = tuple(ent.dxf.start)
    e = tuple(ent.dxf.end)
    if mode == "translate":
        ent.dxf.start = (s[0]+dx, s[1]+dy, s[2])
        ent.dxf.end = (e[0]+dx, e[1]+dy, e[2])
    elif mode == "extend-end":
        ent.dxf.end = (e[0]+dx, e[1]+dy, e[2])
    else:
        raise ValueError(f"未知 mode: {mode}")


def shift_layer_entities(msp, layer: str, dx, dy, params: Optional[dict] = None) -> int:
    """把指定图层下所有实体的几何平移，返回处理实体数。

    dx/dy 支持数字或表达式字符串（同 shift_line）。
    只动 LINE/LWPOLYLINE/CIRCLE/ARC/HATCH/INSERT/MTEXT/TEXT 等典型几何实体的关键坐标。
    简化策略：HATCH 的边界由关联的 LWPOLYLINE 决定，不动 HATCH 本身。
    """
    dx = _resolve_offset(dx, params)
    dy = _resolve_offset(dy, params)
    n = 0
    for ent in msp:
        if ent.dxf.layer != layer:
            continue
        etype = ent.dxftype()
        try:
            if etype == "LINE":
                s, e = ent.dxf.start, ent.dxf.end
                ent.dxf.start = (s[0]+dx, s[1]+dy, s[2])
                ent.dxf.end = (e[0]+dx, e[1]+dy, e[2])
                n += 1
            elif etype in ("LWPOLYLINE",):
                # lwpolyline.points_with_bbox 返回的是 tuple
                pts = [(p[0]+dx, p[1]+dy) + tuple(p[2:]) for p in ent.get_points()]
                ent.set_points(pts)
                # 标 dxf 需要重新算
                n += 1
            elif etype in ("CIRCLE",):
                c = ent.dxf.center
                ent.dxf.center = (c[0]+dx, c[1]+dy, c[2])
                n += 1
            elif etype == "ARC":
                c = ent.dxf.center
                ent.dxf.center = (c[0]+dx, c[1]+dy, c[2])
                n += 1
            elif etype == "INSERT":
                p = ent.dxf.insert
                ent.dxf.insert = (p[0]+dx, p[1]+dy, p[2])
                n += 1
            elif etype in ("TEXT", "MTEXT"):
                p = ent.dxf.insert
                ent.dxf.insert = (p[0]+dx, p[1]+dy, p[2])
                n += 1
        except Exception:
            continue
    return n


def move_wall(
    dxf_path: Path,
    handle: Optional[str] = None,
    point: Optional[tuple] = None,
    idx: int = 0,
    dx=0.0,
    dy=0.0,
    mode: str = "translate",
    sync_layers: bool = True,
    backup_dir: Optional[Path] = None,
    output_suffix: str = "_moved",
    params: Optional[dict] = None,
) -> dict:
    """主入口。

    dx/dy 既可以是数字（老路）也可以是表达式字符串（``"W*0.1"`` 等），
    表达式形式时必须传 params 提供参数字典，例如::

        move_wall(path, idx=0, dx="W*0.1", params={"W": 5000})

    支持的 params 来源可以是用户输入，也可以是另一张图算出来的几何量。
    """
    print(f"=== move_wall ===")
    print(f"  输入 : {dxf_path.name}")
    print(f"  偏移 : dx={dx!r}, dy={dy!r}, mode={mode}"
          + (f", params={params}" if params else ""))

    # 先把 dx/dy 解析成最终数值（既用于实际平移，也用于日志校对）
    dx_val = _resolve_offset(dx, params)
    dy_val = _resolve_offset(dy, params)
    if isinstance(dx, str) or isinstance(dy, str):
        print(f"  解析 : dx={dx}→{dx_val:.3f}, dy={dy}→{dy_val:.3f}")

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    n_before = sum(1 for _ in msp)

    # 选墙
    wall, all_walls = find_wall(msp, handle=handle, point=point, idx=idx)
    print(f"  选中 : handle={wall.dxf.handle}, layer={wall.dxf.layer}")
    print(f"  原始 : start={tuple(round(c,1) for c in wall.dxf.start)}")
    print(f"          end  ={tuple(round(c,1) for c in wall.dxf.end)}")

    # 改主墙（把 params 透传下去，统一在 shift_line 内部解析）
    shift_line(wall, dx, dy, mode, params=params)
    print(f"  改后 : start={tuple(round(c,1) for c in wall.dxf.start)}")
    print(f"          end  ={tuple(round(c,1) for c in wall.dxf.end)}")

    # 联动同族图层（同样的 dx/dy 平移）
    affected_layers = {}
    if sync_layers and mode == "translate":
        for layer in SYNC_LAYER_CANDIDATES:
            n = shift_layer_entities(msp, layer, dx, dy, params=params)
            if n > 0:
                affected_layers[layer] = n
                print(f"  联动 : {layer} 平移了 {n} 个实体")

    # 备份
    if backup_dir is not None:
        bak = backup_with_rotate(dxf_path, backup_dir)
        print(f"  备份 : {bak.name}")
    else:
        bak = None

    # 输出
    out = dxf_path.with_name(f"{dxf_path.stem}{output_suffix}.dxf")
    safe_saveas(doc, out)
    print(f"  输出 : {out.name}")

    # round-trip 数量
    doc2 = ezdxf.readfile(str(out))
    n_after = sum(1 for _ in doc2.modelspace())
    types_before = Counter(e.dxftype() for e in msp)
    types_after = Counter(e.dxftype() for e in doc2.modelspace())
    diff = {k: (types_before.get(k, 0), types_after.get(k, 0))
            for k in set(types_before) | set(types_after)
            if types_before.get(k, 0) != types_after.get(k, 0)}

    return {
        "input": str(dxf_path),
        "output": str(out),
        "backup": str(bak) if bak else None,
        "wall_handle": wall.dxf.handle,
        # 同时记录"原始表达式"和"解析后的数值"，便于日志/审计回溯
        "shift": {
            "dx": dx, "dy": dy, "mode": mode,
            "dx_resolved": dx_val, "dy_resolved": dy_val,
            "params": params or None,
        },
        "synced_layers": affected_layers,
        "round_trip": {
            "before": n_before, "after": n_after,
            "type_diff": diff,
        },
    }


# 作为脚本跑：默认对 3-平面图找一个长墙平移
if __name__ == "__main__":
    base = Path("/data/workdir/19-102/dxf/3-19-102平面系统图.dxf")
    bak_dir = Path("/data/workdir/19-102/backups/move_wall")
    # 用 env 参数化
    dx = float(os.environ.get("DX", "500"))
    dy = float(os.environ.get("DY", "0"))
    mode = os.environ.get("MODE", "translate")
    out_suffix = os.environ.get("OUTPUT_SUFFIX", f"_moved_{int(dx)}_{int(dy)}")

    result = move_wall(
        dxf_path=base,
        idx=0,  # 默认第 0 条墙
        dx=dx, dy=dy,
        mode=mode,
        sync_layers=True,
        backup_dir=bak_dir,
        output_suffix=out_suffix,
    )
    print(f"\n=== 返回 ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
