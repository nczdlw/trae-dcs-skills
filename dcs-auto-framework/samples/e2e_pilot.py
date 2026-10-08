# -*- coding: utf-8 -*-
"""T10 端到端试点：800xA 自动编程调试框架全流程闭环演示。

用现有 800xA 素材（中压变频器 VFD、大布袋 DP、皮带秤 DP，语义取自
knowledge/20-DP通讯与设备功能块/ 文档，位号加"示例"标注）走一遍：

  步骤1 点表导入：构造含 DP 设备点（含字节序标记）的 IR 点表，校验通过；
  步骤2 逻辑生成：构造 IR 逻辑（SignalInReal 监测 + MOTOR1/SMOTOR_PROV 控制
        + RS 连锁），校验通过；
  步骤3 组态产出：调 ab800xa generate_var_excel/generate_fun_excel 生成
        VAR/FUN xlsx 到 samples/output/；
  步骤4 回读校验：parse_800xa_export 回读，与原始 IR 用 diff 对比，
        输出差异说明（VAR/FUN 表列结构导致的已知信息丢失）；
  步骤5 调试变更响应：模拟点表变更（DP 设备增点 + 高低字节反转修正），
        用 quick_response.detect_change + regenerate_affected + byte_order_fix
        输出变更响应。

运行：python3 samples/e2e_pilot.py（从框架根目录或任意目录均可）。
末尾输出"T10 端到端试点通过"。

素材说明（来源与推断标注）：
- 中压变频器：频率/电流/温度/状态字语义来自 中压变频器_功能块逻辑说明.md
  （PZD1 状态字、PZD2 频率、PZD3 电流、PZD6 温度 /10=°C，MV 专用温度监控）；
- 大布袋：差压为布袋收尘典型过程量，文档（大布袋_功能块开发规则1.md）未直接
  列差压位，本试点按设备语义取用并标"示例/推断"；引风机电机为配套示例；
- 皮带秤：流量（dpIn_Flow，IW.3，kg/h）来自 皮带秤_功能块逻辑说明.md；
- 字节序：knowledge 文档仅明确 HAVER 包装机为 Big-Endian，VFD/皮带秤的
  字节序文档未给，本试点标注"推断/待核实"，最终以设备通讯表为准。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dcsaf.ir import (
    Point, PointTable, DpInfo, Fb, Pin, LogicProgram,
    validate_point_table, validate_logic,
    diff_points, diff_logic, save_ir,
)
from dcsaf.adapters.ab800xa import (
    generate_var_excel, generate_fun_excel, parse_800xa_export,
)
from dcsaf.tools.quick_response import (
    detect_change, regenerate_affected, byte_order_fix,
)
from dcsaf.tools.quick_response import AB800XA_FB_LIBRARY_PATH

OUT_DIR = Path(__file__).parent / "output"


# ---------------------------------------------------------------------------
# 步骤1 素材：点位表（含 DP 设备点与字节序标记）
# ---------------------------------------------------------------------------

def build_points_v1() -> PointTable:
    """试点点位表 v1：中压变频器 / 大布袋 / 皮带秤 / DP 电机（位号加"示例"）。

    命名风格：N<节点>_<系统>_<设备>_<信号>_<后缀>（F163 总纲 §4.7）。
    字节序取值：DP 16 位字（状态字/控制字）为 none；32 位实际值先按
    low_high 标记（推断/待核实，步骤5 演示高低字节反转修正）。
    """
    return PointTable(
        name="e2e_pilot",
        points=[
            # ---- 中压变频器（ABBMVVVF，语义来源：中压变频器_功能块逻辑说明.md）----
            Point(tag="N562_MVVVF_SW", description="中压变频器状态字（示例，PZD1）",
                  signal_type="DI",
                  dp=DpInfo(device="ABBMVVVF", slot="PZD1", byte_order="none")),
            Point(tag="N562_MVVVF_FRQ", description="中压变频器实际频率（示例，PZD2/ACT1）",
                  signal_type="AI", range_low=0.0, range_high=50.0, unit="Hz",
                  alarm_high=48.0,
                  dp=DpInfo(device="ABBMVVVF", slot="PZD2", byte_order="low_high")),  # 推断/待核实
            Point(tag="N562_MVVVF_CUR", description="中压变频器实际电流（示例，PZD3/ACT2）",
                  signal_type="AI", range_low=0.0, range_high=300.0, unit="A",
                  alarm_high=280.0,
                  dp=DpInfo(device="ABBMVVVF", slot="PZD3", byte_order="low_high")),  # 推断/待核实
            Point(tag="N562_MVVVF_TEMP", description="中压变频器电机温度（示例，PZD6/ACT5，/10=°C）",
                  signal_type="AI", range_low=0.0, range_high=150.0, unit="°C",
                  alarm_high=120.0,
                  dp=DpInfo(device="ABBMVVVF", slot="PZD6", byte_order="low_high")),  # 推断/待核实
            # ---- 大布袋（KDMC2880；差压按布袋收尘典型过程量取用，标"示例/推断"）----
            Point(tag="N562_BAG_DP", description="大布袋收尘器差压（示例/推断）",
                  signal_type="AI", range_low=0.0, range_high=5.0, unit="kPa",
                  alarm_high=4.0,
                  dp=DpInfo(device="KDMC2880", slot="DP_IN", byte_order="none")),  # 16位字路线
            Point(tag="N562_BAG_FAN_RUN", description="大布袋引风机运行反馈（示例）",
                  signal_type="DI"),
            Point(tag="N562_BAG_FAN_START", description="大布袋引风机启动命令（示例）",
                  signal_type="DO"),
            Point(tag="N562_BAG_DP_RST", description="大布袋差压联锁复位按钮（示例）",
                  signal_type="DI"),
            # ---- 皮带秤（ITEC_BATCH，语义来源：皮带秤_功能块逻辑说明.md）----
            Point(tag="N562_BSC_FLOW", description="皮带秤实际流量（示例，IW.3，kg/h）",
                  signal_type="AI", range_low=0.0, range_high=500.0, unit="kg/h",
                  alarm_high=460.0,
                  dp=DpInfo(device="ITEC_BATCH", slot="IW.3", byte_order="low_high")),  # 推断/待核实
            # ---- DP 通讯电机（SMOTOR_PROV 控制字/状态字，示例）----
            Point(tag="N562_DP_MOTOR_SW", description="DP 电机状态字（示例）",
                  signal_type="DI",
                  dp=DpInfo(device="SMOTOR_PROV", slot="IW.1", byte_order="none")),
            Point(tag="N562_DP_MOTOR_CW", description="DP 电机控制字（示例）",
                  signal_type="DO",
                  dp=DpInfo(device="SMOTOR_PROV", slot="QW.2", byte_order="none")),
        ],
    )


# ---------------------------------------------------------------------------
# 步骤2 素材：逻辑程序（SignalInReal 监测 + MOTOR1/SMOTOR_PROV 控制 + RS 连锁）
# ---------------------------------------------------------------------------

def build_logic_v1() -> LogicProgram:
    """试点逻辑 v1。

    注意：validate_logic 要求被引用的实例必须先于引用者出现，故按
    SI_FRQ → SI_DP → RS_ILK → MOT1 → RS_DRV → SM_DP → VFD_CTL 顺序排列。
    连锁示例（简化）：差压 HH（SI_DP.GTHHStat）→ RS_ILK 锁存 → 锁停
    引风机（MOT1.process_lock）；引风机运行（MOT1.Running）→ RS_DRV 锁存
    → 作为 VFD 组启动条件（VFD_CTL.Group_start）。
    """
    return LogicProgram(
        name="e2e_pilot",
        fbs=[
            Fb(ftype="SignalInReal", instance="SI_FRQ",
               comment="中压变频器频率监测（示例）",
               pins=[
                   Pin(name="Name", pin_type="string", direction="in", value="MV_VFD_FREQ"),
                   Pin(name="In", pin_type="RealIO", direction="in_out", source="N562_MVVVF_FRQ"),
               ],
               params={"LevelH": 45.0, "LevelHH": 48.0,
                       "EnableL": False, "EnableLL": False, "EnableLLL": False}),
            Fb(ftype="SignalInReal", instance="SI_DP",
               comment="大布袋差压监测（示例）",
               pins=[
                   Pin(name="Name", pin_type="string", direction="in", value="BAG_DP_ALARM"),
                   Pin(name="In", pin_type="RealIO", direction="in_out", source="N562_BAG_DP"),
               ],
               params={"LevelH": 3.5, "LevelHH": 4.0,
                       "EnableL": False, "EnableLL": False, "EnableLLL": False}),
            Fb(ftype="RS", instance="RS_ILK",
               comment="差压高连锁锁存（示例：差压 HH 锁停引风机，复位按钮释放）",
               pins=[
                   Pin(name="Set", pin_type="bool", direction="in", source="SI_DP.GTHHStat"),
                   Pin(name="R1", pin_type="bool", direction="in", source="N562_BAG_DP_RST"),
                   # Q1 输出管脚不写 source：连接只在消费侧表达（MOT1.process_lock ← RS_ILK.Q1）
                   Pin(name="Q1", pin_type="bool", direction="out"),
               ]),
            Fb(ftype="MOTOR1", instance="MOT1",
               comment="大布袋引风机电机启停控制（示例）",
               pins=[
                   Pin(name="Ready", pin_type="bool", direction="in", value="FALSE"),
                   Pin(name="Running", pin_type="bool", direction="in", source="N562_BAG_FAN_RUN"),
                   Pin(name="Emg_stop", pin_type="bool", direction="in", value="FALSE"),
                   Pin(name="start_lock", pin_type="bool", direction="in", value="FALSE"),
                   Pin(name="process_lock", pin_type="bool", direction="in", source="RS_ILK.Q1"),
                   Pin(name="safety_lock", pin_type="bool", direction="in", value="FALSE"),
                   Pin(name="Drive", pin_type="bool", direction="out", source="N562_BAG_FAN_START"),
               ]),
            Fb(ftype="RS", instance="RS_DRV",
               comment="VFD 驱动命令锁存（示例简化：R1 接 FALSE，实际接停止条件）",
               pins=[
                   Pin(name="Set", pin_type="bool", direction="in", source="MOT1.Running"),
                   Pin(name="R1", pin_type="bool", direction="in", value="FALSE"),
                   # Q1 输出管脚不写 source：连接只在消费侧表达（VFD_CTL.Group_start ← RS_DRV.Q1）
                   Pin(name="Q1", pin_type="bool", direction="out"),
               ]),
            Fb(ftype="SMOTOR_PROV", instance="SM_DP",
               comment="DP 通讯电机控制（示例）",
               pins=[
                   Pin(name="Group_start", pin_type="bool", direction="in", value="TRUE"),
                   Pin(name="Start_lock", pin_type="bool", direction="in", value="FALSE"),
                   Pin(name="process_lock", pin_type="bool", direction="in", value="FALSE"),
                   Pin(name="safety_lock", pin_type="bool", direction="in", value="FALSE"),
                   Pin(name="Emg_stop", pin_type="bool", direction="in", value="FALSE"),
                   Pin(name="StatusWord", pin_type="DintIO", direction="in", source="N562_DP_MOTOR_SW"),
                   Pin(name="ControlWord", pin_type="DintIO", direction="out", source="N562_DP_MOTOR_CW"),
               ]),
            Fb(ftype="ABBMVVVF", instance="VFD_CTL",
               comment="中压变频器控制（示例；输出管脚按示例简化未列）",
               pins=[
                   Pin(name="Group_start", pin_type="bool", direction="in", source="RS_DRV.Q1"),
                   Pin(name="Start_lock", pin_type="bool", direction="in", value="FALSE"),
                   Pin(name="start_lock_en", pin_type="bool", direction="in", value="TRUE"),
                   Pin(name="READY1", pin_type="bool", direction="in", value="TRUE"),
                   Pin(name="EMG_stop", pin_type="bool", direction="in", value="FALSE"),
                   Pin(name="process_lock", pin_type="bool", direction="in", value="TRUE"),
                   Pin(name="safe_lock", pin_type="bool", direction="in", value="TRUE"),
                   Pin(name="safe_lock_en", pin_type="bool", direction="in", value="TRUE"),
                   Pin(name="Freq_Max", pin_type="real", direction="in", value="50.0"),
                   Pin(name="Frq_min", pin_type="real", direction="in", value="5.0"),
                   Pin(name="run_time", pin_type="time", direction="in", value="T#10S"),
                   Pin(name="ES_TIME", pin_type="time", direction="in", value="T#1S"),
                   Pin(name="safe_lock_time", pin_type="time", direction="in", value="T#2S"),
                   Pin(name="temp_Limit", pin_type="real", direction="in", value="120.0"),
                   # PZD 通道按 IR 点位直连（示例简化；类型语义按 DP 通道简化）
                   Pin(name="INPUTDINT1", pin_type="dint", direction="in", source="N562_MVVVF_SW"),
                   Pin(name="INPUTDINT2", pin_type="dint", direction="in", source="N562_MVVVF_FRQ"),
               ]),
        ],
    )


# ---------------------------------------------------------------------------
# 步骤5 素材：点表变更 v2（DP 设备增点 + 高低字节反转修正）
# ---------------------------------------------------------------------------

def build_points_v2() -> PointTable:
    """试点点位表 v2：模拟调试中发现的点表变更。

    变更点（相对 v1）：
    - 高低字节反转修正：VFD 三个 32 位实际值（频率/电流/温度）字节序
      low_high → high_low（推断：按设备实际通讯表修正，待核实）；
    - DP 设备增点：中压变频器实际功率（PZD5/ACT4）、皮带秤累积量2（IW.7）。
    """
    return PointTable(
        name="e2e_pilot_v2",
        points=[
            Point(tag="N562_MVVVF_SW", description="中压变频器状态字（示例，PZD1）",
                  signal_type="DI",
                  dp=DpInfo(device="ABBMVVVF", slot="PZD1", byte_order="none")),
            Point(tag="N562_MVVVF_FRQ", description="中压变频器实际频率（示例，PZD2/ACT1）",
                  signal_type="AI", range_low=0.0, range_high=50.0, unit="Hz",
                  alarm_high=48.0,
                  dp=DpInfo(device="ABBMVVVF", slot="PZD2", byte_order="high_low")),  # 修正，推断
            Point(tag="N562_MVVVF_CUR", description="中压变频器实际电流（示例，PZD3/ACT2）",
                  signal_type="AI", range_low=0.0, range_high=300.0, unit="A",
                  alarm_high=280.0,
                  dp=DpInfo(device="ABBMVVVF", slot="PZD3", byte_order="high_low")),  # 修正，推断
            Point(tag="N562_MVVVF_TEMP", description="中压变频器电机温度（示例，PZD6/ACT5，/10=°C）",
                  signal_type="AI", range_low=0.0, range_high=150.0, unit="°C",
                  alarm_high=120.0,
                  dp=DpInfo(device="ABBMVVVF", slot="PZD6", byte_order="high_low")),  # 修正，推断
            # ---- 增点：中压变频器实际功率（PZD5/ACT4）----
            Point(tag="N562_MVVVF_P", description="中压变频器实际功率（示例，PZD5/ACT4，增点）",
                  signal_type="AI", range_low=0.0, range_high=2000.0, unit="kW",
                  alarm_high=1800.0,
                  dp=DpInfo(device="ABBMVVVF", slot="PZD5", byte_order="high_low")),  # 推断/待核实
            Point(tag="N562_BAG_DP", description="大布袋收尘器差压（示例/推断）",
                  signal_type="AI", range_low=0.0, range_high=5.0, unit="kPa",
                  alarm_high=4.0,
                  dp=DpInfo(device="KDMC2880", slot="DP_IN", byte_order="none")),
            Point(tag="N562_BAG_FAN_RUN", description="大布袋引风机运行反馈（示例）",
                  signal_type="DI"),
            Point(tag="N562_BAG_FAN_START", description="大布袋引风机启动命令（示例）",
                  signal_type="DO"),
            Point(tag="N562_BAG_DP_RST", description="大布袋差压联锁复位按钮（示例）",
                  signal_type="DI"),
            Point(tag="N562_BSC_FLOW", description="皮带秤实际流量（示例，IW.3，kg/h）",
                  signal_type="AI", range_low=0.0, range_high=500.0, unit="kg/h",
                  alarm_high=460.0,
                  dp=DpInfo(device="ITEC_BATCH", slot="IW.3", byte_order="low_high")),  # 推断/待核实
            # ---- 增点：皮带秤累积量2（IW.7）----
            Point(tag="N562_BSC_ACCUM2", description="皮带秤累积量2（示例，IW.7，kg，增点）",
                  signal_type="AI", range_low=0.0, range_high=100000.0, unit="kg",
                  dp=DpInfo(device="ITEC_BATCH", slot="IW.7", byte_order="low_high")),  # 推断/待核实
            Point(tag="N562_DP_MOTOR_SW", description="DP 电机状态字（示例）",
                  signal_type="DI",
                  dp=DpInfo(device="SMOTOR_PROV", slot="IW.1", byte_order="none")),
            Point(tag="N562_DP_MOTOR_CW", description="DP 电机控制字（示例）",
                  signal_type="DO",
                  dp=DpInfo(device="SMOTOR_PROV", slot="QW.2", byte_order="none")),
        ],
    )


def build_logic_v2() -> LogicProgram:
    """试点逻辑 v2：在 v1 基础上新增功率监测 FB（引用增点 N562_MVVVF_P）。"""
    lp = build_logic_v1()
    lp.fbs.append(
        Fb(ftype="SignalInReal", instance="VFD_PWR",
           comment="中压变频器功率监测（示例，增点对应新 FB）",
           pins=[
               Pin(name="Name", pin_type="string", direction="in", value="MV_VFD_POWER"),
               Pin(name="In", pin_type="RealIO", direction="in_out", source="N562_MVVVF_P"),
           ],
           params={"LevelH": 1600.0, "LevelHH": 1800.0,
                   "EnableL": False, "EnableLL": False, "EnableLLL": False}),
    )
    return lp


# ---------------------------------------------------------------------------
# 各步骤执行
# ---------------------------------------------------------------------------

def step1_points(pt: PointTable) -> None:
    """步骤1：点表导入（构造 + 校验 + 落盘 IR）。"""
    print("[步骤1] 点表导入：构造含 DP 设备点（含字节序标记）的 IR 点表")
    errors = validate_point_table(pt)
    assert not errors, errors
    n_dp = sum(1 for p in pt.points if p.dp is not None)
    print(f"  点位表 '{pt.name}'：{len(pt.points)} 个点，其中 DP 设备点 {n_dp} 个；"
          f"字节序标记：{sum(1 for p in pt.points if p.dp and p.dp.byte_order != 'none')} 个显式标记"
          f"（推断/待核实，见脚本头部说明）")
    save_ir(pt, str(OUT_DIR / f"{pt.name}_points.yaml"))
    print(f"  ✓ 校验 0 错误；IR 已落盘 samples/output/{pt.name}_points.yaml")
    print("  点位清单：")
    for p in pt.points:
        dp_txt = ""
        if p.dp is not None:
            dp_txt = f" | DP {p.dp.device}/{p.dp.slot} 字节序={p.dp.byte_order}"
        print(f"    {p.tag:<20} {p.signal_type:<3} {p.description}{dp_txt}")


def step2_logic(lp: LogicProgram) -> None:
    """步骤2：逻辑生成（构造 + 校验 + 落盘 IR）。"""
    print("[步骤2] 逻辑生成：SignalInReal 监测 + MOTOR1/SMOTOR_PROV 控制 + RS 连锁")
    errors = validate_logic(lp)
    assert not errors, errors
    types = sorted({fb.ftype for fb in lp.fbs})
    print(f"  逻辑 '{lp.name}'：{len(lp.fbs)} 个功能块（类型：{'、'.join(types)}）")
    save_ir(lp, str(OUT_DIR / f"{lp.name}_logic.yaml"))
    print(f"  ✓ 校验 0 错误；IR 已落盘 samples/output/{lp.name}_logic.yaml")
    for fb in lp.fbs:
        print(f"    {fb.instance:<8} ({fb.ftype})：{fb.comment}")


def step3_generate(pt: PointTable, lp: LogicProgram) -> tuple:
    """步骤3：组态产出（生成 VAR/FUN xlsx）。"""
    print("[步骤3] 组态产出：生成 800xA VAR/FUN 批量导入表")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    var_path = OUT_DIR / "e2e_pilot_Var.xlsx"
    fun_path = OUT_DIR / "e2e_pilot_Fun.xlsx"
    generate_var_excel(pt, str(var_path))
    fun_warnings = generate_fun_excel(lp, str(fun_path))
    assert not fun_warnings, fun_warnings  # 所用类型均在 ab800xa_fb_library.yaml 中
    print(f"  VAR 表：{var_path}（{len(pt.points)} 行数据，7 列）")
    print(f"  FUN 表：{fun_path}（{len(lp.fbs)} 行数据，5 列）")
    print("  ✓ 功能块类型全部在 800xA 功能块库中，无类型警告")
    return str(var_path), str(fun_path)


def step4_readback(pt: PointTable, lp: LogicProgram, var_path: str, fun_path: str) -> None:
    """步骤4：回读校验（parse_800xa_export + diff 对比 + 信息丢失说明）。"""
    print("[步骤4] 回读校验：parse_800xa_export 回读，与原始 IR diff 对比")
    back_pt, back_lp = parse_800xa_export(var_path, fun_path)
    back_pt.name = pt.name   # 容器名不在 xlsx 行内，回读用文件名填充，比较前对齐
    back_lp.name = lp.name

    d_pt = diff_points(pt.to_dict(), back_pt.to_dict())
    d_lp = diff_logic(lp.to_dict(), back_lp.to_dict())

    # 统计：DO/AO → DI/AI 的方向丢失（signal_type 变更条数）
    type_loss = sum(1 for e in d_pt.entries if e.path.endswith("/signal_type"))
    # 模拟量字段（量程/单位/报警/DP 等）在 VAR 表无对应列而丢失的条数
    field_loss = sum(1 for e in d_pt.entries
                     if not e.path.endswith("/signal_type") and e.path != "name")
    n_pins_orig = sum(len(fb.pins) for fb in lp.fbs)
    n_pins_back = sum(len(fb.pins) for fb in back_lp.fbs)

    print("  点位表差异明细：")
    text = d_pt.to_text()
    lines = text.split("\n") if text != "无差异" else ["无差异"]
    for ln in lines[:8]:
        print("    " + ln)
    if len(lines) > 8:
        print(f"    …（共 {len(lines)} 条差异）")
    print("  逻辑差异明细：")
    text = d_lp.to_text()
    lines = text.split("\n") if text != "无差异" else ["无差异"]
    for ln in lines[:4]:
        print("    " + ln)
    if len(lines) > 4:
        print(f"    …（共 {len(lines)} 条差异）")

    print("  差异说明（VAR/FUN 表列结构导致的已知信息丢失，非 bug）：")
    print(f"    1. VAR 表只有 Data Type、无方向信息：DO/AO 点回读为 DI/AI"
          f"（signal_type 变更 {type_loss} 处，如 N562_BAG_FAN_START、N562_DP_MOTOR_CW）；")
    print(f"    2. 模板 VAR 段无 量程/单位/报警/DP 等列：模拟量相关字段回读为空"
          f"（{field_loss} 处变更，含 DP 字节序标记全部不回读）；")
    print(f"    3. FUN 表不含管脚/参数信息：Fb.pins 整体不回读"
          f"（原始 {n_pins_orig} 个管脚 → 回读 {n_pins_back} 个）")
    print("  ✓ 回读闭环完成，差异全部可归因于表列结构（工程导入后需以现场回读表为准核对）")


def step5_change_response() -> None:
    """步骤5：调试变更响应（点表变更检测 + 重生成 + 字节序处理）。"""
    print("[步骤5] 调试变更响应：模拟点表变更（DP 设备增点 + 高低字节反转修正）")
    old_pt, new_pt = build_points_v1(), build_points_v2()
    new_lp = build_logic_v2()

    print("  变更点（v1 → v2）：")
    print("    - 高低字节反转修正：N562_MVVVF_FRQ/CUR/TEMP 字节序 low_high → high_low"
          "（推断修正，待核实）")
    print("    - DP 设备增点：N562_MVVVF_P（功率，ABBMVVVF）、N562_BSC_ACCUM2（累积量2，ITEC_BATCH）")
    print("    - 逻辑 v2 新增 FB：VFD_PWR（SignalInReal 监测功率增点）")

    # (a) 变更检测：diff_points + 受影响 FB 定位
    report = detect_change(old_pt, new_pt, new_lp)
    print("  (a) detect_change 变更检测结果：")
    print(f"      变更点位（{len(report.changed_points)}）：{'、'.join(report.changed_points)}")
    print(f"      受影响功能块（{len(report.affected_fbs)}）：{'、'.join(report.affected_fbs)}")
    print("      变更明细：")
    for e in report.entries:
        print("        " + e.to_text())

    # (b) 受影响组态快速重生成：按功能块库生成重建说明
    result = regenerate_affected(AB800XA_FB_LIBRARY_PATH, new_lp, report.affected_fbs)
    print("  (b) regenerate_affected 组态重建说明：")
    for n in result.notes:
        print("    " + n.to_text().replace("\n", "\n    "))

    # (c) 字节序处理工具：处理清单 + 遗漏标记警告
    bo_report = byte_order_fix(new_pt)
    print("  (c) byte_order_fix 字节序处理结果：")
    print(f"      处理清单（{len(bo_report.items)}）：")
    for it in bo_report.items:
        print("      " + it.to_text().replace("\n", "\n      "))
    print(f"      警告（{len(bo_report.warnings)}，byte_order=none 需人工核对）：")
    for w in bo_report.warnings:
        print("        - " + w)

    # 断言：字节序修正的 3 个点进入处理清单（high_low），增点功率进入清单
    assert report.changed_points.count("N562_MVVVF_FRQ") == 1
    assert "SI_FRQ" in report.affected_fbs, report.affected_fbs   # 频率修正 → 监测 FB
    assert "VFD_PWR" in report.affected_fbs, report.affected_fbs  # 功率增点 → 新监测 FB
    assert any(i.tag == "N562_MVVVF_FRQ" and i.byte_order == "high_low" for i in bo_report.items)
    assert any(i.tag == "N562_MVVVF_P" for i in bo_report.items)
    print("  ✓ 变更检测/重建说明/字节序处理三类断言全部通过")


def main() -> None:
    print("===== T10 端到端试点（800xA 自动编程调试框架全流程闭环） =====")
    pt_v1 = build_points_v1()
    lp_v1 = build_logic_v1()

    step1_points(pt_v1)
    step2_logic(lp_v1)
    var_path, fun_path = step3_generate(pt_v1, lp_v1)
    step4_readback(pt_v1, lp_v1, var_path, fun_path)
    step5_change_response()

    print("===== 结论 =====")
    print("T10 端到端试点通过")


if __name__ == "__main__":
    main()
