"""Tools/core/apply_material_rename.py — 重新暴露 #6 材料码替换。

底层 = tools/dxf_edit/apply_material_rename.py 的 process_dxf。
核心层包装：把模块级全局 OLD_CODE/NEW_CODE 替换为函数显式参数。
"""
from __future__ import annotations
import re
import sys
from pathlib import Path
from typing import Optional

_OLD = Path(__file__).resolve().parent.parent / "dxf_edit"
if str(_OLD) not in sys.path:
    sys.path.insert(0, str(_OLD))


def apply_material_rename(
    dxf_path: str | Path,
    old_code: str,
    new_code: str,
    out_path: Optional[str | Path] = None,
    backup_dir: Optional[str | Path] = None,
    dry_run: bool = False,
) -> dict:
    """把 DXF 内所有材料码 old_code 替换为 new_code（全字匹配，不误伤 ST-010/ST-012）。

    替换范围：所有 layout 的 INSERT.attribs(tag/text) + TEXT + MTEXT（plain text）

    Args:
        dxf_path: 输入 DXF 路径
        old_code: 旧材料码（如 "ST-01"）
        new_code: 新材料码（如 "ST-A"）
        out_path: 输出路径（None = 自动 <stem>_<old>_to_<new>.dxf）
        backup_dir: 备份目录（None = 不备份；给路径则首次执行时备份原文件）
        dry_run: True 不写文件，只返回计数

    Returns:
        {"ok": True,
         "input": str, "output": str | None, "backup": str | None,
         "old": str, "new": str,
         "total_replaced": int,
         "by_type": {"INSERT.tag": n, "TEXT": n, "MTEXT": n}}
    """
    import shutil
    import ezdxf
    from collections import Counter

    dxf_path = Path(dxf_path)
    pattern = re.compile(re.escape(old_code) + r"(?![0-9A-Z])")

    def _replace(text: str) -> tuple[str, int]:
        if not text:
            return text, 0
        return pattern.subn(new_code, text)

    def _safe_save(doc, path: Path):
        """绕开 ezdxf 1.4.4 materials 字典 bug（从老代码搬）"""
        original = type(doc)._update_header_vars

        def patched(self):
            try:
                original(self)
            except AttributeError as e:
                # warnings 走 stderr，避免污染 stdout CLI
                import sys as _sys
                _sys.stderr.write(
                    f"[warn] 跳过 header materials 更新: {e}\n"
                )

        type(doc)._update_header_vars = patched
        try:
            doc.saveas(str(path))
        finally:
            type(doc)._update_header_vars = original

    backup_path = None
    if backup_dir:
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{dxf_path.stem}.bak"
        if not backup_path.exists():
            shutil.copy2(dxf_path, backup_path)

    doc = ezdxf.readfile(str(dxf_path))

    type_repl = Counter()
    for layout in doc.layouts:
        for ent in layout:
            etype = ent.dxftype()
            if etype == "INSERT":
                try:
                    for attrib in ent.attribs:
                        for attr_name in ("tag", "text"):
                            try:
                                val = getattr(attrib.dxf, attr_name) or ""
                                if old_code in val:
                                    new_val, n = _replace(val)
                                    if n > 0:
                                        setattr(attrib.dxf, attr_name, new_val)
                                        type_repl[f"INSERT.{attr_name}"] += n
                            except Exception:
                                pass
                except Exception:
                    pass
            elif etype == "TEXT":
                try:
                    txt = ent.dxf.text or ""
                    if old_code in txt:
                        new_txt, n = _replace(txt)
                        if n > 0:
                            ent.dxf.text = new_txt
                            type_repl["TEXT"] += n
                except Exception:
                    pass
            elif etype == "MTEXT":
                try:
                    txt = ent.text or ""
                    if old_code in txt:
                        new_txt, n = _replace(txt)
                        if n > 0:
                            ent.text = new_txt
                            type_repl["MTEXT"] += n
                except Exception:
                    pass

    out_resolved = None
    if not dry_run:
        out_path = Path(out_path) if out_path else dxf_path.with_name(
            f"{dxf_path.stem}_{old_code}_to_{new_code}.dxf"
        )
        _safe_save(doc, out_path)
        out_resolved = str(out_path)

    return {
        "ok": True,
        "input": str(dxf_path),
        "output": out_resolved,
        "backup": str(backup_path) if backup_path else None,
        "old": old_code,
        "new": new_code,
        "total_replaced": sum(type_repl.values()),
        "by_type": dict(type_repl),
    }


__all__ = ["apply_material_rename"]
