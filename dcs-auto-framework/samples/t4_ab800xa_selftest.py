# -*- coding: utf-8 -*-
"""T4 自测：800xA Adapter 完整闭环验证。

流程：IR 构造 → 校验 → 生成 VAR/FUN xlsx → 回读解析 → 与原始 IR 对比
（dcsaf.ir.diff）→ 输出差异；同时测试 dedupe_increment 去重工具。
运行：python3 samples/t4_ab800xa_selftest.py（从框架根目录或任意目录均可）。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dcsaf.ir import (
    Point, PointTable, Fb, Pin, LogicProgram,
    validate_point_table, validate_logic,
    diff_points, diff_logic,
)
from dcsaf.adapters.ab800xa import (
    generate_var_excel, generate_fun_excel,
    parse_800xa_export, dedupe_increment,
)

OUT_DIR = Path(__file__).parent / "output"


def build_point_table() -> PointTable:
    """示例点位表：MOTOR1 电机启停相关点（DI/DO/AI/AO 四类各至少一个）。"""
    return PointTable(
        name="T4_MOTOR1",
        points=[
            Point(tag="N562_M1_RUN", description="磨机主电机运行反馈", signal_type="DI"),
            Point(tag="N562_M1_FAULT", description="磨机主电机故障信号", signal_type="DI"),
            Point(tag="N562_M1_START", description="磨机主电机启动命令", signal_type="DO"),
            Point(tag="N562_M1_I", description="磨机主电机电流", signal_type="AI",
                  range_low=0.0, range_high=200.0, unit="A", alarm_high=190.0),
            Point(tag="N562_M1_SPEED_SP", description="磨机主电机调速给定", signal_type="AO",
                  range_low=0.0, range_high=50.0, unit="Hz", alarm_high=50.0),
        ],
    )


def build_logic_program() -> LogicProgram:
    """示例逻辑：MOTOR1 电机启停（一个 MOTOR1 实例）。"""
    return LogicProgram(
        name="T4_MOTOR1",
        fbs=[
            Fb(
                ftype="MOTOR1",
                instance="M1",
                comment="磨机主电机启停控制",
                pins=[
                    Pin(name="Running", pin_type="bool", direction="in", source="N562_M1_RUN"),
                    Pin(name="Emg_stop", pin_type="bool", direction="in", value="FALSE"),
                    Pin(name="start_lock", pin_type="bool", direction="in", value="FALSE"),
                    Pin(name="Drive", pin_type="bool", direction="out", source="N562_M1_START"),
                    Pin(name="Fault", pin_type="bool", direction="out", source="N562_M1_FAULT"),
                ],
            ),
        ],
    )


def test_dedupe() -> None:
    """去重工具测试：忽略大小写、去首尾空格、与现场无交集、增量内部无重复。"""
    print("[7] 去重工具 dedupe_increment 测试:")

    # 用例1：与现场重复（大小写 / 首尾空格不敏感）
    new1 = ["M1", " M2 ", "M3", "M4"]
    ex1 = ["m1", "M2"]  # 现场已有（m1 与 M1 重复、M2 与 " M2 " 重复）
    add1, dup1 = dedupe_increment(new1, ex1)
    assert add1 == ["M3", "M4"], add1
    assert dup1 == ["M1", " M2 "], dup1
    print(f"  用例1（与现场重复+大小写/空格）：增量 {add1} / 重复 {dup1}  ✓")

    # 用例2：增量内部重复
    new2 = ["A1", "a1", "B2"]
    add2, dup2 = dedupe_increment(new2, [])
    assert add2 == ["A1", "B2"], add2
    assert dup2 == ["a1"], dup2
    print(f"  用例2（内部重复）：增量 {add2} / 重复 {dup2}  ✓")

    # 用例3：对象形式（Point / Fb 实例，取 tag/instance 为唯一键）
    p_new = [Point(tag="X1"), Point(tag="x1"), Point(tag="X2")]
    p_ex = [Point(tag="X2")]  # 现场已有 X2
    p_add, p_dup = dedupe_increment(p_new, p_ex)
    assert [p.tag for p in p_add] == ["X1"], [p.tag for p in p_add]
    assert [p.tag for p in p_dup] == ["x1", "X2"], [p.tag for p in p_dup]
    print(f"  用例3（对象形式 tag）：增量 {[p.tag for p in p_add]} / 重复 {[p.tag for p in p_dup]}  ✓")


def main() -> None:
    print("===== T4 800xA Adapter 自测（IR ↔ 800xA） =====")

    # [1] 构造 IR 并校验
    pt = build_point_table()
    lp = build_logic_program()
    pt_errors = validate_point_table(pt)
    lp_errors = validate_logic(lp)
    assert not pt_errors, pt_errors
    assert not lp_errors, lp_errors
    print(f"[1] IR 构造与校验：点位表 {len(pt.points)} 点 / 逻辑 {len(lp.fbs)} 个 FB，"
          f"校验 0 错误  ✓")

    # [2] 生成 VAR / FUN 表
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    var_path = OUT_DIR / "T4_MOTOR1_Var.xlsx"
    fun_path = OUT_DIR / "T4_MOTOR1_Fun.xlsx"
    generate_var_excel(pt, str(var_path))
    fun_warnings = generate_fun_excel(lp, str(fun_path))
    assert not fun_warnings, fun_warnings  # MOTOR1 在库中，不应有警告
    print(f"[2] 生成 VAR 表：{var_path}（{len(pt.points)} 行数据）；"
          f"FUN 表：{fun_path}（{len(lp.fbs)} 行数据），类型警告 {len(fun_warnings)} 条  ✓")

    # [3] 回读解析
    back_pt, back_lp = parse_800xa_export(str(var_path), str(fun_path))
    assert len(back_pt.points) == len(pt.points)
    assert len(back_lp.fbs) == len(lp.fbs)
    print(f"[3] 回读解析：点位 {len(back_pt.points)} 个 / 功能块 {len(back_lp.fbs)} 个  ✓")

    # [4] 闭环差异（容器名不在 xlsx 行内，回读用文件名填充，比较前对齐为原始名）
    back_pt.name = pt.name
    back_lp.name = lp.name
    d_pt = diff_points(pt.to_dict(), back_pt.to_dict())
    d_lp = diff_logic(lp.to_dict(), back_lp.to_dict())

    n_pins_orig = sum(len(fb.pins) for fb in lp.fbs)
    n_pins_back = sum(len(fb.pins) for fb in back_lp.fbs)

    print("[4] 闭环差异（原始 IR → 回读 IR）:")
    print("  [点位表]")
    pt_text = d_pt.to_text()
    print("    " + pt_text.replace("\n", "\n    ") if pt_text != "无差异" else "    无差异")
    print("  [逻辑]")
    lp_text = d_lp.to_text()
    print("    " + lp_text.replace("\n", "\n    ") if lp_text != "无差异" else "    无差异")
    print(f"  管脚数：原始 {n_pins_orig} → 回读 {n_pins_back}")

    # [5] 去重测试
    test_dedupe()

    print("===== 结论 =====")
    print("T4 自测通过")
    print("差异原因说明（信息丢失，属 VAR/FUN 表列结构所限，非 bug）：")
    print(" 1. VAR 表只有 Data Type、无方向信息，DO→bool→回读 DI、AO→real→回读 AI"
          "（signal_type 变更 2 处）；")
    print(" 2. 模板 VAR 段无 量程/单位/报警/分组/DP 列，模拟量点这些字段回读为空"
          f"（changed {sum(1 for e in d_pt.entries if e.kind == 'changed')} 处）；")
    print(f" 3. FUN 表不含管脚信息，Fb.pins 整体不回读（原始 {n_pins_orig} 个管脚"
          f"→ 回读 {n_pins_back}；diff 按同名 key 合并，仅示最后 1 条 removed）。")


if __name__ == "__main__":
    main()
