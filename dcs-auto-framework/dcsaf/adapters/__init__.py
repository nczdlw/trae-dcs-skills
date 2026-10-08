# -*- coding: utf-8 -*-
"""DCS 平台适配器包。

对外导出各平台适配器类（接口形状统一，继承 DcsAdapter 抽象基类）：
- AB800xAAdapter：ABB 800xA（并行任务实现；若 ab800xa.py 尚不存在则为占位桩）
- PCS7Adapter：西门子 SIMATIC PCS7（桩，官方接口能力待核实）
- FreelanceAdapter：ABB Freelance（桩，官方接口能力待核实）

桩适配器调用其方法一律抛 DcsAdapterNotImplemented（提示含"待核实"），
绝不静默返回空数据或假装成功。
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base import DcsAdapter, DcsAdapterNotImplemented
from .freelance import FreelanceAdapter
from .pcs7 import PCS7Adapter

try:
    from .ab800xa import AB800xAAdapter  # 并行任务实现后自动引用
except ImportError:
    class AB800xAAdapter(DcsAdapter):
        """800xA 适配器占位桩（ab800xa.py 尚未实现）。"""

        platform = "ab800xa"

        @staticmethod
        def pending_items() -> List[Dict[str, str]]:
            return [
                {
                    "item": "800xA 适配器本体",
                    "status": "待核实",
                    "question": "dcsaf/adapters/ab800xa.py 尚未实现，接口由并行任务补充。",
                }
            ]

        def generate_point_table(self, ir: Any) -> Any:
            raise DcsAdapterNotImplemented(
                "AB800xA 适配器尚未实现，官方接口能力待核实"
                "（待核实项见 AB800xAAdapter.pending_items()）",
                pending_items=self.pending_items(),
            )

        def generate_logic(self, ir: Any) -> Any:
            raise DcsAdapterNotImplemented(
                "AB800xA 适配器尚未实现，官方接口能力待核实"
                "（待核实项见 AB800xAAdapter.pending_items()）",
                pending_items=self.pending_items(),
            )

        def parse_export(self, path: str) -> Any:
            raise DcsAdapterNotImplemented(
                "AB800xA 适配器尚未实现，官方接口能力待核实"
                "（待核实项见 AB800xAAdapter.pending_items()）",
                pending_items=self.pending_items(),
            )

        def dedupe(self, increment: Any, existing: Any) -> Any:
            raise DcsAdapterNotImplemented(
                "AB800xA 适配器尚未实现，官方接口能力待核实"
                "（待核实项见 AB800xAAdapter.pending_items()）",
                pending_items=self.pending_items(),
            )

__all__ = ["DcsAdapter", "DcsAdapterNotImplemented", "AB800xAAdapter", "PCS7Adapter", "FreelanceAdapter"]
