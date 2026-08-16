"""Tools/core/verify_rename.py — 验证 #6 材料码替换效果。

底层 = tools/dxf_edit/verify_rename.py 是 print-only 脚本，
这里重构成纯函数 API。
"""
from __future__ import annotations
import re
from collections import Counter
from pathlib import Path
from typing import Optional


def verify_rename(
    dxf_paths: list[str | Path],
    old_code: str = "ST-01",
    new_code: str = "ST-A",
) -> dict:
    """验证一批 DXF 里 old_code 是否真的清空、new_code 是否到位。

    Args:
        dxf_paths: 要验证的 DXF 路径列表
        old_code: 旧材料码（默认 ST-01）
        new_code: 新材料码（默认 ST-A）

    Returns:
        {"ok": True,
         "old_code": str, "new_code": str,
         "files": [{"path": str,
                    "old_remaining": int,
                    "new_count": int,
                    "ok": bool}, ...],
         "total_old_remaining": int,
         "total_new_count": int,
         "overall_ok": bool}
    """
    import ezdxf

    pattern_old = re.compile(re.escape(old_code) + r"(?![0-9A-Z])")
    pattern_new = re.compile(re.escape(new_code) + r"(?![0-9A-Z])")

    def _scan(doc) -> Counter:
        c = Counter()
        for layout in doc.layouts:
            for ent in layout:
                if ent.dxftype() == "INSERT":
                    try:
                        for a in ent.attribs:
                            for k in ("tag", "text"):
                                v = getattr(a.dxf, k, "") or ""
                                c[f"{old_code}_left"] += len(pattern_old.findall(v))
                                c[f"{new_code}_now"] += len(pattern_new.findall(v))
                    except Exception:
                        pass
                elif ent.dxftype() == "TEXT":
                    v = ent.dxf.text or ""
                    c[f"{old_code}_left"] += len(pattern_old.findall(v))
                    c[f"{new_code}_now"] += len(pattern_new.findall(v))
                elif ent.dxftype() == "MTEXT":
                    try:
                        v = ent.text or ""
                        c[f"{old_code}_left"] += len(pattern_old.findall(v))
                        c[f"{new_code}_now"] += len(pattern_new.findall(v))
                    except Exception:
                        pass
        return c

    results: list[dict] = []
    total_old = 0
    total_new = 0
    for p in dxf_paths:
        p = Path(p)
        if not p.exists():
            results.append({"path": str(p), "ok": False, "error": "not found"})
            continue
        doc = ezdxf.readfile(str(p))
        c = _scan(doc)
        n_old = c[f"{old_code}_left"]
        n_new = c[f"{new_code}_now"]
        total_old += n_old
        total_new += n_new
        results.append({
            "path": str(p),
            "old_remaining": n_old,
            "new_count": n_new,
            "ok": n_old == 0,
        })

    return {
        "ok": True,
        "old_code": old_code,
        "new_code": new_code,
        "files": results,
        "total_old_remaining": total_old,
        "total_new_count": total_new,
        "overall_ok": total_old == 0 and total_new > 0,
    }


__all__ = ["verify_rename"]
