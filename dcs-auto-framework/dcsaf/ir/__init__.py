# -*- coding: utf-8 -*-
"""统一中间表示（IR）模块。"""
from .point_table import Point, PointTable, DpInfo, validate_point_table, PointTableError
from .logic_model import Fb, Pin, LogicProgram, validate_logic, LogicError
from .io import save_ir, load_ir
from .diff import diff_points, diff_logic, DiffResult, DiffEntry
from .version import VersionManager

__all__ = [
    "Point", "PointTable", "DpInfo", "validate_point_table", "PointTableError",
    "Fb", "Pin", "LogicProgram", "validate_logic", "LogicError",
    "save_ir", "load_ir",
    "diff_points", "diff_logic", "DiffResult", "DiffEntry",
    "VersionManager",
]
