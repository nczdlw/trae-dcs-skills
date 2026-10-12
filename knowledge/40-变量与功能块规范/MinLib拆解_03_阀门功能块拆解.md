---
title: MinLib拆解复用-阀门功能块VALVE_C拆解
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,VALVE_C,阀门,开关阀,调节阀,状态机,联锁,报警,仿真]
summary: VALVE_C全解剖：开关阀/调节阀双模式、七状态机、双命令互锁、行程超时、阀位偏差、10条报警、面板与调试检查
source: 数据表 p2/p4/p5 + F163规则总纲 §4.3
---

# 03 阀门功能块 VALVE_C 拆解

> 阀门块比电机块多两层难度：**双命令互锁**（开/关输出严禁同时带电）和**阀位闭环**（调节阀）。
> 除标注【核实】外均为【自拟】。

## 1. 定位与双模式

| 模式 | 参数 | 适用 | 反馈 |
|---|---|---|---|
| 开关阀 | EnLoop=FALSE | 两位式气动阀/电动阀（挡板、闸板、排污阀） | DI_OpenFb / DI_CloseFb 到位行程开关 |
| 调节阀 | EnLoop=TRUE | 阀门定位器+AO（喂料、风量调节） | AI_Pos 阀位反馈（0~100%） |

一个块两种模式，切换只改参数；工程里给每个实例配 EnLoop，不复制代码。

## 2. 管脚接口全表

### 2.1 硬件 IO 组

| 管脚 | 方向 | 类型 | 说明 |
|---|---|---|---|
| DI_OpenFb | in | DintIO/Bool | 开到位反馈 |
| DI_CloseFb | in | DintIO/Bool | 关到位反馈 |
| DI_Fault | in | DintIO/Bool | 阀门故障（限位故障/气源失压） |
| DO_Open | out | DintIO/Bool | 开命令输出 |
| DO_Close | out | DintIO/Bool | 关命令输出 |
| AO_Out | out | RealIO | 调节阀开度命令（0~100，仅 EnLoop） |
| AI_Pos | in | RealIO | 阀位反馈（0~100，仅 EnLoop） |

### 2.2 命令组

| 管脚 | 方向 | 类型 | 说明 |
|---|---|---|---|
| Cmd_Open | in | Bool | 开命令（脉冲） |
| Cmd_Close | in | Bool | 关命令（脉冲） |
| Cmd_Stop | in | Bool | 停止/中停命令（切断输出，仅 EnMid=TRUE 有效） |
| Cmd_Pos | in | Real | 目标阀位（0~100，EnLoop 时由 PID/组给定） |
| Cmd_Reset | in | Bool | 故障复位 |
| Cmd_Maint | in | Bool | 检修挂牌 |

### 2.3 联锁组（同 MOTOR_C 语义：true=锁定）

Lock_Start / Lock_Process / Lock_Safety / O2_Perm，含义与 02 文档 §2.3 一致：启动禁止/过程跳停/安全跳停（经延时置故障）/输出允许。

### 2.4 组接口组 / 2.5 信号接口组

与 MOTOR_C 相同：EqCmd/CC 结构体 + Grp + Sig 数组 + SigIn 回读（01 文档 §2）。

## 3. 参数表

| 参数名 | 类型 | 默认值 | 范围/单位 | 在线可改 | 面板显示 | 中文说明 |
|---|---|---|---|---|---|---|
| T_OpenMax | Time | T#10s | 1~120s | 是 | 是 | 开行程超时（全开耗时，含余量） |
| T_CloseMax | Time | T#10s | 1~120s | 是 | 是 | 关行程超时 |
| T_FltDb | Time | T#500ms | 0~5s | 是 | 是 | 故障去抖 |
| T_FbDb | Time | T#100ms | 0~2s | 是 | 是 | 到位反馈去抖 |
| T_SafetyDb | Time | T#1s | 0~10s | 是 | 是 | 安全联锁确认延时 |
| EnLoop | Bool | FALSE | — | 否 | 是 | 调节阀模式 |
| EnMid | Bool | FALSE | — | 否 | 是 | 允许中停（三点控制） |
| EnPulse | Bool | FALSE | — | 否 | 是 | 脉冲输出模式（输出脉宽 T_Pulse 后自断） |
| T_Pulse | Time | T#2s | 0.5~10s | 是 | 是 | 输出脉冲宽度 |
| DeadBand | Real | 2.0 | 0~10 % | 是 | 是 | 阀位控制死区（\|Cmd_Pos−AI_Pos\|≤此值不动作） |
| T_DevMax | Time | T#30s | 5~300s | 是 | 是 | 阀位偏差超时（超差报警） |
| EnSim | Bool | FALSE | — | 是 | 是 | 仿真开关 |
| Sim_OpenFb | Bool | FALSE | — | 是 | 是 | 仿真开到位 |
| Sim_CloseFb | Bool | TRUE | — | 是 | 是 | 仿真关到位 |
| Sim_Pos | Real | 0.0 | 0~100 % | 是 | 是 | 仿真阀位 |
| StepNo | Int | 0 | 0~99 | 是 | 是 | 组内启动步号——数据源在组 StepNoTab 数组，经 EqCmd 下发，本参数只读显示（04 文档 §3） |
| StepNoStop | Int | 0 | 0~99 | 是 | 是 | 组内停止步号——源在组 StepNoStopTab |
| Desc_EN/Desc_CN/TagNo | String | — | — | 否 | 是 | 描述与 tag |

