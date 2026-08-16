"""Lint 测试：确保 5 个 user_tool 的 docstring 满足 §3.4 模板。

跑：python -m pytest tests/test_tool_descriptions.py

MVP 5 个 tool 的 description 直接决定 LLM 路由准确率（KPI §8 "单次会话用工具数 1-3"）。
本测试防止 docstring 漂移：每个 docstring 必须含
  - "不要用于"（明示何时不调）
  - "用户典型口语："（给 LLM 看的用户表达示例）
  - "Args:"（参数契约）
"""

from __future__ import annotations
import sys
import inspect
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.floorplan_tools as ft


EXPECTED_TOOLS = {
    "read_floorplan",
    "list_rooms",
    "move_furniture",
    "render_preview",
    "export_drawing",
}


def test_exactly_five_public_tools():
    public = {n for n, _ in inspect.getmembers(ft, inspect.isfunction)
              if not n.startswith("_") and n != "get_backend"}
    # get_backend 是 import 进来的别名，排除
    assert public == EXPECTED_TOOLS, f"工具集漂移: {public ^ EXPECTED_TOOLS}"


@pytest.mark.parametrize("tool_name", sorted(EXPECTED_TOOLS))
def test_docstring_has_required_sections(tool_name):
    fn = getattr(ft, tool_name)
    doc = inspect.getdoc(fn) or ""
    assert doc, f"{tool_name} 缺 docstring"

    # 必须有"不要用于"段落（路由负例）
    assert "不要用于" in doc, (
        f"{tool_name}: docstring 缺'不要用于'段落（让 LLM 知道何时不调）"
    )
    # 必须有"用户典型口语："（让 LLM 抓用户表达）
    assert "用户典型口语" in doc, (
        f"{tool_name}: docstring 缺'用户典型口语：'示例段落"
    )
    # 必须有 Args:（参数契约）
    assert "Args:" in doc, f"{tool_name}: docstring 缺 'Args:' 段落"
    # 必须提容器内路径换算（让用户给家居路径不会传错）
    if "path" in inspect.signature(fn).parameters:
        assert "容器内" in doc or "/data" in doc, (
            f"{tool_name}: docstring 应说明 path 用容器内路径或 /data 换算"
        )


@pytest.mark.parametrize("tool_name", sorted(EXPECTED_TOOLS))
def test_docstring_at_least_3_user_phrases(tool_name):
    """每个 tool 的口语示例至少 3 条（足够 LLM 启发）。"""
    fn = getattr(ft, tool_name)
    doc = inspect.getdoc(fn) or ""
    # 抓"用户典型口语："后面到 "Args:" 之前那段的列表项
    start = doc.find("用户典型口语")
    end = doc.find("Args:", start)
    section = doc[start:end] if start >= 0 and end > start else ""
    # 用破折号或 "- " 计列表项
    items = section.count("- ")
    assert items >= 3, (
        f"{tool_name}: '用户典型口语' 至少 3 条，实际 {items}"
    )


def test_path_params_are_str():
    """路径参数必须是 str 类型（LLM 容易传错为 float）。

    `from __future__ import annotations` 让 annotation 变成字符串字面，
    所以这里同时接受 str 类本身 或 字符串 'str'。
    """
    for name in EXPECTED_TOOLS:
        fn = getattr(ft, name)
        sig = inspect.signature(fn)
        if "path" in sig.parameters:
            ann = sig.parameters["path"].annotation
            assert ann is str or ann == "str", \
                f"{name}.path 必须是 str，实际 {ann!r}"
        for pn in ("output_path", "output_png"):
            if pn in sig.parameters:
                ann = sig.parameters[pn].annotation
                assert ann is str or ann == "str", \
                    f"{name}.{pn} 必须是 str，实际 {ann!r}"
