---
title: MinLib拆解复用-阀门功能块VLV_C拆解V2（官方对齐）
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,VLV1,VLVNO1,Actuator,MOTP,阀门,参数表,FBErrorMode,联锁,报警]
summary: V2：官方阀门族选型（VLV1/VLVNO1/Actuator/MOTP）、VLV1全71参数、VLV1Data结构、OneCoil/FBErrorMode/CutOrd等阀门特有机制、双位反馈矛盾保护、CL落地映射
source: 04 Consumer Objects手册3BHS161557 RevD §8/§9/§10/§7
---

# 03 阀门功能块 VLV_C 拆解（V2）

> **V2 变更**：全部改为官方手册内容。V1 自拟的"双命令互锁/行程超时/阀位偏差"在官方体系里都有对应机制且更细（FBErrorMode 位掩码、SamePosDelay、CutOrd…）。
> 页码标注：[04手册pN] = Consumer Objects 手册第 N 页。

## 1. 阀门族选型【核实-04手册p195/215/233/160】

| 官方对象 | 管什么 | 关键能力 |
|---|---|---|
| **VLV1** | 常闭（NC）单向阀/执行器 | 1个MCC接口（Availability）；2个位置反馈（**同时到位=故障**，带延时）；1×IC+1×IA(Chain Auto)+2×过程联锁+1×PD；**单线圈/双线圈**（得电到位或持续带电）；开关次数累计 |
| **VLVNO1** | 常开（NO）单向阀/执行器 | 结构同 VLV1，逻辑取反；累计"开→关"操作次数 |
| **Actuator** | 调节阀（AO+位置测量） | 1个MCC接口；2个位置反馈（同时=故障）；**位置反馈开/关仿真（可配位置限值）**；方向性安全联锁+1设备联锁+方向性过程联锁；执行器速度监视+低速报警；位置偏差报警 |
| **MOTP** | 电动阀/挡板（电机驱动） | 见 02 文档 §10：位置控制（内/外给定、脉冲/模拟两种执行、设定值限值、偏差报警） |

**选型口诀：电磁阀/气动阀两位式 NC 用 VLV1、NO 用 VLVNO1；要连续阀位用 Actuator；电机驱动的闸板/挡板用 MOTP。**

## 2. VLV1 全参数表（71 项，官方原样）【核实-04手册p196-199】

### 2.1 标识/结构/组接口（同 MOT1 模式）

| # | 参数 | 类型 | 说明 |
|---|---|---|---|
| 1-2 | Name / Description | string[24]/[40] | Tag 名（允许 . -，禁空格:;）/描述 |
| 3 | IO | VLV1Data | in_out，每阀一个全局变量 |
| 4-5 | Stw / Group | STWData / GrpDrvCon | 接 STW / GROUP |
| 6 | GrpOpnStep | dint | 开步号 1..999，0=不参加组顺序 |
| 7 | GrpClsStep | dint | 关步号 1001..1999，0=不参加 |
| 8-9 | GrpOpnDelay / GrpClsDelay | time | 组顺序开/关延时 |
| 10 | PreSelection | string[50] | 预选分配，语法同 MOT1（`P1&P2\|P3&N4`） |

### 2.2 IO/MCC

| # | 参数 | 类型 | 初值 | 说明 |
|---|---|---|---|---|
| 11-14 | IOStatus1-4 | dint | 0 | IO 板状态（4=串口） |
| 15 | ME | bool | true | 主控制电压 OK，false 禁报警 |
| 16 | M1 | bool | true | 单独控制电压信号1（默认 Availability） |

### 2.3 阀门机构（本节是阀门块的核心）

