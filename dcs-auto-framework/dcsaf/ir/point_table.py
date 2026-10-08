# -*- coding: utf-8 -*-
"""点位表模型与校验器。

字段定义（对应 spec 的"统一中间表示（IR）"）：
- 位号 tag、描述 description、信号类型 signal_type（DI/DO/AI/AO）
- 量程 range_low/range_high、单位 unit、报警上下限 alarm_low/alarm_high
- 系统分组 system_group、连锁关联 interlock_ref、DP 通讯标记 dp（含字节序 byte_order）
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# 信号类型与合法取值范围
SIGNAL_TYPES = {"DI", "DO", "AI", "AO"}
# 字节序取值
BYTE_ORDERS = {"low_high", "high_low", "none"}


class PointTableError(Exception):
    """点位表校验错误。"""


@dataclass
class DpInfo:
    """DP 通讯标记。"""
    device: str = ""          # DP 设备名
    slot: str = ""            # 站内槽位
    byte_order: str = "none"  # 字节序：low_high / high_low / none


@dataclass
class Point:
    """单点定义。"""
    tag: str = ""                      # 位号（唯一键）
    description: str = ""              # 描述
    signal_type: str = ""              # DI/DO/AI/AO
    range_low: Optional[float] = None
    range_high: Optional[float] = None
    unit: str = ""
    alarm_low: Optional[float] = None
    alarm_high: Optional[float] = None
    system_group: str = ""             # 系统分组
    interlock_ref: List[str] = field(default_factory=list)  # 关联连锁
    dp: Optional[DpInfo] = None        # DP 通讯标记

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "tag": self.tag,
            "description": self.description,
            "signal_type": self.signal_type,
            "range_low": self.range_low,
            "range_high": self.range_high,
            "unit": self.unit,
            "alarm_low": self.alarm_low,
            "alarm_high": self.alarm_high,
            "system_group": self.system_group,
            "interlock_ref": self.interlock_ref,
        }
        if self.dp is not None:
            d["dp"] = {
                "device": self.dp.device,
                "slot": self.dp.slot,
                "byte_order": self.dp.byte_order,
            }
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Point":
        dp = None
        if d.get("dp"):
            dp = DpInfo(**d["dp"])
        return cls(
            tag=d.get("tag", ""),
            description=d.get("description", ""),
            signal_type=d.get("signal_type", ""),
            range_low=d.get("range_low"),
            range_high=d.get("range_high"),
            unit=d.get("unit", ""),
            alarm_low=d.get("alarm_low"),
            alarm_high=d.get("alarm_high"),
            system_group=d.get("system_group", ""),
            interlock_ref=list(d.get("interlock_ref", [])),
            dp=dp,
        )


@dataclass
class PointTable:
    """点位表：一组 Point。"""
    name: str = ""
    points: List[Point] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "points": [p.to_dict() for p in self.points],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PointTable":
        return cls(
            name=d.get("name", ""),
            points=[Point.from_dict(p) for p in d.get("points", [])],
        )


def _norm(s: Optional[str]) -> str:
    """比较用规范化：去首尾空格、忽略大小写。"""
    return (s or "").strip().lower()


def validate_point_table(table: PointTable) -> List[str]:
    """校验点位表，返回错误列表（空列表表示通过）。

    检查项：
    - 重复位号（忽略大小写、去首尾空格）
    - 信号类型非法
    - 量程缺失/量程上下限非法
    - 报警限超出量程
    - DP 字节序非法
    """
    errors: List[str] = []
    seen: Dict[str, int] = {}

    for idx, p in enumerate(table.points, start=1):
        key = _norm(p.tag)
        if not key:
            errors.append(f"第{idx}行：位号为空")
            continue
        if key in seen:
            errors.append(
                f"第{idx}行：位号 '{p.tag}' 与第{seen[key]}行重复"
            )
        else:
            seen[key] = idx

        if p.signal_type not in SIGNAL_TYPES:
            errors.append(f"第{idx}行：位号 '{p.tag}' 信号类型 '{p.signal_type}' 非法（应为 {sorted(SIGNAL_TYPES)}）")

        if p.signal_type in ("AI", "AO"):
            if p.range_low is None or p.range_high is None:
                errors.append(f"第{idx}行：位号 '{p.tag}' 模拟量缺少量程")
            elif p.range_low >= p.range_high:
                errors.append(f"第{idx}行：位号 '{p.tag}' 量程上下限非法（low>=high）")

        # 报警限检查（仅模拟量）
        if p.signal_type in ("AI", "AO"):
            for name, val in (("alarm_low", p.alarm_low), ("alarm_high", p.alarm_high)):
                if val is not None and p.range_low is not None and p.range_high is not None:
                    if not (p.range_low <= val <= p.range_high):
                        errors.append(
                            f"第{idx}行：位号 '{p.tag}' {name}={val} 超出量程 [{p.range_low},{p.range_high}]"
                        )

        if p.dp is not None and p.dp.byte_order not in BYTE_ORDERS:
            errors.append(
                f"第{idx}行：位号 '{p.tag}' DP 字节序 '{p.dp.byte_order}' 非法（应为 {sorted(BYTE_ORDERS)}）"
            )

    return errors
