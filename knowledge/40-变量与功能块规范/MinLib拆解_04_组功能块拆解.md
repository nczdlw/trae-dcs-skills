---
title: MinLib拆解复用-组功能块GROUP_C与选择器SEL_C拆解
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,GROUP_C,组控,顺序启停,主备,SEL_C,路由,首报]
summary: GROUP_C全解剖（顺序/周期/首报/汇总/viewer）+SEL_C主备路由；保留F163 GROUP1的CON/COFF接口与AUX_RUN派生方式
source: 数据表 p2 GCC清单 + F163规则总纲 §4.6
---

# 04 组功能块拆解（GROUP_C + SEL_C）

> 组是 CC 体系里的"父对象"：所有命令从组出发，所有状态汇回组。
> 除标注【核实】外均为【自拟】；GCC 功能清单依据数据表 p2【核实】。

## 1. 定位

| 项 | 说明 |
|---|---|
| GROUP_C | 一个组=一组按序启停的设备（电机/阀门/子组/回路） |
| 容量 | 16 个设备槽位（ARRAY[1..16]；实际用不满的槽位 Enable=FALSE 即可） |
| 与现场 Group/GROUP1 关系 | GROUP_C 是升级位；**保留 F163 G10 已定的 CON/COFF 单周期脉冲远程启停接口**【F163 §4.6】 |

## 2. 管脚接口

### 2.1 命令组

| 管脚 | 方向 | 类型 | 说明 |
|---|---|---|---|
| CON | in | Bool | 远程组启动（单周期脉冲）【F163 §4.6】 |
| COFF | in | Bool | 远程组停止（单周期脉冲）【F163 §4.6】 |
| Cmd_Start | in | Bool | 操作员面板启动 |
| Cmd_Stop | in | Bool | 操作员面板停止 |
| Cmd_Reset | in | Bool | 组故障复位 |

### 2.2 设备槽位（父→子 命令总线）

| 管脚 | 方向 | 类型 | 说明 |
|---|---|---|---|
| EqCmds | out | ARRAY[1..16] OF CC_EqCmd | 第 i 个槽位连第 i 台设备。字段见 01 文档 §2.1 |

### 2.3 设备槽位（子→父 状态总线）

| 管脚 | 方向 | 类型 | 说明 |
|---|---|---|---|
| EqStats | in | ARRAY[1..16] OF CC_EqStat | 第 i 个槽位收第 i 台设备状态。字段见 01 文档 §2.2 |

### 2.4 组间接口（组也是"子"）

| 管脚 | 方向 | 类型 | 说明 |
|---|---|---|---|
| ParentCmd | in | CC_EqCmd | 上级组给本组的命令（本组作为一台"设备"挂到上级组） |
| GroupStat | out | CC_EqStat | 本组向上级组上报（Run/Ready/Fault/Status/RunTime…） |
| GrpOut | out | CC_Group | 本组向系统/画面汇总（01 文档 §2.5） |

> **多父落地**（数据表 p2 "several parents for one child"【核实】）：设备侧（MOTOR_C/VALVE_C）的父接口是 `EqCmds: ARRAY[1..2]`，[1]=主父、[2]=副父；副父只在主父 Enable=FALSE 时接管命令，否则只读。02/03 文档里的 EqCmd 即 [1] 槽位。典型场景：一台泵同时属"工艺组"（主父，管运行）和"功能组"（副父，如油系统组，只监视）。

## 3. 参数表

| 参数名 | 类型 | 默认值 | 范围/单位 | 在线可改 | 面板显示 | 中文说明 |
|---|---|---|---|---|---|---|
| EnCyclic | Bool | FALSE | — | 是 | 是 | 周期组模式（FALSE=连续） |
| T_CycleRun | Time | T#10min | 1min~24h | 是 | 是 | 周期运行时长 |
| T_CycleIdle | Time | T#10min | 1min~24h | 是 | 是 | 周期间歇时长 |
| T_StepMax | Time | T#30s | 0~300s | 是 | 是 | 步超时：本步设备启动/停止确认上限（0=无限等） |
| EnGrpHold | Bool | TRUE | — | 是 | 是 | 步失败时是否保持组（TRUE=停后续步，FALSE=跳过继续） |
| T_GrpFltAck | Time | T#0s | 0~60s | 是 | 是 | 组故障自动复位延时（0=必须人工） |
| EnSim | Bool | FALSE | — | 是 | 是 | 组仿真（下传到所有 Enable 设备） |
| Desc_EN/Desc_CN/TagNo | String | — | — | 否 | 是 | 组描述与 tag |

