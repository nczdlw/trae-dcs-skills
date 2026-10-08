# -*- coding: utf-8 -*-
"""T9 自测：AI 工作流编排完整闭环验证。

流程（对应 T9.1/T9.2/T9.3）：
[1] draft_from_requirement("大布袋进出口差压高跳停出口风机")
    生成"框架草稿"（差压→AI/SignalInReal、风机→MOTOR1、跳停→RS 连锁，
    全部条目 source="无来源，需人工核实"）；
[2] 人工构造一个合理示例草稿（真实位号风格：差压 AI SignalInReal、
    风机 MOTOR1、连锁 RS；其中 1 个点位故意漏标来源）；
[3] check_draft_sources 列出无来源条目（缺失来源清单）；
[4] 未审核时 generate_from_approved 被拒绝（返回错误，不生成文件）；
[5] 模拟 review_draft approve 后 generate_from_approved 成功生成
    VAR/FUN xlsx（输出到 samples/output/）；
[6] 运行输出"T9 自测通过"。

运行：python3 samples/t9_ai_workflow_selftest.py（从框架根目录或任意目录均可）。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dcsaf.tools.ai_workflow import (
    MISSING_SOURCE,
    DraftFb, DraftPin, DraftPoint, DraftResult,
    check_draft_sources, draft_from_requirement,
    generate_from_approved, is_approved, review_draft,
)

# 自测用固定草稿 ID（审核记录按 draft_id 检索，固定 ID 便于前后一致；
# 脚本开头清理该 ID 的历史审核记录，保证"未审核拒绝"用例每次从干净状态开始）
SELFTEST_DRAFT_ID = "t9_selftest_manual"

from dcsaf.tools.ai_workflow import REVIEWS_DIR


def build_manual_draft() -> DraftResult:
    """人工构造合理示例草稿：大布袋进出口差压高跳停出口风机。

    差压：AI 点 + SignalInReal 监测（六级报警，连锁用 GTHHStat，F163 总纲 §4.5）；
    出口风机：MOTOR1（运行反馈 DI + 启动命令 DO，F163 总纲 §4.3）；
    连锁：RS 复位优先锁存（Set=差压 HH、R1=连锁复位按钮），Q1 → MOTOR1
    process_lock（true=锁定 → 停机，F163 总纲 §4.4）。
    示例来源标注"待人工核实"，其中 N562_FN1_RUN 故意漏标来源（测试来源校验）。
    """
    return DraftResult(
        draft_id=SELFTEST_DRAFT_ID,
        requirement_text="大布袋进出口差压高跳停出口风机",
        points_draft=[
            DraftPoint(
                tag="N562_BD1_DP_RAW",
                description="大布袋进出口差压",
                signal_type="AI",
                source="示例：3E8-2R 点号表 AI 段（行号待人工核实）",
                range_low=0.0, range_high=10.0, unit="kPa",
                alarm_high=5.0,
                interlock_ref=["差压高跳停出口风机"],
            ),
            DraftPoint(
                tag="N562_FN1_RUN",
                description="出口风机运行反馈",
                signal_type="DI",
                source=MISSING_SOURCE,  # 故意漏标来源，用于验证 check_draft_sources
            ),
            DraftPoint(
                tag="N562_FN1_START",
                description="出口风机启动命令",
                signal_type="DO",
                source="示例：3E8-2R 点号表 DO 段（行号待人工核实）",
            ),
            DraftPoint(
                tag="N562_BD1_DP_RESET",
                description="大布袋差压连锁复位按钮",
                signal_type="DI",
                source="示例：3E8-2R 点号表 DI 段（行号待人工核实）",
            ),
        ],
        logic_draft=[
            DraftFb(
                ftype="SignalInReal",
                instance="N562BD1DP",
                purpose="大布袋进出口差压监测（六级报警；连锁只用 GTHStat/GTHHStat，F163 总纲 §4.5）",
                source="示例：F163_800xA编程规则总纲.md §4.3/§4.5",
                pins=[
                    DraftPin(name="In", pin_type="RealIO", direction="in_out",
                             source="N562_BD1_DP_RAW"),
                ],
                params={"LevelH": 5.0, "LevelHH": 6.0, "EnableH": True, "EnableHH": True},
            ),
            DraftFb(
                ftype="RS",
                instance="RS1_DPH",
                purpose="差压高跳停出口风机连锁锁存（复位优先 RS；Set=差压HH、R1=复位按钮）",
                source="示例：ABB_800XA_DP功能块开发规则.md（RS 复位引脚 R1）",
                pins=[
                    DraftPin(name="Set", pin_type="bool", direction="in",
                             source="N562BD1DP.GTHHStat"),
                    DraftPin(name="R1", pin_type="bool", direction="in",
                             source="N562_BD1_DP_RESET"),
                ],
            ),
            DraftFb(
                ftype="MOTOR1",
                instance="N562FN1E01",
                purpose="出口风机启停控制（MOTOR1，F163 总纲 §4.3；lock 管脚 true=锁定）",
                source="示例：F163_800xA编程规则总纲.md §4.3/§4.4",
                pins=[
                    DraftPin(name="Running", pin_type="bool", direction="in",
                             source="N562_FN1_RUN"),
                    DraftPin(name="Emg_stop", pin_type="bool", direction="in",
                             value="FALSE"),
                    DraftPin(name="start_lock", pin_type="bool", direction="in",
                             value="FALSE"),
                    DraftPin(name="process_lock", pin_type="bool", direction="in",
                             source="RS1_DPH.Q1"),
                    DraftPin(name="Drive", pin_type="bool", direction="out",
                             source="N562_FN1_START"),
                ],
            ),
        ],
        rationale="人工构造合理示例（自测用）：位号为示例命名风格（N562_xxx，F163 总纲 §4.7），"
                  "量程/报警限为示例值；全部来源标注'待人工核实'，不得直接用于工程。",
        created_at="20261008_000000",
    )


def main() -> None:
    print("===== T9 AI 工作流编排 自测 =====")

    # [1] draft_from_requirement：需求 → 框架草稿（AI 能力入口）
    print("[1] draft_from_requirement('大布袋进出口差压高跳停出口风机') 框架草稿:")
    frame_draft = draft_from_requirement("大布袋进出口差压高跳停出口风机")
    assert frame_draft.points_draft, "框架草稿点位为空"
    assert frame_draft.logic_draft, "框架草稿逻辑为空"
    assert all(p.source == MISSING_SOURCE for p in frame_draft.points_draft), \
        "框架草稿点位来源应全部为 MISSING_SOURCE"
    sig_types = {p.signal_type for p in frame_draft.points_draft}
    assert "AI" in sig_types and "DI" in sig_types and "DO" in sig_types, \
        f"差压→AI、风机→DI/DO 推测失败: {sig_types}"
    fb_types = {f.ftype for f in frame_draft.logic_draft}
    assert "SignalInReal" in fb_types and "MOTOR1" in fb_types and "RS" in fb_types, \
        f"SignalInReal/MOTOR1/RS 推测失败: {fb_types}"
    print(f"  点位草稿 {len(frame_draft.points_draft)} 条，信号类型 {sorted(sig_types)}；"
          f"逻辑草稿 {len(frame_draft.logic_draft)} 条，Fb 类型 {sorted(fb_types)}  ✓")
    print(f"  依据说明: {frame_draft.rationale[:40]}...")

    # [2] 人工构造合理示例草稿（真实需求解析由 LLM 完成，此处模拟 LLM 输出）
    print("[2] 人工构造合理示例草稿（差压 AI/SignalInReal、风机 MOTOR1、连锁 RS）:")
    # 清理该草稿 ID 的历史审核记录，保证未审核用例从干净状态开始
    for f in REVIEWS_DIR.glob(f"review_{SELFTEST_DRAFT_ID}_*.yaml"):
        f.unlink()
    manual = build_manual_draft()
    print(f"  点位 {len(manual.points_draft)} 条 / 功能块 {len(manual.logic_draft)} 条  ✓")

    # [3] check_draft_sources：列出无来源条目
    print("[3] check_draft_sources 来源校验:")
    missing = check_draft_sources(manual)
    assert missing, "应至少列出 1 条无来源条目（N562_FN1_RUN 故意漏标）"
    assert any("N562_FN1_RUN" in m for m in missing), f"漏标条目未被列出: {missing}"
    assert manual.missing_source == missing, "missing_source 清单未同步到草稿"
    print(f"  缺失来源清单（{len(missing)} 条）:")
    for m in missing:
        print(f"    - {m}")
    # 补充来源后清单应清空（校验函数可用性）
    for p in manual.points_draft:
        if p.tag == "N562_FN1_RUN":
            p.source = "示例：3E8-2R 点号表 DI 段（行号待人工核实）"
    assert not check_draft_sources(manual), "补全来源后缺失清单应为空"

    # [4] 未审核时 generate_from_approved 被拒绝
    print("[4] 未审核时 generate_from_approved 被拒绝:")
    rejected = generate_from_approved(manual)
    assert not rejected.approved
    assert "草稿未审核通过，禁止进入生成阶段" in rejected.failure_reason, rejected.failure_reason
    assert not rejected.output_files, "未审核不应生成任何文件"
    assert not is_approved(manual.draft_id)
    print(f"  失败原因: {rejected.failure_reason}  ✓")

    # [5] 模拟审核 approve → 审核通过 → 一键生成 xlsx（输出到 samples/output/）
    print("[5] 模拟 review_draft approve 后一键生成:")
    record = review_draft(manual, reviewer="审核人（示例）", action="approve",
                          comments="示例审核通过：差压 AI、风机 MOTOR1、连锁 RS 结构合理")
    assert record.file_path and Path(record.file_path).exists(), "审核记录未落盘"
    print(f"  审核记录落盘: {record.file_path}")
    assert is_approved(manual.draft_id), "approve 后 is_approved 应为 True"

    result = generate_from_approved(manual)
    assert result.approved, result.failure_reason
    assert not result.failure_reason, result.failure_reason
    assert len(result.output_files) == 2, result.output_files
    for fp in result.output_files:
        assert Path(fp).exists(), f"输出文件不存在: {fp}"
    print(f"  输出文件（{len(result.output_files)} 个）:")
    for fp in result.output_files:
        print(f"    - {fp}")
    print(f"  VAR 表摘要（{len(result.var_summary)} 条）:")
    for s in result.var_summary:
        print(f"    - {s}")
    print(f"  FUN 表摘要（{len(result.fun_summary)} 条）:")
    for s in result.fun_summary:
        print(f"    - {s}")

    # [6] 未通过（reject）的草稿不得生成（门禁反例）
    print("[6] reject 审核记录不作为通过依据（门禁反例）:")
    review_draft(manual, reviewer="审核人（示例）", action="reject",
                 comments="示例复核不通过：量程/报警限待与图纸核对")
    assert not is_approved(manual.draft_id), "reject 后 is_approved 应为 False"

    print("\n===== 结论 =====")
    print("T9 自测通过")


if __name__ == "__main__":
    main()
