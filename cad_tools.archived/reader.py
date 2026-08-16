"""
reader — DXF 读取 & 建筑语义解析

解析 DXF 装修图，提取结构化的建筑语义信息：
    - 图层信息
    - 墙体（LINE/LWPOLYLINE）
    - 门（INSERT 块引用）
    - 窗户（INSERT 块引用）
    - 家具（INSERT 块引用，自动分类）
    - 尺寸标注（DIMENSION）
    - 文字标注（TEXT/MTEXT）
    - 房间推断（从墙体闭合区域推断）

使用方式:
    reader = FloorPlanReader("floor_plan.dxf")
    info = reader.parse()
    print(f"共 {len(info['walls'])} 段墙, {len(info['rooms'])} 个房间")
    rooms = reader.get_rooms()
    furniture = reader.get_furniture()
"""

from __future__ import annotations
from typing import Optional
from dataclasses import dataclass, field
import ezdxf
from ezdxf.document import Drawing

from .geometry import (
    distance, polygon_area, point_in_polygon, polyline_length,
    is_closed, bbox_of,
)
from .blocks import BlockLibrary


@dataclass
class Wall:
    """墙体段"""
    layer: str
    coords: list[tuple[float, float]]
    length: float
    closed: bool
    thickness: float = 0.0

    def to_dict(self) -> dict:
        return {
            "layer": self.layer,
            "coords": self.coords,
            "length_mm": round(self.length, 1),
            "length_m": round(self.length / 1000, 3),
            "closed": self.closed,
            "thickness": self.thickness,
        }


@dataclass
class Door:
    """门"""
    block_name: str
    position: tuple[float, float]
    rotation: float
    scale: tuple[float, float, float]
    layer: str

    def to_dict(self) -> dict:
        return {
            "block": self.block_name,
            "position": self.position,
            "rotation": self.rotation,
            "scale": self.scale,
            "layer": self.layer,
            "width_hint": self._guess_width(),
        }

    def _guess_width(self) -> float:
        """从块名猜测门宽"""
        import re
        m = re.search(r'(\d+)', self.block_name)
        return float(m.group(1)) if m else 900.0


@dataclass
class Window:
    """窗户"""
    block_name: str
    position: tuple[float, float]
    rotation: float
    scale: tuple[float, float, float]
    layer: str

    def to_dict(self) -> dict:
        return {
            "block": self.block_name,
            "position": self.position,
            "rotation": self.rotation,
            "scale": self.scale,
            "layer": self.layer,
            "width_hint": self._guess_width(),
        }

    def _guess_width(self) -> float:
        import re
        m = re.search(r'(\d+)', self.block_name)
        return float(m.group(1)) if m else 1500.0


@dataclass
class Furniture:
    """家具"""
    block_name: str
    furniture_type: str
    position: tuple[float, float]
    rotation: float
    scale: tuple[float, float, float]
    layer: str

    def to_dict(self) -> dict:
        return {
            "block": self.block_name,
            "type": self.furniture_type,
            "position": self.position,
            "rotation": self.rotation,
            "scale": self.scale,
            "layer": self.layer,
        }


@dataclass
class Room:
    """房间（从墙体闭合区域推断）"""
    boundary: list[tuple[float, float]]
    area: float  # mm²
    name: str = ""
    furniture_inside: list[str] = field(default_factory=list)

    @property
    def area_m2(self) -> float:
        return self.area / 1e6

    def to_dict(self) -> dict:
        return {
            "boundary": self.boundary,
            "area_mm2": round(self.area, 1),
            "area_m2": round(self.area_m2, 2),
            "name": self.name,
            "furniture": self.furniture_inside,
        }


