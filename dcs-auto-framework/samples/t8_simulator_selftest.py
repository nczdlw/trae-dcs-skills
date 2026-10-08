# -*- coding: utf-8 -*-
"""T8 自测：仿真调试回环（simulator.py）完整闭环验证。

场景 A：probe_simulator_800xa 连接失败路径（无控制器 → connected=False 不崩溃）。
场景 B：调研登记（调研_800xa_virtual_controller / 调研_plcsim / 调研_freelance_sim，
        全部条目 status="待核实"）。
场景 C：本地 asyncua 模拟服务器（T6 模式：asyncua Server 跑在独立线程事件循环，
        asyncua 2.x 无 AllowAll，默认 PermissiveUserManager 行为即"允许所有连接"，
        写操作需 admin 账号，allow_remote_admin 默认开启）
        → probe 成功路径 + inject_test_signals 真实注入（写成功/拒绝/写失败三种）。
场景 D：verify_interlocks 两条连锁：
        ITL-001 润滑压力低 → 停主电机（channel 可用 → 实测 pass）；
        ITL-002 磨机振动 HH → PQSTOP（channel 不可用 → 静态推导"未实测"）；
        输出对照表含"实测/未实测"标注。
运行：python3 samples/t8_simulator_selftest.py（从框架根目录或任意目录均可）。
"""

import asyncio
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from asyncua import Server as UaServer  # noqa: E402

from dcsaf.ir import LogicProgram, Point, PointTable, Fb, Pin  # noqa: E402
from dcsaf.tools.opcua_channel import OpcUaChannel, run_sync  # noqa: E402
from dcsaf.tools.simulator import (  # noqa: E402
    InjectReport,
    ProbeResult,
    VerifyReport,
    inject_test_signals,
    probe_simulator_800xa,
    verify_interlocks,
    调研_800xa_virtual_controller,
    调研_freelance_sim,
    调研_plcsim,
)

# 本地模拟服务器端点（固定端口，脚本结束后 stop）
SIM_URL = "opc.tcp://127.0.0.1:48410/freeopcua/server"
SIM_NAME = "T8_Sim_Server"
# 模拟服务器上真实存在的节点（tag 用完整 OPC UA 节点路径）
SIM_TAGS: List[Tuple[str, Any]] = [
    ("ns=2;s=N562_LQ01_PRESS", 1.5),   # 齿轮箱润滑压力（Real）
    ("ns=2;s=N562_M1_RUN", False),     # 磨机主电机运行反馈（Bool）
    ("ns=2;s=N562_M1_START", False),   # 磨机主电机启动命令（Bool）
    ("ns=2;s=N562_RM01_VIB", 12.0),    # 磨机振动值（Real）
]


class SimServerThread:
    """本地 asyncua 模拟服务器：跑在独立线程事件循环，主线程无事件循环可用同步 API。"""

    def __init__(self, url: str, name: str, tags: List[Tuple[str, Any]]):
        self.url = url
        self.name = name
        self.tags = tags
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._server = None

    def start(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        # 阻塞等待 setup 完成（失败会在此处抛错）
        asyncio.run_coroutine_threadsafe(self._setup(), self._loop).result(timeout=20)

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _setup(self) -> None:
        self._server = UaServer()
        await self._server.init()
        self._server.set_endpoint(self.url)
        self._server.set_server_name(self.name)
        idx = await self._server.register_namespace("urn:t8:sim")
        objects = self._server.get_objects_node()
        for tag, val in self.tags:
            v = await objects.add_variable(f"ns={idx};s={tag.split(';s=')[1]}", tag.split(';s=')[1], val)
            await v.set_writable()
        await self._server.start()

    def stop(self) -> None:
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop).result(timeout=20)
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=20)

    async def _shutdown(self) -> None:
        if self._server is not None:
            await self._server.stop()


def build_point_table() -> PointTable:
    """T8 自测点表：模拟服务器上 4 个点 + 1 个"点表有、服务器无"的点（M2_RUN）。"""
    return PointTable(
        name="T8_SIM",
        points=[
            Point(tag="ns=2;s=N562_LQ01_PRESS", description="齿轮箱润滑压力", signal_type="AI",
                  range_low=0.0, range_high=10.0, unit="bar"),
            Point(tag="ns=2;s=N562_M1_RUN", description="磨机主电机运行反馈", signal_type="DI"),
            Point(tag="ns=2;s=N562_M1_START", description="磨机主电机启动命令", signal_type="DO"),
            Point(tag="ns=2;s=N562_RM01_VIB", description="磨机振动值", signal_type="AI",
                  range_low=0.0, range_high=50.0, unit="mm/s"),
            Point(tag="ns=2;s=N562_M2_RUN", description="（模拟服务器上不存在的点，测写失败）", signal_type="DI"),
        ],
    )


