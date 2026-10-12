---
title: MinLib拆解复用-电机功能块MOTOR_C拆解
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,MOTOR_C,电机,状态机,联锁,报警,仿真,调试]
summary: MOTOR_C全解剖：管脚/参数/九段逻辑/状态机/三lock联锁/10条报警/仿真/面板/10项调试检查，与MOTOR1差异
source: 数据表 p2/p4/p5 + F163规则总纲 §4.3/§4.4/§5
---

# 02 电机功能块 MOTOR_C 拆解

> 本篇把"电机功能块"拆到你能照着重做的程度。除标注【核实】外均为【自拟】。
> 设计基准：MinLib 数据表 p2（控制连接/组接口）、p4（联锁）、p5（报警/仿真）；兼容 F163 现场 MOTOR1 的既有语义（三 lock、无 O2 管脚）。

## 1. 定位与选型

| 场景 | 用哪个块 |
|---|---|
| 硬接线 DI/DO 的电机、加热器、风机、泵、回转给料器等动力设备 | **MOTOR_C**（本篇） |
| PROFIBUS DP 通讯的传动设备（报文控制） | SMOTOR_PROV（现有库继续用；需要时仿本篇扩一个 MOTOR_DP 变体，见 §11） |
| 变频器（低压/中压） | ABBLVVVF / ABBMVVVF（现有库）【F163 §4.3】 |

MOTOR_C 是"通用动力设备"块：**一个块覆盖电机/风机/泵/加热器**，差异全在参数（名称、超时、是否允许本地等），不靠复制代码。

## 2. 管脚接口全表

管脚分五组。命名即 01 文档 §1.3 规则；类型列里 `DintIO` 等硬件型必须 `.Value` 访问【F163 §5.1】。

### 2.1 硬件 IO 组（过程侧）

| 管脚 | 方向 | 类型 | 说明 |
|---|---|---|---|
| DI_RunFb | in | DintIO 或 Bool | 运行反馈（接触器辅助触点/机侧状态） |
| DI_Fault | in | DintIO 或 Bool | 故障跳闸信号（热偶/断路器辅助） |
| DI_Ready | in | DintIO 或 Bool | 就绪/远程允许（可不用，置 TRUE） |
| DI_Local | in | DintIO 或 Bool | 就地/远方切换状态（TRUE=就地） |
| DO_Run | out | DintIO 或 Bool | 运行命令输出（主输出，得电运行） |
| DO_Stop | out | DintIO 或 Bool | 停止命令脉冲输出（仅 EnDOStop=TRUE 时用，如变频器停止端子） |

### 2.2 命令组（操作员/组）

| 管脚 | 方向 | 类型 | 说明 |
|---|---|---|---|
| Cmd_Start | in | Bool | 启动命令（操作员按钮或组 CC_EqCmd.Start，单周期脉冲） |
| Cmd_Stop | in | Bool | 停止命令（同上） |
| Cmd_Reset | in | Bool | 故障复位（单周期脉冲） |
| Cmd_Maint | in | Bool | 检修挂牌（TRUE=检修） |

### 2.3 联锁组（对齐 F163 §4.4 语义：true=锁定）

| 管脚 | 方向 | 类型 | 说明 |
|---|---|---|---|
| Lock_Start | in | Bool | 启动联锁。TRUE=禁止启动（F163 的 start_lock） |
| Lock_Process | in | Bool | 过程联锁。TRUE=运行中跳停（F163 的 process_lock） |
| Lock_Safety | in | Bool | 安全联锁。TRUE=跳停，**经 TOf 延时后置故障**【F163 §4.4】 |
| O2_Perm | in | Bool | O2 硬件许可（与 DO_Run 逻辑相反的独立允许，F163 §4.4 的 O2 概念；无则置 TRUE） |

### 2.4 组接口组（Control Connection）

| 管脚 | 方向 | 类型 | 说明 |
|---|---|---|---|
| EqCmd | in | CC_EqCmd | 组→设备命令通道（01 文档 §2.1 全字段） |
| EqStat | out | CC_EqStat | 设备→组状态通道（01 文档 §2.2 全字段） |
| Grp | in | CC_Group | 所属组汇总（读 GroupActive/GroupStarting 供报警抑制用，数据表 p5） |

### 2.5 联锁信号接口组（PCC）

| 管脚 | 方向 | 类型 | 说明 |
|---|---|---|---|
| Sig | in | ARRAY[1..8] OF CC_SigOut | 最多 8 个联锁信号块送来的联锁量（数量不限的落地=数组扩，数据表 p4） |
| SigIn | out | CC_SigIn | 回读设备状态给信号块（数据表 p4） |

