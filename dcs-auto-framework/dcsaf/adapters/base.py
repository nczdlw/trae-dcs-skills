# -*- coding: utf-8 -*-
"""DCS 平台适配器统一抽象基类。

框架各平台适配器（AB800xA / PCS7 / Freelance）统一继承本基类，
保证对外接口形状一致。四个核心接口对应框架的四大能力：
- generate_point_table(ir)：由 IR 点位表生成目标平台 IO 表（导出方向）
- generate_logic(ir)：由 IR 逻辑模型生成目标平台功能块组态（导出方向）
- parse_export(path)：解析目标平台官方导出文件为 IR（导入方向）
- dedupe(increment, existing)：增量去重合并（增量更新场景）

桩子类（官方接口能力未核实的平台）对未实现方法抛 DcsAdapterNotImplemented
异常，提示信息必须包含"待核实"字样，禁止静默返回空数据或假装成功。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class DcsAdapterNotImplemented(NotImplementedError):
    """适配器接口未实现异常（官方接口能力待核实）。

    继承 NotImplementedError，桩子类抛出此异常表明：
    - 该平台官方接口能力尚未核实，暂不支持自动生成/解析；
    - 不允许静默返回空数据或假装成功。
    异常对象携带结构化待核实项清单（pending_items），供调研登记使用。
    """

    def __init__(self, message: str, pending_items: List[Dict[str, str]] = None) -> None:
        super().__init__(message)
        self.pending_items: List[Dict[str, str]] = pending_items or []


class DcsAdapter(ABC):
    """DCS 平台适配器抽象基类。

    子类必须实现全部四个接口方法；未实现时由抽象基类机制在实例化时
    直接报错（TypeError），保证任何"未实现"都不被静默吞掉。
    """

    #: 平台名（子类覆盖，如 ab800xa / pcs7 / freelance）
    platform: str = "unknown"

    @abstractmethod
    def generate_point_table(self, ir) -> Any:
        """由 IR 点位表生成目标平台 IO 表。

        参数 ir：IR 点位表（dcsaf/ir/point_table.py 的 PointTable）。
        返回：目标平台 IO 表（xlsx/CSV 文件路径或结构化数据，平台自定）。
        """

    @abstractmethod
    def generate_logic(self, ir) -> Any:
        """由 IR 逻辑模型生成目标平台功能块组态。

        参数 ir：IR 逻辑模型（dcsaf/ir/logic_model.py 的 LogicProgram）。
        返回：目标平台功能块组态文件或结构化数据。
        """

    @abstractmethod
    def parse_export(self, path: str) -> Any:
        """解析目标平台官方导出文件为 IR。

        参数 path：官方导出文件路径。
        返回：IR 模型（PointTable / LogicProgram 或组合结构）。
        """

    @abstractmethod
    def dedupe(self, increment: Any, existing: Any) -> Any:
        """增量去重合并。

        参数 increment：增量数据；existing：既有数据。
        返回：合并去重后的结果。
        """