每台设备的 StepNo/DelayStart/DelayStop/EnStandby **统一配在组的参数数组上**（StepNoTab/DelayStartTab/DelayStopTab/EnStandbyTab，§3），组每周期通过 EqCmds[i] 下发给设备——顺序数据唯一来源在组，viewer 也读同一张表，"改组参数=改顺序、下装即生效"（代码零改动）【参照数据表 p2】。设备侧不各自存 StepNo，避免两处不一致。

## 4. 内部逻辑分段（S01~S08）

| 段 | 名称 | 干什么 |
|---|---|---|
| S01 | 输入与模式判定 | 组状态机：STOP/STARTING/RUN/STOPPING/FAULT；ParentCmd 作为最高优先命令源 |
| S02 | 命令仲裁 | CON/COFF（F163 §4.6 单周期脉冲）> ParentCmd > 操作员 Cmd |
| S03 | 设备使能计算 | 扫描 16 槽位：EqStats[i] 有效且该设备 StepNo>0 → 参与本组；无效槽 Enable=FALSE |
| S04 | 启动步进 | 按 StepNo 升序：DelayStart 到→该槽 EqCmds[i].Start=TRUE→等 EqStats[i].Run 或 T_StepMax→下一步 |
| S05 | 停止步进 | 按 StepNoStop 降序（0 时按 StepNo 降序）：DelayStop 到→Stop=TRUE→等 Run=FALSE→下一步 |
| S06 | 周期控制 | EnCyclic：RUN 保持 T_CycleRun→停→STOP 保持 T_CycleIdle→自动重启（数据表 p2 cyclic processes） |
| S07 | 首报与汇总 | 第一个 FirstFault=TRUE 的设备：锁存 FirstFaultTag/SigTag；按 EnGrpHold 决定保持或跳过；汇总 EquipRun/Total（§5） |
| S08 | 上报与诊断填充 | 填 GroupStat/GrpOut；填组 viewer 数据源 |

## 5. 状态汇总与 AUX_RUN 派生（对齐 F163 §4.6）

组状态直接从子设备/子组的 EqStat 派生，**不重复计算子组内部条件**【F163 §4.6】：

```
GroupRun   := (EquipRun = EquipActive) AND (EquipActive > 0)
GroupReady := AND over active slots: EqStats[i].Ready
GroupFault := OR over active slots: EqStats[i].Fault
EquipRun   := count of (EqStats[i].Enable AND EqStats[i].Run)
EquipActive:= count of EqStats[i].Enable
```

F163 G10 的 AUX_RUN 公式 `AUX_RUN = G30_RUN AND G50_RUN AND G40_ENABLED AND G55_RUN`【F163 §4.6，主辅机组单级 STEP=1】在 CL 库里的等价写法：G10 组的 4 个槽位 StepNo 全配 1（单级同时启），槽位分别连 G30/G50/G40/G55 子组的 GroupStat.Run，`GroupRun = 4 个全 Run`——公式不变，连线从"散读 GROUP_STATUS"变成"CC 总线"。

## 6. 首报检测（first fault detection）【核实功能，数据表 p2；自拟实现】

1. 启动过程中任一设备 T_StepMax 超时未 Run → 该设备 FirstFault 候选；运行中任一设备 Fault → FirstFault 候选；
2. 组对候选按 StepNo 取最靠前的一个锁存：`FirstFaultTag`、`FirstFaultStep`、发生时刻；
3. 锁存后：EnGrpHold=TRUE → 组停后续步并进 FAULT；FALSE → 记录后继续；
4. FirstFaultTag 显示在组面板，**带超链接跳到该设备面板**，设备面板再显示 SigTag 跳到联锁信号——两级导航直达根因【数据表 p2/p4】；
5. Cmd_Reset 或 T_GrpFltAck 到清除锁存。

## 7. 组状态 Viewer（数据表 p2 的 viewer 功能【核实】）

一个 Workplace 显示对象（不是 FBD，是 800xA 的 Plant Explorer 显示/Aspect 模板），数据源=本组 GrpOut + 16 槽位：

| 列 | 内容 |
|---|---|
| 步号 | StepNo / StepNoStop |
| 设备 | TagNo + Desc_CN（**点击跳设备面板**） |
| 状态 | 七态符号（三重编码） |
| 联锁 | 当前联锁态（无/警告/故障/override 中） |
| 延时 | DelayStart/DelayStop 实际值 |
| 仿真 | EnSim 指示 |
| 调试 | ChkPass 指示 |

 viewer 每次下装自动刷新——"运行时可增删改启停顺序"的落地：改设备 StepNo 参数→下装→viewer 顺序即变，代码零改动【数据表 p2】。