class FloorPlanReader:
    """DXF 装修图语义解析器"""

    # 墙体图层关键词
    WALL_KEYWORDS = ["WALL", "墙", "WALLS", "W-WALL"]
    # 门图层/块名关键词
    DOOR_KEYWORDS = ["DOOR", "门", "M_", "D_"]
    # 窗户图层/块名关键词
    WINDOW_KEYWORDS = ["WINDOW", "窗", "W_", "WIN"]
    # 文字图层关键词
    TEXT_KEYWORDS = ["TEXT", "文字", "LABEL", "NOTE", "标注"]

    def __init__(self, dxf_path: Optional[str] = None, doc: Optional[Drawing] = None):
        """
        Args:
            dxf_path: DXF 文件路径
            doc: 已加载的 ezdxf 文档（与 dxf_path 二选一）
        """
        if doc is not None:
            self.doc = doc
        elif dxf_path is not None:
            self.doc = ezdxf.readfile(dxf_path)
        else:
            raise ValueError("必须提供 dxf_path 或 doc")

        self.msp = self.doc.modelspace()
        self._cache: Optional[dict] = None

    def parse(self) -> dict:
        """
        完整解析 DXF，返回结构化信息字典。
        结果会被缓存，后续调用直接返回缓存。
        """
        if self._cache is not None:
            return self._cache

        walls = self._parse_walls()
        doors = self._parse_doors()
        windows = self._parse_windows()
        furniture = self._parse_furniture()
        rooms = self._detect_rooms(walls, furniture)
        dimensions = self._parse_dimensions()
        texts = self._parse_texts()
        layers = self._parse_layers()
        block_defs = self._parse_block_defs()

        self._cache = {
            "layers": layers,
            "walls": [w.to_dict() for w in walls],
            "doors": [d.to_dict() for d in doors],
            "windows": [w.to_dict() for w in windows],
            "furniture": [f.to_dict() for f in furniture],
            "rooms": [r.to_dict() for r in rooms],
            "dimensions": dimensions,
            "texts": texts,
            "block_defs": block_defs,
            "summary": {
                "wall_count": len(walls),
                "door_count": len(doors),
                "window_count": len(windows),
                "furniture_count": len(furniture),
                "room_count": len(rooms),
                "dimension_count": len(dimensions),
                "text_count": len(texts),
                "total_wall_length_m": round(
                    sum(w.length for w in walls) / 1000, 2
                ),
                "total_area_m2": round(
                    sum(r.area for r in rooms) / 1e6, 2
                ),
            },
        }
        return self._cache

    def get_rooms(self) -> list[dict]:
        """获取房间列表"""
        return self.parse()["rooms"]

    def get_furniture(self) -> list[dict]:
        """获取家具列表"""
        return self.parse()["furniture"]

    def get_walls(self) -> list[dict]:
        """获取墙体列表"""
        return self.parse()["walls"]

    def get_summary(self) -> dict:
        """获取摘要信息"""
        return self.parse()["summary"]

    # ─── 内部解析方法 ───

    def _match_keywords(self, text: str, keywords: list[str]) -> bool:
        """检查文本是否包含任一关键词（大小写不敏感）"""
        text_upper = text.upper()
        return any(kw.upper() in text_upper for kw in keywords)

    def _parse_layers(self) -> list[dict]:
        """解析所有图层"""
        layers = []
        for layer in self.doc.layers:
            layers.append({
                "name": layer.dxf.name,
                "color": layer.dxf.color,
                "is_on": layer.is_on(),
                "is_frozen": layer.is_frozen(),
                "is_locked": layer.is_locked(),
            })
        return layers

    def _parse_walls(self) -> list[Wall]:
        """提取墙体：多段线/直线，按图层过滤"""
        walls = []

        # LWPOLYLINE
        for entity in self.msp.query('LWPOLYLINE'):
            layer = entity.dxf.layer
            if self._match_keywords(layer, self.WALL_KEYWORDS):
                coords = [(p[0], p[1]) for p in entity.get_points()]
                closed = entity.closed or is_closed(coords)
                walls.append(Wall(
                    layer=layer,
                    coords=coords,
                    length=polyline_length(coords, closed),
                    closed=closed,
                    thickness=getattr(entity.dxf, 'const_width', 0) or 0,
                ))

        # LINE（单段直线也可能是墙）
        for entity in self.msp.query('LINE'):
            layer = entity.dxf.layer
            if self._match_keywords(layer, self.WALL_KEYWORDS):
                start = (entity.dxf.start.x, entity.dxf.start.y)
                end = (entity.dxf.end.x, entity.dxf.end.y)
                walls.append(Wall(
                    layer=layer,
                    coords=[start, end],
                    length=distance(start, end),
                    closed=False,
                    thickness=0,
                ))

        return walls

    def _parse_doors(self) -> list[Door]:
        """提取门：块引用，按图层或块名过滤"""
        doors = []
        for entity in self.msp.query('INSERT'):
            layer = entity.dxf.layer
            name = entity.dxf.name
            if (self._match_keywords(layer, self.DOOR_KEYWORDS) or
                self._match_keywords(name, self.DOOR_KEYWORDS)):
                doors.append(Door(
                    block_name=name,
                    position=(entity.dxf.insert.x, entity.dxf.insert.y),
                    rotation=entity.dxf.rotation,
                    scale=(entity.dxf.xscale, entity.dxf.yscale, 1.0),
                    layer=layer,
                ))
        return doors

    def _parse_windows(self) -> list[Window]:
        """提取窗户：块引用，按图层或块名过滤"""
        windows = []
        for entity in self.msp.query('INSERT'):
            layer = entity.dxf.layer
            name = entity.dxf.name
            # 排除已被门识别的
            if self._match_keywords(name, self.DOOR_KEYWORDS):
                continue
            if (self._match_keywords(layer, self.WINDOW_KEYWORDS) or
                self._match_keywords(name, self.WINDOW_KEYWORDS)):
                windows.append(Window(
                    block_name=name,
                    position=(entity.dxf.insert.x, entity.dxf.insert.y),
                    rotation=entity.dxf.rotation,
                    scale=(entity.dxf.xscale, entity.dxf.yscale, 1.0),
                    layer=layer,
                ))
        return windows

    def _parse_furniture(self) -> list[Furniture]:
        """提取家具：块引用，自动分类"""
        furniture = []
        for entity in self.msp.query('INSERT'):
            layer = entity.dxf.layer
            name = entity.dxf.name

            # 排除门和窗
            if self._match_keywords(name, self.DOOR_KEYWORDS):
                continue
            if self._match_keywords(name, self.WINDOW_KEYWORDS):
                continue
            # 排除轴线等非家具图层
            if self._match_keywords(layer, ["AXIS", "轴", "DIMENSION", "标注"]):
                continue

            ftype = BlockLibrary.classify_block_name(name)
            if ftype != "unknown":
                furniture.append(Furniture(
                    block_name=name,
                    furniture_type=ftype,
                    position=(entity.dxf.insert.x, entity.dxf.insert.y),
                    rotation=entity.dxf.rotation,
                    scale=(entity.dxf.xscale, entity.dxf.yscale, 1.0),
                    layer=layer,
                ))
            else:
                # 未识别的 INSERT 块也保留，标记为 unknown
                # 但排除在 WALL 图层上的（可能是墙块引用）
                if not self._match_keywords(layer, self.WALL_KEYWORDS):
                    furniture.append(Furniture(
                        block_name=name,
                        furniture_type="unknown",
                        position=(entity.dxf.insert.x, entity.dxf.insert.y),
                        rotation=entity.dxf.rotation,
                        scale=(entity.dxf.xscale, entity.dxf.yscale, 1.0),
                        layer=layer,
                    ))
        return furniture

    def _detect_rooms(self, walls: list[Wall], furniture: list[Furniture]) -> list[Room]:
        """
        推断房间：从闭合墙体多段线推断房间区域。
        并将家具归属到对应房间。
        """
        rooms = []
        for wall in walls:
            if wall.closed and len(wall.coords) >= 4:
                area = polygon_area(wall.coords)
                if area > 10000:  # 过滤太小的区域（<0.01㎡）
                    room = Room(
                        boundary=wall.coords,
                        area=area,
                    )
                    # 查找房间内的家具
                    for fur in furniture:
                        if point_in_polygon(fur.position, wall.coords):
                            room.furniture_inside.append(fur.block_name)
                    rooms.append(room)

        # 按面积排序（大到小）
        rooms.sort(key=lambda r: r.area, reverse=True)

        # 尝试从文字标注推断房间名
        texts = self._parse_texts()
        for room in rooms:
            for text_info in texts:
                if point_in_polygon(
                    (text_info["position"][0], text_info["position"][1]),
                    room.boundary
                ):
                    room.name = text_info["text"][:20]
                    break

        return rooms

    def _parse_dimensions(self) -> list[dict]:
        """提取尺寸标注"""
        dims = []
        for entity in self.msp.query('DIMENSION'):
            try:
                dim_data = {
                    "type": entity.dxf.dimtype,
                    "layer": entity.dxf.layer,
                    "measurement": None,
                }
                # 尝试获取实际测量值
                if hasattr(entity, 'get_measurement'):
                    try:
                        dim_data["measurement"] = round(entity.get_measurement(), 1)
                    except Exception:
                        pass
                dims.append(dim_data)
            except Exception:
                continue
        return dims

    def _parse_texts(self) -> list[dict]:
        """提取文字标注（TEXT 和 MTEXT）"""
        texts = []
        for entity in self.msp.query('TEXT MTEXT'):
            try:
                text_content = ""
                pos = (0, 0)
                if entity.dxftype() == "TEXT":
                    text_content = entity.dxf.text
                    pos = (entity.dxf.insert.x, entity.dxf.insert.y)
                elif entity.dxftype() == "MTEXT":
                    text_content = entity.text
                    pos = (entity.dxf.insert.x, entity.dxf.insert.y)

                texts.append({
                    "text": text_content,
                    "position": pos,
                    "height": getattr(entity.dxf, 'height', 0),
                    "layer": entity.dxf.layer,
                    "type": entity.dxftype(),
                })
            except Exception:
                continue
        return texts

    def _parse_block_defs(self) -> list[dict]:
        """解析所有块定义"""
        block_defs = []
        for block in self.doc.blocks:
            if block.name.startswith("*"):
                continue  # 跳过匿名块
            block_defs.append({
                "name": block.name,
                "entity_count": len(block),
                "furniture_type": BlockLibrary.classify_block_name(block.name),
            })
        return block_defs

    def query(self, question: str) -> str:
        """
        简单的自然语言查询接口。
        支持常见问题模式：
        - "有几个房间" / "多少个房间"
        - "面积" / "多大"
        - "多少个门" / "多少个窗"
        - "家具" / "有什么"
        """
        info = self.parse()
        q = question.lower().replace("？", "?").strip()

        if any(k in q for k in ["几个房间", "多少个房间", "房间数"]):
            return f"图中共有 {info['summary']['room_count']} 个房间。"

        if any(k in q for k in ["几个门", "多少个门", "门数"]):
            return f"图中共有 {info['summary']['door_count']} 个门。"

        if any(k in q for k in ["几个窗", "多少个窗", "窗户数", "窗数"]):
            return f"图中共有 {info['summary']['window_count']} 个窗户。"

        if any(k in q for k in ["面积", "多大"]):
            rooms_info = "; ".join(
                f"{r.get('name', f'房间{i+1}')} {r['area_m2']}㎡"
                for i, r in enumerate(info["rooms"])
            )
            return f"总面积约 {info['summary']['total_area_m2']}㎡。各房间: {rooms_info}"

        if any(k in q for k in ["家具", "有什么", "哪些"]):
            fur_types = {}
            for f in info["furniture"]:
                t = f["type"]
                fur_types[t] = fur_types.get(t, 0) + 1
            detail = ", ".join(f"{t}×{c}" for t, c in fur_types.items())
            return f"图中共有 {info['summary']['furniture_count']} 件家具: {detail}"

        if any(k in q for k in ["墙", "墙体"]):
            return (f"图中共有 {info['summary']['wall_count']} 段墙体，"
                    f"总长度 {info['summary']['total_wall_length_m']}m。")

        return f"已解析图纸: {info['summary']}"
