# -*- coding: utf-8 -*-
"""调试快速响应工具（T7）。

面向 DCS 调试场景的三类快速响应能力：
1. detect_change        : 点表变更检测与增量更新（diff_points + 受影响 FB 定位）
2. regenerate_affected  : 受影响组态快速重生成（按功能块库生成重建说明）
3. byte_order_fix       : DP 通讯字节序处理工具（生成/回读校验说明 + 遗漏标记警告）

字节序背景（knowledge/20-DP通讯与设备功能块/ABB_800XA_DP功能块开发规则_20260715_2240.md）：
DP 通讯地址表用 2 字节 WORD 编号，32 位数据拆两个 WORD 时存在高低字节/高低字
排列顺序问题（文档第九节、HAVER 设备 Big-Endian 标注），顺序弄反是调试中
"数值错乱/大小异常"的常见根因。文档未给统一处理公式，本模块的处理说明为
按通用小端/大端常识描述，显式标注"推断"。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Union

import yaml

from ..ir import LogicProgram, PointTable
from ..ir.diff import DiffEntry, diff_points

# 框架根目录（dcs-auto-framework）
ROOT = Path(__file__).resolve().parent.parent.parent
# 800xA 功能块库（重建说明的类型定义基准，只读）
AB800XA_FB_LIBRARY_PATH = ROOT / "libs" / "ab800xa_fb_library.yaml"

# DP 通讯字节序取值说明（high_low 的典型工程场景见知识文档：HAVER 包装机 Big-Endian）
LOW_HIGH_LABEL = "低位在前（小端 little-endian）：32 位数据拆两个 16 位字时，低字（低 16 位）排低地址通道、先发送"
HIGH_LOW_LABEL = "高位在前（大端 big-endian）：32 位数据拆两个 16 位字时，高字（高 16 位）排低地址通道、先发送"


def _norm(s: Any) -> str:
    """比较用规范化：去首尾空格、忽略大小写（与 dcsaf.adapters.ab800xa._norm 一致）。"""
    return str(s or "").strip().lower()


def _load_fb_library(fb_library: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    """加载功能块库：传入路径则读 YAML，传入字典则直接用。

    YAML 结构：{'fbs': {<ftype>: {'comment':..., 'pins': [...], 'params': {...}}}}。
    """
    if isinstance(fb_library, dict):
        return fb_library
    path = Path(fb_library)
    if not path.exists():
        raise FileNotFoundError(f"功能块库不存在: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _tag_from_diff_path(path: str) -> str:
    """从 DiffEntry.path 提取点位 tag。

    diff_points 的 path 形如 'points/<tag>'（整点新增/删除）或
    'points/<tag>/<field>'（字段变更）；非 points 前缀（如 'name'）返回空串。
    """
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "points":
        return parts[1]
    return ""


# ---------------------------------------------------------------------------
# 1. 点表变更检测与增量更新
# ---------------------------------------------------------------------------

@dataclass
class ChangeReport:
    """点表变更检测报告。"""
    changed_points: List[str] = field(default_factory=list)  # 变更/新增/删除的 tag 列表（去重保序）
    affected_fbs: List[str] = field(default_factory=list)    # 受影响 Fb 实例名列表（去重保序）
    entries: List[DiffEntry] = field(default_factory=list)   # 变更明细（diff 原始条目）

    def to_text(self) -> str:
        lines = [
            f"变更点位（{len(self.changed_points)}）：{'、'.join(self.changed_points) or '无'}",
            f"受影响功能块（{len(self.affected_fbs)}）：{'、'.join(self.affected_fbs) or '无'}",
            "变更明细：",
        ]
        lines.extend(f"  {e.to_text()}" for e in self.entries)
        return "\n".join(lines)


def detect_change(old_points: PointTable, new_points: PointTable, logic_program: LogicProgram) -> ChangeReport:
    """点表变更检测与增量更新。

    流程：
    1. 用 diff_points 比较新旧点位表 IR（整表字典），拿到 DiffEntry 明细；
    2. 从明细 path 提取变更 tag（added/removed/changed 三类都算"变更点"）；
    3. 扫描逻辑模型中所有 Fb.pins，若某管脚的 source 或 value 指向变更的 tag
       （规范化后相等），则此 Fb 实例判为受影响。

    注意：管脚引用 tag 的匹配为整串精确比较（忽略大小写/首尾空格），
    与"实例名.管脚"形式的内部引用互不干扰（内部引用带 '.'，不匹配 tag）。
    """
    diff_result = diff_points(old_points.to_dict(), new_points.to_dict())

    # 1) 变更 tag 集合（保序去重）。
    # 注意：diff_lists 的 path 里 tag 是归一化小写 key（diff.py 的 _norm_key），
    # 这里用新旧点表反查原始大小写 tag，避免把位号改写为小写。
    old_tag_map = {_norm(p.tag): p.tag for p in old_points.points}
    new_tag_map = {_norm(p.tag): p.tag for p in new_points.points}
    changed_tags: List[str] = []
    seen: set = set()
    for e in diff_result.entries:
        key = _tag_from_diff_path(e.path)
        if key:
            tag = new_tag_map.get(key) or old_tag_map.get(key) or key
            if tag not in seen:
                seen.add(tag)
                changed_tags.append(tag)

    # 2) 定位受影响 FB：管脚 source/value 指向变更 tag
    tag_keys = {_norm(t) for t in changed_tags}
    affected: List[str] = []
    fb_seen: set = set()
    for fb in logic_program.fbs:
        for pin in fb.pins:
            if _norm(pin.source) in tag_keys or _norm(pin.value) in tag_keys:
                inst = fb.instance
                if inst and inst not in fb_seen:
                    fb_seen.add(inst)
                    affected.append(inst)
                break  # 该 FB 已判受影响，其余管脚不再扫

    return ChangeReport(
        changed_points=changed_tags,
        affected_fbs=affected,
        entries=diff_result.entries,
    )


# ---------------------------------------------------------------------------
# 2. 受影响组态快速重生成
# ---------------------------------------------------------------------------

@dataclass
class RebuildNote:
    """单个受影响 FB 的组态重建说明。"""
    instance: str = ""                              # 实例名
    ftype: str = ""                                 # 功能块类型
    new_pin_connections: List[str] = field(default_factory=list)  # 新管脚连接清单
    new_params: List[str] = field(default_factory=list)           # 新参数清单
    manual_confirm_lines: List[str] = field(default_factory=list) # 需人工在 FBD 编辑器确认的连线

    def to_text(self) -> str:
        lines = [f"  实例 '{self.instance}'（类型 {self.ftype}）重建说明："]
        lines.append(f"    新管脚连接（{len(self.new_pin_connections)}）：")
        lines.extend(f"      - {c}" for c in self.new_pin_connections)
        lines.append(f"    新参数（{len(self.new_params)}）：")
        lines.extend(f"      - {c}" for c in self.new_params)
        lines.append(f"    需人工确认（{len(self.manual_confirm_lines)}）：")
        lines.extend(f"      - {c}" for c in self.manual_confirm_lines)
        return "\n".join(lines)


@dataclass
class RegenerateResult:
    """受影响组态快速重生成结果。"""
    affected_fbs: List[str] = field(default_factory=list)        # 受影响 FB 实例名清单
    notes: List[RebuildNote] = field(default_factory=list)       # 每个受影响 FB 的重建说明
    diff_text: str = ""                                          # 变更差异说明（文本汇总）

    def to_text(self) -> str:
        lines = [f"受影响功能块（{len(self.affected_fbs)}）：{'、'.join(self.affected_fbs) or '无'}"]
        lines.append("重建说明：")
        lines.extend(n.to_text() for n in self.notes)
        lines.append("变更差异说明：")
        lines.append(self.diff_text)
        return "\n".join(lines)


def regenerate_affected(
    fb_library: Union[str, Path, Dict[str, Any]],
    logic_program: LogicProgram,
    affected_fbs: List[str],
) -> RegenerateResult:
    """受影响组态快速重生成：为受影响 FB 生成"组态重建说明"。

    对受影响实例逐个：
    - 从 logic_program.fbs 取该实例的当前连接（Fb.pins / Fb.params）；
    - 从功能块库取 ftype 定义（pins 模板/params 模板）；
    - 新管脚连接     : 逻辑中已连接的管脚（有 source 或 value）；
    - 新参数         : 逻辑中已设置的参数；
    - 人工确认清单   : 库模板中存在但逻辑未连接的管脚（可能需按现场补齐，
                       尤其是可选 in 管脚与 out 管脚），需人工在 FBD 编辑器确认连线。

    fb_library 可传功能块库 YAML 路径或已加载字典。
    """
    lib = _load_fb_library(fb_library)
    lib_fbs: Dict[str, Any] = lib.get("fbs", {})

    # 实例名 → Fb 对象索引（规范化比较，与模型校验规则一致）
    fb_by_inst: Dict[str, Any] = {}
    for fb in logic_program.fbs:
        fb_by_inst[_norm(fb.instance)] = fb

    notes: List[RebuildNote] = []
    diff_lines: List[str] = []
    for inst in affected_fbs:
        fb = fb_by_inst.get(_norm(inst))
        if fb is None:
            diff_lines.append(f"实例 '{inst}' 不在当前逻辑程序中，请核实")
            continue
        ftype = fb.ftype
        lib_def = lib_fbs.get(ftype, {})
        lib_pins: List[Dict[str, Any]] = lib_def.get("pins", [])
        lib_pin_names = {_norm(p.get("name")) for p in lib_pins}

        # 逻辑中已连接的管脚 → 新管脚连接
        connections = []
        for pin in fb.pins:
            if pin.source:
                connections.append(f"{pin.name} ← {pin.source}")
            elif pin.value is not None:
                connections.append(f"{pin.name} = {pin.value}")

        # 逻辑中已设置的参数 → 新参数
        params = [f"{k} = {v!r}" for k, v in fb.params.items()]

        # 库模板有、逻辑未连接的管脚 → 人工确认清单
        fb_pin_names = {_norm(p.name) for p in fb.pins}
        manual = []
        for p in lib_pins:
            pname = p.get("name")
            if pname is None:
                continue
            if _norm(pname) not in fb_pin_names:
                opt = "可选" if p.get("optional") else "必连"
                manual.append(
                    f"{pname}（{opt}，库定义 {p.get('pin_type')}）：逻辑中未连接，"
                    f"需人工在 FBD 编辑器确认是否补连/补值"
                )

        if not lib_pins:
            manual.append("功能块库对该类型未提供管脚定义（可能待补），连线需人工按现场确认")

        notes.append(RebuildNote(
            instance=inst,
            ftype=ftype,
            new_pin_connections=connections,
            new_params=params,
            manual_confirm_lines=manual,
        ))
        diff_lines.append(f"实例 '{inst}'（{ftype}）：需重新生成 {len(connections)} 个管脚连接、"
                          f"{len(params)} 个参数，{len(manual)} 处需人工确认")

    return RegenerateResult(
        affected_fbs=list(affected_fbs),
        notes=notes,
        diff_text="\n".join(diff_lines) if diff_lines else "无差异",
    )


# ---------------------------------------------------------------------------
# 3. DP 通讯字节序处理工具
# ---------------------------------------------------------------------------

@dataclass
class ByteOrderItem:
    """单个 DP 点的字节序处理说明。"""
    tag: str = ""            # 位号
    device: str = ""         # DP 设备名
    byte_order: str = ""     # low_high / high_low
    advice: str = ""         # 建议处理方式（生成时应用 + 回读校验核对）

    def to_text(self) -> str:
        return f"  {self.tag}（设备 {self.device}，字节序 {self.byte_order}）：\n{self.advice}"


@dataclass
class ByteOrderReport:
    """DP 字节序处理报告。"""
    items: List[ByteOrderItem] = field(default_factory=list)  # 处理清单（有明确字节序的 DP 点）
    warnings: List[str] = field(default_factory=list)          # 警告（DP 点但 byte_order=none）

    def to_text(self) -> str:
        lines = [f"字节序处理清单（{len(self.items)}）："]
        lines.extend(i.to_text() for i in self.items)
        lines.append(f"警告（{len(self.warnings)}）：")
        lines.extend(f"  - {w}" for w in self.warnings)
        return "\n".join(lines)


def _byte_order_advice(byte_order: str) -> str:
    """生成单个 DP 点的处理说明（生成时应用 + 回读校验核对）。

    说明：knowledge 文档仅标注了"高低字节反转是 DP 通讯常见问题"及部分设备
    （HAVER）为 Big-Endian，未给统一处理公式，以下按小端/大端通用常识描述，
    显式标注"推断"，工程上以设备通讯表为准。
    """
    if byte_order == "low_high":
        return (
            "【处理方式】" + LOW_HIGH_LABEL + "。"
            "生成组态（FUN/地址映射）时：32 位数据按 低字在前、高字在后 的顺序排列通道，"
            "或加转换块将两个 WORD 按小端组合成 DINT/REAL 后再进入功能块管脚。"
            "回读校验时：若回读到的是原始 32 位合并值可直接比对；若按通道读到两个 16 位字，"
            "须先按小端重组 value = 低字 + 高字*65536 再与期望工程值比较，否则数值错乱。"
            "（推断，最终以设备通讯表/字节序定义为准）"
        )
    # high_low
    return (
        "【处理方式】" + HIGH_LOW_LABEL + "（知识文档中 HAVER 包装机即 Big-Endian）。"
        "生成组态（FUN/地址映射）时：32 位数据按 高字在前、低字在后 的顺序排列通道，"
        "或加转换块将两个 WORD 按大端组合成 DINT/REAL 后再进入功能块管脚。"
        "回读校验时：若按通道读到两个 16 位字，须先按大端重组 value = 高字*65536 + 低字"
        "再与期望工程值比较，否则高低字颠倒导致数值异常。"
        "（推断，最终以设备通讯表/字节序定义为准）"
    )


def byte_order_fix(points_ir: PointTable) -> ByteOrderReport:
    """DP 通讯字节序处理工具。

    扫描点位表中带 DP 标记（dp 非空）的点：
    - byte_order 为 low_high / high_low 的点 → 进入处理清单，附生成时应用方式
      与回读校验核对方式；
    - byte_order 为 none 但属于 DP 设备（dp 非空）的点 → 进入警告列表，
      提示可能遗漏字节序标记（高低字节反转是 DP 通讯常见问题），需人工确认。
    """
    items: List[ByteOrderItem] = []
    warnings: List[str] = []
    for p in points_ir.points:
        if p.dp is None:
            continue  # 非 DP 点，不涉及字节序
        bo = p.dp.byte_order or "none"
        if bo in ("low_high", "high_low"):
            items.append(ByteOrderItem(
                tag=p.tag,
                device=p.dp.device,
                byte_order=bo,
                advice=_byte_order_advice(bo),
            ))
        elif bo == "none":
            warnings.append(
                f"点 '{p.tag}'（DP 设备 {p.dp.device or '未知'}）未标记字节序"
                f"（byte_order=none）：可能遗漏字节序标记，高低字节反转是 DP 通讯常见问题，"
                f"需人工核对设备通讯表后补标记"
            )
        # byte_order 非法值由 validate_point_table 负责提示，此处不重复
    return ByteOrderReport(items=items, warnings=warnings)
