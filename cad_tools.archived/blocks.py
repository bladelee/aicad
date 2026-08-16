"""
blocks — 装修图常用块库

提供房屋装修图中常用的门、窗、家具等块定义。
每个块定义是一个工厂函数，在 DXF 文档中创建对应的块定义。

使用方式:
    lib = BlockLibrary(doc)
    lib.create_door_block("M_900", width=900)
    lib.create_window_block("W_1500", width=1500)
    lib.create_sofa_block("SOFA_3P", width=2100, depth=850)
"""

from __future__ import annotations
from typing import Optional
import ezdxf
from ezdxf.document import Drawing
from ezdxf.layouts import Modelspace
from ezdxf.enums import TextEntityAlignment


class BlockLibrary:
    """装修图常用块定义库"""

    # 家具类型关键词映射（用于自动识别块名/图层）
    FURNITURE_KEYWORDS = {
        "sofa": ["SOFA", "沙发", "Couch", "SEATING"],
        "bed": ["BED", "床", "Mattress"],
        "table": ["TABLE", "桌", "DESK", "台"],
        "chair": ["CHAIR", "椅", "SEAT"],
        "tv": ["TV", "电视", "TELEVISION", "SCREEN"],
        "fridge": ["FRIDGE", "冰箱", "REFRIGERATOR"],
        "washer": ["WASH", "洗", "WASHER", "LAUNDRY"],
        "toilet": ["TOILET", "马桶", "WC", "CLOSET"],
        "bathtub": ["BATHTUB", "浴", "TUB", "BATH"],
        "sink": ["SINK", "盆", "BASIN", "LAVATORY"],
        "stove": ["STOVE", "灶", "COOKTOP", "RANGE"],
        "wardrobe": ["WARDROBE", "柜", "CLOSET", "CABINET"],
        "kitchen": ["KITCHEN", "厨", "COUNTER"],
        "aircon": ["AC", "空调", "AIRCON", "AIR_CONDITIONER"],
        "door": ["DOOR", "门", "M_"],
        "window": ["WINDOW", "窗", "W_", "WIN"],
    }

    def __init__(self, doc: Drawing):
        self.doc = doc

    # ─── 门 ───

    def create_door_block(
        self,
        name: str = "M_900",
        width: float = 900,
        thickness: float = 40,
        layer: str = "DOOR",
    ):
        """
        创建门块定义（含门板弧线）。

        门由以下部分组成:
        - 门板（矩形，可旋转）
        - 开门弧线（四分之一圆弧）

        Args:
            name: 块名
            width: 门洞宽度（mm），默认 900
            thickness: 门板厚度（mm），默认 40
            layer: 所在图层
        """
        if name in self.doc.blocks:
            return self.doc.blocks[name]

        block = self.doc.blocks.new(name=name)
        # 门板矩形（从原点向上）
        points = [
            (0, 0),
            (0, thickness),
            (width, thickness),
            (width, 0),
        ]
        block.add_lwpolyline(points, close=True, dxfattribs={"layer": layer})

        # 开门弧线（从门板末端扫过 90°）
        block.add_arc(
            center=(0, 0),
            radius=width,
            start_angle=0,
            end_angle=90,
            dxfattribs={"layer": layer},
        )

        # 门铰链标记（小圆点）
        block.add_circle(
            center=(0, 0),
            radius=15,
            dxfattribs={"layer": layer},
        )

        return block

    # ─── 窗 ───

    def create_window_block(
        self,
        name: str = "W_1500",
        width: float = 1500,
        wall_thickness: float = 240,
        layer: str = "WINDOW",
    ):
        """
        创建窗户块定义。

        窗由外框和中间两条平行线表示（标准建筑画法）。

        Args:
            name: 块名
            width: 窗洞宽度（mm），默认 1500
            wall_thickness: 墙厚（mm），默认 240
            layer: 所在图层
        """
        if name in self.doc.blocks:
            return self.doc.blocks[name]

        block = self.doc.blocks.new(name=name)

        # 外框（上下两条线表示墙体截面）
        block.add_line(
            (0, 0), (width, 0),
            dxfattribs={"layer": layer},
        )
        block.add_line(
            (0, wall_thickness), (width, wall_thickness),
            dxfattribs={"layer": layer},
        )

        # 窗框中线（两条平行线表示玻璃）
        gap = wall_thickness / 3
        block.add_line(
            (0, gap), (width, gap),
            dxfattribs={"layer": layer},
        )
        block.add_line(
            (0, gap * 2), (width, gap * 2),
            dxfattribs={"layer": layer},
        )

        # 左右封口
        block.add_line(
            (0, 0), (0, wall_thickness),
            dxfattribs={"layer": layer},
        )
        block.add_line(
            (width, 0), (width, wall_thickness),
            dxfattribs={"layer": layer},
        )

        return block

    # ─── 家具 ───

    def create_sofa_block(
        self,
        name: str = "SOFA_3P",
        width: float = 2100,
        depth: float = 850,
        layer: str = "FURNITURE",
    ):
        """创建三人沙发块定义"""
        if name in self.doc.blocks:
            return self.doc.blocks[name]

        block = self.doc.blocks.new(name=name)

        # 外框
        block.add_lwpolyline(
            [(0, 0), (width, 0), (width, depth), (0, depth)],
            close=True,
            dxfattribs={"layer": layer},
        )

        # 靠背
        back_thickness = 200
        block.add_lwpolyline(
            [
                (0, depth - back_thickness),
                (width, depth - back_thickness),
                (width, depth),
                (0, depth),
            ],
            close=True,
            dxfattribs={"layer": layer},
        )

        # 扶手
        arm_width = 80
        block.add_lwpolyline(
            [(0, 0), (arm_width, 0), (arm_width, depth - back_thickness),
             (0, depth - back_thickness)],
            close=True,
            dxfattribs={"layer": layer},
        )
        block.add_lwpolyline(
            [(width - arm_width, 0), (width, 0), (width, depth - back_thickness),
             (width - arm_width, depth - back_thickness)],
            close=True,
            dxfattribs={"layer": layer},
        )

        # 坐垫分隔线（三人位）
        cushion_width = (width - 2 * arm_width) / 3
        for i in range(1, 3):
            x = arm_width + cushion_width * i
            block.add_line(
                (x, 0), (x, depth - back_thickness),
                dxfattribs={"layer": layer},
            )

        # 标签文字
        block.add_text(
            "沙发",
            dxfattribs={"layer": layer, "height": 60},
        ).set_placement((width / 2, depth / 2 - 30), align=TextEntityAlignment.MIDDLE_CENTER)

        return block

    def create_bed_block(
        self,
        name: str = "BED_1800",
        width: float = 1800,
        length: float = 2000,
        layer: str = "FURNITURE",
    ):
        """创建双人床块定义"""
        if name in self.doc.blocks:
            return self.doc.blocks[name]

        block = self.doc.blocks.new(name=name)

        # 外框
        block.add_lwpolyline(
            [(0, 0), (width, 0), (width, length), (0, length)],
            close=True,
            dxfattribs={"layer": layer},
        )

        # 床头板
        headboard = 100
        block.add_lwpolyline(
            [(0, length - headboard), (width, length - headboard),
             (width, length), (0, length)],
            close=True,
            dxfattribs={"layer": layer},
        )

        # 枕头
        pillow_w = width / 2 - 50
        pillow_h = 250
        for i in range(2):
            px = 50 + i * (pillow_w + 50)
            block.add_lwpolyline(
                [(px, length - headboard - pillow_h - 20),
                 (px + pillow_w, length - headboard - pillow_h - 20),
                 (px + pillow_w, length - headboard - 20),
                 (px, length - headboard - 20)],
                close=True,
                dxfattribs={"layer": layer},
            )

        # 被子线（从枕头下方延伸的弧线表示被子）
        block.add_line(
            (0, length - headboard - pillow_h - 40),
            (width, length - headboard - pillow_h - 40),
            dxfattribs={"layer": layer},
        )

        # 标签
        block.add_text(
            "床",
            dxfattribs={"layer": layer, "height": 60},
        ).set_placement((width / 2, length / 4), align=TextEntityAlignment.MIDDLE_CENTER)

        return block

    def create_table_block(
        self,
        name: str = "TABLE_1200",
        width: float = 1200,
        depth: float = 700,
        layer: str = "FURNITURE",
    ):
        """创建餐桌/书桌块定义"""
        if name in self.doc.blocks:
            return self.doc.blocks[name]

        block = self.doc.blocks.new(name=name)
        block.add_lwpolyline(
            [(0, 0), (width, 0), (width, depth), (0, depth)],
            close=True,
            dxfattribs={"layer": layer},
        )
        block.add_text(
            "桌",
            dxfattribs={"layer": layer, "height": 50},
        ).set_placement((width / 2, depth / 2), align=TextEntityAlignment.MIDDLE_CENTER)
        return block

    def create_chair_block(
        self,
        name: str = "CHAIR",
        size: float = 450,
        layer: str = "FURNITURE",
    ):
        """创建椅子块定义"""
        if name in self.doc.blocks:
            return self.doc.blocks[name]

        block = self.doc.blocks.new(name=name)
        back = 50
        # 座面
        block.add_lwpolyline(
            [(0, 0), (size, 0), (size, size - back), (0, size - back)],
            close=True,
            dxfattribs={"layer": layer},
        )
        # 椅背
        block.add_lwpolyline(
            [(0, size - back), (size, size - back), (size, size), (0, size)],
            close=True,
            dxfattribs={"layer": layer},
        )
        return block

    def create_toilet_block(
        self,
        name: str = "TOILET",
        width: float = 400,
        depth: float = 600,
        layer: str = "FURNITURE",
    ):
        """创建马桶块定义"""
        if name in self.doc.blocks:
            return self.doc.blocks[name]

        block = self.doc.blocks.new(name=name)
        # 水箱
        tank_h = 150
        block.add_lwpolyline(
            [(0, depth - tank_h), (width, depth - tank_h),
             (width, depth), (0, depth)],
            close=True,
            dxfattribs={"layer": layer},
        )
        # 坐圈（用椭圆近似）
        seat_w = width / 2
        seat_h = (depth - tank_h) / 2
        if seat_w >= seat_h:
            block.add_ellipse(
                center=(width / 2, seat_h),
                major_axis=(seat_w, 0),
                ratio=seat_h / seat_w,
                dxfattribs={"layer": layer},
            )
        else:
            block.add_ellipse(
                center=(width / 2, seat_h),
                major_axis=(0, seat_h),
                ratio=seat_w / seat_h,
                dxfattribs={"layer": layer},
            )
        return block

    def create_sink_block(
        self,
        name: str = "SINK",
        width: float = 600,
        depth: float = 450,
        layer: str = "FURNITURE",
    ):
        """创建洗手盆块定义"""
        if name in self.doc.blocks:
            return self.doc.blocks[name]

        block = self.doc.blocks.new(name=name)
        block.add_lwpolyline(
            [(0, 0), (width, 0), (width, depth), (0, depth)],
            close=True,
            dxfattribs={"layer": layer},
        )
        # 内框（水槽）
        margin = 50
        block.add_lwpolyline(
            [(margin, margin), (width - margin, margin),
             (width - margin, depth - margin), (margin, depth - margin)],
            close=True,
            dxfattribs={"layer": layer},
        )
        # 水龙头
        block.add_circle(
            center=(width / 2, depth - margin / 2),
            radius=20,
            dxfattribs={"layer": layer},
        )
        return block

    def create_fridge_block(
        self,
        name: str = "FRIDGE",
        width: float = 600,
        depth: float = 650,
        layer: str = "FURNITURE",
    ):
        """创建冰箱块定义"""
        if name in self.doc.blocks:
            return self.doc.blocks[name]

        block = self.doc.blocks.new(name=name)
        block.add_lwpolyline(
            [(0, 0), (width, 0), (width, depth), (0, depth)],
            close=True,
            dxfattribs={"layer": layer},
        )
        # 分割线（冷藏/冷冻）
        block.add_line(
            (0, depth / 3), (width, depth / 3),
            dxfattribs={"layer": layer},
        )
        block.add_text(
            "冰箱",
            dxfattribs={"layer": layer, "height": 50},
        ).set_placement((width / 2, depth / 2), align=TextEntityAlignment.MIDDLE_CENTER)
        return block

    def create_washer_block(
        self,
        name: str = "WASHER",
        width: float = 600,
        depth: float = 550,
        layer: str = "FURNITURE",
    ):
        """创建洗衣机块定义"""
        if name in self.doc.blocks:
            return self.doc.blocks[name]

        block = self.doc.blocks.new(name=name)
        block.add_lwpolyline(
            [(0, 0), (width, 0), (width, depth), (0, depth)],
            close=True,
            dxfattribs={"layer": layer},
        )
        # 滚筒
        block.add_circle(
            center=(width / 2, depth / 2),
            radius=min(width, depth) / 3,
            dxfattribs={"layer": layer},
        )
        block.add_text(
            "洗衣机",
            dxfattribs={"layer": layer, "height": 40},
        ).set_placement((width / 2, depth - 30), align=TextEntityAlignment.MIDDLE_CENTER)
        return block

    def create_stove_block(
        self,
        name: str = "STOVE",
        width: float = 750,
        depth: float = 450,
        layer: str = "FURNITURE",
    ):
        """创建灶台块定义"""
        if name in self.doc.blocks:
            return self.doc.blocks[name]

        block = self.doc.blocks.new(name=name)
        block.add_lwpolyline(
            [(0, 0), (width, 0), (width, depth), (0, depth)],
            close=True,
            dxfattribs={"layer": layer},
        )
        # 四个灶眼
        r = 60
        positions = [
            (width / 4, depth / 4 * 3),
            (width / 4 * 3, depth / 4 * 3),
            (width / 4, depth / 4),
            (width / 4 * 3, depth / 4),
        ]
        for px, py in positions:
            block.add_circle(
                center=(px, py), radius=r,
                dxfattribs={"layer": layer},
            )
            block.add_circle(
                center=(px, py), radius=r * 0.5,
                dxfattribs={"layer": layer},
            )
        return block

    # ─── 批量初始化标准块 ───

    def init_standard_blocks(self):
        """初始化全套标准装修图块定义"""
        self.create_door_block("M_700", width=700)
        self.create_door_block("M_800", width=800)
        self.create_door_block("M_900", width=900)
        self.create_door_block("M_1000", width=1000)
        self.create_window_block("W_900", width=900)
        self.create_window_block("W_1200", width=1200)
        self.create_window_block("W_1500", width=1500)
        self.create_window_block("W_1800", width=1800)
        self.create_sofa_block("SOFA_3P", width=2100, depth=850)
        self.create_sofa_block("SOFA_2P", width=1400, depth=850)
        self.create_bed_block("BED_1800", width=1800, length=2000)
        self.create_bed_block("BED_1500", width=1500, length=2000)
        self.create_bed_block("BED_1200", width=1200, length=2000)
        self.create_table_block("TABLE_1200", width=1200, depth=700)
        self.create_table_block("TABLE_800", width=800, depth=500)
        self.create_chair_block("CHAIR", size=450)
        self.create_toilet_block("TOILET")
        self.create_sink_block("SINK")
        self.create_fridge_block("FRIDGE")
        self.create_washer_block("WASHER")
        self.create_stove_block("STOVE")

    # ─── 识别辅助 ───

    @classmethod
    def classify_block_name(cls, block_name: str) -> str:
        """
        根据块名判断家具类型。
        返回类型字符串，无法识别时返回 'unknown'。
        """
        name_upper = block_name.upper()
        for ftype, keywords in cls.FURNITURE_KEYWORDS.items():
            for kw in keywords:
                if kw.upper() in name_upper:
                    return ftype
        return "unknown"
