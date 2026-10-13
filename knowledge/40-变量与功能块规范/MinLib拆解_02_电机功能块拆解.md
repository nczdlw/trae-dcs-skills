---
title: MinLib拆解复用-电机功能块MOT_C拆解V2（官方对齐）
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,MOT1,MOT2,MOTP,电机,参数表,联锁,报警,仿真,POC]
summary: V2：官方电机族五对象选型、MOT1全77参数表、MOT1Data四组件字段、IC/IB/IA/PD联锁语义、POC命令矩阵、Faceplate页签、报警消息结构与停止原因码、组级仿真、CL落地映射
source: 04 Consumer Objects手册3BHS161557 RevD §2/§3/§5/§7/§4（p5-51等）
---

# 02 电机功能块 MOT_C 拆解（V2）

> **V2 变更**：全部改为官方手册内容（04 Consumer Objects，3BHS161557 RevD）。官方参数一个不改；CL 落地块 `MOT_C` 与官方 MOT1/MOT2/MOTP 的映射见 §11。
> 页码标注：[04手册pN] = Consumer Objects 手册第 N 页。

## 1. 电机族选型（先选对对象）【核实-04手册p29/94/160/52】

| 官方对象 | 管什么 | 方向/速度 | 标志能力 |
|---|---|---|---|
| **MOT1** | 单方向单速电机（组内或独立） | 1 | 电流指示+高限警告；3个MCC接口（Overtemp/Overload/Availability）；2个功能反馈FB1/FB2（带反馈超时，支持脉冲反馈+实际周期显示）；1个运行反馈；1×IC+1×IA(Chain Auto)+4×过程联锁+1×PD；4个过程联锁中2个可配为启动许可；运行小时+启动次数累计；**经 DISFastPCC 的快速联锁** |
| **MOT2** | 两方向（两速度）电机 | 2 | 每方向1个运行反馈；每方向各1×IC/IA/PD（共2+2+2）；4个过程联锁方向无关；除设备联锁外全部联锁方向相关 |
| **MOTP** | 电动阀/挡板（带或不带模拟位置反馈） | 2（位） | 2个位置限位反馈（同时到位=故障）；2个运行反馈；每方向2×IC/2×IA/2×过程联锁；2个强制命令；**自动位置控制**（内/外给定）；位置+偏差控制两种接线（1AI+2DO脉冲 / 1AI+1AO）；设定值上下限；位置偏差报警 |
| **MOT1_VVVF** | 变频单速电机 | 1 | MOT1 全部+速度监视（FB3）：Run Speed Supervision / Off Speed Supervision（含参数、报警清单，04手册§4.4） |
| **MOT2_VVVF** | 变频两速电机 | 2 | MOT2+速度反馈监视 |

**选型口诀：不反转用 MOT1，反转用 MOT2，要阀位用 MOTP，带变频加 _VVVVF 后缀。** 现场 F163 的 MOTOR1（硬接线）→ 对标 MOT1；SMOTOR_PROV（DP 通讯）→ 对标通讯型消费者（另见 07 Communication Objects 手册）。

## 2. MOT1 全参数表（77 项，官方原样）【核实-04手册p30-33】

### 2.1 标识与结构

| # | 参数 | 类型 | 初值 | 方向 | 说明 |
|---|---|---|---|---|---|
| 1 | Name | string | 'Name' | in | Tag 名（允许 . 和 -，禁空格 : ;） |
| 2 | Description | string | 'Description' | in | 描述文本 |
| 3 | IO | MOT1Data | default | in_out | MOT1Data 变量（每电机一个全局变量） |
| 4 | Stw | STWData | default | in_out | 接 STW（启动预告）模块 |
| 5 | Group | GrpDrvCon | default | in_out | 接 GROUP（顺序器）模块 |

### 2.2 组接口（GCC）

| # | 参数 | 类型 | 初值 | 说明 |
|---|---|---|---|---|
| 6 | GrpStartStep | dint | 0 | 启动步号 1..999，**0=不参加组顺序** |
| 7 | GrpStopStep | dint | 0 | 停止步号 1001..1999，**0=不参加组顺序** |
| 8 | GrpStartDelay | time | 0s | 组顺序启动时的启动延时 |
| 9 | GrpStopDelay | time | 0s | 组顺序停止时的停止延时 |
| 10 | PreSelection | string | 空 | 分配的 PreBin，语法 `P1&P2\|P3&N4`（=P1且P2 或 P3且非P4），AND 优先 OR，最多5个OR，禁空格 |

