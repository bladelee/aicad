"""FloorplanBackend — 装修图后端接口（Protocol）。

A/B/C 三个后端都是该接口的实现，按 FLOORPLAN_BACKEND 环境变量切换。
user_tools 只调 get_backend()，不直接 import 具体后端，保证可热切换。

设计依据：见 方案-F-容器化.md §6 / 方案-F2 风险表 R2。
"""

from __future__ import annotations
from typing import Protocol


class FloorplanBackend(Protocol):
    """装修图后端接口。
    所有 user_tool 都通过此接口工作，主备切换零代码改动。
    """

    # ─── 2D 能力（A/B/C 三套都支持）───

    def read(self, path: str) -> dict:
        """读取装修图 → 结构化 JSON。

        返回结构（最小约定，后端可扩展）：
            {
              "layers":    [{"name": str, "color": int, "on": bool}],
              "walls":     [{"layer": str, "coords_mm": list[xy], "length_mm": float, "closed": bool}],
              "doors":     [{"block": str, "position_xy": list, "rotation_deg": float, "layer": str}],
              "windows":   [{"block": str, "position_xy": list, "rotation_deg": float, "layer": str}],
              "furniture": [{"block": str, "type": str, "position_xy": list, "rotation_deg": float, "layer": str}],
              "rooms":     [{"name": str, "area_m2": float, "furniture": list[str]}],
              "summary":   {"wall_count": int, "door_count": int, "furniture_count": int, "room_count": int},
            }
        """
        ...

    def list_rooms(self, path: str) -> list[dict]:
        """列出所有房间：名称/面积(m²)/边界/内含家具。"""
        ...

    def move_entity(
        self,
        path: str,
        handle: str,
        dx_mm: float,
        dy_mm: float,
        auto_backup: bool = True,
    ) -> dict:
        """移动实体。

        Args:
            path: DWG/DXF 路径（容器内 /data/...）
            handle: 实体 handle 或 (block_name, idx)
            dx_mm, dy_mm: 平移量（毫米）
            auto_backup: True 时自动生成 *.bak.N（防永久坏文件）

        Returns:
            {"ok": True, "backup_path": str | None, "before_png": str, "after_png": str}

        注意（R2）：freecad-ai 的 user_tools handler 不走 _with_undo，
        所以后端实现必须自己包 openTransaction + .bak。
        见 backends/_safety.py。
        """
        ...

    def render_preview(
        self,
        path: str,
        output_png: str,
        highlight_handles: list[str] | None = None,
    ) -> str:
        """渲染 PNG 预览。

        实现注意：不得修改原文档的图层状态（v1 renderer 的破坏性 bug）。
        用 offscreen Qt 或 RenderContext 副本，绝不调用 layer.off()。
        """
        ...

    def export(self, path: str, target_format: str, acad_version: str = "ACAD2018") -> str:
        """导出为目标格式（DWG/PDF/DXF）。

        DWG 走 ODA File Converter（合规：用户自行安装，不打包进镜像）。
        """
        ...

    # ─── 3D 联动能力（仅 C 支持，A/B 默认拒绝）───

    def has_3d_support(self) -> bool:
        """是否支持 3D 联动。A/B 返回 False。"""
        return False

    def import_3d_model(self, model_path: str) -> dict:
        """从 SketchUp IFC 导入，建立/更新 IFC 模型。仅 C 实现。"""
        raise NotImplementedError("当前后端不支持 3D，未来方案 C 提供")

    def sync_to_3d(self, ifc_path: str, target_skp: str) -> dict:
        """反向同步到 SketchUp。仅 C 实现。"""
        raise NotImplementedError
