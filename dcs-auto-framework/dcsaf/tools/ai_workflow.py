# -*- coding: utf-8 -*-
"""AI 工作流编排（T9）。

面向"自然语言需求 → 人工审核 → 一键生成 800xA 组态"的 AI 辅助编程闭环：

1. draft_from_requirement : 需求 → 点位草稿 + IR 逻辑草稿 + 依据说明
   （AI 能力入口：本函数提供结构化输出框架与类型推测"示例"，草稿具体内容
   由调用方 LLM 依据图纸/点号表填充，本函数不编造真实位号与来源）
2. check_draft_sources    : 来源强制校验（用户规则：生成结果必须附来源，
   无来源禁止编造；缺失条目列入 missing_source 清单）
3. review_draft           : 人工审核入口，审核记录落盘 docs/reviews/（YAML，
   含时间/审核人/意见/对应草稿摘要）
4. is_approved            : 审核门禁（未审核通过（无 approve 记录）的草稿
   不得进入生成阶段）
5. generate_from_approved : 审核通过后一键生成 800xA VAR/FUN xlsx
   （复用 dcsaf/adapters/ab800xa.py 的 generate_var_excel/generate_fun_excel）

来源约束（用户规则，强制）：
- DraftResult 每个条目（点位/逻辑）必须带 source 字段；
- 无来源的条目一律 source="无来源，需人工核实" 并列入 missing_source 清单；
- check_draft_sources(draft) 返回缺失来源清单，禁止生成无来源条目而不标注。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..ir import Fb, LogicProgram, Pin, Point, PointTable
from ..ir.point_table import validate_point_table
from ..ir.logic_model import validate_logic

# 框架根目录（dcs-auto-framework）
ROOT = Path(__file__).resolve().parent.parent.parent
# 审核记录落盘目录（docs/reviews/）
REVIEWS_DIR = ROOT / "docs" / "reviews"
# 默认输出目录（与 T4 自测一致：samples/output/）
DEFAULT_OUTPUT_DIR = ROOT / "samples" / "output"

# 无来源条目的统一标注（用户规则：无来源禁止编造，必须显式标注待人工核实）
MISSING_SOURCE = "无来源，需人工核实"

# 审核动作合法值
REVIEW_ACTIONS = ("approve", "reject")

# ---------------------------------------------------------------------------
# 需求关键词 → 类型推测表（仅框架建议，真实类型以点号表/图纸为准）
# 依据：F163_800xA编程规则总纲.md §4.3 功能块选型（模拟量 SignalInReal、
# 电机 MOTOR1、连锁 RS）；57E_IO点表核对方法论（信号类型 DI/DO/AI/AO）
# ---------------------------------------------------------------------------

# 需求词 → 信号类型推测（差压→AI、风机运行反馈→DI、风机启动命令→DO）
_SIGNAL_KEYWORDS: Dict[str, str] = {
    "差压": "AI", "压力": "AI", "温度": "AI", "流量": "AI",
    "液位": "AI", "振动": "AI", "电流": "AI", "给定": "AO",
    "运行": "DI", "反馈": "DI", "故障": "DI", "状态": "DI", "就绪": "DI",
    "启动": "DO", "停止": "DO", "命令": "DO",
}

# 设备词 → 功能块类型推测（F163 总纲 §4.3 选型表）
_DEVICE_FB_KEYWORDS: Dict[str, str] = {
    "风机": "MOTOR1", "电机": "MOTOR1", "泵": "MOTOR1", "加热器": "MOTOR1",
    "变频": "ABBMVVVF", "阀门": "VALVE1",
}

# 连锁类关键词（出现即提示生成 RS/报警连锁关联）
_INTERLOCK_KEYWORDS = ("跳停", "连锁", "联锁", "高跳", "低跳", "停机")


# ---------------------------------------------------------------------------
# 草稿数据结构
# ---------------------------------------------------------------------------

@dataclass
class DraftPoint:
    """点位草稿（对应 IR Point）。

    source 必填：真实来源（图纸文件名/页码、点号表行号）由 LLM 依据设计资料
    填写；无法给出的条目保持 MISSING_SOURCE 并进入 missing_source 清单。
    """
    tag: str = ""                 # 位号建议（真实位号以点号表为准，框架用 TBD_ 前缀）
    description: str = ""         # 描述
    signal_type: str = ""         # DI/DO/AI/AO
    source: str = ""              # 来源（强制字段）
    range_low: Optional[float] = None    # 模拟量量程下限（AI/AO 必填，IR 校验要求）
    range_high: Optional[float] = None   # 模拟量量程上限
    unit: str = ""                # 工程单位
    alarm_low: Optional[float] = None    # 报警下限（L/LL）
    alarm_high: Optional[float] = None   # 报警上限（H/HH）
    interlock_ref: List[str] = field(default_factory=list)  # 关联连锁（如"差压高跳停出口风机"）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tag": self.tag,
            "description": self.description,
            "signal_type": self.signal_type,
            "source": self.source,
            "range_low": self.range_low,
            "range_high": self.range_high,
            "unit": self.unit,
            "alarm_low": self.alarm_low,
            "alarm_high": self.alarm_high,
            "interlock_ref": self.interlock_ref,
        }


@dataclass
class DraftPin:
    """功能块管脚草稿（对应 IR Pin）。"""
    name: str = ""
    pin_type: str = ""
    direction: str = "in"         # in / out / in_out
    value: Optional[str] = None   # 直接值（常量）
    source: Optional[str] = None  # 来源（"实例名.管脚" 或 点位号）


@dataclass
class DraftFb:
    """功能块草稿（对应 IR Fb）。

    source 必填：功能块选型依据来源（如"F163 总纲 §4.3 选型表"或具体图纸页码）。
    """
    ftype: str = ""               # 功能块类型（MOTOR1 / SignalInReal / RS 等）
    instance: str = ""            # 实例名（唯一键）
    purpose: str = ""             # 用途说明（生成时写入 FUN 表 Description）
    source: str = ""              # 选型来源（强制字段）
    pins: List[DraftPin] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DraftResult:
    """需求解析 → 草稿结果。

    由 draft_from_requirement 生成"框架+示例"；真实内容由调用方 LLM 填充。
    强制约束：每个条目带 source；无来源条目 source=MISSING_SOURCE 并列入
    missing_source 清单（由 check_draft_sources 维护）。
    """
    draft_id: str = ""                        # 草稿唯一标识
    requirement_text: str = ""                # 原始自然语言需求
    points_draft: List[DraftPoint] = field(default_factory=list)  # 点位草稿
    logic_draft: List[DraftFb] = field(default_factory=list)      # 逻辑草稿
    missing_source: List[str] = field(default_factory=list)       # 缺失来源清单
    rationale: str = ""                       # 依据说明
    created_at: str = ""                      # 创建时间

    def to_dict(self) -> Dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "requirement_text": self.requirement_text,
            "points_draft": [p.to_dict() for p in self.points_draft],
            "logic_draft": [{
                "ftype": f.ftype,
                "instance": f.instance,
                "purpose": f.purpose,
                "source": f.source,
                "pins": [{
                    "name": p.name, "pin_type": p.pin_type,
                    "direction": p.direction, "value": p.value, "source": p.source,
                } for p in f.pins],
                "params": f.params,
            } for f in self.logic_draft],
            "missing_source": self.missing_source,
            "rationale": self.rationale,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# 1. 需求解析 → 草稿（AI 能力入口：结构化输出框架 + 类型推测示例）
# ---------------------------------------------------------------------------

def _now_stamp() -> str:
    """当前时间戳（YYYYmmddHHMMSS）。"""
    return datetime.now().strftime("%Y%m%d%H%M%S")


def _guess_signal_type(text: str) -> List[str]:
    """按关键词推测需求涉及哪些信号类型（仅框架建议，真实类型以点号表为准）。"""
    found: List[str] = []
    for kw, sig in _SIGNAL_KEYWORDS.items():
        if kw in text and sig not in found:
            found.append(sig)
    return found


def _guess_device_fbs(text: str) -> List[str]:
    """按设备关键词推测功能块类型（仅框架建议，选型最终依据 F163 总纲 §4.3）。"""
    found: List[str] = []
    for kw, fb_type in _DEVICE_FB_KEYWORDS.items():
        if kw in text and fb_type not in found:
            found.append(fb_type)
    return found


def draft_from_requirement(requirement_text: str) -> DraftResult:
    """自然语言需求 → 草稿（点位草稿 + IR 逻辑草稿 + 依据说明）。

    本函数是 AI 能力入口，提供两个能力：
    a) 生成"需求 → 所需点位清单草稿"框架：按关键词推测 signal 类型
       （差压→AI、风机→电机 DO+状态 DI、跳停→连锁关联）；
    b) 生成 IR 逻辑草稿框架：按设备词推测 Fb 类型
       （SignalInReal 测差压、MOTOR1 风机、连锁用 RS/报警 AlarmCond）。

    强制来源约束：所有条目 source 一律置 MISSING_SOURCE（"无来源，需人工核实"），
    由 check_draft_sources 列出缺失清单——本函数只给"结构框架"，不编造任何
    真实位号/图纸来源；真实内容须由 LLM 依据图纸/点号表填充后进入审核。

    位号建议统一用 "TBD_<设备>_<信号>" 前缀（TBD=To Be Determined），
    提示真实位号须查点号表（F163 总纲 §4.7 命名规则 N<节点>_<系统>_<设备>_<信号>_<后缀>）。
    """
    if not requirement_text or not requirement_text.strip():
        raise ValueError("需求文本不能为空")

    text = requirement_text.strip()
    draft_id = f"draft_{_now_stamp()}"
    device_fbs = _guess_device_fbs(text)
    signal_types = _guess_signal_type(text)

    points_draft: List[DraftPoint] = []
    logic_draft: List[DraftFb] = []

    # a) 点位清单草稿框架：按设备生成 运行反馈 DI + 启动命令 DO，
    #    按信号词生成 AI/AO 点（差压→AI 等）
    for fb_type in device_fbs:
        if fb_type == "MOTOR1":
            points_draft.append(DraftPoint(
                tag=f"TBD_{_pick_device(text)}_RUN",
                description="运行反馈（DI，真实位号以点号表为准）",
                signal_type="DI",
                source=MISSING_SOURCE,
            ))
            points_draft.append(DraftPoint(
                tag=f"TBD_{_pick_device(text)}_START",
                description="启动命令（DO，真实位号以点号表为准）",
                signal_type="DO",
                source=MISSING_SOURCE,
            ))
            # 跳停连锁：给电机点挂连锁关联（interlock_ref 仅工程输入记录，见 io 模板）
            if _has_interlock(text):
                for p in points_draft:
                    if p.signal_type in ("DI", "DO"):
                        p.interlock_ref.append("差压高跳停（连锁关联，见连锁图 VP 9007 系列）")
                        p.description += f"【连锁】{p.interlock_ref[-1]}"
        elif fb_type in ("ABBMVVVF", "VALVE1"):
            points_draft.append(DraftPoint(
                tag=f"TBD_{_pick_device(text)}_CTRL",
                description=f"控制命令（{fb_type} 关联，真实位号以点号表为准）",
                signal_type="DO",
                source=MISSING_SOURCE,
            ))

    for sig in signal_types:
        if sig in ("AI", "AO"):
            points_draft.append(DraftPoint(
                tag=f"TBD_{_pick_signal(text)}_RAW",
                description=f"模拟量信号（{sig}，真实位号/量程以点号表为准）",
                signal_type=sig,
                source=MISSING_SOURCE,
            ))

    # b) IR 逻辑草稿框架：按设备词推测 Fb 类型，连锁用 RS/报警
    inst_idx = 1
    for fb_type in device_fbs:
        logic_draft.append(DraftFb(
            ftype=fb_type,
            instance=f"TBD_{_pick_device(text)}{inst_idx:02d}",
            purpose=f"{_pick_device(text)}控制（Fb 类型由需求推测，选型依据 F163 总纲 §4.3）",
            source=MISSING_SOURCE,
        ))
        inst_idx += 1

    for sig in signal_types:
        if sig in ("AI", "AO"):
            logic_draft.append(DraftFb(
                ftype="SignalInReal",
                instance=f"TBD_SIR_{inst_idx:02d}",
                purpose=f"模拟量监测（{sig}，六级报警；连锁只用 GTHStat/GTHHStat，见 F163 总纲 §4.5）",
                source=MISSING_SOURCE,
            ))
            inst_idx += 1

    if _has_interlock(text):
        logic_draft.append(DraftFb(
            ftype="RS",
            instance="TBD_RS_ILK",
            purpose="连锁锁存（复位优先 RS；如 差压HH → Set，复位 → R1，Q1 → 电机 process_lock，"
                    "MOTOR1 lock 管脚 true=锁定，见 F163 总纲 §4.4）",
            source=MISSING_SOURCE,
        ))
        logic_draft.append(DraftFb(
            ftype="AlarmCond",
            instance="TBD_ALM_ILK",
            purpose="连锁报警（Severity 800 重报警，见 F163 总纲 §5.9）",
            source=MISSING_SOURCE,
        ))

    rationale = (
        "草稿由 AI 能力入口 draft_from_requirement 生成：仅提供结构化输出框架与"
        "类型推测示例（差压→AI/SignalInReal、风机→MOTOR1、跳停→RS 连锁），"
        "全部条目的真实位号、量程、来源均待人工依据设计资料（点号表 3E8-2R、"
        "连锁图 VP 9007-00、F163 总纲 §4.7 命名规则）核实填充；"
        "未填充来源的条目一律标注“无来源，需人工核实”并列入 missing_source，"
        "禁止无来源进入生成阶段。"
    )

    draft = DraftResult(
        draft_id=draft_id,
        requirement_text=text,
        points_draft=points_draft,
        logic_draft=logic_draft,
        rationale=rationale,
        created_at=_now_stamp(),
    )
    check_draft_sources(draft)  # 立即刷新缺失来源清单
    return draft


def _pick_device(text: str) -> str:
    """从需求文本提取设备词（用于位号建议前缀；取第一个命中的设备词，无则 'DEV'）。"""
    for kw in _DEVICE_FB_KEYWORDS:
        if kw in text:
            return kw
    return "DEV"


def _pick_signal(text: str) -> str:
    """从需求文本提取信号词（用于位号建议前缀；取第一个命中的信号词，无则 'SIG'）。"""
    for kw in _SIGNAL_KEYWORDS:
        if kw in text:
            return kw
    return "SIG"


def _has_interlock(text: str) -> bool:
    """需求文本是否含连锁类关键词（跳停/连锁/高跳/低跳等）。"""
    return any(kw in text for kw in _INTERLOCK_KEYWORDS)


# ---------------------------------------------------------------------------
# 2. 来源强制校验（用户规则：无来源禁止编造）
# ---------------------------------------------------------------------------

def check_draft_sources(draft: DraftResult) -> List[str]:
    """校验草稿来源，返回缺失来源清单（空列表表示全部有来源）。

    规则（用户规则，强制）：
    - DraftResult 每个条目（点位/逻辑）必须带 source 字段；
    - source 为空 → 自动置为 MISSING_SOURCE（"无来源，需人工核实"）并列入清单；
    - source 等于 MISSING_SOURCE → 视为缺失并列入清单；
    - 缺失清单同步写入 draft.missing_source（保持草稿自洽）。

    禁止生成无来源条目而不标注：任何缺失来源的条目必须能通过本函数被列出。
    """
    missing: List[str] = []

    for p in draft.points_draft:
        if not p.source.strip() or p.source.strip() == MISSING_SOURCE:
            if not p.source.strip():
                p.source = MISSING_SOURCE  # 空来源自动标注，禁止静默无来源
            missing.append(f"点位 '{p.tag}'（{p.signal_type}）无来源")

    for f in draft.logic_draft:
        if not f.source.strip() or f.source.strip() == MISSING_SOURCE:
            if not f.source.strip():
                f.source = MISSING_SOURCE
            missing.append(f"功能块 '{f.instance}'（{f.ftype}）无来源")

    draft.missing_source = missing
    return list(missing)


# ---------------------------------------------------------------------------
# 3. 人工审核入口与审核记录（落盘 docs/reviews/）
# ---------------------------------------------------------------------------

@dataclass
class ReviewRecord:
    """单次审核记录（对应落盘的 YAML 文件）。"""
    draft_id: str = ""
    reviewer: str = ""
    action: str = ""              # approve / reject
    comments: str = ""
    reviewed_at: str = ""
    draft_summary: Dict[str, Any] = field(default_factory=dict)  # 对应草稿摘要
    file_path: str = ""           # 落盘路径（空表示未落盘）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "reviewer": self.reviewer,
            "action": self.action,
            "comments": self.comments,
            "reviewed_at": self.reviewed_at,
            "draft_summary": self.draft_summary,
        }


def _draft_summary(draft: DraftResult) -> Dict[str, Any]:
    """生成审核记录用的草稿摘要（需求文本 + 条目数 + 缺失来源清单）。"""
    return {
        "requirement_text": draft.requirement_text,
        "points_count": len(draft.points_draft),
        "logic_count": len(draft.logic_draft),
        "missing_source": list(draft.missing_source),
    }


def review_draft(draft: DraftResult, reviewer: str, action: str,
                 comments: str = "") -> ReviewRecord:
    """人工审核入口：把审核记录落盘 docs/reviews/（YAML）。

    审核记录内容：草稿 ID、时间、审核人、意见（comments）、对应草稿摘要
    （需求文本/点位与功能块条目数/缺失来源清单）。文件名
    review_<draft_id>_<时间戳>.yaml，同草稿多次审核各留一份（审核留痕）。

    action 仅允许 approve / reject；其他值抛 ValueError。
    """
    if action not in REVIEW_ACTIONS:
        raise ValueError(f"审核动作 '{action}' 非法，应为 {list(REVIEW_ACTIONS)}")
    if not reviewer or not reviewer.strip():
        raise ValueError("审核人不能为空")

    record = ReviewRecord(
        draft_id=draft.draft_id,
        reviewer=reviewer.strip(),
        action=action,
        comments=comments,
        reviewed_at=_now_stamp(),
        draft_summary=_draft_summary(draft),
    )

    # 落盘：docs/reviews/review_<draft_id>_<时间戳>.yaml
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = REVIEWS_DIR / f"review_{draft.draft_id}_{record.reviewed_at}.yaml"
    file_path.write_text(
        yaml.safe_dump(record.to_dict(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    record.file_path = str(file_path)
    return record


def is_approved(draft_id: str) -> bool:
    """审核门禁：草稿是否已审核通过（存在 action=approve 的审核记录）。

    未审核通过（无 approve 记录）的草稿不得进入生成阶段；
    reject 记录不算通过；approve 与 reject 并存时以最后一条记录为准。
    """
    if not draft_id:
        return False
    if not REVIEWS_DIR.exists():
        return False

    records: List[Dict[str, Any]] = []
    for f in sorted(REVIEWS_DIR.glob(f"review_{draft_id}_*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            data["_file"] = f.name
            records.append(data)
        except Exception:
            continue  # 记录文件损坏时跳过，不让其影响门禁判断

    if not records:
        return False
    # 按落盘时间取最后一条记录，approve 才算通过（reject 不算）
    latest = records[-1]
    return str(latest.get("action", "")).strip().lower() == "approve"


# ---------------------------------------------------------------------------
# 4. 审核后一键生成（800xA VAR/FUN xlsx）
# ---------------------------------------------------------------------------

@dataclass
class GenerateResult:
    """一键生成结果。"""
    draft_id: str = ""
    approved: bool = False              # 是否通过审核门禁
    output_files: List[str] = field(default_factory=list)   # 输出文件路径列表
    var_summary: List[str] = field(default_factory=list)    # VAR 表摘要（每点一行）
    fun_summary: List[str] = field(default_factory=list)    # FUN 表摘要（每 FB 一行）
    failure_reason: str = ""            # 失败原因（空串表示成功）


def _draft_to_ir(draft: DraftResult) -> tuple[PointTable, LogicProgram]:
    """草稿 → IR 模型（DraftPoint→Point、DraftFb→Fb）。

    仅映射草稿中已明确填写的字段；未填写（None/空）的字段不编造。
    """
    points: List[Point] = []
    for dp in draft.points_draft:
        points.append(Point(
            tag=dp.tag,
            description=dp.description,
            signal_type=dp.signal_type,
            range_low=dp.range_low,
            range_high=dp.range_high,
            unit=dp.unit,
            alarm_low=dp.alarm_low,
            alarm_high=dp.alarm_high,
            interlock_ref=list(dp.interlock_ref),
        ))

    fbs: List[Fb] = []
    for df in draft.logic_draft:
        fbs.append(Fb(
            ftype=df.ftype,
            instance=df.instance,
            pins=[
                Pin(name=p.name, pin_type=p.pin_type, direction=p.direction,
                    value=p.value, source=p.source)
                for p in df.pins
            ],
            params=dict(df.params),
            comment=df.purpose,
        ))

    return PointTable(name=draft.draft_id, points=points), \
        LogicProgram(name=draft.draft_id, fbs=fbs)


def generate_from_approved(draft: DraftResult, platform: str = "ab800xa",
                           output_dir: Optional[str] = None) -> GenerateResult:
    """审核后一键生成 800xA 组态文件（VAR/FUN xlsx）。

    流程：
    1. 先检查 is_approved(draft.draft_id)：未审核通过 → 拒绝并返回错误
       （"草稿未审核通过，禁止进入生成阶段"），不生成任何文件；
    2. 平台检查：当前仅支持 ab800xa（其他平台官方接口待核实，不静默假装成功）；
    3. 草稿 → IR（DraftPoint→PointTable、DraftFb→LogicProgram）；
    4. IR 校验（validate_point_table / validate_logic）：校验错误作为失败原因
       返回，不生成文件（如 AI 点缺量程、输入管脚悬空、功能块类型不在库中）；
    5. 调用 ab800xa adapter 的 generate_var_excel / generate_fun_excel，
       xlsx 输出到 output_dir（默认 samples/output/，与 T4 自测目录一致）。

    返回 GenerateResult：输出文件路径列表、VAR/FUN 表摘要、失败原因（若有）。
    """
    # 1) 审核门禁：未审核通过禁止进入生成阶段
    if not is_approved(draft.draft_id):
        return GenerateResult(
            draft_id=draft.draft_id,
            approved=False,
            failure_reason="草稿未审核通过，禁止进入生成阶段",
        )

    # 2) 平台检查（仅支持 ab800xa，其余待核实，禁止假装成功）
    if platform != "ab800xa":
        return GenerateResult(
            draft_id=draft.draft_id,
            approved=True,
            failure_reason=f"平台 '{platform}' 暂不支持自动生成（官方接口待核实），"
                           f"当前仅支持 ab800xa",
        )

    # 3) 草稿 → IR
    point_table, logic_program = _draft_to_ir(draft)

    # 4) IR 校验：错误作为失败原因返回，不生成文件
    pt_errors = validate_point_table(point_table)
    lg_errors = validate_logic(logic_program)
    if pt_errors or lg_errors:
        reasons = pt_errors + lg_errors
        return GenerateResult(
            draft_id=draft.draft_id,
            approved=True,
            failure_reason="草稿转 IR 校验未通过：\n  - " + "\n  - ".join(reasons),
        )

    # 5) 调用 ab800xa adapter 生成 VAR/FUN xlsx
    out_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    var_path = out_dir / f"{draft.draft_id}_Var.xlsx"
    fun_path = out_dir / f"{draft.draft_id}_Fun.xlsx"

    from ..adapters.ab800xa import generate_fun_excel, generate_var_excel

    try:
        generate_var_excel(point_table, str(var_path))
        fun_warnings = generate_fun_excel(logic_program, str(fun_path))
    except Exception as e:  # 生成过程异常（如模板缺失）作为失败原因返回
        return GenerateResult(
            draft_id=draft.draft_id,
            approved=True,
            failure_reason=f"生成 xlsx 失败：{e}",
        )

    var_summary = [f"{p.tag} | {p.signal_type} | {p.description or ''}"
                   for p in point_table.points]
    fun_summary = [f"{fb.instance} | {fb.ftype} | {fb.comment or ''}"
                   for fb in logic_program.fbs]
    if fun_warnings:
        fun_summary.append("类型警告：")
        fun_summary.extend(f"  - {w}" for w in fun_warnings)

    return GenerateResult(
        draft_id=draft.draft_id,
        approved=True,
        output_files=[str(var_path), str(fun_path)],
        var_summary=var_summary,
        fun_summary=fun_summary,
    )
