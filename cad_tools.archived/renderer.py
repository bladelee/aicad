"""
renderer — DXF → PNG 预览渲染

将 DXF 文件渲染为 PNG 预览图，支持:
    - 自定义画布大小和 DPI
    - 按图层着色
    - 显示/隐藏指定图层
    - 高亮指定实体

使用方式:
    renderer = DXFRenderer()
    renderer.render("floor_plan.dxf", "preview.png")
    renderer.render(doc, "preview.png", figsize=(20, 15), dpi=150)
"""

from __future__ import annotations
from typing import Optional, Sequence
import os

import ezdxf
from ezdxf.document import Drawing
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib
matplotlib.use("Agg")  # 无 GUI 后端
import matplotlib.pyplot as plt


class DXFRenderer:
    """DXF → PNG 渲染器"""

    def __init__(self):
        pass

    def render(
        self,
        source: str | Drawing,
        output_path: str = "preview.png",
        figsize: tuple[float, float] = (20, 15),
        dpi: int = 150,
        show_layers: Optional[Sequence[str]] = None,
        hide_layers: Optional[Sequence[str]] = None,
        highlight_entities: Optional[Sequence] = None,
        bg_color: str = "white",
        title: Optional[str] = None,
    ) -> str:
        """
        渲染 DXF 为 PNG 图片。

        Args:
            source: DXF 文件路径或 ezdxf 文档对象
            output_path: 输出 PNG 路径
            figsize: 画布尺寸（英寸）
            dpi: 分辨率
            show_layers: 仅显示这些图层（None 表示全部显示）
            hide_layers: 隐藏这些图层
            highlight_entities: 高亮的实体列表（ezdxf 实体对象）
            bg_color: 背景色
            title: 图片标题（None 表示不显示）

        Returns:
            输出文件路径
        """
        # 加载文档
        if isinstance(source, str):
            doc = ezdxf.readfile(source)
        else:
            doc = source

        # 图层可见性控制
        if hide_layers:
            for layer_name in hide_layers:
                if layer_name in doc.layers:
                    doc.layers.get(layer_name).off()
        if show_layers:
            for layer in doc.layers:
                if layer.dxf.name not in show_layers:
                    layer.off()

        # 创建画布
        fig = plt.figure(figsize=figsize, facecolor=bg_color)
        ax = fig.add_subplot(1, 1, 1)
        ax.set_facecolor(bg_color)

        # 渲染 DXF
        ctx = RenderContext(doc)
        out = MatplotlibBackend(ax)
        Frontend(ctx, out).draw_layout(doc.modelspace())

        # 高亮实体
        if highlight_entities:
            for entity in highlight_entities:
                self._highlight_entity(ax, entity)

        # 标题
        if title:
            ax.set_title(title, fontsize=16, fontfamily="sans-serif")

        # 等比例
        ax.set_aspect("equal")
        ax.autoscale()
        ax.margins(0.05)

        # 移除坐标轴
        ax.axis("off")

        # 保存
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        fig.savefig(
            output_path,
            dpi=dpi,
            bbox_inches="tight",
            facecolor=bg_color,
            pad_inches=0.1,
        )
        plt.close(fig)

        return output_path

    def render_with_info(
        self,
        source: str | Drawing,
        output_path: str = "preview_annotated.png",
        info: Optional[dict] = None,
        **kwargs,
    ) -> str:
        """
        渲染 DXF 并叠加信息标注（房间名、面积等）。

        Args:
            source: DXF 文件路径或文档对象
            output_path: 输出路径
            info: 解析信息字典（来自 FloorPlanReader.parse()）
            **kwargs: 传递给 render() 的额外参数
        """
        if isinstance(source, str):
            doc = ezdxf.readfile(source)
        else:
            doc = source

        # 先正常渲染
        self.render(doc, output_path, **kwargs)

        # 如果有信息，在图上叠加文字标注
        if info and info.get("rooms"):
            from .reader import FloorPlanReader

            fig, ax = plt.subplots(figsize=kwargs.get("figsize", (20, 15)))
            ctx = RenderContext(doc)
            out = MatplotlibBackend(ax)
            Frontend(ctx, out).draw_layout(doc.modelspace())

            # 标注房间信息
            for i, room in enumerate(info["rooms"]):
                boundary = room["boundary"]
                # 计算房间中心点
                cx = sum(p[0] for p in boundary) / len(boundary)
                cy = sum(p[1] for p in boundary) / len(boundary)
                label = room.get("name", f"房间{i+1}")
                area = room.get("area_m2", 0)
                ax.text(
                    cx, cy,
                    f"{label}\n{area}㎡",
                    fontsize=10,
                    ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.3",
                              facecolor="lightyellow",
                              edgecolor="gray",
                              alpha=0.8),
                )

            ax.set_aspect("equal")
            ax.autoscale()
            ax.margins(0.05)
            ax.axis("off")

            fig.savefig(output_path, dpi=kwargs.get("dpi", 150),
                        bbox_inches="tight", facecolor="white")
            plt.close(fig)

        return output_path

    def _highlight_entity(self, ax, entity):
        """在图上高亮单个实体"""
        etype = entity.dxftype()
        color = "red"
        linewidth = 3

        try:
            if etype == "LWPOLYLINE":
                points = entity.get_points()
                xs = [p[0] for p in points] + [points[0][0]]
                ys = [p[1] for p in points] + [points[0][1]]
                ax.plot(xs, ys, color=color, linewidth=linewidth, alpha=0.6)
            elif etype == "LINE":
                ax.plot(
                    [entity.dxf.start.x, entity.dxf.end.x],
                    [entity.dxf.start.y, entity.dxf.end.y],
                    color=color, linewidth=linewidth, alpha=0.6,
                )
            elif etype == "INSERT":
                x, y = entity.dxf.insert.x, entity.dxf.insert.y
                ax.plot(x, y, "r*", markersize=20, alpha=0.8)
                ax.annotate(
                    entity.dxf.name,
                    (x, y),
                    fontsize=8,
                    color=color,
                    xytext=(10, 10),
                    textcoords="offset points",
                )
        except Exception:
            pass

    def render_thumbnail(
        self,
        source: str | Drawing,
        output_path: str = "thumbnail.png",
        size: int = 400,
    ) -> str:
        """
        生成小尺寸缩略图。

        Args:
            source: DXF 文件路径或文档对象
            output_path: 输出路径
            size: 缩略图边长（像素）
        """
        # 计算合适的 figsize 和 dpi
        dpi = 72
        figsize = (size / dpi, size / dpi)
        return self.render(
            source, output_path,
            figsize=figsize, dpi=dpi,
        )
