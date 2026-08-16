"""V1 自动化烟雾测试：跑通 backend 接口 + 安全层 + 类分类，
确认骨架在 Phase 0 之前是可 import、可调用、不改文档状态下跑通的。

跑：python3 floorplan-mcp/tests/smoke_v1.py
"""

from __future__ import annotations
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("==> V1 烟雾测试：骨架可 import 性 + 安全层 + 分类")
    failed = []

    tests = [
        ("backend selection default", _test_default),
        ("backend selection ezdxf env", _test_env_ezdxf),
        ("make_backup incremental", _test_backup),
        ("with_transaction abort on error", _test_abort),
        ("with_transaction commit on success", _test_commit),
        ("classify block", _test_classify),
        ("user_tool signature AST", _test_ast),
        ("ifc 3d flag", _test_ifc),
    ]
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except Exception as e:
            failed.append(name)
            print(f"  ✗ {name}: {e}")

    print()
    if failed:
        print(f"❌ {len(failed)} 个失败: {failed}")
        sys.exit(1)
    print(f"✓ 全部通过（{len(tests)} 项）")


def _test_default():
    from tools import get_backend
    os.environ.pop("FLOORPLAN_BACKEND", None)


def _test_env_ezdxf():
    os.environ["FLOORPLAN_BACKEND"] = "ezdxf"
    try:
        from backends.ezdxf_backend import EzdxfBackend
    finally:
        os.environ.pop("FLOORPLAN_BACKEND", None)


def _test_backup():
    from backends._safety import make_backup
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.dxf")
        Path(p).write_text("v0")
        b1 = make_backup(p)
        assert b1.endswith(".bak.1"), b1


def _test_abort():
    from backends._safety import with_transaction
    class D:
        def __init__(self): self.t = []
        def openTransaction(self, l): self.t.append("o")
        def commitTransaction(self): self.t.append("c")
        def abortTransaction(self): self.t.append("a")
        def recompute(self): pass
        def saveAs(self, p): pass
    doc = D()
    res = with_transaction(doc, "T", lambda d: (_ for _ in ()).throw(ValueError("x")),
                           save_path=None, auto_backup=False)
    assert res["ok"] is False
    assert "a" in doc.t and "c" not in doc.t


def _test_commit():
    from backends._safety import with_transaction
    class D:
        saved = None
        def openTransaction(self, l): pass
        def commitTransaction(self): pass
        def abortTransaction(self): raise AssertionError()
        def recompute(self): pass
        def saveAs(self, p): self.saved = p
    doc = D()
    with tempfile.TemporaryDirectory() as d:
        sp = os.path.join(d, "x.FCStd")
        Path(sp).write_text("0")
        res = with_transaction(doc, "M", lambda d: {"k": 1},
                               save_path=sp, auto_backup=True)
        assert res["ok"] and res["data"] == {"k": 1} and doc.saved == sp


def _test_classify():
    from backends.freecad_backend import _classify
    assert _classify("SOFA") == "sofa"
    assert _classify("M_900") == "door"


def _test_ast():
    import ast
    here = Path(__file__).parent.parent
    src = (here / "tools" / "floorplan_tools.py").read_text()
    funcs = [n for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
    assert len(funcs) == 5


def _test_ifc():
    from backends.ifc_backend import IfcBackend
    assert IfcBackend().has_3d_support() is True


if __name__ == "__main__":
    main()
