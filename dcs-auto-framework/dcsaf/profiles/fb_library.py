# -*- coding: utf-8 -*-
"""功能块库结构与校验器（T3 任务产物）。

功能块库数据文件位于 libs/*.yaml，本模块定义其结构与校验规则。
结构与数据文件一一对应：

- library   : 库名（如 "AB800xA" / "PCS7" / "Freelance"）
- platform  : 平台描述（可选）
- comment   : 库说明
- fbs       : 功能块字典 {ftype: FbDef}，ftype 为功能块类型名（如 MOTOR1）

FbDef 字段：
- comment    : 功能块说明（中文）
- source     : 来源引用，格式 "来源：<文件名>"；推断内容标注 "来源：<文件名> 推断"
- pins       : 管脚定义列表，每项为字典：
    - name        : 管脚名（800xA 管脚名大小写敏感，如 R1 / Reset / In / Clk）
    - pin_type    : 数据类型（bool / real / int / dint / string / time / word / dword /
                    DintIO / RealIO / DwordIO / 结构体类型名等）
    - direction   : 方向，仅允许 in / out / in_out
    - optional    : 是否可选（True/False，缺省 False）
    - description : 中文说明
- params      : 参数定义 {参数名: {type, default, description}}（如 SignalInReal 阈值等）
"""

from __future__ import annotations

from typing import Any, Dict, List

# 合法管脚方向
VALID_DIRECTIONS = ("in", "out", "in_out")


def validate_fb_library(fb_library: Any) -> List[str]:
    """校验功能块库，返回错误列表（空列表表示通过）。

    检查项：
    - 库名存在（library 字段非空）
    - fbs 为字典或列表，结构完整
    - ftype 唯一（忽略大小写、去首尾空格；800xA 类型名大小写敏感，但库内
      不应存在仅大小写不同的近似重复，如 TOf 与 TOF）
    - 管脚名唯一（同一功能块内不重名；管脚名大小写敏感，按精确名比较）
    - 管脚方向合法（in / out / in_out）

    入参支持两种形态：
    - 字典（yaml.safe_load 加载 libs/*.yaml 的结果）
    - 带 library / fbs 属性的对象
    """
    errors: List[str] = []

    if isinstance(fb_library, dict):
        lib_name = fb_library.get("library", "")
        fbs = fb_library.get("fbs", {})
    else:
        lib_name = getattr(fb_library, "library", "")
        fbs = getattr(fb_library, "fbs", {})

    if not lib_name:
        errors.append("库缺少 library（库名）字段")

    # fbs 支持字典 {ftype: 定义} 或列表 [定义]，统一转成列表项
    if isinstance(fbs, dict):
        items = list(fbs.items())
    elif isinstance(fbs, list):
        items = [(fb.get("ftype", "") if isinstance(fb, dict) else "", fb) for fb in fbs]
    else:
        errors.append("库缺少 fbs（功能块字典）字段")
        return errors

    # 检查 1：ftype 唯一（忽略大小写）
    seen_types: Dict[str, str] = {}
    for idx, (ftype, fb_def) in enumerate(items, start=1):
        ftype = (ftype or "").strip()
        if not ftype:
            errors.append(f"第{idx}个功能块：ftype 为空")
            continue
        key = ftype.lower()
        if key in seen_types:
            errors.append(
                f"功能块类型 '{ftype}' 与 '{seen_types[key]}' 重复（不唯一）"
            )
        else:
            seen_types[key] = ftype

        if not isinstance(fb_def, dict):
            errors.append(
                f"功能块 '{ftype}'：定义必须是字典（含 comment/source/pins/params）"
            )
            continue

        # 检查 2：管脚名唯一 + 检查 3：管脚方向合法
        pins = fb_def.get("pins") or []
        if not isinstance(pins, list):
            errors.append(f"功能块 '{ftype}'：pins 必须是列表")
            continue

        seen_pins: set = set()
        for pin in pins:
            if not isinstance(pin, dict) or not pin.get("name"):
                errors.append(f"功能块 '{ftype}'：存在缺少 name 的管脚")
                continue
            pname = str(pin["name"]).strip()
            if pname in seen_pins:
                errors.append(f"功能块 '{ftype}'：管脚 '{pname}' 重名（不唯一）")
            seen_pins.add(pname)

            direction = pin.get("direction", "")
            if direction not in VALID_DIRECTIONS:
                errors.append(
                    f"功能块 '{ftype}'：管脚 '{pname}' 方向 '{direction}' 非法"
                    f"（应为 {'/'.join(VALID_DIRECTIONS)}）"
                )

        # params 需为字典（参数定义）
        params = fb_def.get("params")
        if params is not None and not isinstance(params, dict):
            errors.append(f"功能块 '{ftype}'：params 必须是字典")

    return errors
