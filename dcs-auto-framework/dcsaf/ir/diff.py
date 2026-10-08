# -*- coding: utf-8 -*-
"""IR diff：比较两份 IR 的差异，输出结构化差异清单。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class DiffEntry:
    """一条差异。"""
    kind: str = ""       # added / removed / changed
    path: str = ""       # 如 points/N562_HD1_T1_T_H/range_high
    old: Any = None
    new: Any = None

    def to_text(self) -> str:
        if self.kind == "added":
            return f"[新增] {self.path} = {self.new!r}"
        if self.kind == "removed":
            return f"[删除] {self.path} = {self.old!r}"
        return f"[变更] {self.path}: {self.old!r} -> {self.new!r}"


@dataclass
class DiffResult:
    """diff 结果。"""
    entries: List[DiffEntry] = field(default_factory=list)

    def to_text(self) -> str:
        if not self.entries:
            return "无差异"
        return "\n".join(e.to_text() for e in self.entries)


def _norm_key(k: Any) -> str:
    """列表元素的比较键：tag / instance / name（管脚）。"""
    if isinstance(k, dict):
        return str((k.get("tag") or k.get("instance") or k.get("name") or "").strip().lower())
    return str(k).strip().lower()


def diff_dicts(old: Dict[str, Any], new: Dict[str, Any], path: str = "", out: List[DiffEntry] | None = None) -> List[DiffEntry]:
    """递归比较两个字典。"""
    if out is None:
        out = []

    # 键集合（列表按关键字段归一化）
    for key in sorted(set(old) | set(new), key=str):
        cur = f"{path}/{key}" if path else key
        if key not in old:
            out.append(DiffEntry("added", cur, None, new[key]))
        elif key not in new:
            out.append(DiffEntry("removed", cur, old[key], None))
        else:
            ov, nv = old[key], new[key]
            if isinstance(ov, dict) and isinstance(nv, dict):
                diff_dicts(ov, nv, cur, out)
            elif isinstance(ov, list) and isinstance(nv, list):
                diff_lists(ov, nv, cur, out)
            elif ov != nv:
                out.append(DiffEntry("changed", cur, ov, nv))
    return out


def diff_lists(old: List[Any], new: List[Any], path: str, out: List[DiffEntry]) -> None:
    """比较两个列表：按归一化键做映射，逐项 diff。"""
    old_map = {_norm_key(k): (i, k) for i, k in enumerate(old) if isinstance(k, dict)}
    new_map = {_norm_key(k): (i, k) for i, k in enumerate(new) if isinstance(k, dict)}

    for key in sorted(set(old_map) | set(new_map), key=str):
        cur = f"{path}/{key}"
        if key not in old_map:
            out.append(DiffEntry("added", cur, None, new_map[key][1]))
        elif key not in new_map:
            out.append(DiffEntry("removed", cur, old_map[key][1], None))
        else:
            _, ov = old_map[key]
            _, nv = new_map[key]
            if isinstance(ov, dict) and isinstance(nv, dict):
                diff_dicts(ov, nv, cur, out)
            elif ov != nv:
                out.append(DiffEntry("changed", cur, ov, nv))


def diff_points(old: Dict[str, Any], new: Dict[str, Any]) -> DiffResult:
    """对比两份点位表 IR 字典。"""
    return DiffResult(diff_dicts(old, new))


def diff_logic(old: Dict[str, Any], new: Dict[str, Any]) -> DiffResult:
    """对比两份逻辑 IR 字典。"""
    return DiffResult(diff_dicts(old, new))