### 2.3 IO 与 MCC 接口

| # | 参数 | 类型 | 初值 | 说明 |
|---|---|---|---|---|
| 11-14 | IOStatus1-4 | dint | 0 | 相关 IO 板状态信号（IOStatus4 兼串口监视） |
| 15 | ME | bool | true | 主控制电压分配 OK；**false=禁止报警生成** |
| 16 | M1 | bool | true | MCC 接口信号1（默认 Overtemp 超温） |
| 17 | M2 | bool | true | MCC 接口信号2（默认 Overload 过载） |
| 18 | M3 | bool | true | MCC 接口信号3（默认 Availability 可用） |

### 2.4 反馈

| # | 参数 | 类型 | 初值 | 说明 |
|---|---|---|---|---|
| 19 | FdBckRun | bool | — | 运行反馈（默认"接触器吸合"）；无 IO 时用 MOT1Data.Out.Ord |
| 20 | FdBckTime | time | 2s | 接触器响应最大延时 |
| 21 | FB1 | bool | true | 功能反馈1（如速度开关） |
| 22 | FB1Txt | string | 空 | FB1 描述文本（NLS 用 `\|\|AE_NLS_` 前缀无空格） |
| 23 | FB1Mode | dint | 0 | 0=连续；>0=脉冲时间（1=0.1s…999999=99999.9s）；-1=连续且 FB Opn 报警 |
| 24 | FB2 | bool | true | 功能反馈2（如压力开关） |
| 25 | FB2Txt | string | 空 | FB2 描述 |
| 26 | FB2Mode | dint | 0 | 0=连续；-1=连续且 FB Opn 报警 |
| 27 | FBTime | time | 10s | FB1/2 响应和 HiCurrent 响应最大延时 |

### 2.5 就地盒 LCB

| # | 参数 | 类型 | 初值 | 说明 |
|---|---|---|---|---|
| 28 | LcbStart | bool | false | 现场启动脉冲 |
| 29 | LcbStop | bool | true | 现场任何停止命令（stop/not remote..），停=0 |
| 30 | LcbRem | bool | false | 正脉冲→POC 切 Seq 或 Cen（按 MOT1_LCB 配置） |
| 31 | LcbLoc | bool | false | 正脉冲→POC 切 Loc |
| 32 | LcbMaint | bool | true | 置维护模式（按用户配置） |
| 33 | LcbType | dint | 0 | 0=POC CCR启停信号 1=POC LCB 2=硬线LCB带LOC/REM DO 3=POC LCB切POC时停止 4=POC CCR启动+Rem信号 |

### 2.6 电流与输出

| # | 参数 | 类型 | 说明 |
|---|---|---|---|
| 34 | MC | RealIO | 电机电流或功率（模拟量输入） |
| 35 | MCNominal | real | 额定电流 |
| 36 | Ord | bool | out 启动命令（输出到接触器） |
| 37 | LocAlarmAck | bool | out 报警复位脉冲（如复位 SCP 报警） |

### 2.7 联锁

| # | 参数 | 类型 | 初值 | 说明 |
|---|---|---|---|---|
| 38 | PrevDrive | bool | true | 链式联锁"前序设备运行中" |
| 39 | PrevDriveTxt | string | 空 | 前序设备联锁描述（NLS `\|\|IL_NLS_`） |
| 40 | IATxt | string | 空 | IA 链/自动联锁描述 |
| 41 | IBF | bool | false | true 时 IB3/IB4 作为**启动联锁** |
| 42-45 | IB1Txt~IB4Txt | string | 空 | 各 IB 联锁描述 |
| 46 | ICTxt | string | 空 | IC 安全联锁描述 |

### 2.8 启动预告/自动模式/POC 使能