### 2.6 参数组（PAR，见 §3）

## 3. 参数表（六要素，全）

| 参数名 | 类型 | 默认值 | 范围/单位 | 在线可改 | 面板显示 | 中文说明 |
|---|---|---|---|---|---|---|
| T_StartMax | Time | T#5s | 0~60s | 是 | 是 | 启动反馈超时 |
| T_StopMax | Time | T#5s | 0~60s | 是 | 是 | 停止反馈超时 |
| T_FltDb | Time | T#500ms | 0~5s | 是 | 是 | 故障信号去抖延时 |
| T_RunFbDb | Time | T#100ms | 0~2s | 是 | 是 | 运行反馈去抖延时 |
| T_RunMin | Time | T#0s | 0~300s | 否 | 是 | 最短运行时间（防喘振，未到不给停） |
| T_Restart | Time | T#0s | 0~600s | 否 | 是 | 停止后防重复启动延时 |
| T_SafetyDb | Time | T#1s | 0~10s | 是 | 是 | 安全联锁确认延时（经此才置故障）【F163 §4.4】 |
| EnDOStop | Bool | FALSE | — | 否 | 是 | 是否启用独立停止输出 DO_Stop |
| EnLocalDet | Bool | TRUE | — | 否 | 是 | 是否检测就地模式（FALSE=无就地回路） |
| EnRunTime | Bool | TRUE | — | 否 | 是 | 是否统计运行时长（主备均衡用） |
| EnSim | Bool | FALSE | — | 是 | 是 | 仿真开关（TRUE=反馈用仿真值，见 §8） |
| Sim_RunFb | Bool | FALSE | — | 是 | 是 | 仿真运行反馈值 |
| Sim_Fault | Bool | FALSE | — | 是 | 是 | 仿真故障注入 |
| Sim_Local | Bool | FALSE | — | 是 | 是 | 仿真就地状态 |
| StepNo | Int | 0 | 0~99 | 是 | 是 | 组内启动步号——**数据源在组的 StepNoTab 数组，组经 EqCmd 下发；本参数只读显示**（改组参数=改顺序，04 文档 §3） |
| StepNoStop | Int | 0 | 0~99 | 是 | 是 | 组内停止步号——同上，源在组 StepNoStopTab |
| Desc_EN | String[40] | — | — | 否 | 是 | 英文描述 |
| Desc_CN | String[40] | — | — | 否 | 是 | 中文描述 |
| TagNo | String[32] | — | — | 否 | 是 | 设备 tag（首报显示+超链接用，数据表 p2） |

## 4. 内部逻辑分段（S01~S09）

大逻辑原则：**状态机用 ST（分段编号），去抖/计时/报警触发用 FBD 标准块**。分段号即 ST 段号，也是排查入口。

| 段 | 名称 | 干什么 | 实现 | 关键点 |
|---|---|---|---|---|
| S01 | 输入采集与去抖 | 硬件 DI 经去抖成内部布尔 | FBD：TDeb 块（TON+TOF） | DI_RunFb→RunFb_DB；DI_Fault→Fault_DB；DI_Local→Local_DB |
| S02 | 仿真注入 | EnSim 时用仿真值替换反馈 | ST | RunFb_Eff = EnSim ? Sim_RunFb : RunFb_DB；Fault_Eff、Local_Eff 同理；见 §8 |
| S03 | 模式判定 | 本地/检修/远控 | ST | Local_Eff→ST_LOCAL；Cmd_Maint→ST_MAINT；两者优先于一切命令 |
| S04 | 联锁汇总 | 三个 lock + O2 + 信号联锁合成允许位 | ST/FBD | Perm_Start=NOT Lock_Start AND NOT SigInhibit AND NOT (T_Restart 计时中)；Perm_Run=NOT Lock_Process AND NOT Lock_Safety_DB |
| S05 | 命令仲裁 | 操作员 vs 组命令，定最终启停 | ST | 组命令（EqCmd.Enable=TRUE）优先于操作员；本地/检修时全屏蔽 |
| S06 | 状态机 | 核心，见 §5 | ST（CASE） | 七个状态；FAULT 必须 Cmd_Reset 且无安全联锁才退出 |
| S07 | 输出驱动 | 状态→DO | ST | DO_Run 在 STARTING/RUN 为 TRUE；STOPPING/STOP/FAULT 为 FALSE；DO_Stop 脉冲仅在 EnDOStop |
| S08 | 报警生成 | 见 §7 清单 | FBD：AlarmCond | 每条报警的 Enable 引脚=对应段的条件 AND 抑制逻辑（06 文档） |
| S09 | 统计与上报 | RunTime 累加、EqStat 填充 | ST | EqStat 每周期刷新；FirstFault/FaultTag 在进 FAULT 时锁存 |

