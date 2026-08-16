"""IfcBackend — 未来 Phase 3：若要 3D 联动（IFC + IfcOpenShell）。

骨架占位，Phase 0 / 1 不会实现。当 3D 联动需求落地时填充。

支持的方法（FloorplanBackend 协议扩展）：
  - has_3d_support() = True
  - import_3d_model(model_path)  从 SketchUp Pro 导出的 IFC 建立模型
  - sync_to_3d(ifc_path, target_skp)  反向同步到 SketchUp

详见 方案-C-BIM.md（被本文取代前的第三套方案）。
"""

from __future__ import annotations


class IfcBackend:
    def has_3d_support(self) -> bool:
        return True

    def read(self, path: str) -> dict:
        raise NotImplementedError("IfcBackend 待 Phase 3 实现（3D 联动）")

    def list_rooms(self, path: str) -> list[dict]:
        raise NotImplementedError

    def move_entity(self, *a, **kw):
        raise NotImplementedError

    def render_preview(self, *a, **kw):
        raise NotImplementedError

    def export(self, *a, **kw):
        raise NotImplementedError

    def import_3d_model(self, model_path: str) -> dict:
        """从 SketchUp Pro 导出的 IFC 建立/更新 IFC 模型。"""
        raise NotImplementedError

    def sync_to_3d(self, ifc_path: str, target_skp: str) -> dict:
        """反向同步到 SketchUp（半自动：导出 IFC，用户在 SKP 里重导入）。"""
        raise NotImplementedError