| # | 参数 | 类型 | 初值 | 说明 |
|---|---|---|---|---|
| 47 | StwCen | bool | 工程常量 | true=CEN/SEQ 启动时自动触发启动预告 |
| 48 | StwField | bool | false | true=现场（LCB）启动时自动触发预告 |
| 49 | AutoMode | dint | 工程常量 | 1=Man 模式下若 EnAuto 则禁用 IA；8=Auto 模式等下次触发再启动 |
| 50 | EnAuto | bool | false | Auto 模式使能（true=组顺序启动时激活 Auto） |
| 51 | EnSeq | bool | true | POC Sequence 使能 |
| 52 | EnCen | bool | true | POC Central 使能 |
| 53 | EnLoc | bool | 工程常量 | POC Local 使能 |
| 54 | EnMaint | bool | true | 维护子模式使能 |
| 55 | EnFPLStopInAllModes | bool | 工程常量 | false=面板停止只在 POC Central 有效 |

### 2.9 报警/事件与文本

| # | 参数 | 类型 | 说明 |
|---|---|---|---|
| 56 | ExtendedInfo | dint | 多路开关：1=ConsumerExt 2=报警列表 4=事件列表 8=详细图形 16=状态 32=趋势 64=面板 |
| 57 | Class | dint | 报警/事件类 1..9999（工艺段） |
| 58 | AlarmTr | dint | 报警处理 1/2/3=ALPrio#（1最低） |
| 59 | InterlockTr | dint | 联锁处理 1/2/3=ALPrio# |
| 60 | ModeTr | bool | true=模式/POC 变化产生事件 |
| 61 | StatusTr | bool | true=状态（开/停）变化产生事件 |
| 62-71 | 各类 Txt | string | IOStatTxt/IOStat4Txt/METxt/M1Txt/M2Txt/M3Txt/LcbStopTxt/FdBckTxt/MCTxt/WarningTxt |
| 72 | MCHiLim | real | 100 | 电流高限（额定电流 %） |
| 73-76 | GrpRunOverride/GrpOffOverride/GrpTripOverride/GrpRFSOverride | bool | false | 向组强制回送 RUN/OFF；跳闸不触发预选切换；未就绪不上报且组跳步 |
| 77 | AlarmAck | bool | 脉冲，报警确认 |

## 3. MOT1Data 数据类型（每电机一个全局变量）【核实-04手册p34-37】

四组件：**In（16字段）/ Out（25字段）/ PCC（PCCComData）/ ProcessPanel（PanelLinkConsumer）**。

### 3.1 MOT1Input（入）

| 字段 | 说明 |
|---|---|
| PreSel | true=被预选（未参数化 PreSelection 时接 PreBinData.PreSel） |
| PreSelStdBy | true=被预选为 standby；**仅 cBMI.StdType=1 时用于把指示降为 Warning** |
| EnSeqStart / EnSeqStop | true=才允许组启/停本电机（软允许位） |
| SeqStart/SeqStop/SetSeq/SetCen/SetLoc | 脉冲：外部启/停/POC 切换（SeqStart 会切 POC 到 Seq 并启动） |
| IC | 安全联锁，**所有操作模式都生效** |
| IB1 | 操作员可闭锁联锁，**本地模式不激活** |
| IB2 | 联锁，本地不激活 |
| IB3 | 操作员可闭锁，本地不激活；IBF=1 时作启动联锁 |
| IB4 | 同 IB3 |
| IA | 自动+链式联锁，**不计入 RFS**；true 时 Auto 模式重启 |
| Warning | 外部警告（不停机） |

### 3.2 MOT1Output（出）

| 字段 | 说明 |
|---|---|
| Auto/Seq/Cen/Loc/Maint/OutOfSrv | 模式指示 |
| Trip | 跳闸指示（可启动冗余驱动），由 FdBckRun/M1/M2/M3/FB1/FB2 激活（不含联锁） |
| Rfs | Ready For Start |
| NoInt | 无联锁（就绪且无 IA） |
| Run | 运行中（条件：Ord AND FdBckRun AND FB1 AND FB2） |
| Ord | 启动命令输出1（**仿真模式也输出**） |
| StartCnt/RuntimeCnt | 启动次数/运行小时累计（coldretain） |
| ALNumber/ALPending/ALUnack | 实际报警号/待确认/未确认 |
| FieldStartRelease | LOC 选中且启动条件 OK |
| ForcedRun | 强制运行（如硬线 LCB 启动） |
| FdBckOffErr | 主接触器未断开（Feedback Off 报警） |
| FB1PulseTime | FB1 脉冲实际周期（秒，如速度开关） |
| **FirstOrMaxAETag** | **首报/最高报警的 IO 设备 tag（对电机/组/阀产生动作的那个）** |
| FirstOrMaxAEIndTr | 首报/最高报警的指示处理号 |
| LastReset/LastTripTxt/LastTrip | 上次复位时间/上次跳闸联锁描述或 PCC AE tag/跳闸时间 |