def build_logic_program() -> LogicProgram:
    """示例逻辑：MOTOR1 主电机控制 + SignalInReal 振动监测（静态推导模式用）。"""
    return LogicProgram(
        name="T8_LOGIC",
        fbs=[
            Fb(
                ftype="MOTOR1",
                instance="MOTOR1_1",
                comment="磨机主电机启停控制（润滑压力低 → 停主电机）",
                pins=[
                    Pin(name="Running", pin_type="bool", direction="in", source="ns=2;s=N562_M1_RUN"),
                    Pin(name="start_lock", pin_type="bool", direction="in", source="ns=2;s=N562_LQ01_PRESS"),
                    Pin(name="Drive", pin_type="bool", direction="out", source="ns=2;s=N562_M1_START"),
                ],
            ),
            Fb(
                ftype="SignalInReal",
                instance="SI_VIB",
                comment="磨机振动监测（HH → PQSTOP）",
                pins=[
                    Pin(name="In", pin_type="RealIO", direction="in_out", source="ns=2;s=N562_RM01_VIB"),
                    Pin(name="Name", pin_type="string", direction="in", value="VIB"),
                ],
            ),
        ],
    )


def build_interlock_table() -> List[Dict[str, Any]]:
    """T8 自测连锁表：ITL-001 润滑压力低 → 停主电机；ITL-002 磨机振动 HH → PQSTOP。"""
    return [
        {
            "id": "ITL-001",
            "condition_conditions": "润滑压力低 → 停主电机（STAITL 类连锁）",
            "expected_response": "主电机停止（M1_START 置 FALSE）",
            "tags": ["ns=2;s=N562_LQ01_PRESS", "ns=2;s=N562_M1_RUN", "ns=2;s=N562_M1_START"],
            "boundary_cases": [
                {"ns=2;s=N562_LQ01_PRESS": 0.5, "ns=2;s=N562_M1_RUN": True},
            ],
        },
        {
            "id": "ITL-002",
            "condition_conditions": "磨机振动 HH → PQSTOP",
            "expected_response": "过程快速停止（停主电机/风机/喷淋/原料喂料）",
            "tags": ["ns=2;s=N562_RM01_VIB", "ns=2;s=N562_M1_START"],
            "boundary_cases": [
                {"ns=2;s=N562_RM01_VIB": 46.0},
            ],
        },
    ]


def test_scene_a() -> None:
    """场景 A：probe 连接失败路径（无控制器 → connected=False 不崩溃）。"""
    print("[1] 场景 A：probe_simulator_800xa 连接失败路径")
    result = probe_simulator_800xa("opc.tcp://127.0.0.1:9/no_server", timeout=2.0)
    assert isinstance(result, ProbeResult), type(result)
    assert result.connected is False, result
    assert result.error, result
    print("  " + result.to_text().replace("\n", "\n  "))
    print("  ✓ 断言通过（无控制器返回 connected=False 且不抛异常）")


def test_scene_b() -> None:
    """场景 B：调研登记全部条目 status='待核实'。"""
    print("[2] 场景 B：调研登记（800xA 虚拟控制器 / PCS7 PLCSIM / Freelance 模拟器）")
    for func in (调研_800xa_virtual_controller, 调研_plcsim, 调研_freelance_sim):
        reg = func()
        items = reg["items"]
        assert reg["status"] == "待核实", reg
        assert items, reg
        for it in items:
            assert it["status"] == "待核实", it
            assert "结论落盘 knowledge 后填充" in it["note"], it
        print(f"  {reg['simulator']}：{len(items)} 项待核实")
        for it in items:
            print(f"    - [{it['status']}] {it['question']}")
    print("  ✓ 断言通过（全部条目 status='待核实'，未编造接入细节）")


