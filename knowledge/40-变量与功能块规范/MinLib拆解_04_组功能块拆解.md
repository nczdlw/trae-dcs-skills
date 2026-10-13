---
title: MinLib拆解复用-组功能块GRP_C拆解V2（官方对齐）
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,Group,SubGroup,DriveGroup,GrpCycleCtrl,Prebin,STW,GroupConnect,步号,预选,主备]
summary: V2：官方组族七对象选型、GROUP全34参数、GrpInput/GrpOutput/GrpDrvCon结构、步号规则（1-999/1001-1999/2001-2999）、Step Viewer/Status Viewer列定义、周期组/预选/启动预告/GroupConnect、CL落地映射
source: 05 Group Objects手册3BHS161561 RevD §1-9 + 00产品指南§3.3
---

# 04 组功能块 GRP_C 拆解（V2）

> **V2 变更**：全部改为官方手册内容（05 Group Objects，3BHS161561 RevD）。V1 自拟的"前沿法步进/EnCyclic/SEL_C"分别被官方**步号规则/GrpCycleCtrl/Prebin**取代。
> 页码标注：[05手册pN] = Group Objects 手册第 N 页；[00手册pN] = 产品指南。

## 1. 组族选型【核实-05手册p5/22/48/53/79/98/109/111】

| 官方对象 | 管什么 | 独有功能 |
|---|---|---|
| **GROUP** | 顺序启停组成员（最多 999 个电机/阀） | 首步保持/首步未停监视；**Duty Standby 2 个执行周期内自动重启**；POC 传递三选一；预选成员汇总；启停超时报警；1×IC+1×IA+4 启动+4 停止联锁；快停；Hold；Show Tag/Member/Steps；仿真；Auto；无条件启动；当前步剩余时间；Process Panel；STW 整组可配 |
| **SubGroup** | GROUP 全部功能+**作为成员挂到上级 GROUP** | 组总线；可配启停步和预选；PCC 接 IO.PCC（GROUP 是接 IOGrpDrvCon.PCC） |
| **DriveGroup** | 主辅设备工艺驱动（大皮带等） | 1 条组总线上级+**2 条独立总线（辅/主）**；辅/主汇总独立；4 过程联锁+1 PD；PreselectionX/Y；辅设备可配随主组立即启动（不等步号）；**不支持启停联锁和 Process Panel** |
| **GrpCycleCtrl** | 组成员周期启停（料仓充氮、润滑冷却等） | **脚本化周期激活**；程序选择器 3 程序；1×IC+1×IA+2 启动+1×PD；2 外报警+2 外警告；周期时间监视；连续或定周期数执行；面控/程序控制下一步 |
| **Prebin** | 预选：激活/去激活一个或一组组成员 | 路由（按 Silo1 选一片设备）+ **参数化 Duty Standby**（冗余泵/倒仓）；RFS 监视释放预选；StandbyPreselected 状态；与组联锁 1oo3/2oo3 紧耦合；预选变更需组重启 |
| **STW** | 启动预告（单个消费者或组） | 先响蜂鸣/闪光再给启动释放；按 POC 配置（Seq/Cen 有预告、Loc 无） |
| **GroupConnect_2/4/8** | **一个消费者挂到多个组（最多8个）** | 仅 2 根连接转发全部 GCC 总线信息 |

## 2. GROUP 全参数表（34 项，官方原样）【核实-05手册p23-24】