### 3.3 PCC 与 ProcessPanel

- PCC = `PCCComData`（IN：来自输入模块的联锁总线、PriorityCommand/Interlock）；
- ProcessPanel = `PanelLinkConsumer`：Status（Ready_Off=0/Ready_Run=3/NotRFS_Off=6/NotRFS_Run=7/Fault_Off=9/Fault_Run=10/FaultNotRFS_Off=12/FaultNotRFS_Run=13）、StatusModes（Seq=0/Cen=1/Loc=2/Auto=3/AutoCen=4/OOS=9）、Cmd（Start=0/Stop=2/AlarmAck=7）、CmdModes（SetCen=0/SetSeq=1/SetLoc=2/SetAuto=3/SetMan=4）、Blink【04手册p36-37】。

## 4. 联锁语义速查【核实-04手册p34-35】

| 联锁 | 本地模式 | 维护模式 | RFS 影响 | 备注 |
|---|---|---|---|---|
| IC 安全 | **仍生效** | 默认仍生效（DisableICInMaint 可关） | 影响 | 唯一本地不释放的联锁 |
| IB 设备 | 释放 | 释放 | 影响 | IBF=1 时 IB3/IB4 作启动联锁 |
| IA 过程/链式 | 释放 | 释放 | **不计入** | Auto 模式 ok 后不自复（见 01 文档 §3.2） |
| PD 前序 | 释放 | 释放 | 组保持 RFS（PD_PrevDrive 类型） | |
| PCC 联锁 | 按信号 IntlkType/IntlkDir | 按配置 | 按类型 | 信号侧参数决定，见 01 文档 §3 |

维护模式额外规则：**IA/IB 一律禁用（不管 Local 配置）**，IC 可用 DisableICInMaint 关（默认 false）；维护模式默认限制在 POC Local【04手册p9】。

## 5. POC×模式 命令矩阵（官方原表）【核实-04手册p8】

| 命令 | Seq·Man | Seq·Auto | Cen·Man | Cen·Auto | Local |
|---|---|---|---|---|---|
| 程序 启/开 | ✓ | Set Auto | ✓ | Set Seq/Auto | — |
| 程序 停/关 | ✓ | Stop+set Man | ✓ | Stop+set Man | — |
| 操作员 启/开 | — | — | ✓ | — | — |
| 操作员 停/关 | — | Stop+set Man | ✓ | Stop+set Man | Stop/关 |
| 程序 快停 | ✓ | Stop+set Man | ✓ | Stop+set Man | Stop/关 |
| IA=true 或 PCC Auto Start | 启 | 启 | — | 启 | — |
| IA=false 联锁 | 停 | 停 | 停 | 停 | Trip/关 |
| 现场 启/停 | — | — | — | — | 启 / Trip+set Man |

注：①面板停止受 EnFPLStopInAllModes 控制；②组可配 SetSeqMode=2 在对象非 Seq 模式时暂停；③AutoMode=1 可让 Man 模式下 IA 不停机【04手册p8】。

## 6. Faceplate（官方结构）【核实-04手册p39-42 + 00手册p19】

- **Aspect 视图按钮**：PCC Viewer 等；
- **命令按钮**：Start / Stop / Acknowledge alarm / 切 POC（Seq/Cen/Loc）/ 切模式（Auto/Man）；
- **Default View 指示**：Sim（整组顺序仿真中，**硬件信号被忽略**）/ Block（有联锁或信号被闭锁）/ Tag 名与描述 / 电机状态 / Normal View / 警告与报警指示 / 实际电流（额定 %）/ 电流值；
- **页签**：Interlock（联锁指示与闭锁）/ PCC（PCC 联锁指示）/ Alarm（报警指示与闭锁）/ Trend（电流在线趋势）/ Group（所属 Drive Group 事项）；
- **VCO 图形元素**：VCO_MOT1（状态/控制点/模式/报警符号）、VCO_MOT1FBTxt（反馈文本）、VCO_MOT1MCValue（电流值）【04手册p38】。

