# -*- coding: utf-8 -*-
"""
参数化坐标表达式引擎 — 借鉴 wheel-drawing-tools（Rosyal/wheel-drawing-tools）。

设计意图（见 docs/借鉴-wheel-drawing-tools-参数化模式.md 模式 1/2/3）：
  - 几何/平移量可以用 **表达式字符串**（如 ``"L/2"``、``"PCD*sin(30*pi/180)"``）
    而不是字面量；同一份模板用不同参数即时产出不同坐标
  - 统一接口：所有取坐标/取平移量的地方都走 ``get_num()``
  - ``flatten_shapes()`` 把参数化图形先求值成绝对坐标，再 ``scale`` + ``dx/dy``
    搬运到目标位置（多视图合成、跨视图联动都靠它）

源码直接对齐 wheel 项目的 ``drawing_engine.py`` / ``cad_dxf.py``，只做了：
  1. 命名去掉前导下划线（公开 API，便于 move_wall.py 等工具导入）
  2. 加 docstring + 中文注释，方便团队理解
  3. 补一组单测（tests/test_param_expr.py）

保留的关键安全约束：
  - ``eval`` 的 namespace 禁掉 ``__builtins__``，只放 ``sqrt/cos/sin/pi``
  - 表达式异常时返回 0.0（不让一处坐标算错中断整张图）

宿主机 ezdxf 1.4.4 已可直用（见 floorplan-mcp 容器内同样可用）。
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List

__all__ = [
    "eval_expr",
    "get_num",
    "params_for_eval",
    "flatten_shapes",
]


# ---------- 模式 2：表达式求值 + 统一取值 ----------

def eval_expr(expr: Any, params: Dict[str, float]) -> float:
    """将表达式求值，支持参数名、四则运算及 sqrt/cos/sin/pi。

    - 数字/浮点直接返回
    - 字符串先按 ``\\b 单词边界`` 把参数名替换成数值，再 `eval`
    - 任何异常（未知参数、语法错、除零）返回 0.0，避免一处坏点中断整图

    Examples:
        >>> eval_expr(100, {})
        100.0
        >>> eval_expr("L/2", {"L": 200})
        100.0
        >>> round(eval_expr("PCD/2*cos(60*pi/180)", {"PCD": 200}), 6)
        50.0
        >>> eval_expr("undefined_name + 1", {})
        0.0
    """
    if isinstance(expr, (int, float)):
        return float(expr)
    s = str(expr).strip()
    for name, val in params.items():
        # 用 \b 单词边界，避免短参数名（如 L）误伤到 "LINE" 里的 "L"
        s = re.sub(rf"\b{re.escape(name)}\b", str(val), s)
    safe = {"sqrt": math.sqrt, "cos": math.cos, "sin": math.sin, "pi": math.pi}
    try:
        return float(eval(s, {"__builtins__": {}}, safe))  # noqa: S307 (deliberate, sandboxed)
    except Exception:
        return 0.0


def get_num(attrs: Dict, key: str, params: Dict[str, float], default: float = 0) -> float:
    """统一取值接口：从字典里取 ``key``，缺失或表达式错误都回退到 default。

    Attributes 是 shape_definition 里的一项；``params`` 既可以是含表达式键的
    混合字典（被 params_for_eval 清洗），也可以是已经求值过的纯 float 字典。
    """
    return eval_expr(attrs.get(key, default), params)


def params_for_eval(params: Dict[str, Any]) -> Dict[str, float]:
    """将混合类型参数字典清洗为可参与表达式求值的纯 float 字典。

    - bool 不参与（True/False 进表达式会变成 1/0 误导）
    - int/float 直接转
    - 纯数字字符串（如 "500"）也转，方便从 env / CLI 拿到的值直接用
    - 其他（型号名、备注等）丢弃
    """
    out: Dict[str, float] = {}
    for k, v in params.items():
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            out[k] = float(v)
        elif isinstance(v, str) and v.strip():
            try:
                out[k] = float(v)
            except ValueError:
                pass
    return out


# ---------- 模式 3：flatten_shapes 多视图组合 ----------

def flatten_shapes(
    shape_definition: List[Dict],
    params: Dict[str, Any],
    scale: float = 1.0,
    dx: float = 0.0,
    dy: float = 0.0,
) -> List[Dict[str, Any]]:
    """把含表达式的图形求值为常量坐标，便于平移/缩放后合并导出 DXF/MCP 包。

    Args:
        shape_definition: 形如 ``[{"type": "rect", "x": "L/2", ...}, ...]``
        params: 参数字典（可含字符串/型号等非数值键，内部会过滤）
        scale: 整体缩放（半径/宽高/坐标都 * scale）
        dx, dy: 缩放后再叠加的平移（半径不叠加平移）

    Returns:
        全部坐标都是 float 字面量的 shape 列表，原样可喂给 ezdxf 画出来。

    场景对应本项目：
      #4/#5/#9 跨视图联动 — 平面图改过的墙线先 flatten 到绝对坐标，
      再 (dx, dy) 整体搬到立面/节点图的对应位置。
    """
    fp = params_for_eval(params)
    out: List[Dict[str, Any]] = []
    for sh in shape_definition:
        kind = (sh.get("type") or "line").lower()
        if kind == "rect":
            out.append({
                "type": "rect",
                "x": get_num(sh, "x", fp) * scale + dx,
                "y": get_num(sh, "y", fp) * scale + dy,
                "width": get_num(sh, "width", fp) * scale,
                "height": get_num(sh, "height", fp) * scale,
                "fill": sh.get("fill", True),
                "facecolor": sh.get("facecolor", "lightgray"),
                "edgecolor": sh.get("edgecolor", "black"),
            })
        elif kind == "circle":
            out.append({
                "type": "circle",
                "cx": get_num(sh, "cx", fp) * scale + dx,
                "cy": get_num(sh, "cy", fp) * scale + dy,
                "r": get_num(sh, "r", fp) * scale,
                "fill": sh.get("fill", True),
                "facecolor": sh.get("facecolor", "lightgray"),
                "edgecolor": sh.get("edgecolor", "black"),
            })
        elif kind == "arc":
            out.append({
                "type": "arc",
                "cx": get_num(sh, "cx", fp) * scale + dx,
                "cy": get_num(sh, "cy", fp) * scale + dy,
                "r": get_num(sh, "r", fp) * scale,
                "start_angle": get_num(sh, "start_angle", fp),
                "end_angle": get_num(sh, "end_angle", fp),
                "edgecolor": sh.get("edgecolor", "black"),
            })
        elif kind == "line":
            out.append({
                "type": "line",
                "x1": get_num(sh, "x1", fp) * scale + dx,
                "y1": get_num(sh, "y1", fp) * scale + dy,
                "x2": get_num(sh, "x2", fp) * scale + dx,
                "y2": get_num(sh, "y2", fp) * scale + dy,
                "color": sh.get("color", "black"),
                "linewidth": eval_expr(sh.get("linewidth", 1.5), fp),
            })
        elif kind == "text":
            text = str(sh.get("text", ""))
            for pname, pval in params.items():
                text = text.replace("{" + pname + "}", str(pval))
            out.append({
                "type": "text",
                "x": get_num(sh, "x", fp) * scale + dx,
                "y": get_num(sh, "y", fp) * scale + dy,
                "text": text,
                "fontsize": int(eval_expr(sh.get("fontsize", 10), fp)),
            })
    return out
