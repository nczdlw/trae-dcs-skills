# -*- coding: utf-8 -*-
"""T7 自测：调试快速响应工具（quick_response.py）完整闭环验证。

场景 A：点表变更检测与增量更新
  点表新增 1 个点（N562_M1_START）+ 修改 1 个模拟量量程（N562_M1_I 0~200 → 0~250）；
  逻辑中新增点被 MOTOR1_1（MOTOR1）的 Drive 管脚引用、修改点被 SI1（SignalInReal）
  的 In 管脚引用 → detect_change 应报出 MOTOR1_1 与 SI1 受影响。
场景 B：受影响组态快速重生成（regenerate_affected 输出重建说明）。
场景 C：DP 通讯字节序处理工具（low_high 与 none 各一个点）。
运行：python3 samples/t7_quick_response_selftest.py（从框架根目录或任意目录均可）。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dcsaf.ir import (
    Point, PointTable, DpInfo, Fb, Pin, LogicProgram,
)
from dcsaf.tools.quick_response import (
    detect_change, regenerate_affected, byte_order_fix,
    ChangeReport, RegenerateResult, ByteOrderReport,
)
from dcsaf.tools.quick_response import AB800XA_FB_LIBRARY_PATH


def build_old_points() -> PointTable:
    """旧点位表：运行反馈 DI + 电流 AI（量程 0~200A）。"""
    return PointTable(
        name="T7_OLD",
        points=[
            Point(tag="N562_M1_RUN", description="磨机主电机运行反馈", signal_type="DI"),
            Point(tag="N562_M1_I", description="磨机主电机电流", signal_type="AI",
                  range_low=0.0, range_high=200.0, unit="A"),
        ],
    )


def build_new_points() -> PointTable:
    """新点位表：新增启动命令 DO 点；电流量程改为 0~250A（修改）。"""
    return PointTable(
        name="T7_NEW",
        points=[
            Point(tag="N562_M1_RUN", description="磨机主电机运行反馈", signal_type="DI"),
            Point(tag="N562_M1_I", description="磨机主电机电流（量程调整）", signal_type="AI",
                  range_low=0.0, range_high=250.0, unit="A"),
            Point(tag="N562_M1_START", description="磨机主电机启动命令", signal_type="DO"),
        ],
    )


def build_logic_program() -> LogicProgram:
    """示例逻辑：MOTOR1 电机控制 + SignalInReal 电流监测。

    MOTOR1_1.Drive 输出连到新增点 N562_M1_START（引用变更点）；
    SI1.In 输入连到修改点 N562_M1_I（引用变更点）。
    """
    return LogicProgram(
        name="T7_LOGIC",
        fbs=[
            Fb(
                ftype="MOTOR1",
                instance="MOTOR1_1",
                comment="磨机主电机启停控制",
                pins=[
                    Pin(name="Running", pin_type="bool", direction="in", source="N562_M1_RUN"),
                    Pin(name="Emg_stop", pin_type="bool", direction="in", value="FALSE"),
                    Pin(name="start_lock", pin_type="bool", direction="in", value="FALSE"),
                    Pin(name="Drive", pin_type="bool", direction="out", source="N562_M1_START"),
                ],
            ),
            Fb(
                ftype="SignalInReal",
                instance="SI1",
                comment="磨机主电机电流监测",
                pins=[
                    Pin(name="In", pin_type="RealIO", direction="in_out", source="N562_M1_I"),
                    Pin(name="Name", pin_type="string", direction="in", value="M1_CURRENT"),
                ],
            ),
        ],
    )


def build_dp_points() -> PointTable:
    """DP 字节序场景点位表：low_high 与 none 各一个，外加一个非 DP 点。"""
    return PointTable(
        name="T7_DP",
        points=[
            Point(tag="N562_DP_A_FLOW", description="DP 皮带秤实际流量", signal_type="AI",
                  range_low=0.0, range_high=500.0,
                  dp=DpInfo(device="ITEC_BATCH", slot="IW.3", byte_order="low_high")),
            Point(tag="N562_DP_B_STATUS", description="DP 包装机状态字", signal_type="DI",
                  dp=DpInfo(device="HAVER", slot="IW.0", byte_order="none")),
            Point(tag="N562_M1_RUN", description="普通 DI 点（非 DP）", signal_type="DI"),
        ],
    )


def test_scene_a() -> ChangeReport:
    """场景 A：点表变更检测与增量更新。"""
    print("[1] 场景 A：点表变更检测与增量更新 detect_change")
    old_pt = build_old_points()
    new_pt = build_new_points()
    lp = build_logic_program()

    report = detect_change(old_pt, new_pt, lp)

    # 变更点位断言：新增 N562_M1_START、修改 N562_M1_I，未变的 N562_M1_RUN 不得出现
    assert "N562_M1_START" in report.changed_points, report.changed_points
    assert "N562_M1_I" in report.changed_points, report.changed_points
    assert "N562_M1_RUN" not in report.changed_points, report.changed_points
    assert len(report.changed_points) == 2, report.changed_points

    # 受影响 FB 断言：引用新增点的 MOTOR1_1 与引用修改点的 SI1 都须报出
    assert "MOTOR1_1" in report.affected_fbs, report.affected_fbs
    assert "SI1" in report.affected_fbs, report.affected_fbs
    assert len(report.affected_fbs) == 2, report.affected_fbs

    # 变更明细非空，且 path 形如 points/<tag>[/<field>]
    assert report.entries, "变更明细为空"
    assert any(e.path.startswith("points/") for e in report.entries)

    print("  变更点位：", "、".join(report.changed_points))
    print("  受影响功能块：", "、".join(report.affected_fbs))
    print("  变更明细：")
    for e in report.entries:
        print("    " + e.to_text())
    print("  ✓ 断言全部通过（新增/修改点均被定位，未变点不误报）")
    return report


def test_scene_b(lp: LogicProgram, affected_fbs: list) -> RegenerateResult:
    """场景 B：受影响组态快速重生成 regenerate_affected。"""
    print("[2] 场景 B：受影响组态快速重生成 regenerate_affected")
    result = regenerate_affected(str(AB800XA_FB_LIBRARY_PATH), lp, affected_fbs)

    assert result.affected_fbs == affected_fbs, result.affected_fbs
    assert len(result.notes) == len(affected_fbs), len(result.notes)
    # MOTOR1_1 来自库定义有管脚模板，应生成管脚连接与人工确认清单
    note_m1 = next(n for n in result.notes if n.instance == "MOTOR1_1")
    assert note_m1.ftype == "MOTOR1", note_m1.ftype
    assert note_m1.new_pin_connections, "MOTOR1_1 应生成新管脚连接"
    assert "Running" in " ".join(note_m1.new_pin_connections), note_m1.new_pin_connections
    assert note_m1.manual_confirm_lines, "MOTOR1_1 库模板存在逻辑未连接的管脚，应生成人工确认清单"
    assert "MOTOR1_1" in result.diff_text, result.diff_text

    print("  受影响功能块：", "、".join(result.affected_fbs))
    for n in result.notes:
        print(n.to_text())
    print("  变更差异说明：")
    print("   " + result.diff_text.replace("\n", "\n   "))
    print("  ✓ 断言全部通过（重建说明含新管脚连接、人工确认连线清单与差异文本）")
    return result


def test_scene_c() -> ByteOrderReport:
    """场景 C：DP 通讯字节序处理工具 byte_order_fix。"""
    print("[3] 场景 C：DP 通讯字节序处理工具 byte_order_fix")
    report = byte_order_fix(build_dp_points())

    # 处理清单：仅 low_high 点进入，附处理说明（含"推断"标注）
    assert len(report.items) == 1, report.items
    item = report.items[0]
    assert item.tag == "N562_DP_A_FLOW", item.tag
    assert item.device == "ITEC_BATCH", item.device
    assert item.byte_order == "low_high", item.byte_order
    assert "推断" in item.advice and "回读校验" in item.advice, item.advice
    assert "low_high" in item.advice or "低位在前" in item.advice, item.advice

    # 警告：DP 点但 byte_order=none 进入警告列表；非 DP 点两边都不出现
    assert len(report.warnings) == 1, report.warnings
    assert "N562_DP_B_STATUS" in report.warnings[0], report.warnings

    print("  字节序处理清单：")
    for i in report.items:
        print(i.to_text())
    print("  警告：")
    for w in report.warnings:
        print("  - " + w)
    print("  ✓ 断言全部通过（low_high 进处理清单含回读核对说明，none 进警告提示人工确认）")
    return report


def main() -> None:
    print("===== T7 调试快速响应工具 自测 =====")
    report_a = test_scene_a()
    test_scene_b(build_logic_program(), report_a.affected_fbs)
    test_scene_c()
    print("===== 结论 =====")
    print("T7 自测通过")


if __name__ == "__main__":
    main()