| # | 参数 | 类型 | 初值 | 说明 |
|---|---|---|---|---|
| 1-2 | Name / Description | string[24]/[40] | | 组 tag（允许 . -，禁空格:;）/描述 |
| 3 | IOGrpDrvCon | GrpDrvCon | default | in_out **组-驱动连接变量（只连消费者，禁应用程序读写！）** |
| 4 | IOIn | GrpInput | default | in_out 组输入变量 |
| 5 | IOOut | GrpOutput | default | out 组输出变量 |
| 6 | StwMode | dint | 1 | 0=禁 STW；1=正常；2=预选切换不预告；3=standby 切换不预告 |
| 7 | StwFirst | bool | false | false=各电机自己预告；**true=全部预告先执行完再走第一步** |
| 8 | SeqALEn | bool | true | 顺序运行时间监视使能（超时后保持） |
| 9 | SeqALTime | time | 5min | 顺序运行时间监视值 |
| 10 | ChngOver | bool | true | **组启动结束时自动停掉全部未预选设备**（路由切换核心） |
| 11 | ICTxt | string[35] | | IC 安全联锁描述（IC 是 RUN 联锁，执行正常停） |
| 12-15 | StartInt1-4Txt | string[35] | | 4 个启动联锁描述 |
| 16-19 | StopInt1-4Txt | string[35] | | 4 个停止联锁描述 |
| 20 | IATxt | string[35] | | IA 链式联锁描述（RUN 联锁，正常停） |
| 21 | ExtendedInfo | dint | 6 | 多路：1 ConsumerExt/2 报警表/4 事件表/8 详图/16 状态/32 趋势/64 面板 |
| 22-24 | Class / AlarmTr / InterlockTr | dint | 1 | AE 类 1..9999；报警/联锁处理 1/2/3=ALPrio# |
| 25-26 | ModeTr / StatusTr | bool | true | 模式/POC 变化、状态变化产生事件 |
| 27 | EnAuto | bool | false | 组 Auto 模式（顺序停+延时） |
| 28 | EnSeq | bool | false | POC Sequence 使能 |
| 29 | SetSeqMode | dint | 1 | 组启动时设消费者 POC：0=立即全设/1=到该设备步才设/2=从不 |
| 30-31 | EnCen / EnLoc | bool | true | POC Central / Local 使能 |
| 32 | EnForceLoc | bool | false | 组在 Local 时自动把全部成员改 Local |
| 33 | ChngLcTsNotStrdOnly | bool | false | true=组停时才允许切 Local |
| 34 | AlarmAck | bool | | 脉冲，确认报警 |

## 3. GrpInput / GrpOutput / GrpDrvCon【核实-05手册p24-33】

- **GrpInput**：SeqStart（切 SEQ 并无启动联锁则启动）、SeqStop（切 SEQ 并无停止联锁则停）、SeqHold（把启/停中的组置 HOLD）等；
- **GrpOutput**：组状态/首步保持/当前步号与 tag/剩余时间等；
- **GrpDrvCon**：**严格只用于连消费者对象；应用程序读写会致组故障**【05手册p24】——这是官方红线，CL 库照抄这条警告。

## 4. 步号规则（顺序的唯一配置源）【核实-05手册p9-10】

| 步号 | 含义（GROUP） |
|---|---|
| 0 | 组不启/不停本设备（快停除外） |
| 1–999 | **启动和切换启动序列中按升序执行** |
| 1001–1999 | **停止序列和切换启动后按降序执行** |
| 2001–2999 | 停止序列中**在切换启动之前**按降序执行 |

要点：①步号**不必连续**，空号自动跳过；②**建议默认增量 10**（10/20/30…），留空位以后插设备不改配置；③可以给 GrpStopStep 配 1 让电机在组**启动序列中**就停掉（切换场景）；④**顺序配在消费者参数上**（GrpStartStep/GrpStopStep/Delay/PreSelection），组对象只汇总【05手册p8】。

## 5. 组行为要点（官方）【核实-05手册p11-13 + 00手册p37-46】

- **单步调试**：扩展面板 Next/Previous 按钮逐步走启动/停止步——测试顺序神器；组重启的切换停止序列不能用 Next 步进；
- **错误+standby**：启动或运行中设备跳闸→组尝试启动 standby 设备；standby 也起不来→按无 standby 流程（Hold + 面板显示故障设备名+链接）；
- **顺序超时**：SeqALEn+SeqALTime 超时组保持并报警；
- **Show Tag / Show Member / Show Number of Steps**：流程画面上显示成员 tag、高亮成员+步号、显示步数；
- **Auto 模式**：组顺序停+延时（区别于消费者 Auto 的 IA 驱动）；
- **无条件启动**：绕过组 RFS（启动联锁/IC/预选缺失仍有效除外）；
- 预选五态、on-the-fly 切换、radio-button、启停中禁改——见 00 文档 §2.5【核实-00手册p40-41】。

## 6. 两个 Viewer（官方列定义）【核实-05手册p18-21】

**Group Step Viewer**（GROUP/SubGroup/DriveGroup 都有，面板顶部 Aspect Link 进入；**需先用 Uploader 灌 Functional Structure**：对象名唯一+Name Uploader 执行+应用已下载+OPC 数据可用）：

| 列 | 内容 |
|---|---|
| Object Name / Description | 对象名/描述（同面板） |
| Status | 步骤状态（含预选和运行/停止）：Selected to <Action> / Standby to <Action> / <Action>（进行中）/ <Action> (not selected) / <Action> out of Service / <Action> not controlled（被别的组管着） |
| Step | 组顺序步号 |
| Delay Time | 启动时该步等待延时 |

默认只显示预选步；取消"Show only Preselected Steps"看全部。