| # | 参数 | 类型 | 初值 | 说明 |
|---|---|---|---|---|
| 17 | AlarmInClsPos | bool | false | true=阀在关闭位也产生报警 |
| 18 | **OneCoil** | bool | true | **单线圈=true；false=双线圈**。false 时：FBCls 报警是 Trip，且 FBErrorMode=0 下 Trip 活跃期间不发关命令 |
| 19 | FBinverted | bool | false | true=FBOpn=0 表示"开到位"（FBCls 同理）——常开型接线 |
| 20 | FBOpnEn | bool | true | true=有开限位开关；**false=开到位反馈被仿真** |
| 21 | FBOpn | bool | false | 开到位反馈信号 |
| 22 | FBOpnTxt | string[35] | 工程常量 | 开到位故障文本（NLS `\|\|AE_NLS_`） |
| 23 | FBClsEn | bool | true | true=有关限位；false=仿真 |
| 24 | FBCls | bool | false | 关到位反馈 |
| 25 | FBClsTxt | string[35] | 工程常量 | 关到位故障文本 |
| 26 | FBTime | time | 10s | FBOpn/Cls 响应最大延时 |
| 27 | **FBErrorMode** | dint | 工程常量 | 位掩码：**0=FBError 发 OrdCls**；仿真/动作细分：1=Full，2=OrdOpn 保持但非 RFS，4=OrdOpn，8=OrdCls，16=RFS Opn，32=RFS Cls，64=FBOpn，128=FBCls |
| 28 | SamePosDelay | time | 0.8s | 允许执行器在同一位置的延时（防两位反馈抖动误判） |
| 29-33 | LcbOpn/LcbCls/LcbRem/LcbLoc/LcbMaint | bool | false/true/… | 就地开脉冲/关命令/切POC/切Loc或Tst/维护 |
| 34 | LcbType | dint | 0 | 同 MOT1 五种型式 |
| 35 | **CutOrd** | bool | false | true=**到位（限位）后输出自动切断**（脉冲式控制，防线圈长带电） |
| 36-37 | OrdOpn / OrdCls | bool | out | 开/关命令输出（到接触器/电磁阀线圈） |

### 2.4 联锁/预告/模式/报警（同 MOT1 结构）