### S06 状态机状态转移表（核心，背下来）

| 当前状态 | 条件 | 下一状态 | 动作 |
|---|---|---|---|
| 上电 | — | STOP | 输出清零 |
| STOP | StartCmd AND Ready AND NOT T_Restart计时 | STARTING | DO_Run=TRUE，启 T_StartMax |
| STOP | Local_Eff | LOCAL | DO_Run=FALSE |
| STOP | Cmd_Maint | MAINT | DO_Run=FALSE |
| STARTING | RunFb_Eff（持续 T_RunFbDb） | RUN | 记启动成功时间 |
| STARTING | T_StartMax 到 | FAULT(启动失败) | 锁存 FaultTag=自身 |
| RUN | Cmd_Stop 或 Lock_Process 或 Lock_Safety_DB | STOPPING | DO_Run=FALSE，启 T_StopMax |
| RUN | Fault_Eff | FAULT(运行跳闸) | 锁存 FaultTag/SigTag |
| RUN | 运行时长 < T_RunMin 时收到停止 | （忽略停止） | 到 T_RunMin 才允许停 |
| STOPPING | NOT RunFb_Eff | STOP | 启 T_Restart 计时 |
| STOPPING | T_StopMax 到仍有反馈 | FAULT(停止失败) | 锁存 |
| FAULT | Cmd_Reset AND NOT Lock_Safety_DB AND NOT Lock_Start | STOP | 清锁存 |
| LOCAL | NOT Local_Eff | STOP | — |
| MAINT | NOT Cmd_Maint | STOP | — |

## 5. 联锁设计细节（对齐 F163 §4.4）

1. **三个 lock 全是 TRUE=锁定，直接赋值不取反**——工程侧 ST 写 `Lock_Start := N562_xx_RS;` 这种，RS 触发器输出 TRUE 就是锁定【F163 §4.4】；
2. **safety_lock 经 TOf 延时**（参数 T_SafetyDb）再置故障，防瞬时抖动跳车【F163 §4.4】；
3. **O2_Perm 与 DO_Run 逻辑相反**：F163 现场 O2 是硬件 DO 直接赋值，与 start_lock 相反【F163 §4.4】；MOTOR_C 里 O2_Perm=TRUE 才允许 DO_Run=TRUE。没有独立 O2 回路时把 O2_Perm 常置 TRUE；
4. **联锁信号（Sig 数组）**：任一 Sig[i].Interlock=TRUE 且类型含"禁止启动"→ 参与 Perm_Start= FALSE；类型含"跳停"→ 直接进 STOPPING 或 FAULT（按 SigType，见 01 文档 §1.4）；
5. **联锁信号抑制**：设备在 LOCAL/MAINT 时，SigIn.Local/Maint 回 TRUE，信号块据此屏蔽报警（数据表 p4）。

## 6. 输出与反馈异常组合（防呆）

| DO_Run | RunFb_Eff | 判定 | 处理 |
|---|---|---|---|
| TRUE | TRUE | 正常 | — |
| TRUE | FALSE 超 T_StartMax | 启动失败 | FAULT，报警 800 |
| FALSE | FALSE | 正常停止 | — |
| FALSE | TRUE 超 T_StopMax | 停止失败 | FAULT，报警 800 |
| FALSE | TRUE < T_StopMax | 停止中 | 等 |

## 7. 报警清单（AlarmCond，Severity 800 重报警/500 警告，F163 §5.9）

| # | 报警名(EN) | 报警名(CN) | 触发条件 | 延时 | Sev | 抑制条件 |
|---|---|---|---|---|---|---|
| A1 | Start fail | 启动失败 | STARTING 超时无反馈 | T_StartMax | 800 | 组活动中且非启动抑制期 |
| A2 | Stop fail | 停止失败 | STOPPING 超时仍有反馈 | T_StopMax | 800 | 同上 |
| A3 | Trip in run | 运行中跳闸 | RUN 中 Fault_Eff | T_FltDb | 800 | 同上 |
| A4 | Safety interlock | 安全联锁动作 | Lock_Safety 经 T_SafetyDb | T_SafetyDb | 800 | 同上 |
| A5 | Process interlock | 过程联锁动作 | RUN 中 Lock_Process | 0 | 500 | 同上 |
| A6 | Start inhibited | 启动被禁止 | STOP 时 StartCmd 但 Lock_Start | T#2s | 500 | 组停止时抑制（数据表 p5 规则1） |
| A7 | Feedback flicker | 反馈闪断 | RUN 中反馈丢失又恢复 | T_RunFbDb | 500 | 同上 |
| A8 | Local mode | 就地模式 | Local_Eff | 0 | 事件 | — |
| A9 | Maintenance | 检修挂牌 | Cmd_Maint | 0 | 事件 | — |
| A10 | Signal interlock | 联锁信号故障 | 任一 Sig[i].AlmLevel=2 | 对应 DelayFlt | 800 | 设备 LOCAL/MAINT 时抑制 |