## 7. 报警与事件（官方消息结构）【核实-04手册p49-51】

**消息结构**：`[POC] + [MODE] + [STATUS] + [STOP REASON] + Blk: + [BLOCK LIST]`

| 段 | 取值 |
|---|---|
| POC | Seq（组/应用程序）/ Cen（面板）/ Loc（现场）/ Out（退出服务） |
| MODE | Aut / Man / Mtc（维护）/ Frc（强制） |
| STATUS | Starting / Run / Off |
| STOP REASON | QSP 组快停 / SSP 组顺序命令或 SeqStop / CSP 面板 / FSP 现场 / PSP 过程面板 / IOS 的 IOStatus 故障 / ME 的 ME 报警 / SQX 组顺序联锁 / IC / IB1-4 / IA / PD / **PCC-IC / PCC-IB / PCC-IA / PCC-PD** |
| BLOCK LIST | - 无 / IB1-4 / IA / FB1 / FB2 / PD（面板闭锁中） |

**报警文本参数**：M1→M1Txt、M2→M2Txt、M3→M3Txt、Local Stop→LcbStopTxt、Contactor Fault→FdBckTxt、FB1 Fault→FB1Txt、FB2 Fault→FB2Txt。未用 NLS（cBMI.AE.AE_NLS_Used=False）时 FB 类报警自动加后缀：

| 后缀 | 原因 |
|---|---|
| On | FBTime 后 FB 未 true |
| Trip | 运行中 FB 变 false |
| Off | FBTime 后 FB 未 false |
| Frc | 停止时 FB 变 true |

## 8. 仿真模式（官方）【核实-04手册p9 + 02手册p11】

- **组置仿真→属下所有消费者和基础对象强制仿真**；反馈（run/open/close）和输入信号被仿真（如 MC 电流仿真到设定高限的 0.8 倍），**命令和报警被禁用**；
- MCC 信号仍可逐对象测试：面板维护页签勾 "Allow Alarm In Simulation"；
- 基础对象（AIS/AIC/DIS/DIC）被阻塞并置正常值；
- **安全红线：仿真前必须断开 Profibus/Modbus 及一切到现场的接口**（数字/模拟输出在仿真中仍可能被激活）。

## 9. Project Constants 关键项【核实-04手册p37-38】

| 常量 | 默认 | 作用 |
|---|---|---|
| cBMI.MOT.DisableIAPDInLoc | true | 本地禁用 IA/PD |
| cBMI.MOT.DisableIBInLoc | true | 本地禁用 IB |
| cBMI.MOT.DisableIBInMaint | true | 维护禁用 IB |
| cBMI.MOT.DisableICInMaint | false | 维护是否禁用 IC |
| cBMI.MOT.DisableFPLLocIfLCBIsPOCMaster | true | LCB 是 POC 主时禁面板 Local |
| cBMI.MOT.EnFdBckFrcAlr | true | 强制运行反馈报警 |
| cBMI.MOT.IOS4StopMotor | true | IOStatus4 故障停电机 |
| cBMI.MOT.FieldStopIfNotRemOrLoc | true | 非 Rem/Loc 时现场停止 |
| cBMI.MOT.EnMaintInCenSeq / KeepMaintInCenSeq | false | Cen/Seq 下维护模式行为 |
| cBMI.MOT.EventStarting | false | 启动过程事件 |

## 10. MOT2 / MOTP / MOT1_VVVF 差异要点【核实-04手册p94/160/52】

- **MOT2**：双向；每方向独立 FB/联锁（IC/IA/PD 各 2）；过程联锁 4 个方向无关；除设备联锁外联锁方向相关；DirXFast 等快速任务方向用于定位停止【02手册p8】；
- **MOTP**：阀/挡板；两位限位反馈同时到=故障；**位置控制**：内/外给定、脉冲(1AI+2DO)或模拟(1AI+1AO)两种执行方式、设定值上下限、位置偏差报警；DirXFast 用于中停；
- **MOT1_VVVF**：MOT1+速度监视 FB3（Run/Off Speed Supervision，含独立参数与报警清单，04手册§4.4 p83-89）；应用示例：喂料秤闭环（§4.5 p90）。