## 8. SEL_C 选择器（主备 + 路由）【数据表 p2 selector【核实】；自拟实现】

### 8.1 用途

- **主备（duty/standby）**：两台同职责设备（润滑泵 A/B、风机 A/B），一台运行一台备用，故障/磨损失效自动切换；
- **路由（routing）**：多路阀/挡板群按 PathNo 选择通路（如入库/入摩、布料器）。

### 8.2 管脚

| 管脚 | 方向 | 类型 | 说明 |
|---|---|---|---|
| EqStats | in | ARRAY[1..4] OF CC_EqStat | 候选设备状态（主备用 2，路由用 4） |
| Cmd | in | CC_EqCmd | 上游命令（来自组或操作员） |
| OutCmds | out | ARRAY[1..4] OF CC_EqCmd | 分发后的命令（只给选中的设备 Enable+Start） |
| Cmd_Sel | in | Int | 手动指定选择（0=自动） |
| Cmd_Swap | in | Bool | 手动切换主备（脉冲） |

### 8.3 参数

| 参数名 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| Mode | Int | 0 | 0=主备 1=路由 |
| Policy | Int | 0 | 主备策略：0=故障切换 1=时长均衡 2=仅手动 |
| T_SwapDb | Time | T#5s | 切换间隔保护（防频繁切换） |
| PathNo | Int | 0 | 路由号（1..4） |
| T_BalanceDiff | Time | T#1h | 时长均衡切换门限（运行时长差超此值才均衡） |

### 8.4 逻辑要点

- 故障切换：当前主设备 Fault 且备用 Ready → T_SwapDb 后切到备用；旧主 FirstFault 已由设备自己锁存；
- 时长均衡：比较两台 RunTime（MOTOR_C S09 上报的），差超 T_BalanceDiff 且都在允许切换窗口 → 切换；
- 被选中的设备：OutCmds[i]=Cmd；**未选中的设备 OutCmds[i].EnStandby=TRUE**——它的报警自动降级【数据表 p5】；
- 路由：PathNo 选中哪路，哪路 Enable；其余全 EnStandby。

## 9. 组面板 FP_Group（详见 05 文档）

必备区：①组状态符号+启停/复位按钮②FirstFaultTag **大字 + 超链接**③模式/周期参数④设备清单缩略（点击跳 viewer/设备面板）⑤组内设备汇总计数（Run/Total）⑥仿真指示。

## 10. 调试检查项

| # | 检查项 | 通过判据 |
|---|---|---|
| C1 | CON/COFF | 脉冲启停整组，顺序正确 |
| C2 | 顺序 | 各设备 StepNo 顺序启动，步间 DelayStart 生效 |
| C3 | 停止反序 | 停止按 StepNoStop 反序 |
| C4 | 步超时 | T_StepMax 设 2s，某设备不给反馈，T_StepMax 后按 EnGrpHold 行为 |
| C5 | 首报 | 制造第 3 步设备故障，组面板 FirstFaultTag=该设备且超链接可达 |
| C6 | 周期 | EnCyclic，T_CycleRun/Idle 各设 30s，循环正确 |
| C7 | 多父 | 副父场景：主父断开时副父能命令 |
| C8 | 汇总 | GroupRun/Ready/Fault 与设备实际一致 |
| C9 | 主备 | SEL_C 故障切换+时长均衡各演练一次 |
| C10 | 路由 | PathNo 1..4 逐一验证 |

## 11. 与现场 Group/GROUP1 的差异

| 项 | Group/GROUP1 | GROUP_C |
|---|---|---|
| 远程接口 | CON/COFF 单周期脉冲【F163 §4.6】 | **同名保留** |
| 设备连接 | G_start/G_stop Boolean16 按序对应【F163 §4.6】 | CC_EqCmd 数组（步号参数化） |
| 顺序调整 | 改代码/改位序 | 改 StepNo 参数 |
| 首报/viewer/主备/周期 | 无/无/无/无 | 内建 |
| 子组派生 | 直读子组 GROUP_STATUS【F163 §4.6】 | GroupStat 总线（同样不重算内部条件） |

## 12. 本篇结论

GROUP_C 记住四个数：**16 个槽位、两个步号参数（StepNo/StepNoStop）、两个周期参数（T_CycleRun/Idle）、一个首报锁存（FirstFaultTag）**。组的全部智能在"按步号排队、按状态推进、按首报停机"这三件事上，其余都是参数。ST 骨架见 08 文档 §3。
