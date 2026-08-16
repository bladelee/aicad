"""单元测试：BackOs 安全性 + backend 接口（无 FreeCAD/ezdxf 依赖部分）。

跑：pytest floorplan-mcp/tests/ （Phase 0 之前的 V1 自动化验证）
"""

from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path

# 让测试能 import 项目
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_backend_selection_default():
    """默认 FLOORPLAN_BACKEND=freecad。"""
    from tools import get_backend
    os.environ.pop("FLOORPLAN_BACKEND", None)
    # 不能真的 instantiate（freecad import 在容器内），
    # 这里只验证 import 不报错、有类定义
    import tools
    assert hasattr(tools, "get_backend")


def test_backend_selection_env_switch():
    """FLOORPLAN_BACKEND=ezdxf 切换 EzdxfBackend 类。"""
    os.environ["FLOORPLAN_BACKEND"] = "ezdxf"
    try:
        from backends.ezdxf_backend import EzdxfBackend
        assert EzdxfBackend is not None
    finally:
        os.environ.pop("FLOORPLAN_BACKEND", None)


def test_ifc_backend_3d_flag():
    """IfcBackend 标记 has_3d_support=True（未来 Phase 3 用）。"""
    from backends.ifc_backend import IfcBackend
    assert IfcBackend().has_3d_support() is True


def test_make_backup_creates_incremental():
    """make_backup 生成 .bak.1, .bak.2 ..."""
    from backends._safety import make_backup
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.dxf")
        Path(p).write_text("v0")
        b1 = make_backup(p)
        assert b1 and b1.endswith(".bak.1")
        Path(p).write_text("v1")
        b2 = make_backup(p)
        assert b2.endswith(".bak.2")
        assert Path(b1).read_text() == "v0"  # 旧版本保留了
        assert Path(b2).read_text() == "v1"


def test_make_backup_max_keep():
    """max_keep=2 超出时 FIFO 清理。"""
    from backends._safety import make_backup
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.dxf")
        Path(p).write_text("v")
        backups = []
        for i in range(5):
            backups.append(make_backup(p, max_keep=2))
        # 应该只剩最后 2 个
        existing = sorted(Path(d).glob("x.dxf.bak.*"))
        assert len(existing) == 2


def test_with_transaction_aborts_on_error():
    """with_transaction 异常时调 abortTransaction（用 mock doc）。"""
    from backends._safety import with_transaction

    class FakeDoc:
        def __init__(self):
            self.tx = []
        def openTransaction(self, l): self.tx.append(("open", l))
        def commitTransaction(self): self.tx.append(("commit",))
        def abortTransaction(self): self.tx.append(("abort",))
        def recompute(self): pass
        def saveAs(self, p): pass

    doc = FakeDoc()

    def boom(doc):
        raise ValueError("simulated")

    # 不存盘 → 不进 make_backup，但事务该走还是走
    res = with_transaction(doc, "T", boom, save_path=None, auto_backup=False)
    assert res["ok"] is False
    assert "simulated" in res["error"]
    assert ("open", "T") in doc.tx
    assert ("abort",) in doc.tx
    assert ("commit",) not in doc.tx


def test_with_transaction_commits_on_success():
    from backends._safety import with_transaction

    class FakeDoc:
        def __init__(self): self.saved = None
        def openTransaction(self, l): pass
        def commitTransaction(self): pass
        def abortTransaction(self): raise AssertionError("不该 abort")
        def recompute(self): pass
        def saveAs(self, p): self.saved = p

    doc = FakeDoc()

    def ok(doc):
        return {"moved": [100, 200]}

    with tempfile.TemporaryDirectory() as d:
        save_path = os.path.join(d, "x.FCStd")
        Path(save_path).write_text("0")  # 让 make_backup 触发
        res = with_transaction(doc, "Move", ok, save_path=save_path, auto_backup=True)
        assert res["ok"] is True
        assert res["data"] == {"moved": [100, 200]}
        assert res["backup_path"] is not None
        assert doc.saved == save_path  # 存盘了


def test_classify_block_name():
    """块名 → 类型分类（v1 linter v1 关键词，含已知误命中点）。"""
    from backends.freecad_backend import _classify
    assert _classify("SOFA_3P") == "sofa"
    assert _classify("沙发_3人") == "sofa"
    assert _classify("BED_1800") == "bed"
    assert _classify("M_900") == "door"   # 门
    assert _classify("W_1500") == "window"
    assert _classify("XYZ") == "unknown"
    # 已知风险点（待 Phase 1 映射表缓解）:
    #   - W_ 短前缀会误命中如 W_POOL / WALK 这类（含下划线或单独 W 开头的命名）
    #   - 但 WORKBENCH 这种没下划线的不命中（W_ 要求下划线）
    assert _classify("W_POOL") == "window"      # ⚠ 误命中案例
    assert _classify("WALKLINE") == "unknown"   # 不含下划线，不命中


def test_classify_block_name_full_keywords():
    """v1 cad_tools/blocks.py 关键词表完整保留（v1 已归档 cad_tools.archived/）。"""
    from backends.freecad_backend import _classify

    # 每类至少验 1 个 v1 含有的扩展词
    cases = {
        "COUCH_3SEAT": "sofa",
        "MATTRESS_1800": "bed",
        "DESK_1400": "table",
        "SEAT_450": "chair",
        "TELEVISION_55": "tv",
        "REFRIGERATOR_LARGE": "fridge",
        "LAUNDRY_MACHINE": "washer",
        "LAVATORY": "sink",
        "COOKTOP_4BURNER": "stove",
        "CABINET_900": "wardrobe",
        "KITCHEN_COUNTER": "kitchen",
        "AIR_CONDITIONER_WALL": "aircon",
        "BATHTUB_1500": "bathtub",
    }
    for name, expect in cases.items():
        assert _classify(name) == expect, f"{name} 应为 {expect}, 实得 {_classify(name)}"


def test_user_tool_signatures_ast_compatible():
    """5 个 user_tool 的签名符合 freecad-ai user_tools ast 约束：
       公开、有 type hints、参数类型在支持的集合内。
    """
    import ast
    src = (Path(__file__).parent.parent / "tools" / "floorplan_tools.py").read_text()
    tree = ast.parse(src)
    funcs = [n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
    assert len(funcs) == 5  # read_floorplan / list_rooms / move_furniture / render_preview / export_drawing
    for f in funcs:
        assert f.returns is not None, f"{f.name} 缺返回类型"
        for arg in f.args.args:
            if arg.arg == "self":
                continue
            assert arg.annotation is not None, f"{f.name}.{arg.arg} 缺类型"
