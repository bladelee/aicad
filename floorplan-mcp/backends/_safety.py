"""安全工具：写操作的事务包装 + 自动备份（.bak.N）。

⚠️ R2 调研结论：freecad-ai 的 user_tools handler 不走 _with_undo，
所以我们的写工具必须自己包 openTransaction + .bak。
本模块是所有写后端的共用基础。

设计原则：
  1. 永远先备份原文件（*.bak.N）—— 防永久坏文件，肉眼看不到的错也能回滚
  2. 在 FreeCAD 事务内做修改 —— 出异常时 abortTransaction 把文档状态弹回
  3. 只有事务 commit 成功才落盘 —— 双重保险

备份文件命名：原文件 .bak.1, .bak.2, ...（数字越大越新）。
"""

from __future__ import annotations
import os
import shutil
from pathlib import Path


def make_backup(path: str, max_keep: int = 10) -> str | None:
    """复制 path 到 path.bak.N（N = 现有 .bak 数 + 1），返回备份路径。

    Args:
        path: 原文件
        max_keep: 最多保留多少个 .bak（FIFO 清理）
    """
    if not os.path.isfile(path):
        return None
    p = Path(path)
    # 找现有 .bak.* 数量
    existing = sorted(p.parent.glob(f"{p.name}.bak.*"))
    n = len(existing) + 1
    backup = p.parent / f"{p.name}.bak.{n}"
    shutil.copy2(path, backup)
    # FIFO 清理
    if len(existing) + 1 > max_keep:
        for old in existing[: len(existing) + 1 - max_keep]:
            try:
                old.unlink()
            except OSError:
                pass
    return str(backup)


def with_transaction(doc, label: str, do, *, save_path: str | None = None,
                     auto_backup: bool = True):
    """在 FreeCAD 事务里执行 do(doc)，提交后保存。

    Args:
        doc: FreeCAD ActiveDocument
        label: 事务名（出现在 undo stack）
        do: callable(doc) -> dict  实际的修改逻辑，返回要塞进结果的数据
        save_path: 落盘路径（None 则不存盘，仅改内存）
        auto_backup: True 时存盘前先 make_backup

    Returns:
        {"ok": True, "data": do 返回值, "backup_path": str | None,
         "error": None}

    出异常时：
        - abortTransaction 回滚 doc
        - 文件未被覆盖（备份+存盘顺序保证）
        - 返回 {"ok": False, "error": str}
    """
    backup = None
    if auto_backup and save_path and os.path.isfile(save_path):
        backup = make_backup(save_path)

    doc.openTransaction(label)
    try:
        data = do(doc)
        doc.recompute()
        doc.commitTransaction()
        if save_path:
            doc.saveAs(save_path)
        return {"ok": True, "data": data, "backup_path": backup, "error": None}
    except Exception as e:
        try:
            doc.abortTransaction()
            doc.recompute()
        except Exception:
            pass
        # 文件未被覆盖 —— 但内存 doc 已可能脏，调用方应重新 open
        return {"ok": False, "data": None, "backup_path": backup, "error": str(e)}
