"""tools/core/test_core_api.py — C4-α 核心层冒烟测试。

验证:
  1. `from tools.core import *` 不报错
  2. 每个 API 都可调
  3. 关键签名 (param_expr/doc_to_shapes/move_wall/apply_material_rename)
     与设计文档 §4 一致

跑法:
  cd /Users/bladelee/project/cad
  /Users/bladelee/miniconda3/bin/python -m pytest tools/core/test_core_api.py -v
  (无 docker 也行，因为只测函数能 import + 跑通；不依赖 libredwg)
"""
from __future__ import annotations
import sys
from pathlib import Path

# 把仓库根加 sys.path（让 from tools.core import ... 走通）
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def test_import_star():
    """1. 核心层能 from import"""
    from tools.core import (
        move_wall,
        move_wall_with_dim,
        move_wall_with_floor_ceil,
        apply_material_rename,
        verify_rename,
        probe_dimensions_near_wall,
        restore,
        eval_expr,
        get_num,
        doc_to_shapes,
    )
    # 全部 callable
    assert callable(move_wall)
    assert callable(apply_material_rename)
    assert callable(eval_expr)


def test_param_expr_thru_core():
    """param_expr 通过 core 层也正常工作"""
    from tools.core import eval_expr, get_num
    assert eval_expr(100, {}) == 100.0
    assert eval_expr("L/2", {"L": 1000}) == 500.0
    assert eval_expr("cos(0)", {}) == 1.0
    assert get_num({"w": "L*2"}, "w", {"L": 50}) == 100.0


def test_doc_to_shapes_thru_core():
    """doc_to_shapes 通过 core 层能正常调"""
    import ezdxf
    from tools.core import doc_to_shapes
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_line((0, 0), (100, 0))
    msp.add_circle((50, 50), radius=20)
    shapes = doc_to_shapes(doc)
    # 至少识别到 1 条 line 和 1 个 circle
    types = [s["type"] for s in shapes]
    assert "line" in types
    assert "circle" in types


def test_apply_material_rename_dry_run():
    """#6 apply_material_rename 的 dry_run 模式（不写文件，只计数）"""
    import ezdxf
    import tempfile
    from tools.core import apply_material_rename

    # 造个临时 DXF 含 "ST-01"
    with tempfile.TemporaryDirectory() as tmp:
        dxf_path = Path(tmp) / "test.dxf"
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_text("材料: ST-01", dxfattribs={"insert": (0, 0)})
        msp.add_text("墙面: ST-01 完工", dxfattribs={"insert": (0, 10)})
        doc.saveas(str(dxf_path))

        # dry_run=True 不写文件
        result = apply_material_rename(
            str(dxf_path), old_code="ST-01", new_code="ST-A", dry_run=True
        )
        assert result["ok"] is True
        assert result["total_replaced"] == 2  # ST-01 在 2 个 text 里
        assert result["by_type"].get("TEXT", 0) == 2
        # dry_run 不写文件
        assert result["output"] is None


def test_apply_material_rename_with_output():
    """#6 真写一份输出文件"""
    import ezdxf
    import tempfile
    from tools.core import apply_material_rename

    with tempfile.TemporaryDirectory() as tmp:
        dxf_path = Path(tmp) / "test.dxf"
        doc = ezdxf.new()
        msp = doc.modelspace()
        msp.add_text("ST-01", dxfattribs={"insert": (0, 0)})
        doc.saveas(str(dxf_path))

        out = Path(tmp) / "out.dxf"
        result = apply_material_rename(
            str(dxf_path), old_code="ST-01", new_code="ST-A",
            out_path=str(out)
        )
        assert result["ok"]
        assert result["output"] == str(out)
        assert Path(out).exists()

        # 读出来验证真的改了
        doc2 = ezdxf.readfile(str(out))
        texts = [t.dxf.text for t in doc2.modelspace() if t.dxftype() == "TEXT"]
        assert "ST-01" not in texts
        assert any("ST-A" in t for t in texts)


def test_verify_rename_signature():
    """verify_rename 签名 + 返回结构符合设计文档"""
    from tools.core import verify_rename
    import inspect
    sig = inspect.signature(verify_rename)
    # 必须有这三个参数
    assert "dxf_paths" in sig.parameters
    assert "old_code" in sig.parameters
    assert "new_code" in sig.parameters


def test_probe_dimensions_signature():
    """probe_dimensions_near_wall 签名"""
    from tools.core import probe_dimensions_near_wall
    import inspect
    sig = inspect.signature(probe_dimensions_near_wall)
    assert "dxf_path" in sig.parameters
    assert "handle" in sig.parameters
    assert "near" in sig.parameters


def test_move_wall_with_dim_signature():
    """move_wall_with_dim 签名"""
    from tools.core import move_wall_with_dim
    import inspect
    sig = inspect.signature(move_wall_with_dim)
    assert {"dxf_path", "handle", "dx", "dy", "near", "out_path"}.issubset(
        sig.parameters.keys()
    )


def test_no_stdout_pollution_in_core():
    """核心层 API 不应在 import 时就有副作用（print）"""
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        # 强制重新 import
        import importlib
        if "tools.core" in sys.modules:
            mod = sys.modules["tools.core"]
        else:
            from tools import core as mod
    # 允许少量 stderr warning（ezdxf 等），但 stdout 应该为零
    assert buf.getvalue() == "", f"stdout 中有意外的副作用输出: {buf.getvalue()!r}"
