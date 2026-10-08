# -*- coding: utf-8 -*-
"""功能块逻辑模型与校验器。

字段定义（对应 spec 的"统一中间表示（IR）"）：
- 功能块类型 ftype（如 MOTOR1 / SMOTOR_PROV / SignalInReal / GROUP1 / VALVE1 / TOf）
- 实例名 instance（唯一键）
- 输入/输出管脚连接（引用其他实例名或点位）
- 参数、注释
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# 常用功能块类型（800xA 基线，见 knowledge；PCS7/Freelance 后续扩展）
KNOWN_FB_TYPES = {
    "MOTOR1", "SMOTOR_PROV", "SMOTORD_PROV", "SignalInReal", "SignalInBool",
    "GROUP1", "VALVE1", "PVALVE", "ABBLVVVF", "ABBMVVVF", "TOf", "R_Trig",
    "RS", "SR", "AlarmCond", "SimpleEventDetector", "Group", "P98", "P101",
}

# 简单管脚数据类型
PIN_TYPES = {"bool", "int", "real", "dint", "string", "word", "dword"}


class LogicError(Exception):
    """逻辑模型校验错误。"""


@dataclass
class Pin:
    """管脚。"""
    name: str = ""          # 管脚名（大小写敏感，如 R1 / Reset / In / Clk）
    pin_type: str = ""      # 数据类型
    direction: str = "in"   # in / out / in_out
    value: Optional[str] = None   # 直接值（常量/变量名）
    source: Optional[str] = None  # 来源（"实例名.管脚" 或 点位号）


@dataclass
class Fb:
    """功能块实例。"""
    ftype: str = ""                 # 功能块类型
    instance: str = ""              # 实例名（唯一键）
    pins: List[Pin] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)  # 参数（阈值等）
    comment: str = ""               # 注释

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ftype": self.ftype,
            "instance": self.instance,
            "pins": [
                {
                    "name": p.name,
                    "pin_type": p.pin_type,
                    "direction": p.direction,
                    "value": p.value,
                    "source": p.source,
                }
                for p in self.pins
            ],
            "params": self.params,
            "comment": self.comment,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Fb":
        return cls(
            ftype=d.get("ftype", ""),
            instance=d.get("instance", ""),
            pins=[Pin(**p) for p in d.get("pins", [])],
            params=d.get("params", {}),
            comment=d.get("comment", ""),
        )


@dataclass
class LogicProgram:
    """一组功能块逻辑（对应一个 Group/Program）。"""
    name: str = ""
    fbs: List[Fb] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "fbs": [fb.to_dict() for fb in self.fbs],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LogicProgram":
        return cls(
            name=d.get("name", ""),
            fbs=[Fb.from_dict(fb) for fb in d.get("fbs", [])],
        )


def validate_logic(program: LogicProgram) -> List[str]:
    """校验逻辑模型，返回错误列表（空列表表示通过）。

    检查项：
    - 实例名唯一（忽略大小写、去首尾空格）
    - 功能块类型已知
    - 管脚方向合法
    - 输入管脚必须连（有 value 或 source），不允许悬空输入
    - source 引用的实例必须存在
    """
    errors: List[str] = []
    seen: Dict[str, int] = {}

    for idx, fb in enumerate(program.fbs, start=1):
        key = (fb.instance or "").strip().lower()
        if not key:
            errors.append(f"第{idx}个 FB：实例名为空")
            continue
        if key in seen:
            errors.append(f"第{idx}个 FB：实例名 '{fb.instance}' 与第{seen[key]}个重复")
        else:
            seen[key] = idx

        if fb.ftype and fb.ftype not in KNOWN_FB_TYPES:
            errors.append(f"第{idx}个 FB：实例 '{fb.instance}' 类型 '{fb.ftype}' 不在已知库中")

        for pin in fb.pins:
            if pin.direction not in ("in", "out", "in_out"):
                errors.append(
                    f"第{idx}个 FB：实例 '{fb.instance}' 管脚 '{pin.name}' 方向 '{pin.direction}' 非法"
                )
            # 输入管脚不允许悬空
            if pin.direction == "in" and not pin.value and not pin.source:
                errors.append(
                    f"第{idx}个 FB：实例 '{fb.instance}' 输入管脚 '{pin.name}' 悬空"
                )
            # source 引用检查：格式 "实例名.管脚" 时实例必须存在
            if pin.source and "." in pin.source:
                src_inst = pin.source.split(".")[0].strip().lower()
                if src_inst not in seen:
                    errors.append(
                        f"第{idx}个 FB：实例 '{fb.instance}' 管脚 '{pin.name}' 引用不存在的实例 '{src_inst}'"
                    )

    return errors
