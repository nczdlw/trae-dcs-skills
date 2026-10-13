---
title: MinLib拆解复用-报警处理框架V2（官方对齐）
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,报警,AlarmTr,StdType,首报,PCC,ASM,事件列表]
summary: V2：官方报警体系全量——报警禁用三条件与Std_Type矩阵、AlarmTr五档处理、状态门控报警生成、联锁不是报警原则、首报与双向确认、消息结构与ALP后缀、CL落地映射
source: 04 Consumer手册§2.4/§2.5 + 02 Basic手册p6-7 + 00产品指南§2 + 05手册
---

# 06 报警处理框架（V2）

> **V2 变更**：全部改为官方手册内容。最重要的纠偏：**联锁本身不产生报警，产生联锁的过程条件（信号）才报警**——V1 把联锁当设备报警是错的。
> 页码标注：[04手册pN]=Consumer Objects，[02手册pN]=Basic Objects，[00手册pN]=产品指南。

## 1. 官方报警体系总览【核实-04手册p5-6】

| 机制 | 官方规则 |
|---|---|
| 报警禁用（按工况） | 三条件：**组活动或停止 / 消费者活动或停止 / 消费者远程或本地**（细化见 §2 Std_Type 矩阵） |
| 双向确认 | AIS/DIS ↔ Consumer/Group 任一面板确认；组面板确认下传到信号级；Local 控制时自动确认 |
| 首报检测 | 对象+全部联锁信号的首报检测，首报信号 tag 显示在消费者/组面板，带链接按钮 |
| 启动报警抑制 | 可选的 start-up alarm inhibits（针对动态过程信号，如启动电流） |
| 报警转发 | 信号报警自动转发到消费者 |
| 动态优先级 | Dynamic alarm priority control（AlarmTr/IndTr） |
| Electrical 接口报警 | 3 静态（availability/overload/trip/emergency stop 选三）+最多 4 动态（run x/y 反馈、位置限位、速度开关）+1 控制电压监视+4 IO 板状态 |

## 2. 报警禁用矩阵（Std_Type）【核实-02手册p6-7】

| 设置 | 规则 |
|---|---|
| `cBMI.Std_Type = 0`（默认） | 电机未运行 / NC 阀关闭 / NO 阀开启 / 组未启动 → 信号报警自动禁用 |
| `cBMI.Std_Type = 1` | 同 0，但组已启动且消费者被预选时一律报警；**standby 预选的消费者报警优先级自动 Failure→Warning** |
| `PCCAEListFrcEn = true` | 关闭自动禁用（用于料位等需独立报警的信号） |

## 3. 报警生成门控（官方硬规则）【核实-04手册p23】

**报警只在以下状态产生**：

| 对象 | 产生报警的状态 |
|---|---|
| MOT1/MOT2/MOTP/MOT1_VVVF | **运行中或启动中** |
| VLV1 | **阀开** |
| VLVNO1 | **阀闭** |

推论：设备停止期间的"过程异常"不弹设备报警——这正是 Std_Type 0 的细化。**联锁（IC/IB/IA/PD）不是报警**：联锁动作只在事件列表留记录，进操作员报警清单的是**信号对象上**的那个过程条件（高温/低压/无流量）【04手册p23】。

## 4. AlarmTr 五档处理【核实-04手册p23】

| 值 | 行为 |
|---|---|
| 3（默认） | 未确认报警 "Failure" |
| 2 | 未确认报警 "Warning" |
| 1 | 自动确认报警 "Warning" |
| 0 | 仅事件 |
| -1 | 不产生报警/事件 |

- AlarmTr 在 Control Builder 里对所有对象可改；类似 AI/DI 对象的 AlarmTr/LimTr；
- 未用 NLS 时报警文本自动加优先级后缀：ALP1/ALP2→Warning、ALP3→Failure（常量 cBMI.AE.ALP1_SubTxt 等，NLS Resource Manager 里也定义）；
- **AlarmTr 就是 F163 项目 Severity 800/500 的官方对应**：800↔3/2（Failure/Warning 未确认），500↔1（自动确认 Warning）【F163 §5.9】。

## 5. 消息结构（事件列表）【核实-04手册p49-51】

**结构**：`[POC] + [MODE] + [STATUS] + [STOP REASON] + Blk: + [BLOCK LIST]`

- POC：Seq / Cen / Loc / Out
- MODE：Aut / Man / Mtc / Frc
- STATUS：Starting / Run / Off
- STOP REASON：QSP / SSP / CSP / FSP / PSP / IOS / ME / SQX / IC / IB1-4 / IA / PD / PCC-IC / PCC-IB / PCC-IA / PCC-PD（全表见 02 文档 §7）
- BLOCK LIST：- / IB1-4 / IA / FB1 / FB2 / PD（面板闭锁中）

