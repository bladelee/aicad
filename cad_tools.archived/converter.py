"""
converter — DWG ↔ DXF 格式转换桥

提供 DWG 与 DXF 之间的格式转换。由于 DWG 是 AutoCAD 闭源格式，
需要借助外部工具实现转换。

支持的转换后端（按优先级自动探测）:
    1. ODA File Converter  — 免费但闭源，最可靠
    2. LibreDWG (dwg2dxf)  — GNU 开源
    3. 无后端时降级为仅 DXF 模式

使用方式:
    converter = DWGConverter()
    converter.dwg_to_dxf("input.dwg", "output.dxf")
    converter.dxf_to_dwg("input.dxf", "output.dwg")
"""

from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional


class DWGConverter:
    """DWG ↔ DXF 格式转换器"""

    def __init__(self):
        self._backend: Optional[str] = None
        self._oda_path: Optional[str] = None
        self._dwg2dxf_path: Optional[str] = None
        self._detect_backend()

    def _detect_backend(self):
        """自动探测可用的转换后端"""
        # 1. 尝试 ODA File Converter
        oda_names = [
            "ODAFileConverter",
            "ODA File Converter",
            "odafileconverter",
        ]
        oda_search_paths = [
            "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter",
            "/usr/local/bin/ODAFileConverter",
            "/opt/local/bin/ODAFileConverter",
            os.path.expanduser("~/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter"),
        ]
        for p in oda_search_paths:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                self._oda_path = p
                self._backend = "oda"
                return
        for name in oda_names:
            found = shutil.which(name)
            if found:
                self._oda_path = found
                self._backend = "oda"
                return

        # 2. 尝试 LibreDWG (dwg2dxf / dxf2dwg)
        for tool in ["dwg2dxf", "dxf2dwg"]:
            found = shutil.which(tool)
            if found:
                if tool == "dwg2dxf":
                    self._dwg2dxf_path = found
                    self._backend = "libredwg"
                    return

        # 3. 无后端
        self._backend = None

    @property
    def backend(self) -> Optional[str]:
        """当前使用的转换后端名称"""
        return self._backend

    @property
    def is_available(self) -> bool:
        """是否有可用的转换后端"""
        return self._backend is not None

    def dwg_to_dxf(
        self, dwg_path: str, dxf_path: Optional[str] = None
    ) -> str:
        """
        将 DWG 文件转换为 DXF 文件。

        Args:
            dwg_path: 输入 DWG 文件路径
            dxf_path: 输出 DXF 文件路径（默认同名 .dxf）

        Returns:
            输出 DXF 文件路径

        Raises:
            RuntimeError: 没有可用的转换后端
            FileNotFoundError: DWG 文件不存在
        """
        dwg_path = str(Path(dwg_path).resolve())
        if not os.path.isfile(dwg_path):
            raise FileNotFoundError(f"DWG 文件不存在: {dwg_path}")

        if dxf_path is None:
            dxf_path = str(Path(dwg_path).with_suffix(".dxf"))
        else:
            dxf_path = str(Path(dxf_path).resolve())

        if not self.is_available:
            raise RuntimeError(
                "没有可用的 DWG 转换后端。请安装以下之一:\n"
                "  1. ODA File Converter: https://www.opendesign.com/guestfiles/oda_file_converter\n"
                "  2. LibreDWG: brew install libredwg (需要 macOS 13+)"
            )

        if self._backend == "oda":
            self._convert_with_oda(dwg_path, dxf_path, to_dxf=True)
        elif self._backend == "libredwg":
            self._convert_with_libredwg(dwg_path, dxf_path, to_dxf=True)

        return dxf_path

    def dxf_to_dwg(
        self, dxf_path: str, dwg_path: Optional[str] = None
    ) -> str:
        """
        将 DXF 文件转换为 DWG 文件。

        Args:
            dxf_path: 输入 DXF 文件路径
            dwg_path: 输出 DWG 文件路径（默认同名 .dwg）

        Returns:
            输出 DWG 文件路径
        """
        dxf_path = str(Path(dxf_path).resolve())
        if not os.path.isfile(dxf_path):
            raise FileNotFoundError(f"DXF 文件不存在: {dxf_path}")

        if dwg_path is None:
            dwg_path = str(Path(dxf_path).with_suffix(".dwg"))
        else:
            dwg_path = str(Path(dwg_path).resolve())

        if not self.is_available:
            raise RuntimeError(
                "没有可用的 DWG 转换后端。请安装 ODA File Converter 或 LibreDWG。"
            )

        if self._backend == "oda":
            self._convert_with_oda(dxf_path, dwg_path, to_dxf=False)
        elif self._backend == "libredwg":
            self._convert_with_libredwg(dxf_path, dwg_path, to_dxf=False)

        return dwg_path

    def _convert_with_oda(
        self, input_path: str, output_path: str, to_dxf: bool
    ):
        """使用 ODA File Converter 进行转换"""
        input_dir = str(Path(input_path).parent)
        output_dir = str(Path(output_path).parent)
        input_name = Path(input_path).stem

        # ODA File Converter 的用法:
        # ODAFileConverter <input_dir> <output_dir> <ACADversion> <recurse> <audit> < DWG | DXF >
        # ACAD version: ACAD9..ACAD2018
        acad_version = "ACAD2018"
        recurse = "0"
        audit = "1"
        output_format = "DXF" if to_dxf else "DWG"

        cmd = [
            self._oda_path,
            input_dir,
            output_dir,
            acad_version,
            recurse,
            audit,
            output_format,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ODA File Converter 转换失败:\n{result.stderr}"
            )

        # ODA 输出文件名与输入同名，需要重命名
        expected_output = str(
            Path(output_dir) / f"{input_name}.{output_format.lower()}"
        )
        if expected_output != output_path and os.path.isfile(expected_output):
            shutil.move(expected_output, output_path)

    def _convert_with_libredwg(
        self, input_path: str, output_path: str, to_dxf: bool
    ):
        """使用 LibreDWG 进行转换"""
        if to_dxf:
            # dwg2dxf -o output.dxf input.dwg
            tool = self._dwg2dxf_path or shutil.which("dwg2dxf")
            cmd = [tool, "-o", output_path, input_path]
        else:
            # dxf2dwg -o output.dwg input.dxf
            tool = shutil.which("dxf2dwg")
            if not tool:
                raise RuntimeError("dxf2dwg 未安装")
            cmd = [tool, "-o", output_path, input_path]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"LibreDWG 转换失败:\n{result.stderr}"
            )

    def status(self) -> dict:
        """返回转换器状态信息"""
        return {
            "backend": self._backend,
            "is_available": self.is_available,
            "oda_path": self._oda_path,
            "libredwg_path": self._dwg2dxf_path,
            "hint": (
                "DWG 转换可用" if self.is_available
                else "请安装 ODA File Converter 或 LibreDWG 以启用 DWG 支持"
            ),
        }