报警抑制逻辑（三规则）汇总实现见 06 文档 §2，这里只登记每条报警的抑制条件。

## 8. 仿真模式（数据表 p5：built-in simulation）

- `EnSim=TRUE` 时：**所有硬件写输出被屏蔽**（DO_Run/DO_Stop 不送物理通道，改送内部仿真寄存器），反馈用 Sim_RunFb；Fault/Local 同理；
- 报警照常产生——培训时就要听报警；
- 组命令照常流转——培训组启停顺序时整组置仿真，操作员看到的现象与真机一致（数据表 p5：operator training with built-in simulation）；
- Sim_Fault=TRUE 注入故障，演练"运行中跳闸→首报→组面板显示 tag→超链接导航"全链路；
- 下装前必须全组 EnSim=FALSE，核对清单见 09 文档。

## 9. 面板 FP_Motor（布局详见 05 文档）

- 绑定 MOTOR_C 实例，Aspect 对象自动生成（800xA 的 Application/Aspect Object）；
- 必备区：①头部（Desc_EN/Desc_CN + TagNo）②状态符号（三重编码，见 05 §2）③启停/复位按钮④故障信息+**SigTag 超链接**（数据表 p4）⑤参数在线编辑区（延时类）⑥所属组名+StepNo+**跳转组面板按钮**（数据表 p2）⑦仿真开关指示；
- 颜色+形状+文字三编码：例如 RUN=绿圆形+"运行"，FAULT=红八角+"故障"——颜色只是其中一维【数据表 p5】。

## 10. 调试检查项（CHK_C 集成，框架见 07 文档）

| # | 检查项 | 通过判据 |
|---|---|---|
| C1 | 启动 IO | 强制 Cmd_Start，DO_Run 亮、DI 回路灯亮 |
| C2 | 停止 IO | Cmd_Stop，DO_Run 灭 |
| C3 | 启动超时 | T_StartMax 设 2s，不给反馈，A1 报警出现 |
| C4 | 停止超时 | T_StopMax 设 2s，反馈不消，A2 出现 |
| C5 | 运行跳闸 | 运行中拨 DI_Fault，A3 出现、状态=FAULT |
| C6 | 安全联锁 | Lock_Safety 置 TRUE 超 T_SafetyDb，A4 出现 |
| C7 | 过程联锁 | RUN 中 Lock_Process，进 STOPPING |
| C8 | 启动禁止 | STOP 时 Lock_Start+StartCmd，A6 出现 |
| C9 | 本地模式 | DI_Local=TRUE，命令无效，A8 事件 |
| C10 | 仿真 | EnSim=TRUE，Sim_RunFb 驱动全状态机，硬件无输出 |

## 11. 与现有 MOTOR1 的差异与迁移

| 项 | MOTOR1（现场） | MOTOR_C |
|---|---|---|
| 组接口 | G_start/G_stop Boolean16 位操作【F163 §4.6】 | EqCmd/EqStat 结构体 |
| 联锁管脚 | 三个 lock 直接赋【F163 §4.4】 | 同名同义（true=锁定），改走 CC 字段 |
| O2 | 硬件 DO 直接赋值，无管脚【F163 §4.4】 | O2_Perm 显式管脚，语义相同 |
| 仿真/调试/报警抑制 | 无 | 内建 |
| DP 电机 | SMOTOR_PROV【F163 §4.3】 | 不动；需通讯版时仿本篇加 MOTOR_DP：把 DI/DO 组换成报文读写+控制字/状态字解析（Release bit 恒 1，F163 §5.8） |

**迁移建议**：老组的 MOTOR1 实例不要动；新组全部 MOTOR_C。等 CL 库在一个新组跑通、调试检查全过，再评估老组是否值当切换。

## 12. 本篇结论

MOTOR_C 的骨架就三句话：**九个逻辑段（S01~S09）、七个状态（STOP/STARTING/RUN/STOPPING/FAULT/LOCAL/MAINT）、十个报警（A1~A10）**。所有现场差异（超时、延时、是否允许本地、步号）全是参数。ST 骨架照抄版在 08 文档 §1。
