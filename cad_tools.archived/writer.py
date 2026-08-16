"""
writer — DXF 创建 & 修改

提供房屋装修图的创建和修改功能：
    - 从零创建户型图（墙体/门窗/家具）
    - 修改现有 DXF（移动/旋转/删除元素）
    - 添加标注（文字/尺寸标注）
    - 批量布局家具

使用方式:
    writer = FloorPlanWriter()
    writer.create_wall([(0,0), (5000,0), (5000,3000), (0,3000)], closed=True)
    writer.add_door("M_900", position=(1000, 0), rotation=90)
    writer.add_furniture("SOFA_3P", position=(500, 500))
    writer.save("output.dxf")
"""

from __future__ import annotations
from typing import Optional, Sequence
import ezdxf
from ezdxf.document import Drawing
from ezdxf.layouts import Modelspace
from ezdxf.enums import InsertUnits, TextEntityAlignment

from .geometry import rotate_point, distance, midpoint
from .blocks import BlockLibrary


class FloorPlanWriter:
    """DXF 装修图创建器/编辑器"""

    # 标准图层定义
    STANDARD_LAYERS = {
        "WALL": {"color": 7},        # 白色/黑色
        "DOOR": {"color": 30},       # 橙色
        "WINDOW": {"color": 140},    # 浅蓝
        "FURNITURE": {"color": 8},   # 灰色
        "DIMENSION": {"color": 2},   # 黄色
        "TEXT": {"color": 3},        # 绿色
        "HATCH": {"color": 9},       # 浅灰
        "AXIS": {"color": 1},        # 红色
    }

    def __init__(self, doc: Optional[Drawing] = None):
        """
        Args:
            doc: 已有的 ezdxf 文档（修改模式），不传则创建新文档
        """
        if doc is not None:
            self.doc = doc
        else:
            self.doc = ezdxf.new("R2010")
            # 设置单位为毫米
            self.doc.units = InsertUnits.Millimeters
            self.doc.header["$INSUNITS"] = 13  # 13 = mm

        self.msp = self.doc.modelspace()
        self.block_lib = BlockLibrary(self.doc)
        self._init_layers()

    def _init_layers(self):
        """初始化标准图层"""
        for name, attrs in self.STANDARD_LAYERS.items():
            if name not in self.doc.layers:
                self.doc.layers.add(name, **attrs)

    # ─── 墙体 ───

    def create_wall(
        self,
        coords: Sequence[tuple[float, float]],
        closed: bool = True,
        thickness: float = 0,
        layer: str = "WALL",
    ):
        """
        创建墙体（多段线）。

        Args:
            coords: 墙体顶点坐标列表 [(x,y), ...]
            closed: 是否闭合
            thickness: 墙厚（0 表示无宽度多段线）
            layer: 图层名
        """
        if layer not in self.doc.layers:
            self.doc.layers.add(layer, color=7)

        kwargs = {"close": closed, "dxfattribs": {"layer": layer}}
        if thickness > 0:
            poly = self.msp.add_lwpolyline(
                list(coords), **kwargs
            )
            poly.set_const_width(thickness)
        else:
            poly = self.msp.add_lwpolyline(list(coords), **kwargs)

        return poly

    def create_wall_rect(
        self,
        x: float, y: float,
        width: float, height: float,
        thickness: float = 0,
        layer: str = "WALL",
    ):
        """创建矩形墙体"""
        coords = [
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height),
        ]
        return self.create_wall(coords, closed=True, thickness=thickness, layer=layer)

    # ─── 门 ───

    def add_door(
        self,
        block_name: str = "M_900",
        position: tuple[float, float] = (0, 0),
        rotation: float = 0,
        scale: float = 1.0,
        layer: str = "DOOR",
    ):
        """
        添加门（块引用）。
        自动创建块定义（如不存在）。

        Args:
            block_name: 门块名（如 "M_900" 表示 900mm 宽门）
            position: 插入位置
            rotation: 旋转角度（度）
            scale: 缩放比例
            layer: 图层
        """
        if layer not in self.doc.layers:
            self.doc.layers.add(layer, color=30)

        # 自动创建块定义
        if block_name not in self.doc.blocks:
            import re
            m = re.search(r'(\d+)', block_name)
            width = float(m.group(1)) if m else 900
            self.block_lib.create_door_block(block_name, width=width, layer=layer)

        return self.msp.add_blockref(
            block_name,
            insert=position,
            dxfattribs={
                "rotation": rotation,
                "xscale": scale,
                "yscale": scale,
                "layer": layer,
            },
        )

    # ─── 窗户 ───

    def add_window(
        self,
        block_name: str = "W_1500",
        position: tuple[float, float] = (0, 0),
        rotation: float = 0,
        scale: float = 1.0,
        wall_thickness: float = 240,
        layer: str = "WINDOW",
    ):
        """添加窗户（块引用）"""
        if layer not in self.doc.layers:
            self.doc.layers.add(layer, color=140)

        if block_name not in self.doc.blocks:
            import re
            m = re.search(r'(\d+)', block_name)
            width = float(m.group(1)) if m else 1500
            self.block_lib.create_window_block(
                block_name, width=width,
                wall_thickness=wall_thickness, layer=layer
            )

        return self.msp.add_blockref(
            block_name,
            insert=position,
            dxfattribs={
                "rotation": rotation,
                "xscale": scale,
                "yscale": scale,
                "layer": layer,
            },
        )

    # ─── 家具 ───

    def add_furniture(
        self,
        block_name: str,
        position: tuple[float, float] = (0, 0),
        rotation: float = 0,
        scale: float = 1.0,
        layer: str = "FURNITURE",
    ):
        """
        添加家具（块引用）。
        根据块名自动判断类型并创建块定义。
        """
        if layer not in self.doc.layers:
            self.doc.layers.add(layer, color=8)

        # 根据块名自动创建对应块定义
        if block_name not in self.doc.blocks:
            ftype = BlockLibrary.classify_block_name(block_name)
            self._auto_create_block(block_name, ftype, layer)

        return self.msp.add_blockref(
            block_name,
            insert=position,
            dxfattribs={
                "rotation": rotation,
                "xscale": scale,
                "yscale": scale,
                "layer": layer,
            },
        )

    def _auto_create_block(self, name: str, ftype: str, layer: str):
        """根据家具类型自动创建块定义"""
        import re
        m = re.search(r'(\d+)', name)
        size = float(m.group(1)) if m else None

        creators = {
            "sofa": lambda: self.block_lib.create_sofa_block(
                name, width=size or 2100, depth=850, layer=layer
            ),
            "bed": lambda: self.block_lib.create_bed_block(
                name, width=size or 1800, length=2000, layer=layer
            ),
            "table": lambda: self.block_lib.create_table_block(
                name, width=size or 1200, depth=700, layer=layer
            ),
            "chair": lambda: self.block_lib.create_chair_block(
                name, size=size or 450, layer=layer
            ),
            "toilet": lambda: self.block_lib.create_toilet_block(
                name, layer=layer
            ),
            "sink": lambda: self.block_lib.create_sink_block(
                name, layer=layer
            ),
            "fridge": lambda: self.block_lib.create_fridge_block(
                name, layer=layer
            ),
            "washer": lambda: self.block_lib.create_washer_block(
                name, layer=layer
            ),
            "stove": lambda: self.block_lib.create_stove_block(
                name, layer=layer
            ),
        }

        creator = creators.get(ftype)
        if creator:
            creator()
        else:
            # 创建一个占位方块
            block = self.doc.blocks.new(name=name)
            s = size or 500
            block.add_lwpolyline(
                [(0, 0), (s, 0), (s, s), (0, s)],
                close=True,
                dxfattribs={"layer": layer},
            )

    # ─── 标注 ───

    def add_text(
        self,
        text: str,
        position: tuple[float, float],
        height: float = 300,
        rotation: float = 0,
        layer: str = "TEXT",
    ):
        """添加文字标注"""
        if layer not in self.doc.layers:
            self.doc.layers.add(layer, color=3)
        return self.msp.add_text(
            text,
            dxfattribs={
                "height": height,
                "rotation": rotation,
                "layer": layer,
            },
        ).set_placement(position, align=TextEntityAlignment.MIDDLE_CENTER)

    def add_dimension(
        self,
        p1: tuple[float, float],
        p2: tuple[float, float],
        offset: float = 1000,
        layer: str = "DIMENSION",
    ):
        """
        添加两点之间的尺寸标注。

        Args:
            p1: 第一个点
            p2: 第二个点
            offset: 标注线偏移量
            layer: 图层
        """
        if layer not in self.doc.layers:
            self.doc.layers.add(layer, color=2)
        return self.msp.add_linear_dim(
            base=p1,
            p1=p1,
            p2=p2,
            angle=0 if abs(p2[1] - p1[1]) < 1 else 90,
            offset=offset,
            dxfattribs={"layer": layer},
        )

    # ─── 修改操作 ───

    def move_entity(self, entity, dx: float, dy: float):
        """
        移动实体。
        支持 INSERT, LINE, LWPOLYLINE, TEXT 等。
        """
        etype = entity.dxftype()
        if etype == "INSERT":
            entity.dxf.insert = entity.dxf.insert + (dx, dy, 0)
        elif etype == "LINE":
            entity.dxf.start = entity.dxf.start + (dx, dy, 0)
            entity.dxf.end = entity.dxf.end + (dx, dy, 0)
        elif etype == "LWPOLYLINE":
            points = entity.get_points()
            new_points = [(x + dx, y + dy, b, w1, w2) for x, y, b, w1, w2 in points]
            entity.set_points(new_points)
        elif etype in ("TEXT", "MTEXT"):
            entity.dxf.insert = entity.dxf.insert + (dx, dy, 0)
        return entity

    def rotate_entity(self, entity, angle: float, center: tuple[float, float] = (0, 0)):
        """
        旋转实体。
        """
        etype = entity.dxftype()
        if etype == "INSERT":
            # 旋转位置
            old_pos = (entity.dxf.insert.x, entity.dxf.insert.y)
            new_pos = rotate_point(old_pos, angle, center)
            entity.dxf.insert = (new_pos[0], new_pos[1], 0)
            # 累加旋转角度
            entity.dxf.rotation = entity.dxf.rotation + angle
        elif etype == "LINE":
            old_start = (entity.dxf.start.x, entity.dxf.start.y)
            old_end = (entity.dxf.end.x, entity.dxf.end.y)
            new_start = rotate_point(old_start, angle, center)
            new_end = rotate_point(old_end, angle, center)
            entity.dxf.start = (new_start[0], new_start[1], 0)
            entity.dxf.end = (new_end[0], new_end[1], 0)
        elif etype == "LWPOLYLINE":
            points = entity.get_points()
            new_points = []
            for x, y, b, w1, w2 in points:
                np = rotate_point((x, y), angle, center)
                new_points.append((np[0], np[1], b, w1, w2))
            entity.set_points(new_points)
        return entity

    def delete_entity(self, entity):
        """删除实体"""
        self.msp.delete_entity(entity)

    def find_entities_by_layer(self, layer: str):
        """查找指定图层的所有实体"""
        return list(self.msp.query(f'*[layer=="{layer}"]'))

    def find_inserts_by_name(self, block_name: str):
        """查找指定块名的所有块引用"""
        return list(self.msp.query(f'INSERT[name=="{block_name}"]'))

    def move_furniture_by_name(
        self, block_name: str, dx: float, dy: float
    ) -> int:
        """
        按块名移动所有匹配的家具。
        Returns: 移动的数量
        """
        inserts = self.find_inserts_by_name(block_name)
        for ins in inserts:
            self.move_entity(ins, dx, dy)
        return len(inserts)

    # ─── 文件操作 ───

    def save(self, path: str):
        """保存为 DXF 文件"""
        self.doc.saveas(path)

    def saveas(self, path: str):
        """另存为（别名）"""
        self.doc.saveas(path)

    # ─── 快速创建户型 ───

    def create_apartment(
        self,
        rooms: list[dict],
        wall_thickness: float = 240,
    ):
        """
        快速创建户型图。

        Args:
            rooms: 房间列表，每个房间包含:
                - name: 房间名
                - x, y: 左下角坐标
                - width, height: 宽高（mm）
                - doors: [(position_x, position_y, block_name), ...]  门
                - windows: [(position_x, position_y, block_name), ...]  窗
                - furniture: [(block_name, position_x, position_y, rotation), ...]  家具
            wall_thickness: 墙厚
        """
        for room in rooms:
            # 墙体
            self.create_wall_rect(
                room["x"], room["y"],
                room["width"], room["height"],
                thickness=0,
            )
            # 房间名标注
            self.add_text(
                room.get("name", ""),
                (room["x"] + room["width"] / 2,
                 room["y"] + room["height"] / 2),
                height=300,
            )
            # 门
            for door in room.get("doors", []):
                self.add_door(
                    block_name=door[2] if len(door) > 2 else "M_900",
                    position=(door[0], door[1]),
                    rotation=door[3] if len(door) > 3 else 0,
                )
            # 窗
            for win in room.get("windows", []):
                self.add_window(
                    block_name=win[2] if len(win) > 2 else "W_1500",
                    position=(win[0], win[1]),
                    rotation=win[3] if len(win) > 3 else 0,
                )
            # 家具
            for fur in room.get("furniture", []):
                self.add_furniture(
                    block_name=fur[0],
                    position=(fur[1], fur[2]),
                    rotation=fur[3] if len(fur) > 3 else 0,
                )
