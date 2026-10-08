# -*- coding: utf-8 -*-
"""OPC UA 统一调试通道（T6）。

封装 asyncua 客户端，提供：
- 连接、浏览、读、写、订阅、断线重连
- 按 IR 点表批量读写
- 下装后回读校验器（存在性与值域比对）

注意：asyncua 为异步 API，本模块全部用 asyncio 实现；调用方用
run_sync 包装同步执行，或直接 await。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..ir.point_table import PointTable

try:
    from asyncua import Client as UaClient
    from asyncua import ua
except ImportError:  # pragma: no cover
    UaClient = None
    ua = None


class OpcUaError(Exception):
    """OPC UA 操作错误。"""


@dataclass
class ReadResult:
    """单点读取结果。"""
    tag: str = ""
    exists: bool = False       # 变量在服务器中是否存在
    value: Optional[Any] = None
    error: str = ""


@dataclass
class ReadBackReport:
    """下装后回读校验报告。"""
    total: int = 0
    missing: List[str] = field(default_factory=list)   # 不存在
    out_of_range: List[str] = field(default_factory=list)  # 超出量程
    ok: int = 0

    def to_text(self) -> str:
        lines = [f"回读校验：总数 {self.total}，存在且正常 {self.ok}，缺失 {len(self.missing)}，超量程 {len(self.out_of_range)}"]
        if self.missing:
            lines.append("缺失变量：")
            lines.extend(f"  - {t}" for t in self.missing)
        if self.out_of_range:
            lines.append("超量程变量：")
            lines.extend(f"  - {t}" for t in self.out_of_range)
        return "\n".join(lines)


class OpcUaChannel:
    """OPC UA 客户端封装。"""

    def __init__(self, url: str, username: str = "", password: str = "", timeout: float = 5.0):
        if UaClient is None:
            raise OpcUaError("asyncua 未安装，请先 pip install asyncua")
        self.url = url
        self.username = username
        self.password = password
        self.timeout = timeout
        self._client: Optional[UaClient] = None
        self._running = False

    async def connect(self) -> None:
        """连接（含断线重连逻辑：已连接则跳过）。"""
        if self._running and self._client is not None:
            return
        if self._client is None:
            self._client = UaClient(self.url, timeout=self.timeout)
            if self.username:
                self._client.set_user(self.username)
                self._client.set_password(self.password)
        try:
            await self._client.connect()
            self._running = True
        except Exception as exc:
            raise OpcUaError(f"连接失败 {self.url}: {exc}") from exc

    async def disconnect(self) -> None:
        if self._client is not None:
            try:
                await self._client.disconnect()
            finally:
                self._running = False

    async def reconnect(self) -> None:
        """断线重连：先断开再连接。"""
        await self.disconnect()
        await self.connect()

    async def _ensure(self) -> None:
        await self.connect()
        if not self._running:
            await self.reconnect()

    async def browse_nodes(self, node_path: Optional[str] = None) -> List[str]:
        """浏览节点，返回子节点 Id 字符串列表。"""
        await self._ensure()
        root = self._client.nodes.root
        children = await root.get_children()
        return [str(c) for c in children]

    async def read_value(self, node_path: str) -> ReadResult:
        """读取单个节点值。node_path 如 'ns=2;s=xxx' 或对象名路径。"""
        await self._ensure()
        try:
            node = self._client.get_node(node_path)
            val = await node.read_value()
            return ReadResult(tag=node_path, exists=True, value=val)
        except Exception as exc:
            # 不存在 vs 其他错误
            if "BadNodeIdUnknown" in str(exc) or "BadNodeIdInvalid" in str(exc):
                return ReadResult(tag=node_path, exists=False, error=str(exc))
            return ReadResult(tag=node_path, exists=False, error=str(exc))

    async def write_value(self, node_path: str, value: Any) -> bool:
        """写入单个节点值。"""
        await self._ensure()
        try:
            node = self._client.get_node(node_path)
            dv = ua.DataValue(ua.Variant(value))
            await node.set_value(dv)
            return True
        except Exception as exc:
            raise OpcUaError(f"写入失败 {node_path}: {exc}") from exc

    async def subscribe(self, node_paths: List[str], callback: Callable[[str, Any], None]) -> None:
        """订阅节点值变化。callback(tag, value)。"""
        await self._ensure()
        sub = await self._client.create_subscription(100, None)
        for path in node_paths:
            node = self._client.get_node(path)

            async def on_data(d: ua.DataChangeNotification, _node=node, _path=path) -> None:
                callback(_path, d.monitored_item.value.value)

            await sub.subscribe_data_change(node, on_data)

    # ---------- 按 IR 点表批量操作 ----------

    async def read_table(self, table: PointTable) -> Dict[str, ReadResult]:
        """按 IR 点表批量读取。返回 {tag: ReadResult}。"""
        results: Dict[str, ReadResult] = {}
        for p in table.points:
            results[p.tag] = await self.read_value(p.tag)
        return results

    async def write_table(self, table: PointTable, values: Dict[str, Any]) -> List[str]:
        """按 IR 点表批量写入。values: {tag: value}，返回失败列表。"""
        fails: List[str] = []
        for p in table.points:
            if p.tag in values:
                try:
                    await self.write_value(p.tag, values[p.tag])
                except OpcUaError:
                    fails.append(p.tag)
        return fails

    async def readback_check(self, table: PointTable) -> ReadBackReport:
        """下装后回读校验：按 IR 点表回读，比对存在性与值域。

        值域规则：对模拟量（AI/AO）且有量程的点，读回数值超出
        [range_low, range_high]（含小容差）判为超量程。
        """
        report = ReadBackReport(total=len(table.points))
        for p in table.points:
            r = await self.read_value(p.tag)
            if not r.exists:
                report.missing.append(p.tag)
                continue
            if p.signal_type in ("AI", "AO") and p.range_low is not None and p.range_high is not None:
                try:
                    v = float(r.value)
                except (TypeError, ValueError):
                    report.out_of_range.append(f"{p.tag}(非数值:{r.value!r})")
                    continue
                tol = abs(p.range_high - p.range_low) * 0.01
                if v < p.range_low - tol or v > p.range_high + tol:
                    report.out_of_range.append(f"{p.tag}({v})")
                    continue
            report.ok += 1
        return report


def run_sync(coro):
    """同步包装：在事件循环中运行异步协程并返回结果。"""
    try:
        asyncio.get_running_loop()
        raise OpcUaError("已在事件循环中，请直接 await")
    except RuntimeError:
        return asyncio.run(coro)
