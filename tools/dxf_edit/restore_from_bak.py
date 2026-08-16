"""P3 原型：restore_from_bak.py 骨架

解决 R3（决策 4C 回滚链路模糊）：
- verify_change 只输出结构化报告（审计员）
- restore_from_bak 是只写执行器（执行者）
- LLM 在对话里读 verify_change 报告 → 决定 → 显式调本工具

功能:
    - 用最近 .bak 恢复 DXF
    - 自动给当前 DXF 做 .bak1（防回滚错）
    - 输出结构化结果供 LLM 确认

用法：
    # 恢复最新备份（默认找当前 dxf 同目录下最大的 .bakN.dxf）
    python tools/dxf_edit/restore_from_bak.py /path/to/file.dxf --latest

    # 恢复指定备份
    python tools/dxf_edit/restore_from_bak.py /path/to/file.dxf --bak file.dxf.bak3.dxf

    # 干跑（只看备份，不动文件）
    python tools/dxf_edit/restore_from_bak.py /path/to/file.dxf --latest --dry-run
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path


_BAK_PATTERN = re.compile(r"^(?P<stem>.+)\.bak(?P<n>\d+)\.dxf$")


def list_backups(dxf_path: Path) -> list[dict]:
    """列出 dxf_path 同目录下所有 .bakN.dxf，按编号降序"""
    out: list[dict] = []
    for p in dxf_path.parent.iterdir():
        m = _BAK_PATTERN.match(p.name)
        if not m:
            continue
        if m.group("stem") != dxf_path.stem:
            continue
        try:
            n = int(m.group("n"))
        except ValueError:
            continue
        out.append({"path": p, "n": n, "size_kb": p.stat().st_size // 1024})
    out.sort(key=lambda x: -x["n"])
    return out


def pick_latest_backup(dxf_path: Path) -> Path | None:
    backups = list_backups(dxf_path)
    return backups[0]["path"] if backups else None


def backup_current(dxf_path: Path) -> Path:
    """给当前 dxf 做 .bakN（轮转最大编号 + 1），防止回滚错无备份。"""
    existing = list_backups(dxf_path)
    max_n = max((b["n"] for b in existing), default=0)
    new_n = max_n + 1
    bak = dxf_path.with_name(f"{dxf_path.stem}.bak{new_n}.dxf")
    shutil.copy2(dxf_path, bak)
    return bak


def restore(dxf_path: Path, bak_path: Path,
            backup_current_first: bool = True,
            dry_run: bool = False) -> dict:
    """核心恢复逻辑"""
    if not dxf_path.exists():
        raise FileNotFoundError(f"目标文件不存在: {dxf_path}")
    if not bak_path.exists():
        raise FileNotFoundError(f"备份文件不存在: {bak_path}")

    result = {
        "ok": False,
        "target": str(dxf_path),
        "backup_source": str(bak_path),
        "pre_restore_backup": None,
        "dry_run": dry_run,
    }
    if dry_run:
        # 干跑只统计信息
        result["ok"] = True
        result["would_backup_to"] = str(dxf_path.with_name(
            f"{dxf_path.stem}.bakN.dxf"
        )) if backup_current_first else None
        return result

    pre_bak = None
    if backup_current_first:
        pre_bak = backup_current(dxf_path)
        result["pre_restore_backup"] = str(pre_bak)

    shutil.copy2(bak_path, dxf_path)
    result["ok"] = True
    result["restored_at"] = str(dxf_path)
    result["restored_size_kb"] = dxf_path.stat().st_size // 1024
    return result


def _cli() -> int:
    p = argparse.ArgumentParser(
        description="从 .bak 恢复 DXF（场景 B 的回滚执行器）"
    )
    p.add_argument("dxf", help="目标 DXF 文件路径")
    p.add_argument("--latest", action="store_true",
                   help="用最新 .bak 恢复（默认）")
    p.add_argument("--bak", help="指定 .bak 路径")
    p.add_argument("--no-pre-backup", action="store_true",
                   help="回滚前不先备份当前文件（不推荐）")
    p.add_argument("--dry-run", action="store_true",
                   help="只列出备份信息，不实际恢复")
    args = p.parse_args()

    dxf_path = Path(args.dxf).resolve()

    # 列所有 .bak 给用户确认
    backups = list_backups(dxf_path)
    if not backups:
        print(f"❌ {dxf_path.name} 同目录下无 .bak 文件")
        return 1

    if args.latest:
        bak_path = backups[0]["path"]
    elif args.bak:
        bak_path = Path(args.bak).resolve()
    else:
        # 默认就是 latest
        bak_path = backups[0]["path"]

    print(f"目标: {dxf_path.name}")
    print(f"恢复源: {bak_path.name}")
    print(f"  备份时间/大小: {bak_path.stat().st_size // 1024} KB, "
          f"mtime={bak_path.stat().st_mtime:.0f}")
    if not args.no_pre_backup and not args.dry_run:
        print(f"回滚前会先备份当前到 {dxf_path.stem}.bakN+1.dxf")
    print()

    result = restore(
        dxf_path, bak_path,
        backup_current_first=not args.no_pre_backup,
        dry_run=args.dry_run,
    )

    # 输出结构化结果（JSON 到 stdout，方便 LLM 解析）
    print("=== RESULT ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(_cli())