def test_scene_c(server: SimServerThread) -> None:
    """场景 C：probe 成功路径 + inject_test_signals 真实注入。"""
    print("[3] 场景 C：本地模拟服务器 probe 成功 + 测试信号批量注入")

    # 3a) probe 成功路径：服务器名从端点 ApplicationName 读取
    probe_ok = probe_simulator_800xa(SIM_URL, timeout=3.0)
    assert probe_ok.connected, probe_ok
    assert probe_ok.server_name == SIM_NAME, probe_ok
    assert probe_ok.node_count >= 3, probe_ok  # 根目录直连子节点（Objects/Types/Views 等）
    assert "支持读写/强制" in probe_ok.description, probe_ok
    print("  probe 成功路径：")
    print("  " + probe_ok.to_text().replace("\n", "\n  "))

    # 3b) 真实注入：admin 账号（asyncua 2.x 默认 PermissiveUserManager，写需 Admin 角色）
    ch = OpcUaChannel(SIM_URL, username="admin", password="", timeout=3.0)
    pt = build_point_table()
    report = inject_test_signals(ch, pt, {
        "ns=2;s=N562_M1_RUN": True,          # 模拟服务器上有 → 写成功
        "ns=2;s=N562_LQ01_PRESS": 3.2,       # 模拟服务器上有 → 写成功
        "ns=2;s=N562_M2_RUN": True,          # 点表有、服务器无 → 写失败（BadNodeIdUnknown）
        "ns=2;s=N562_NOT_IN_TABLE": 1.0,     # 不在点表 → 拒绝
    })
    assert isinstance(report, InjectReport), type(report)
    assert report.total == 4, report
    assert report.success == 2, report
    assert len(report.failed) == 2, report
    assert "ns=2;s=N562_M2_RUN" in report.failed and "ns=2;s=N562_NOT_IN_TABLE" in report.failed, report
    print("  " + report.to_text().replace("\n", "\n  "))

    # 3c) 回读验证写入生效。
    # 注意：OpcUaChannel 实例绑定创建它的 asyncio 事件循环，跨 run_sync 复用
    # 会失败（旧循环 transport 在新循环中报错），因此每个读操作用独立实例。
    r1 = run_sync(OpcUaChannel(SIM_URL, username="admin", password="", timeout=3.0).read_value("ns=2;s=N562_M1_RUN"))
    assert r1.exists and r1.value is True, r1
    r2 = run_sync(OpcUaChannel(SIM_URL, username="admin", password="", timeout=3.0).read_value("ns=2;s=N562_LQ01_PRESS"))
    assert r2.exists and abs(r2.value - 3.2) < 1e-9, r2
    print("  回读验证：M1_RUN=%(run)s，LQ01_PRESS=%(press)s" % {"run": r1.value, "press": r2.value})
    print("  ✓ 断言通过（2 个点写成功，点表外拒绝、服务器缺失写失败均收集不中断）")


def test_scene_d_measured() -> VerifyReport:
    """场景 D1：channel 可用 → 两条连锁实测（注入+回读）。"""
    print("[4] 场景 D：verify_interlocks（实测 / 静态推导对照）")
    ch = OpcUaChannel(SIM_URL, username="admin", password="", timeout=3.0)
    report = verify_interlocks(build_interlock_table(), build_logic_program(), ch)
    assert isinstance(report, VerifyReport), type(report)
    assert report.channel_available is True, report
    assert len(report.items) == 2, report
    for it in report.items:
        assert it.mode == "实测", it
        assert it.status == "pass", it
        assert "信号级回环验证通过" in it.actual_response, it
    assert report.summary.get("pass") == 2, report.summary
    print("  —— 实测模式（channel 可用）对照表 ——")
    print(report.to_text().replace("\n", "\n  "))
    return report


def test_scene_d_derived() -> VerifyReport:
    """场景 D2：channel 不可用 → 两条连锁静态推导（标注"未实测"）。"""
    ch_bad = OpcUaChannel("opc.tcp://127.0.0.1:9/no_server", timeout=2.0)
    report = verify_interlocks(build_interlock_table(), build_logic_program(), ch_bad)
    assert isinstance(report, VerifyReport), type(report)
    assert report.channel_available is False, report
    assert len(report.items) == 2, report
    for it in report.items:
        assert it.mode == "静态推导", it
        assert it.status == "未实测", it
        assert "未实测（无仿真器连接）" in it.note, it
        assert "静态推导" in it.actual_response, it
    assert report.summary.get("未实测") == 2, report.summary
    print("  —— 静态推导模式（channel 不可用）对照表 ——")
    print(report.to_text().replace("\n", "\n  "))
    return report


def main() -> None:
    print("===== T8 仿真调试回环 自测 =====")
    test_scene_a()
    test_scene_b()

    server = SimServerThread(SIM_URL, SIM_NAME, SIM_TAGS)
    server.start()
    try:
        test_scene_c(server)
        rep_measured = test_scene_d_measured()
        rep_derived = test_scene_d_derived()
    finally:
        server.stop()

    # 合并对照表文本，确认同时含"实测"与"未实测"标注
    merged_text = rep_measured.to_text() + "\n" + rep_derived.to_text()
    assert "实测" in merged_text and "未实测" in merged_text, merged_text
    print("  ✓ 断言通过（对照表含 实测/未实测 两种标注，pass/未实测 汇总正确）")
    print("===== 结论 =====")
    print("T8 自测通过")


if __name__ == "__main__":
    main()