## 4. 内部逻辑分段（S01~S09）

| 段 | 名称 | 干什么 | 实现 |
|---|---|---|---|
| S01 | 输入采集与去抖 | DI_OpenFb/DI_CloseFb/DI_Fault 去抖 | FBD：TDeb |
| S02 | 仿真注入 | EnSim 替换反馈/阀位 | ST |
| S03 | 模式判定 | LOCAL/MAINT/LOOP | ST |
| S04 | 联锁汇总 | 同 02 文档 S04 | ST/FBD |
| S05 | 命令仲裁 | 组命令/操作员/PID 优先级 | ST |
| S06 | 状态机 | 见 §5 | ST（CASE） |
| S07 | 输出驱动 | 开/关/AO，**含双命令互锁**，见 §6 | ST |
| S08 | 报警生成 | 见 §7 | FBD：AlarmCond |
| S09 | 统计与上报 | EqStat/开度统计 | ST |

## 5. 状态机（七状态）

| 状态 | 进入条件 | 输出 |
|---|---|---|
| CLOSED | 上电/关到位 | DO_Open=FALSE, DO_Close=FALSE, AO=0 |
| OPENING | CLOSED 收到开命令且允许 | DO_Open=TRUE（或脉冲） |
| OPEN | 开到位确认 | 输出保持（调节阀：AO=Cmd_Pos 闭环） |
| CLOSING | OPEN 收到关命令且允许 | DO_Close=TRUE（或脉冲） |
| MID | OPENING/CLOSING 中收到 Cmd_Stop 且 EnMid | 双输出 FALSE，AO 保持 |
| FAULT | 任一故障条件 | 双输出 FALSE，AO=0 |
| LOCAL/MAINT | Local_Eff/Cmd_Maint | 双输出 FALSE |

状态转移要点：
- OPENING 超 T_OpenMax 无开到位 → FAULT（开超时）；
- CLOSING 超 T_CloseMax 无关到位 → FAULT（关超时）；
- OPEN/CLOSED 收到**反向命令** = 正常切换（先无条件执行互锁见 §6）；
- FAULT 退出：Cmd_Reset 且 Lock_Safety 未动作且反馈回到 consistent 状态（两个到位开关不能同时 TRUE）；
- 调节阀模式没有 OPENING/CLOSING 状态机——只有 CLOSED(AI_Pos≤DeadBand)/OPEN(AI_Pos≥100−DeadBand)/MID(中间)/FAULT，运动由 S07 闭环驱动。

## 6. 双命令互锁（本节是阀门块的核心）

**铁律：DO_Open 和 DO_Close 任何时刻不得同时为 TRUE。** 三重防护：

1. **软件仲裁**（S07 第一行）：`DO_Open := DO_Open AND NOT DO_Close;`——关优先（安全惯例：故障时往关的方向倒）；
2. **互锁条件**：只有当前状态允许某方向才给对应输出；从 OPEN 直接收关命令时，先强制 DO_Open=FALSE 一个扫描周期再 DO_Close=TRUE（反向切换死区，防电弧）；
3. **脉冲模式**（EnPulse=TRUE）：输出给 T_Pulse 宽脉冲后自动断，靠行程开关自保持，从根上消除长带电风险；
4. **到位反馈矛盾保护**：DI_OpenFb 与 DI_CloseFb 同时 TRUE 超 T_FbDb → FAULT（限位开关故障，报警 A6）。