| # | 参数 | 说明 |
|---|---|---|
| 38-40 | PrevDrive/PrevDriveTxt/IATxt | 前序设备联锁+描述/IA 描述 |
| 41-43 | IB1Txt/IB2Txt/ICTxt | VLV1 为 2 个过程联锁（IB1/IB2）+IC |
| 44-45 | OpnTxt/ClsTxt | 开/关文本（如 forward/open/up、reverse/close/down） |
| 46-47 | StwCen/StwField | 启动预告触发条件 |
| 48-54 | AutoMode/EnAuto/EnSeq/EnCen/EnLoc/EnMaint/EnFPLClsInAllModes | 同 MOT1（54：false=常闭阀只能中控关） |
| 55-60 | ExtendedInfo/Class/AlarmTr/InterlockTr/ModeTr/StatusTr | 同 MOT1 |
| 61-66 | IOStatTxt/IOStat4Txt/METxt/M1Txt/LcbClsTxt/**OpnClsErrTxt** | **OpnClsErrTxt=开和关位反馈同时出现的错误文本** |
| 67-70 | GrpOpnOverride/GrpClsOverride/GrpTripOverride/GrpRFSOverride | 同 MOT1 |
| 71 | AlarmAck | 报警确认脉冲 |

## 3. VLV1Data 与联锁语义【核实-04手册p199-203】

- 四组件同 MOT1：In / Out / PCC / ProcessPanel；每阀一个全局变量；
- In 侧联锁：IC（全模式生效）/ IB1-2（本地释放）/ IA（不计 RFS）/ PrevDrive（PD，组保持 RFS）；
- **V1 自拟的"双命令互锁"官方解法**：OneCoil/CutOrd/FBErrorMode 三件套——双线圈阀 OneCoil=false 且 FBErrorMode=0 时 Trip 活跃期禁发关命令；CutOrd=true 到位自断输出； SamePosDelay 防抖；
- **V1 自拟的"行程超时"官方解法**：FBTime（FBOpn/Cls 响应最大延时）+ FB On/Trip/Off/Frc 四后缀报警（同 MOT1 机制）；
- **V1 自拟的"阀位偏差"官方解法**：Actuator/MOTP 的 Position Deviation Alarm（VLV1 无此功能——两位阀不需要）。

## 4. VLVNO1 与 Actuator 要点【核实-04手册p215/233】

- **VLVNO1**：常开阀。参数结构与 VLV1 相同（反馈/联锁/线圈逻辑镜像），操作累计方向相反（Open→Close 计一次）；
- **Actuator**：AO+位置测量；2 个位置反馈（同时=故障）；**位置反馈开/关仿真（可配位置限值）**——无位置反馈的调节阀也能调试；方向性 IC + 1 个 IB + 方向性 IA；**执行器速度监视+低速报警**（阀卡涩早期发现）；**位置偏差报警**（命令阀位 vs 实际阀位）；应用示例：调节阀闭环控制（04手册p262）。

## 5. Faceplate 与报警【核实-04手册p204-213】

- 按钮：Open / Close / Acknowledge / 切 POC（Seq/Cen/Loc）/ 切模式（Auto/Man）；
- Default View：Sim / Block / Tag+描述 / 阀状态（开/关/中间）/ Normal View / 报警指示 / 位置指示；
- 页签：Interlock / PCC / Alarm / Trend / Group（同 MOT1 结构）；
- 报警消息结构同 MOT1（[POC]+[MODE]+[STATUS]+[STOP REASON]+Blk:），阀门特有停止原因：OSP/CSP 等开/关来源 + **OpnClsErr（双位反馈故障）**；文本参数：M1/Local Close/OpnClsErr/FBOpn/FBCls。

## 6. CL 落地：VLV_C 映射表【CL 适配】

| CL VLV_C 设计 | 对齐官方 | 说明 |
|---|---|---|
| 参数 GrpOpnStep/GrpClsStep/Delay | 同名同义 | 开 1..999 / 关 1001..1999 |
| In.FBOpn/FBCls+En | 同名同义 | 无限位时 En=false 自动仿真（调试利器） |
| OneCoil/CutOrd/FBErrorMode | 同名同义 | 替代 V1 自拟互锁三重防护 |
| FBTime+四后缀 | 同名同义 | 替代 V1 T_OpenMax/T_CloseMax |
| SamePosDelay | 同名同义 | 两位反馈抖动防护 |
| OpnClsErrTxt | 同名同义 | 双位反馈矛盾报警 |
| IC/IB1-2/IA/PD | 同名同义 | 联锁语义同电机 |
| NC/NO 双模式 | VLV1/VLVNO1 两个官方块 | CL 用参数 EnNormallyOpen 合并（V1 的 EnLoop 思路保留但改官方语义） |
| 调节阀 | Actuator/MOTP | CL 拆两个变体：VLV_C(两位)+ACT_C(调节)，不合并成一个块 |

**F163 现场迁移**：VALVE1/PVALVE 的管脚语义与 VLV1/Actuator 对齐——VALVE1（两位阀）→VLV1；PVALVE（带阀位）→Actuator。现场现有描述文本直接搬进各 Txt 参数。

## 7. V1→V2 关键差异

| V1 自拟 | V2 官方 |
|---|---|
| EnLoop 一个块双模式 | VLV1/VLVNO1（两位）+ Actuator/MOTP（阀位）官方分块 |
| 双命令互锁软件仲裁 | OneCoil+CutOrd+FBErrorMode 机构级机制 |
| T_OpenMax/T_CloseMax | FBTime+FB On/Trip/Off/Frc |
| DeadBand 自拟死区 | Actuator/MOTP 的 Position Deviation Alarm |
| 无线圈类型概念 | OneCoil 单/双线圈+得电到位或持续带电 |
| 无限位仿真概念 | FBOpnEn/FBClsEn=false 自动仿真 |

## 8. 本篇结论

阀门族的官方设计比电机多一个"机构层"：**线圈型式（OneCoil）、输出方式（CutOrd）、故障模式（FBErrorMode 位掩码）、限位仿真（FBxEn）**四件事参数化。CL 库 VLV_C 按 §6 映射落地，两位阀和调节阀分开两个块，别学 V1 硬合并。
