# -*- coding: utf-8 -*-
"""IR 读写（YAML/JSON）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union

import yaml

from .point_table import PointTable
from .logic_model import LogicProgram


def _dump(data: Any, fmt: str) -> str:
    if fmt == "yaml":
        return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
    return json.dumps(data, ensure_ascii=False, indent=2)


def _load(text: str, fmt: str) -> Any:
    if fmt == "yaml":
        return yaml.safe_load(text)
    return json.loads(text)


def save_ir(obj: Union[PointTable, LogicProgram], path: str, fmt: str = "yaml") -> None:
    """将 IR 对象保存为 YAML/JSON 文件。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_dump(obj.to_dict(), fmt), encoding="utf-8")


def load_ir(path: str, kind: str = "points", fmt: str = "") -> Union[PointTable, LogicProgram]:
    """从 YAML/JSON 文件加载 IR 对象。kind: 'points' 或 'logic'。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"IR 文件不存在: {path}")
    if not fmt:
        fmt = "yaml" if p.suffix.lower() in (".yaml", ".yml") else "json"
    data = _load(p.read_text(encoding="utf-8"), fmt)
    if kind == "points":
        return PointTable.from_dict(data)
    return LogicProgram.from_dict(data)
