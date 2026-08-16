"""共享房间识别算法——shapely polygonize（planar-graph face detection）。

由 freecad_backend 和 ezdxf_backend **共用调用**，保证主备 backend 的
房间数永远一致。这是 v3-final 后定下的架构原则（避免 Arch Space 的不确定
性 + 备选切换结果对不上）。

边界用例验证见 tests/test_rooms_edge_cases.py（7 个真实结构形态全过）。

输入: 一组 2D 墙线段 [(p1_xy, p2_xy), ...]，单位 mm
输出: list[dict] 排序后的房间
  {
    "name": "Room1",
    "area_m2": float,
    "boundary": [[x,y], ...],
    "furniture": [block_name, ...]，                        # 调用方注入
    "furniture_inside": [block_name, ...]，                  # 算法分配（可选）
  }
"""

from __future__ import annotations
from typing import Sequence, Iterable


def detect_rooms(
    wall_segments: Iterable[tuple[Sequence[float], Sequence[float]]],
    *,
    min_area_m2: float = 0.5,
    furniture: Sequence[dict] | None = None,
    close_openings_mm: float | None = None,
) -> list[dict]:
    """识别房间。

    Args:
        wall_segments: 墙线段迭代，每段 ((x1,y1),(x2,y2))，单位 mm
        min_area_m2: 面积阈值，过滤碎片（默认 0.5 m²）
        furniture: 可选家具列表（dict 含 block + position_xy），算法会把
                   每件家具按 point-in-polygon 归属到房间。None 则每个房间的
                   furniture_inside 为空。
        close_openings_mm: **真实装修图门洞/窗洞让外墙断开，shapely 无法闭合**。
            若设，距离 ≤ 此值的端点对会被补一条"虚拟墙"再 polygonize。
            推荐 1000mm（典型 900/1000m 门洞尺度），None 关闭此行为。
            ⚠️ 这是 2026-08-08 调研 mock_realistic 暴露的 P0 风险缓解路径，
            真实 Phase 0 样本到来时必须确认此阈值是否合适。

    返回按面积从大到小排序的房间列表。
    """
    try:
        from shapely.ops import unary_union, polygonize
        from shapely.geometry import LineString, Point
    except ImportError:
        return []  # 调用方会降级（无 shapely → 房间识别不可用）

    segs = []
    for a, b in wall_segments:
        if len(a) < 2 or len(b) < 2:
            continue
        segs.append(LineString([(float(a[0]), float(a[1])),
                                (float(b[0]), float(b[1]))]))
    if not segs:
        return []

    # ── 真实装修图门洞/窗洞导致墙断开，polygonize 无法闭合房间 ──
    # 补虚拟墙：扫所有线段端点，距离 ≤ close_openings_mm 的端点对补一段
    # 这是 shapely polygonize 处理真实图的关键预处理（2026-08-08 调研发现）
    if close_openings_mm:
        endpoints = []
        for s in segs:
            endpoints.append((s.coords[0]))
            endpoints.append((s.coords[-1]))
        # 端点去重 + 配对距离过滤
        seen = set()
        unique_ep = []
        for ep in endpoints:
            key = (round(ep[0], 1), round(ep[1], 1))
            if key not in seen:
                seen.add(key)
                unique_ep.append(ep)
        for i, p1 in enumerate(unique_ep):
            for p2 in unique_ep[i + 1:]:
                d = ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5
                if 0 < d <= close_openings_mm:
                    # 补一段桥接线（让 polygonize 能跨门洞闭合）
                    segs.append(LineString([p1, p2]))

    min_area_mm2 = min_area_m2 * 1e6
    rooms = []
    polys = list(polygonize(unary_union(segs)))
    for poly in polys:
        area_mm2 = poly.area
        if area_mm2 < min_area_mm2:
            continue
        # 家具归属（可选）：用旋转后的块中心；这里家具 dict 可能只有 position_xy
        fur_inside: list[str] = []
        if furniture:
            for f in furniture:
                pos = f.get("position_xy") or f.get("position") or \
                    f.get("insert")  # ezdxf/freecad 不同字段兼容
                if not pos or len(pos) < 2:
                    continue
                try:
                    if Point(float(pos[0]), float(pos[1])).within(poly):
                        name = f.get("block") or f.get("block_name") or "?"
                        fur_inside.append(name)
                except Exception:
                    pass
        rooms.append({
            "name": f"Room{len(rooms) + 1}",
            "area_m2": round(area_mm2 / 1e6, 2),
            "boundary": [list(p) for p in poly.exterior.coords],
            "furniture": fur_inside[:5],  # 与原用法一致，最多 5
        })
    rooms.sort(key=lambda r: -r["area_m2"])
    return rooms
