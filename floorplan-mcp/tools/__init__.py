"""user_tools 包入口 + backend 选择器。

按 FLOORPLAN_BACKEND 环境变量选后端：
    FLOORPLAN_BACKEND=freecad  (默认) → FreeCAD BIM + Arch Space
    FLOORPLAN_BACKEND=ezdxf    (备选) → ezdxf + shapely polygonize
    FLOORPLAN_BACKEND=ifc      (未来) → IfcOpenShell（3D 联动）
"""

from __future__ import annotations
import os


def get_backend():
    """返回 FloorplanBackend 实现的单例。

    user_tools / MCP tool 永远通过此函数取后端，
    不直接 import FreeCAD/ezdxf/IfcOpenShell。
    """
    choice = os.getenv("FLOORPLAN_BACKEND", "freecad").lower()
    if choice == "ezdxf":
        from backends.ezdxf_backend import EzdxfBackend
        return EzdxfBackend()
    if choice == "ifc":
        from backends.ifc_backend import IfcBackend
        return IfcBackend()
    from backends.freecad_backend import FreeCADBackend
    return FreeCADBackend()


__all__ = ["get_backend"]