调节阀闭环（S07，EnLoop=TRUE）：
```
IF ABS(Cmd_Pos - AI_Pos) > DeadBand THEN
    AO_Out := MIN(100, MAX(0, Cmd_Pos));   (* 简单位置式；需要调节品质时外接 PID 块 *)
ELSE
    AO_Out := AI_Pos;                       (* 死区内保持 *)
END_IF;
```
> 位置式够用于大多数工艺阀门；要求高的回路（如窑喂料）按 F163 思路外接标准 PID，VALVE_C 只做执行层。偏差 \|Cmd_Pos−AI_Pos\|>DeadBand 持续超 T_DevMax → 报警 A7。

## 7. 报警清单

| # | 报警名(EN) | 报警名(CN) | 触发条件 | 延时 | Sev | 备注 |
|---|---|---|---|---|---|---|
| A1 | Open timeout | 开超时 | OPENING 无开到位 | T_OpenMax | 800 | |
| A2 | Close timeout | 关超时 | CLOSING 无关到位 | T_CloseMax | 800 | |
| A3 | Trip in motion | 运动中跳闸 | 非全开全关位 DI_Fault | T_FltDb | 800 | |
| A4 | Safety interlock | 安全联锁动作 | Lock_Safety 经 T_SafetyDb | T_SafetyDb | 800 | |
| A5 | Process interlock | 过程联锁动作 | Lock_Process 动作 | 0 | 500 | |
| A6 | Limit sw fault | 限位开关故障 | 两位移反馈同时有效 | T_FbDb | 800 | |
| A7 | Position deviation | 阀位偏差 | 超差持续 | T_DevMax | 500 | 仅 EnLoop |
| A8 | Start inhibited | 启动被禁止 | 锁定中收到命令 | T#2s | 500 | 组停时抑制 |
| A9 | Local mode | 就地模式 | Local_Eff | 0 | 事件 | |
| A10 | Maintenance | 检修挂牌 | Cmd_Maint | 0 | 事件 | |

## 8. 仿真模式

- EnSim=TRUE：DI_OpenFb/DI_CloseFb 用 Sim_* 值，AI_Pos 用 Sim_Pos，硬件输出屏蔽；
- **行程仿真**：高级用法——仿真里让 Sim_Pos 按命令方向以参数化速率爬行（如 100%/T_OpenMax），培训时能看到"阀门正在开"的过程，不是瞬跳；
- Sim_CloseFb 默认 TRUE（上电态=关闭），与"失电关闭"的安全方向一致。

## 9. 面板 FP_Valve（详见 05 文档）

- 开关阀：开/关/中停三态符号（三重编码）+ 开/关/停按钮 + 到位指示灯；
- 调节阀：**阀位竖条+百分比** + 目标阀位给定滑块 + 偏差指示 + 模式标签（MAN/AUTO/CASCADE）；
- 公共区：故障信息+SigTag 超链接、参数区（超时/死区/脉冲宽）、所属组+StepNo+跳转、仿真指示。

## 10. 调试检查项

| # | 检查项 | 通过判据 |
|---|---|---|
| C1 | 开 IO | 点开，DO_Open 亮、开到位反馈翻 |
| C2 | 关 IO | 点关，DO_Close 亮、关到位反馈翻 |
| C3 | 互锁 | 任何操作下 DO_Open/DO_Close 不同时亮（看趋势） |
| C4 | 开超时 | T_OpenMax 设 2s 不给反馈，A1 出现 |
| C5 | 关超时 | T_CloseMax 设 2s，A2 出现 |
| C6 | 限位故障 | 同时给两个到位反馈，A6 出现 |
| C7 | 中停 | EnMid=TRUE，运动中 Cmd_Stop，双输出断 |
| C8 | 调节阀闭环 | 给 Cmd_Pos=60，AI_Pos 稳定到 60±DeadBand |
| C9 | 偏差报警 | T_DevMax 设 5s，卡住阀位，A7 出现 |
| C10 | 联锁与本地 | 同 02 文档 C5~C10 |

## 11. 与现有 VALVE1/PVALVE 的差异

| 项 | VALVE1/PVALVE | VALVE_C |
|---|---|---|
| 模式 | 分类型 | 一个块双模式（EnLoop） |
| 互锁 | 靠工程代码 | 块内三重防护 |
| 组接口 | 散线 | CC_EqCmd/EqStat |
| 仿真/调试 | 无 | 内建 |
| 阀位闭环 | 外接 | 内置位置式（可选外接 PID） |

## 12. 本篇结论

VALVE_C = MOTOR_C 的框架 + **双命令互锁 + 阀位闭环**两件特产。记住三个数：**七个状态、两条超时（T_OpenMax/T_CloseMax）、一个死区（DeadBand）**。ST 骨架照抄版在 08 文档 §3（与 MOTOR_C 同构，差异段已标注）。
