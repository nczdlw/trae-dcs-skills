# -*- coding: utf-8 -*-
"""仿真调试回环（T8，800xA 先行）。

面向 DCS 调试闭环的仿真能力：
1. probe_simulator_800xa      : 800xA 虚拟控制器探测（OPC UA 接入探测）
2. 调研登记                    : 调研_800xa_virtual_controller / 调研_plcsim / 调研_freelance_sim
   ——真实 800xA 虚拟控制器 / PCS7 PLCSIM / Freelance 模拟器在本环境均不可得，
     登记项全部 status="待核实"，禁止编造接入细节；结论核实后落盘 knowledge 再回填。
3. inject_test_signals         : 强制值下发与测试信号批量注入
4. verify_interlocks           : 连锁逻辑逐条验证
   ——仿真器连接可用 → 实测（注入+回读）；不可用 → 静态推导（按逻辑程序 Fb 连接关系），
     标注"未实测（无仿真器连接）"。

连锁背景（knowledge/90-项目档案/F163_800xA编程规则总纲.md §6.2，只读）：
800xA 连锁类型 STAITL（启动）/OPITL（操作）/PRTITL（保护）/PSTITL（保护性启动）
/PQSTOP（过程快速停止）；PQSTOP 来源 OR：MGB 保护、磨机振动 HH、主电机保护、
磨机风机保护 → 停主电机、风机、喷淋、原料喂料。
连锁图：E12893-1602-9007-00-Interlocking_diagram_VP.pdf。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..ir import LogicProgram, PointTable
from .opcua_channel import OpcUaChannel, OpcUaError, run_sync

# 800xA 连锁类型（knowledge F163_800xA编程规则总纲.md §6.2）
INTERLOCK_TYPES = ("STAITL", "OPITL", "PRTITL", "PSTITL", "PQSTOP")


# ---------------------------------------------------------------------------
# 1. 800xA 虚拟控制器调研与接入
# ---------------------------------------------------------------------------

@dataclass
class ProbeResult:
    """虚拟控制器探测结果。"""
    connected: bool = False
    endpoint_url: str = ""
    server_name: str = ""
    node_count: int = 0         # 可用节点数（根目录直连子节点数，粗糙统计）
    description: str = ""
    error: str = ""

    def to_text(self) -> str:
        if self.connected:
            return (
                f"连接成功 {self.endpoint_url}\n"
                f"  服务器名: {self.server_name or '（未知）'}\n"
                f"  可用节点数（根目录直连子节点）: {self.node_count}\n"
                f"  说明: {self.description}"
            )
        return f"连接失败 {self.endpoint_url}: {self.error}"


def probe_simulator_800xa(endpoint_url: str, timeout: float = 5.0) -> ProbeResult:
    """探测 800xA 虚拟控制器（OPC UA 接入）。

    endpoint_url 形如 'opc.tcp://虚拟控制器IP:4840'。

    流程：
    1. 用独立 OPC UA 临时客户端取服务器端点，读 ApplicationName 作为 server_name
       （临时客户端不影响后续正式连接）；
    2. 用 OpcUaChannel 正式连接，浏览根节点统计可用节点数（根目录直连子节点数）；
    3. 成功返回 connected=True + 说明"800xA 虚拟控制器通过 OPC UA 接入，支持读写/强制"；
       失败返回 connected=False + error，不抛异常。

    注意：连接真实虚拟控制器需要网络可达，本环境无实际控制器，
    此函数是"可运行但预期连不上"的探测工具；
    虚拟控制器软件名/启动方式/端点/强制功能等细节见 调研_800xa_virtual_controller()。
    """
    async def _probe() -> ProbeResult:
        # 1) 取端点服务器名（独立临时客户端；失败不影响后续正式连接判定）
        server_name = ""
        try:
            from asyncua import Client as UaClient

            temp = UaClient(endpoint_url, timeout=timeout)
            try:
                endpoints = await temp.connect_and_get_server_endpoints()
                for ep in endpoints or []:
                    app = getattr(ep, "Server", None)
                    an = getattr(app, "ApplicationName", None)
                    text = getattr(an, "Text", None) or getattr(an, "text", None)
                    if text:
                        server_name = str(text)
                        break
            finally:
                temp.disconnect_socket()
        except Exception:
            # 端点获取失败（网络不可达/不支持 GetEndpoints）→ 服务器名留空，
            # 仍走正式连接判定，由连接的成败决定探测结果
            pass

        # 2) 正式连接
        ch = None
        try:
            ch = OpcUaChannel(endpoint_url, timeout=timeout)
            await ch.connect()
        except OpcUaError as exc:
            return ProbeResult(connected=False, endpoint_url=endpoint_url, error=str(exc))
        except Exception as exc:  # 兜底：任何异常都转成失败结果，不向上抛
            return ProbeResult(connected=False, endpoint_url=endpoint_url, error=str(exc))

        # 3) 浏览根节点统计可用节点数
        node_count = 0
        try:
            nodes = await ch.browse_nodes()
            node_count = len(nodes)
        except OpcUaError:
            node_count = 0
        finally:
            await ch.disconnect()

        return ProbeResult(
            connected=True,
            endpoint_url=endpoint_url,
            server_name=server_name,
            node_count=node_count,
            description="800xA 虚拟控制器通过 OPC UA 接入，支持读写/强制",
        )

    return run_sync(_probe())


def _todo_items(questions: List[str]) -> List[Dict[str, str]]:
    """待核实问题清单登记项：全部 status='待核实'，注明结论落盘 knowledge 后填充。"""
    return [
        {"question": q, "status": "待核实", "note": "结论落盘 knowledge 后填充"}
        for q in questions
    ]


def 调研_800xa_virtual_controller() -> Dict[str, Any]:
    """800xA 虚拟控制器调研登记：返回待核实项清单。

    真实 800xA 虚拟控制器在本环境不可得（未安装/网络不可达），
    以下各项均为待核实问题，禁止凭猜测填充结论；
    核实后结论落盘 knowledge（90-项目档案/F163_800xA编程规则总纲.md 或 DP 设备资料）再回填。
    """
    questions = [
        "虚拟控制器软件名与版本（800xA 6.x 虚拟控制器的准确产品名/组件名）",
        "启动方式（Control Builder 内建离线仿真 / 独立虚拟控制器工具 / 随 800xA 系统服务启动）",
        "OPC UA 端点地址与安全策略（opc.tcp://<IP>:4840；Anonymous / 用户名 / 证书认证）",
        "强制功能支持（Force/Override 是否经 OPC UA 暴露，还是仅 Control Builder 在线操作）",
        "位号到 OPC UA 节点的映射规则（命名空间 ns 与标识符格式）",
        "写权限模型（哪些信号可写、是否需要专用账号/角色）",
    ]
    return {"simulator": "800xA 虚拟控制器", "status": "待核实", "items": _todo_items(questions)}


def 调研_plcsim() -> Dict[str, Any]:
    """PCS7 PLCSIM 模拟器调研登记：返回待核实项清单（结论落盘 knowledge 后填充）。"""
    questions = [
        "S7-PLCSIM 版本与 PCS7 集成方式（V9.x / V16+ 与 PCS7 的配套关系）",
        "启动方式（PCS7 工程组态内建仿真启动 / 独立 S7-PLCSIM 程序加载）",
        "OPC UA 端点地址与安全策略（PLCSIM 对外 OPC UA 服务的端口与认证方式）",
        "强制功能支持（PLCSIM 的强制/调试功能经 OPC UA 可用的程度）",
        "位号到 OPC UA 节点的映射规则（DB/地址 到节点标识符的换算）",
        "写权限模型（哪些信号可写、是否需要专用账号/角色）",
    ]
    return {"simulator": "PCS7 PLCSIM（S7-PLCSIM）", "status": "待核实", "items": _todo_items(questions)}


def 调研_freelance_sim() -> Dict[str, Any]:
    """Freelance 模拟器调研登记：返回待核实项清单（结论落盘 knowledge 后填充）。"""
    questions = [
        "Freelance 软 PLC 模拟器产品名与版本（ABB Freelance 2016+ 的仿真组件）",
        "启动方式（Control Builder F 内建仿真 / 独立模拟器程序）",
        "OPC UA 端点地址与安全策略（Freelance 模拟器对外 OPC UA 服务的端口与认证方式）",
        "强制功能支持（模拟器上强制/修改变量经 OPC UA 可用的程度）",
        "位号到 OPC UA 节点的映射规则（命名空间 ns 与标识符格式）",
        "写权限模型（哪些信号可写、是否需要专用账号/角色）",
    ]
    return {"simulator": "Freelance 模拟器", "status": "待核实", "items": _todo_items(questions)}


# ---------------------------------------------------------------------------
# 2. 强制值下发与测试信号批量注入
# ---------------------------------------------------------------------------

@dataclass
class InjectReport:
    """测试信号注入报告。"""
    total: int = 0
    success: int = 0
    failed: List[str] = field(default_factory=list)                  # 失败 tag 列表（保序）
    failed_errors: Dict[str, str] = field(default_factory=dict)      # tag → 错误说明

    def to_text(self) -> str:
        lines = [f"测试信号注入：总数 {self.total}，成功 {self.success}，失败 {len(self.failed)}"]
        if self.failed:
            lines.append("失败清单：")
            lines.extend(f"  - {t}：{self.failed_errors.get(t, '')}" for t in self.failed)
        return "\n".join(lines)


def inject_test_signals(channel: OpcUaChannel, point_table: PointTable, values: Dict[str, Any]) -> InjectReport:
    """强制值下发与测试信号批量注入。

    channel   : OpcUaChannel 实例（异步 API，本函数用 run_sync 包装执行；
                若调用方已在 asyncio 循环内，请自行 await 内部协程）。
    point_table: IR 点表，提供合法位号集合；values 中不在点表内的 tag 记失败
                （防错写，仍不中断）。
    values    : {tag: value}，逐点 write_value，失败收集进 failed 列表并继续下一点。

    返回 InjectReport：total/success/failed（含错误说明）/to_text()。
    """
    valid_tags = {p.tag for p in point_table.points}

    async def _run() -> InjectReport:
        report = InjectReport(total=len(values))
        for tag, value in values.items():
            if tag not in valid_tags:
                report.failed.append(tag)
                report.failed_errors[tag] = "不在点表内，拒绝注入"
                continue
            try:
                await channel.write_value(tag, value)
                report.success += 1
            except OpcUaError as exc:
                report.failed.append(tag)
                report.failed_errors[tag] = str(exc)
        return report

    return run_sync(_run())


# ---------------------------------------------------------------------------
# 3. 连锁逻辑逐条验证器
# ---------------------------------------------------------------------------

@dataclass
class VerifyItem:
    """单条连锁 × 单组边界信号的验证条目。"""
    interlock_id: str = ""                # 连锁编号
    condition: str = ""                   # 触发条件描述（condition_conditions）
    expected_response: str = ""           # 期望响应描述
    boundary: Dict[str, Any] = field(default_factory=dict)  # 边界信号组合 {tag: value}
    mode: str = ""                        # "实测" / "静态推导" / "无组合"
    actual_response: str = ""             # 实际响应（实测回读快照）或推导响应说明
    status: str = ""                      # pass / fail / 未实测
    note: str = ""                        # 附加说明（如"未实测（无仿真器连接）"）

    def to_text(self) -> str:
        return (
            f"  [{self.mode}] {self.interlock_id} | 条件: {self.condition} | "
            f"组合: {self.boundary} | 响应: {self.actual_response} | 状态: {self.status}"
            + (f" | 注: {self.note}" if self.note else "")
        )


@dataclass
class VerifyReport:
    """连锁验证报告。"""
    items: List[VerifyItem] = field(default_factory=list)
    channel_available: bool = False
    summary: Dict[str, int] = field(default_factory=dict)  # {"pass": n, "fail": n, "未实测": n}

    def to_text(self) -> str:
        """输出"连锁 → 条件 → 实际响应"对照表。"""
        lines = ["连锁 → 条件 → 实际响应 对照表："]
        lines.append(f"  通道可用: {'是（实测模式）' if self.channel_available else '否（静态推导模式）'}")
        lines.extend(i.to_text() for i in self.items)
        s = self.summary
        lines.append(
            f"汇总：实测 {s.get('pass', 0) + s.get('fail', 0)} 条"
            f"（pass {s.get('pass', 0)}，fail {s.get('fail', 0)}），"
            f"未实测（静态推导/无组合）{s.get('未实测', 0)} 条"
        )
        return "\n".join(lines)


def _norm_tag(t: Any) -> str:
    """tag 规范化：去首尾空格、忽略大小写（与模型校验规则一致）。"""
    return str(t or "").strip().lower()


def _derive_response(entry: Dict[str, Any], logic_program: LogicProgram, boundary: Dict[str, Any]) -> str:
    """静态推导：按逻辑程序里引用相关 tag 的 Fb 连接关系，输出推导响应说明。

    不做 FB 真值仿真（本框架无 FB 仿真引擎），只描述数据流：
    边界组合注入 → 命中哪些 Fb 输入管脚 → 哪些输出管脚指向响应目标，
    动作语义（如"停主电机"是否真的停）标注需按连锁图人工核验。
    """
    tags = set(entry.get("tags") or []) | set(boundary.keys())
    norm_tags = {_norm_tag(t) for t in tags if t}
    parts: List[str] = []
    for fb in logic_program.fbs:
        # 输入命中：只统计输入/双向管脚引用相关 tag 的连接（输出管脚单独列出）
        hit_pins = [
            p for p in fb.pins
            if p.direction in ("in", "in_out")
            and (
                (p.source and _norm_tag(p.source) in norm_tags)
                or (p.value and _norm_tag(p.value) in norm_tags)
            )
        ]
        if not hit_pins:
            continue
        outs = [p for p in fb.pins if p.direction == "out"]
        pin_desc = "、".join(f"{p.name} ← {p.source or p.value}" for p in hit_pins)
        out_desc = "、".join(f"{p.name} → {p.source}" for p in outs if p.source) or "（无输出管脚）"
        parts.append(f"{fb.instance}({fb.ftype}) 输入[{pin_desc}] 输出[{out_desc}]")
    if not parts:
        parts.append(f"逻辑程序中未找到引用相关 tag（{sorted(norm_tags)}）的 Fb，需核对连锁表 tags 与逻辑模型对应关系")
    resp = "静态推导（未实测，无仿真器连接）：" + "；".join(parts)
    resp += (
        f"；边界组合 {boundary} 注入后影响上述 Fb 输入管脚，"
        f"期望响应「{entry.get('expected_response') or ''}」的动作语义需按连锁图"
        f"（E12893-1602-9007-00）人工核验"
    )
    return resp


async def _verify_measured(channel: OpcUaChannel, entry: Dict[str, Any], boundary: Dict[str, Any]) -> VerifyItem:
    """实测模式：注入边界组合 → 回读相关 tag → 判定注入回读回环是否通过。

    status 判定：
    - 任一注入失败 → fail；
    - 全部注入成功但任一相关 tag 回读失败（节点不存在等）→ fail；
    - 全部注入+回读成功 → pass（信号级回环通过；动作语义需按连锁图人工核验）。
    """
    eid = entry.get("id", "?")
    cond = entry.get("condition_conditions", "")
    exp = entry.get("expected_response", "")
    tags = [t for t in (entry.get("tags") or []) if t]
    errors: List[str] = []

    # 注入边界组合
    for t, v in boundary.items():
        try:
            await channel.write_value(t, v)
        except OpcUaError as exc:
            errors.append(f"注入 {t}={v!r} 失败：{exc}")

    # 回读相关 tag（tags 为空时回读组合涉及的点）
    read_tags = tags if tags else list(boundary.keys())
    snapshot: Dict[str, Any] = {}
    for t in read_tags:
        try:
            r = await channel.read_value(t)
            snapshot[t] = r.value if r.exists else f"<节点不存在: {r.error}>"
        except OpcUaError as exc:
            snapshot[t] = f"<读失败: {exc}>"

    if errors:
        status = "fail"
        resp = "注入失败：" + "；".join(errors) + f"；回读快照 {snapshot}"
    elif any(isinstance(v, str) and v.startswith("<") for v in snapshot.values()):
        status = "fail"
        resp = f"注入成功但相关 tag 回读异常：回读快照 {snapshot}"
    else:
        status = "pass"
        resp = (
            f"回读快照 {snapshot}；信号级回环验证通过（注入生效），"
            f"期望响应「{exp}」的动作语义需按连锁图（E12893-1602-9007-00）人工核验"
        )
    return VerifyItem(
        interlock_id=eid,
        condition=cond,
        expected_response=exp,
        boundary=dict(boundary),
        mode="实测",
        actual_response=resp,
        status=status,
    )


async def _channel_available(
    channel: OpcUaChannel, interlock_table: List[Dict[str, Any]], probe_fn: Optional[Callable]
) -> bool:
    """判定仿真器通道是否可用。

    - 传了 probe_fn（如 probe_simulator_800xa）→ 以探测结果 connected 为准；
    - 未传 → 试读连锁表第一个 tag，read_value 不抛异常即认为通道可用
      （节点不存在也视为通道本身可用，节点缺失属注入/回读层面的问题）。
    """
    if probe_fn is not None:
        try:
            result = probe_fn(getattr(channel, "url", ""))
            if isinstance(result, ProbeResult):
                return result.connected
            return bool(result)
        except Exception:
            return False
    for entry in interlock_table:
        for t in entry.get("tags") or []:
            if not t:
                continue
            try:
                await channel.read_value(t)
                return True
            except OpcUaError:
                return False
    return False


def verify_interlocks(
    interlock_table: List[Dict[str, Any]],
    logic_program: LogicProgram,
    channel: OpcUaChannel,
    probe_fn: Optional[Callable] = None,
) -> VerifyReport:
    """连锁逻辑逐条验证器。

    interlock_table: 连锁表，list[dict]，每项字段：
        id                 : 连锁编号
        condition_conditions: 触发条件描述
        expected_response  : 期望响应描述
        tags               : 涉及点位 tag 列表
        boundary_cases     : 边界信号组合 list[dict]，每组合 {tag: value}
    logic_program: IR 逻辑程序（LogicProgram，静态推导模式用）
    channel      : OpcUaChannel 实例（异步 API，本函数 run_sync 包装；已在事件循环内请 await 内部协程）
    probe_fn     : 可选探测函数（如 probe_simulator_800xa），返回 ProbeResult/可转 bool；
                   不传则试读首个 tag 判通道可用性。

    模式：
    - channel 可用 → 实测：对每个边界组合逐点注入并回读相关 tag，
      注入+回读全部成功判 pass，否则 fail（仅信号级回环，动作语义需人工核验）；
    - channel 不可用 → 静态推导：按逻辑程序 Fb 连接关系输出推导响应，状态"未实测"，
      标注"未实测（无仿真器连接）"；
    - 连锁表未提供边界组合 → 单条"无组合"条目，状态"未实测"。

    返回 VerifyReport：条目列表 + channel_available + 汇总，
    to_text() 输出"连锁 → 条件 → 实际响应"对照表。
    """
    async def _run() -> VerifyReport:
        available = await _channel_available(channel, interlock_table, probe_fn)
        items: List[VerifyItem] = []
        for entry in interlock_table:
            eid = entry.get("id", "?")
            cond = entry.get("condition_conditions", "")
            exp = entry.get("expected_response", "")
            cases = entry.get("boundary_cases") or []
            if not cases:
                # 连锁表未提供边界组合：无法注入，单条未实测条目
                items.append(VerifyItem(
                    interlock_id=eid,
                    condition=cond,
                    expected_response=exp,
                    boundary={},
                    mode="无组合",
                    actual_response="连锁表未提供边界信号组合，未做注入验证",
                    status="未实测",
                    note="未实测（无边界组合）",
                ))
                continue
            for b in cases:
                if available:
                    items.append(await _verify_measured(channel, entry, b))
                else:
                    items.append(VerifyItem(
                        interlock_id=eid,
                        condition=cond,
                        expected_response=exp,
                        boundary=dict(b),
                        mode="静态推导",
                        actual_response=_derive_response(entry, logic_program, b),
                        status="未实测",
                        note="未实测（无仿真器连接）",
                    ))
        summary = {"pass": 0, "fail": 0, "未实测": 0}
        for it in items:
            if it.status in summary:
                summary[it.status] += 1
        return VerifyReport(items=items, channel_available=available, summary=summary)

    return run_sync(_run())