**Status Viewer**（GROUP/SubGroup/DriveGroup/GrpCycleCtrl，扩展面板进入）：列成员+全部 PCC 信号+组自身：

| 列 | 内容 |
|---|---|
| Name / Description | 对象名/描述 |
| Type | 对象类型（group/motor/valve/PID/subgroup…） |
| Status | 当前状态（on/off/RFS/running…） |
| Alarm / Intlk / Blk | 有报警 / 有活动联锁 / 有闭锁 |
| Control | POC（Cen/Seq/Loc） |
| Mode | Man/Auto |

点对象名直达对应面板；'+'展开子对象（如信号挂在消费者下）。

## 7. 其余组对象要点

- **SubGroup**：PCC 信号必须接 IO.PCC，**不能**用 GrpDrvCon.PCC（GROUP 相反）【05手册p48】；
- **DriveGroup**：辅/主两条总线独立汇总；辅设备可配随组立即启动；无启停联锁、无 Process Panel【05手册p53】；
- **GrpCycleCtrl**：脚本周期（如料仓充氮）；3 个程序选择器；连续或定周期数；下一步可面控/程控【05手册p79】；
- **Prebin**：路由=按目标（Silo1）一片设备预选；**Duty Standby 参数化**（冗余泵、倒仓）；预选释放需全部成员 RFS；与组联锁 1oo3/2oo3 紧耦合；预选变更需组重启【05手册p98】；
- **STW**：先蜂鸣/闪光后释放启动；按 POC 配置；面板和流程画面上有符号【05手册p109】；
- **GroupConnect_2/4/8**：一个消费者最多挂 8 个独立组，2 根连接转发全部 GCC 信息【05手册p111】。

## 8. CL 落地映射【CL 适配】

| CL 设计 | 对齐官方 | 说明 |
|---|---|---|
| GRP_C | GROUP | 34 参数照抄；IOGrpDrvCon 禁写警告保留 |
| GRP_C 步号 | 官方步号规则 | **废弃 V1"前沿法"**：启动 1-999 升序、停止 1001-1999 降序、切换前停 2001-2999；增量 10 惯例 |
| PRE_C | Prebin | 路由+主备合一，替代 V1 SEL_C |
| STW_C | STW | 新增（V1 无） |
| SUB_C | SubGroup | 子组挂上级（V1 无） |
| GRPCYC_C | GrpCycleCtrl | 周期组（替代 V1 EnCyclic 参数） |
| GCX_C | GroupConnect_2/4/8 | 一消费者多组（V1 的"多父"设想落地） |
| ChngOver 参数 | 同名同义 | 路由切换自动停未选设备 |
| SetSeqMode | 同名同义 | 组启动时消费者 POC 设置策略 |
| StwFirst/StwMode | 同名同义 | 预告策略 |

**F163 现场迁移**：
- GROUP1 的 CON/COFF 单周期脉冲【F163 §4.6】→ 官方 `GrpInput.SeqStart/SeqStop`（同样切 POC 到 SEQ 并启/停，语义一致）；
- G10 的 AUX_RUN 派生（`AUX_RUN = G30_RUN AND G50_RUN AND G40_ENABLED AND G55_RUN`，单级 STEP=1【F163 §4.6】）→ 官方做法：G10 组 4 个消费者 GrpStartStep 全配 10（同步号并列同启），组汇总状态直接来自成员 Rfs/Run，不重算内部条件；
- G_start/G_stop Boolean16 位操作【F163 §4.6】→ 淘汰，改 GrpStartStep/GrpStopStep+PreSelection。

## 9. V1→V2 关键差异

| V1 自拟 | V2 官方 |
|---|---|
| 16 槽位数组 | 最多 999 成员 |
| 前沿法排序 | 步号三段规则（1-999/1001-1999/2001-2999） |
| 自拟周期模式 | GrpCycleCtrl 独立块 |
| SEL_C 主备 | Prebin（预选即主备/路由，2 周期内自动重启） |
| 无启动预告 | STW 模块 |
| 自拟 FirstFaultTag 锁存 | 官方组面板"第一个不运行消费者"+链接 |
| 无单步调试 | Next/Previous 单步 |
| 无无条件启动/Show Tag/Member | 官方全有 |

## 10. 本篇结论

官方组体系的灵魂是**"顺序配在消费者上，组只汇总"**：加设备=拖消费者块+配 GrpStartStep（按 10 的增量），删设备=步号清 0，改顺序=改步号——代码零改动。CL 库 GRP_C 照 §8 映射落地，步号规则和 GrpDrvCon 禁写红线一条都不改。
