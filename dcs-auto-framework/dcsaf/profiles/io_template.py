# -*- coding: utf-8 -*-
"""IO 表格模板结构定义与校验器。

三平台（ABB 800xA / 西门子 PCS7 / ABB Freelance）IO 表格模板的结构定义。
模板数据文件存放在 /workspace/dcs-auto-framework/profiles/io_templates/*.yaml。

模板结构（dict，对应 YAML 顶层）：
- template_name: 模板名（唯一标识）
- platform:      平台标识（ab800xa / pcs7 / freelance）
- description:   模板用途说明
- columns:       列定义列表，每项 dict：
    - name:        列名（表头文字，在同一模板内唯一）
    - group:       列组（io=IR 输入侧 / import=平台导入侧）
    - required:    是否必填（bool）
    - ir_field:    映射到的 IR 点位表字段（point_table.py 的字段名），
                   平台专有列填 null；DP 子字段用 "dp.device"/"dp.slot"/"dp.byte_order"
    - source:      数据来源标注（"来源: <文件名>" / "来源: <文件名>推断" / "待核实"）
    - description: 列说明（取值规则、映射关系、注意事项）
- export_format: 导出格式说明（dict，文件头/命名/导入顺序等）
"""

from __future__ import annotations

from typing import Any, Dict, List

# IR 点位表合法字段（与 dcsaf/ir/point_table.py 的 Point 字段一致）
VALID_IR_FIELDS = {
    "tag", "description", "signal_type", "range_low", "range_high",
    "unit", "alarm_low", "alarm_high", "system_group", "interlock_ref", "dp",
}
# IR 合法 DP 子字段（DP 通讯标记 dp 的三个成员）
VALID_DP_SUBFIELDS = {"dp.device", "dp.slot", "dp.byte_order"}
# 模板中必须存在映射列的 IR 必填字段（位号是 IR 唯一键）
REQUIRED_IR_FIELDS = {"tag"}
# 合法列组
VALID_GROUPS = {"io", "import"}
# 合法平台标识
VALID_PLATFORMS = {"ab800xa", "pcs7", "freelance"}


class IoTemplateError(Exception):
    """IO 模板校验错误。"""


def _norm(name: Any) -> str:
    """规范化列名用于唯一性比较：去首尾空格、忽略大小写。"""
    return str(name or "").strip().lower()


def validate_template(io_template: Dict[str, Any]) -> List[str]:
    """校验 IO 模板，返回错误列表（空列表表示通过）。

    检查项：
    1. 模板名非空、平台标识合法
    2. columns 为非空列表
    3. 必填列存在：每个列定义含 name/required/ir_field/source/description 必要键；
       IR 必填字段（位号 tag）至少有一个映射列
    4. 列名唯一（忽略大小写、去首尾空格）
    5. 类型映射合法：ir_field 为 null（平台专有列），或属于 IR 合法字段 / DP 子字段
    """
    errors: List[str] = []

    if not io_template.get("template_name"):
        errors.append("模板名 template_name 为空")
    if io_template.get("platform") not in VALID_PLATFORMS:
        errors.append(
            f"平台 platform='{io_template.get('platform')}' 非法（应为 {sorted(VALID_PLATFORMS)}）"
        )

    columns = io_template.get("columns")
    if not isinstance(columns, list) or not columns:
        errors.append("columns 必须为非空列表")
        return errors

    seen: Dict[str, int] = {}
    # IR 必填字段覆盖记录：只有出现 required 的映射列才计为覆盖
    ir_covered: Dict[str, bool] = {f: False for f in REQUIRED_IR_FIELDS}

    for idx, col in enumerate(columns, start=1):
        if not isinstance(col, dict):
            errors.append(f"第{idx}列：列定义必须是 dict")
            continue

        name = col.get("name")
        if not name or not str(name).strip():
            errors.append(f"第{idx}列：列名为空")
            continue

        # 列名唯一性（忽略大小写、去首尾空格）
        key = _norm(name)
        if key in seen:
            errors.append(f"第{idx}列：列名 '{name}' 与第{seen[key]}列重复（忽略大小写）")
        else:
            seen[key] = idx

        # 必填键存在性
        if "required" not in col or not isinstance(col.get("required"), bool):
            errors.append(f"第{idx}列 '{name}'：required 缺失或非布尔")
        if "ir_field" not in col:
            errors.append(f"第{idx}列 '{name}'：ir_field 缺失（平台专有列应填 null）")
        if not col.get("source"):
            errors.append(f"第{idx}列 '{name}'：source（数据来源标注）缺失")
        if not col.get("description"):
            errors.append(f"第{idx}列 '{name}'：description（列说明）缺失")

        # 类型映射合法性：null 或 IR 合法字段 / DP 子字段
        ir_field = col.get("ir_field")
        if ir_field is not None:
            if ir_field in VALID_IR_FIELDS:
                ir_covered[ir_field] = True
            elif ir_field in VALID_DP_SUBFIELDS:
                pass
            else:
                errors.append(
                    f"第{idx}列 '{name}'：ir_field '{ir_field}' 非法"
                    f"（应为 null 或 {sorted(VALID_IR_FIELDS)} 或 {sorted(VALID_DP_SUBFIELDS)}）"
                )

        # 列组合法性
        group = col.get("group")
        if group is not None and group not in VALID_GROUPS:
            errors.append(
                f"第{idx}列 '{name}'：group '{group}' 非法（应为 {sorted(VALID_GROUPS)}）"
            )

    # 必填 IR 字段覆盖检查：位号列必须存在
    for f in REQUIRED_IR_FIELDS:
        if not ir_covered[f]:
            errors.append(f"IR 必填字段 '{f}'（位号）在模板中没有映射列")

    return errors
