# -*- coding: utf-8 -*-
"""ABB Freelance 适配器（桩实现）。

当前为 T5 任务接口桩：Freelance 官方接口能力（Control Builder 工程格式、
DigiVis 变量表、OPC UA 支持等）尚未核实，桩方法一律抛"待核实"异常，
绝不静默成功。待核实项结构化清单见 FreelanceAdapter.pending_items()。

接口形状参考 800xA 适配器（dcsaf/adapters/ab800xa.py）：
generate_point_table / generate_logic / parse_export / dedupe。
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base import DcsAdapter, DcsAdapterNotImplemented


class FreelanceAdapter(DcsAdapter):
    """Freelance 适配器（桩）。

    平台：ABB Freelance（Control Builder F 组态 + DigiVis 操作员站）。
    官方接口能力待核实，所有桩方法抛"待核实"异常。
    """

    platform = "freelance"

    @staticmethod
    def pending_items() -> List[Dict[str, str]]:
        """返回本平台官方接口能力的待核实项登记（只登记问题，不写答案）。"""
        return [
            {
                "item": "Control Builder 工程格式",
                "status": "待核实",
                "question": "Control Builder F（AC 900F 组态）工程文件的官方格式/扩展名/批量导入导出方式是什么？",
            },
            {
                "item": "DigiVis 变量表",
                "status": "待核实",
                "question": "DigiVis 操作员站画面/归档变量表的官方批量导入导出格式是什么？",
            },
            {
                "item": "OPC UA 支持",
                "status": "待核实",
                "question": "Freelance 是否支持 OPC UA 服务器接口，能否用于自动化读写组态数据？",
            },
            {
                "item": "功能块类型映射",
                "status": "待核实",
                "question": "IR 功能块类型与 Freelance 功能块库（见 libs/freelance_fb_library.yaml）的映射规则是什么？",
            },
            {
                "item": "IO 导入列格式",
                "status": "待核实",
                "question": "profiles/io_templates/freelance_io_template.yaml 导入侧草案列是否与官方格式一致？",
            },
        ]

    def generate_point_table(self, ir: Any) -> Any:
        """由 IR 点位表生成 Freelance IO 表（桩，未实现）。"""
        raise DcsAdapterNotImplemented(
            "Freelance 官方接口能力待核实，暂不支持自动生成点位表"
            "（待核实项见 FreelanceAdapter.pending_items()）",
            pending_items=self.pending_items(),
        )

    def generate_logic(self, ir: Any) -> Any:
        """由 IR 逻辑模型生成 Freelance 功能块组态（桩，未实现）。"""
        raise DcsAdapterNotImplemented(
            "Freelance 官方接口能力待核实，暂不支持自动生成逻辑组态"
            "（待核实项见 FreelanceAdapter.pending_items()）",
            pending_items=self.pending_items(),
        )

    def parse_export(self, path: str) -> Any:
        """解析 Freelance 官方导出文件为 IR（桩，未实现）。"""
        raise DcsAdapterNotImplemented(
            "Freelance 官方接口能力待核实，暂不支持解析官方导出文件"
            "（待核实项见 FreelanceAdapter.pending_items()）",
            pending_items=self.pending_items(),
        )

    def dedupe(self, increment: Any, existing: Any) -> Any:
        """Freelance 增量去重合并（桩，未实现）。"""
        raise DcsAdapterNotImplemented(
            "Freelance 官方接口能力待核实，暂不支持增量去重合并"
            "（待核实项见 FreelanceAdapter.pending_items()）",
            pending_items=self.pending_items(),
        )
