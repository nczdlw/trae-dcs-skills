---
title: GROUP远程命令接口修改说明
date: 2026-07-25
project: F163
type: 实施说明
device: G10
tags: [G10,GROUP,接口]
summary: GROUP远程命令接口的修改说明
source: outputs\f163_loesche_programming\02_G10组程序\GROUP_远程命令接口修改说明.md
---

# GROUP1 功能块最小接口扩展

## 结论

项目通用 `Group` 类型保持不修改。以其为基础复制出莱歇磨专用 `GROUP1`，并在 `GROUP1` 中增加 `CON`、`COFF` 输入。G10 要向 G20、G30、G40、G50、G55、G60 广播启停命令，必须使用 `GROUP1`。

ABB 功能块的内部变量不能从外部程序直接写入，因此不要尝试使用 `G20.Gstart_cmd`、`G20.Gstop_cmd` 之类的写法。

## 参数表新增

在 `GROUP1` 类型参数最后追加：

| Name | Data type | Direction | Initial value | Description |
|---|---|---|---|---|
| CON | bool | in | false | Remote group ON command, one-cycle pulse |
| COFF | bool | in | false | Remote group OFF command, one-cycle pulse |

保留原有 `Group` 类型、其参数和所有既有项目实例不变。莱歇磨的 G10、G20、G30、G40、G50、G55、G60 实例改为 `GROUP1` 类型。

## FBD 修改位置

依据 `DP设备资料\莱歇磨 - trae\GROUP\GROUP_CODE.pdf` 第 1 页，在 `GROUP1` 的 FBD 中修改：

1. `CON` 与原有本地启动命令做“或”，再进入启动许可与 `RS_1.Set` 路径。
2. `COFF` 加入停止命令汇总“或”逻辑，使其同时：
   - 复位 `RS_1` 的组启动状态；
   - 置位 `RS_2` 的停止顺控状态。
3. `CON`、`COFF` 均由 G10ST 生成一个任务周期的脉冲；在每个子组的 FBD 中，把这两个变量直接连至对应 `GROUP1` 实例的新引脚。功能块内部不需要再增加沿检测。
4. 急停、`Gfault`、`stop_step`、启动锁、停止锁等原逻辑保持不变。

## 子组 FBD 连接

G20、G30、G40、G50、G55、G60 的 `GROUP1` **FBD 实例**统一增加以下两根输入线：

```text
CON := G10_CON_PULSE,
COFF := G10_COFF_PULSE,
```

这不是 ST 调用修改。应在 Control Builder 中逐一打开六个子组的 FBD，显示 `GROUP1.CON`、`GROUP1.COFF` 管脚，并从同一程序作用域的 `G10_CON_PULSE`、`G10_COFF_PULSE` 变量连线到这两个管脚。

## 验证

完成类型修改后，必须执行：

1. 确认项目通用 `Group` 没有任何修改；
2. 确认莱歇磨的 G10、G20、G30、G40、G50、G55、G60 均为 `GROUP1` 类型；
3. 对库/应用做一次完整 Check；
4. 确认六个子组调用都显示 `CON`、`COFF`；
5. 在线强制仅允许在仿真或无负载条件下进行；
6. 验证 G10 开命令只产生一个周期的 `G10_CON_PULSE`；
7. 验证 G10 关命令只产生一个周期的 `G10_COFF_PULSE`；
8. 验证子组仍可通过各自 HMI 本地远程按钮独立启停。