报警文本参数：M1/M2/M3→各 Txt；Local Stop→LcbStopTxt；Contactor Fault→FdBckTxt；FB1/FB2 Fault→FB1Txt/FB2Txt；FB 类未用 NLS 时加后缀 On/Trip/Off/Frc（FBTime 后未 true / 运行中变 false / FBTime 后未 false / 停止时变 true）【04手册p51】。

## 6. PCC Viewer（报警/联锁一览）【核实-04手册p24-27】

- 按**联锁类型+启动方向**分类显示一台消费者全部联锁条件；无联锁定义的信号归 "Unassigned" 组（其报警在图形上显示但不影响操作）；
- 显示实际状态、被禁用的联锁、被强制/闭锁的信号；
- 过滤选项：只看使能 / 只看活动 / 只看当前方向 / 显示全部方向选项（默认只显 X/Y 和 FB）。

## 7. 画面表示【核实-04手册p13 + 00手册p20-22】

- 图形元素报警/警告时背景变报警处理色；
- VCO ASM：过程状态灰度+颜色只给报警+冗余编码（形状+颜色）；
- 报警列表（红按钮）/事件列表（绿按钮）：**事件列表=全部历史（事件+报警）；报警列表=仅当前活动报警**；从面板打开的列表只显示该对象的【04手册p21-22】。

## 8. CL 落地映射【CL 适配】

| CL 设计 | 对齐官方 | 说明 |
|---|---|---|
| 报警产生位置 | **信号对象（SIG_C）产生报警，设备对象不产生联锁报警** | 废弃 V1"设备10条报警含联锁"设计，改官方门控 |
| 严重度 | AlarmTr 五档 | F163 现场 AlarmCond 映射：Failure→800、Warning→500、Event→SimpleEventDetector【F163 §5.9】 |
| 禁用逻辑 | Std_Type 矩阵+PCCAEListFrcEn | 废弃 V1 自拟 Inhib_GroupStop/Starting 公式，改官方工程常量 |
| 首报 | FirstOrMaxAETag/FirstOrMaxAEIndTr + 组面板链接 | V1 FaultTag/SigTag 字段被官方字段取代 |
| 启动抑制 | 信号侧 IntlkStartInhibit（01 文档 §3.1） | V1 的"启动抑制期"改官方参数 |
| 本地确认 | 双向确认+Local 自动确认 | 官方机制 |
| 消息 | 官方消息结构 | CL 事件文本照抄结构，中文用 NLS 前缀 `\|\|AE_NLS_` |
| 报警清单 | 官方各对象 Alarm&Event List | CL 按对象类型预置（电机=M1/M2/M3/LocalStop/Contactor/FB1/FB2；阀门=M1/LocalClose/OpnClsErr/FBOpn/FBCls；组=启停超时/联锁） |

**F163 现场迁移要点**：现场 SignalInReal/SignalInBool 报警【F163 §4.5】→ 对标 AIS/DIS：报警在信号上产生；设备侧的 RS/process_lock 赋值【F163 §4.4】→ 对标 IB/IA 联锁输入（联锁不是报警）；现场 AlarmCond 的 CondName 不支持【F163 §5.9】→ 官方用 NLS Txt 参数+ALP 后缀实现等效。

## 9. V1→V2 关键差异

| V1 自拟 | V2 官方 |
|---|---|
| 设备 10 条报警（含联锁动作） | 报警只在运行/开（闭）态产生；**联锁不是报警** |
| 自拟抑制公式 | Std_Type 0/1 + PCCAEListFrcEn 工程常量 |
| Severity 800/500 两档 | AlarmTr 五档（3/2/1/0/-1） |
| 自拟首报转发 | 官方双向确认+FirstOrMaxAETag |
| 无消息结构 | [POC]+[MODE]+[STATUS]+[STOP REASON]+Blk: |
| 报警清单自拟 10 条 | 官方按对象预置+文本参数化+ALP 后缀 |

## 10. 本篇结论

官方报警体系三句话：**①报警归信号（过程条件），联锁归设备（动作），两路都进事件列表但只有活动报警进报警清单；②报不报看设备状态（Std_Type 矩阵）；③多严重看 AlarmTr 五档**。CL 库按 §8 映射落地，现场 AlarmCond 用法不变（Failure=800/Warning=500），禁用逻辑从自拟公式换成官方工程常量。