## 11. CL 落地：MOT_C 映射表【CL 适配】

| CL MOT_C 设计 | 对齐官方 | 说明 |
|---|---|---|
| 参数 GrpStartStep/GrpStopStep/GrpStartDelay/GrpStopDelay | 同名同义 | 步号 1..999/1001..1999，0=不参加 |
| 参数 PreSelection | 同名同义 | 字符串语法照抄 `P1&P2\|P3&N4` |
| In.IC/IB1-4/IA/PD/Warning | 同名同义 | F163 现场三 lock 迁移：start_lock→IB（+IBF）、process_lock→IA、safety_lock→IC（唯一本地不释放） |
| In.EnSeqStart/EnSeqStop | 同名同义 | 软允许位，替代 V1 的 Perm_Start 散逻辑 |
| Out.Ord/FdBckRun | 同名同义 | F163 的 O2 硬件 DO = Ord；反馈超时=FdBckTime（替代 V1 T_StartMax/T_StopMax 的一部分） |
| Out.Rfs/NoInt/Trip/Run | 同名同义 | 组汇总直接用，不自己算 |
| Out.FirstOrMaxAETag/LastTripTxt | 同名同义 | 首报 tag + 上次跳闸描述，替代 V1 的 FaultTag/SigTag 自拟字段 |
| IO.ME/M1/M2/M3 | 同名同义 | F163 的热偶/断路器辅助→M1/M2/M3 |
| IO.FB1/FB2+FBTime | 同名同义 | 速度/压力/流量功能反馈（F163 现无，新增能力） |
| LCB 一组（LcbStart/Stop/Rem/Loc/Maint/Type） | 同名同义 | 就地箱接口标准化 |
| StwCen/StwField+STW 模块 | 同名同义 | 启动预告（V1 无） |
| EnAuto/AutoMode | 同名同义 | 温度/液位自动启停（F163 加热器场景直接可用） |
| MCHiLim+MC/MCNominal | 同名同义 | 电流高限警告（V1 无） |
| Grp*Override 四个 | 同名同义 | 调试/强制工具 |
| PanelLinkConsumer | 同名同义 | 面板接口一次到位 |

**F163 现场迁移注意**：MOTOR1 的 start_lock/process_lock/safety_lock 三个管脚语义（true=锁定）与官方 IC/IB/IA 一致（true=联锁生效），迁移是"改名+归位"：safety_lock→IC、start_lock→IB(IBF=1 时作启动联锁)、process_lock→IA。**MOTOR1 无 O2 管脚、O2 是硬件 DO 与 start_lock 相反**【F163 §4.4】——官方体系里对应关系：O2=Ord（启动命令输出）+ ME（主控制电压允许，false 禁报警）。

## 12. V1→V2 关键差异

| V1 自拟 | V2 官方 |
|---|---|
| 七态状态机自拟 | POC×Mode×Status 体系（Seq/Cen/Loc/OOS × Man/Auto/Maint × Starting/Run/Off） |
| 三 lock 管脚 | IC/IB1-4/IA/PD + PCC 联锁（RFS 后缀机制） |
| T_StartMax/T_StopMax 自管 | FdBckTime/FBTime + FB On/Trip/Off/Frc 后缀 |
| FaultTag/SigTag 自拟 | FirstOrMaxAETag/LastTripTxt + FirstOrMaxAEIndTr |
| EnSim 自拟仿真 | 组级强制仿真+0.8 高限电流+Allow Alarm In Simulation |
| 无启动预告 | STW 模块+StwCen/StwField |
| 无预选 | PreSelection 字符串+PreBin |
| 报警 10 条自拟 | 官方消息结构（POC/MODE/STATUS/STOP REASON/BLOCK LIST） |

## 13. 本篇结论

MOT1 的官方设计可以概括为：**一个 MOT1Data（In/Out/PCC/Panel 四组件）+ 77 个参数 + 四类联锁 + 一条结构化报警消息**。CL 库 MOT_C 照 §11 映射表落地，字段名与官方一致——现场调试时你报的参数名 ABB 支持人员听得懂，这就是双轨制的价值。
