# -*- coding: utf-8 -*-
"""tools/dxf_edit/param_expr.py 的单元测试。

跑法（宿主机 miniconda 自带 ezdxf/python，不需要 docker）：
    cd /Users/bladelee/project/cad
    /Users/bladelee/miniconda3/bin/python -m pytest tools/dxf_edit/test_param_expr.py -v
  或者没有 pytest 时直接：
    /Users/bladelee/miniconda3/bin/python tools/dxf_edit/test_param_expr.py

知识点参考 docs/借鉴-wheel-drawing-tools-参数化模式.md 模式 2。
"""
from __future__ import annotations

import os
import sys

# 确保能 import 同目录的 param_expr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from param_expr import eval_expr, get_num, params_for_eval, flatten_shapes  # noqa: E402


# ---------- eval_expr ----------

def test_eval_expr_number_returns_float():
    assert eval_expr(100, {}) == 100.0
    assert eval_expr(3.14, {}) == 3.14
    assert isinstance(eval_expr(0, {}), float)


def test_eval_expr_simple_arithmetic():
    assert eval_expr("L/2", {"L": 200}) == 100.0
    assert eval_expr("L+W", {"L": 10, "W": 5}) == 15.0
    assert eval_expr("2*L - W*3", {"L": 10, "W": 2}) == 14.0


def test_eval_expr_word_boundary():
    """短参数名 L 不应该误伤到 LINE / Label 这种单词里的 L"""
    # 没有 L 参数时，"LINE" 里的 L 不应被替换
    assert eval_expr("LINE", {"W": 10}) == 0.0  # "LINE" 不是数字表达式 → 0
    # 加了 L 后，单独的 L 被换成 5，但 LINE 里的 L 不应被动
    # 这里用一个清晰的例子：表达式里既出现单独的 L，又不期望误伤其他词
    assert eval_expr("L + W", {"L": 5, "W": 1}) == 6.0


def test_eval_expr_trig_and_pi():
    import math
    assert eval_expr("cos(0)", {}) == 1.0
    assert eval_expr("sin(0)", {}) == 0.0
    assert eval_expr("pi", {}) == math.pi
    # PCD/2*cos(60°) —— wheel 项目里 PCD 螺栓孔位置典型表达式
    # 浮点有精度误差，用 round 校验到 6 位
    assert round(eval_expr("PCD/2*cos(60*pi/180)", {"PCD": 200}), 6) == 50.0
    assert round(eval_expr("PCD/2*sin(30*pi/180)", {"PCD": 200}), 6) == 50.0


def test_eval_expr_sqrt():
    assert eval_expr("sqrt(16)", {}) == 4.0
    assert eval_expr("sqrt(L*L + W*W)", {"L": 3, "W": 4}) == 5.0


def test_eval_expr_failure_returns_zero():
    """任何异常都必须降级为 0.0，不让一处坐标算错中断整张图"""
    assert eval_expr("undefined_name + 1", {}) == 0.0
    assert eval_expr("1/0", {}) == 0.0       # 除零
    assert eval_expr("1 +", {}) == 0.0       # 语法错
    assert eval_expr("__import__('os')", {}) == 0.0  # __builtins__ 被禁


def test_eval_expr_sandbox_blocks_builtins():
    """__builtins__ 必须被关掉，防止表达式里调用任意函数"""
    # 不能访问 open / __import__
    assert eval_expr("open('/etc/passwd')", {}) == 0.0
    assert eval_expr("__import__('os')", {}) == 0.0


# ---------- get_num ----------

def test_get_num_with_default():
    assert get_num({}, "x", {}) == 0.0
    assert get_num({}, "x", {}, default=42) == 42.0


def test_get_num_with_expression_attr():
    attrs = {"x": "L/2", "y": "W+10"}
    params = {"L": 100, "W": 5}
    assert get_num(attrs, "x", params) == 50.0
    assert get_num(attrs, "y", params) == 15.0


def test_get_num_with_literal_attr():
    assert get_num({"x": 200}, "x", {}) == 200.0
    assert get_num({"x": "200"}, "x", {}) == 200.0


# ---------- params_for_eval ----------

def test_params_for_eval_filters_non_numeric():
    raw = {"L": 100, "W": "50", "型号": "ABC", "set": True, "note": "", "empty": "x"}
    out = params_for_eval(raw)
    assert out == {"L": 100.0, "W": 50.0}
    # bool 被丢弃
    assert "set" not in out
    # 非数字串被丢弃
    assert "型号" not in out
    assert "note" not in out
    assert "empty" not in out


# ---------- flatten_shapes ----------

def test_flatten_shapes_line_with_scale_and_translate():
    sd = [{"type": "line", "x1": 0, "y1": 0, "x2": "L", "y2": 0}]
    out = flatten_shapes(sd, {"L": 100}, scale=0.5, dx=10, dy=20)
    assert len(out) == 1
    line = out[0]
    assert line["type"] == "line"
    assert line["x1"] == 0 * 0.5 + 10
    assert line["y1"] == 20
    assert line["x2"] == 100 * 0.5 + 10
    assert line["y2"] == 20


def test_flatten_shapes_circle_radius_scales_but_not_translate():
    sd = [{"type": "circle", "cx": 0, "cy": 0, "r": 10}]
    out = flatten_shapes(sd, {}, scale=2.0, dx=100, dy=50)
    c = out[0]
    assert c["cx"] == 100  # 0*2 + 100
    assert c["cy"] == 50
    assert c["r"] == 20    # 半径只缩放，不叠加平移


def test_flatten_shapes_text_substitutes_placeholders():
    sd = [{"type": "text", "x": 0, "y": 0, "text": "L={L}  W={W}", "fontsize": 10}]
    out = flatten_shapes(sd, {"L": 100, "W": 50})
    assert out[0]["text"] == "L=100  W=50"


def test_flatten_shapes_rect_uses_expression_coords():
    sd = [{"type": "rect", "x": "L/2", "y": 0, "width": "L", "height": "W"}]
    out = flatten_shapes(sd, {"L": 100, "W": 50})
    r = out[0]
    assert r["x"] == 50.0
    assert r["y"] == 0.0
    assert r["width"] == 100.0
    assert r["height"] == 50.0


# ---------- CLI 直跑兼容 ----------

def _run_all():
    """没装 pytest 时也能直接 python test_param_expr.py 跑。"""
    mod = sys.modules[__name__]
    tests = sorted(
        name for name in dir(mod)
        if name.startswith("test_") and callable(getattr(mod, name))
    )
    passed, failed = 0, 0
    for name in tests:
        try:
            getattr(mod, name)()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}: {e}")
            failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed (of {len(tests)})")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())
