---
title: MinLib拆解复用-报警处理框架
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,报警,AlarmCond,抑制,首报,standby降级,800,500]
summary: MinLib四条报警规则核实与落地：组停抑制/启动抑制/本地自动确认/standby降级+首报转发；AlarmCond架构；三类功能块报警清单模板
source: 数据表 p5 + ABB官网2019 + F163规则总纲 §5.9
---

# 06 报警处理框架

> MinLib 报警体系是它区别于普通库的核心之一。规则全部来自数据表 p5【核实】，落地方式是【自拟】。
> 项目现状：F163 用 `AlarmCond`（Severity 800 重报警 / 500 警告，不支持 CondName）【F163 §5.9】——CL 库沿用同一底座，不引新块。

## 1. 四条报警规则（核实 → 落地对照）

| # | MinLib 规则【核实，数据表 p5】 | CL 库落地 |
|---|---|---|
| R1 | 父对象停止 → 只报活动父的报警（组停=设备报警不弹） | AlmEnable 串联 `Grp.GroupActive` |
| R2 | 父对象启动中 → 启动报警抑制期 | AlmEnable 串联 `NOT (Grp.GroupStarting AND InInhibit)` |
| R3 | 本地控制模式 → 自动确认 | `Local AND EnAckLocal` → 报警自动确认（不打断操作员） |
| R4 | standby 消费者 → 自动降低严重度 | `EnStandby` → Severity 由 800 降 500（或按参数全抑制） |
| R5 | 首报 + 最高优先级报警 → 转发到 consumer 和 group | 设备级 FirstFault 锁存 + 组级 FirstFaultTag 锁存（04 文档 §6） |
| R6 | 2019 新版：按过程状况自动降级 + 报警形状/颜色冗余编码 | 面板三重编码（05 文档 §1）；"过程状况"降级先落 R4，细化的按工况降级留二期 |

## 2. 抑制逻辑公式（每个 FBT 内统一）

```
(* 抑制总线：任何一条为 TRUE，对应报警不进报警清单 *)
Inhib_GroupStop   := NOT Grp.GroupActive;                    (* R1 *)
Inhib_Starting    := Grp.GroupStarting AND (T_Now < Grp.StartInhibitEnd); (* R2 *)
Inhib_Local       := Local_Eff AND EnAckLocal;               (* R3 *)

(* 每条报警的使能 *)
AlmEnable[i] := Cond[i] AND NOT Inhib_GroupStop AND NOT (Inhib_Starting AND AlarmInStartInhibit[i]);
```

- `Grp.StartInhibitEnd`：组启动开始时刻 + `T_StartInhibit`（组参数，默认 = T_StepMax×2+5s，覆盖最慢两步）；
- `AlarmInStartInhibit[i]`：该报警是否属于"启动瞬态类"（A6 启动被禁止、A7 反馈闪断、A5 过程联锁、SIG 的警告级）——TRUE 的才被启动抑制；**重报警（启动失败/跳闸）永不被抑制**；
- R3 自动确认的实现：`AlarmCond` 的 Ack/Enable 引脚组合【需实测确认 6.1.0 AlarmCond 是否有 Ack 引脚；没有就用"Enable=FALSE 时报警根本不产生"的等效做法】。

## 3. 严重度与文本

| 项 | 规则 |
|---|---|
| 重报警 Severity | 800（跳闸/失败类，必须人工确认）【F163 §5.9】 |
| 警告 Severity | 500（异常但未停机）【F163 §5.9】 |
| standby 降级 | 800→500；参数 `EnStandbyAlmMode`：0=降级 1=全抑制 |
| 文本 | EN+CN 双段：`Start fail / 启动失败 - <TagNo>`；AlarmCond 不支持 CondName【F163 §5.9】，动态部分（TagNo）靠消息体拼接或静态化，**拼接可行性需实测确认**；不行就每条报警一个静态文本实例 |
| 形状冗余 | 报警符号必须带形状（▲/⬣），不只变色（05 文档 §1） |

## 4. 三类功能块报警清单模板

> 电机/阀门明细见 02/03 文档 §7，这里给"组 + 通用"补齐，并统一六要素：**触发/延时/Severity/文本/抑制/转发**。
> 转发列：C=转发 consumer（设备面板），G=转发 group（组面板首报），V=进 viewer。

### 4.1 组级报警（GROUP_C）

| # | 名称(EN/CN) | 触发 | 延时 | Sev | 抑制 | 转发 |
|---|---|---|---|---|---|---|
| G1 | Group start fail / 组启动失败 | 启动过程首报设备未 RUN | T_StepMax | 800 | 无（永不被抑制） | G,V |
| G2 | Group stop fail / 组停止失败 | 停止过程设备未停 | T_StepMax | 800 | 无 | G,V |
| G3 | Group fault / 组故障 | 运行中任一设备 Fault | 0 | 800 | 无 | G,V |
| G4 | First fault / 首报 | 锁存 FirstFaultTag 时刻 | 0 | 800 | 无 | G,V |
| G5 | Equip standby active / 备用设备在运 | 主设备故障切备 | 0 | 500 | R1 | C,G |
| G6 | Cyclic idle / 周期间歇 | 进入 T_CycleIdle | 0 | 事件 | R1 | V |
| G7 | Local mode / 组就地 | 组本地操作 | 0 | 事件 | — | V |
| G8 | Simulation active / 组仿真中 | EnSim=TRUE | 0 | 事件 | — | V |

### 4.2 信号级报警（SIG_C）

| # | 名称(EN/CN) | 触发 | 延时 | Sev | 抑制 | 转发 |
|---|---|---|---|---|---|---|
| S1 | Warn limit / 警告值 | 超 ThrWarn | DelayWarn | 500 | R1/R2/R3/设备 MAINT | C,V |
| S2 | Fault limit / 故障值 | 超 ThrFlt | DelayFlt | 800 | R1/设备 MAINT | C,G,V |
| S3 | Override active / 旁路中 | Override=TRUE | 0 | 事件 | — | C,V |
| S4 | Override expired / 旁路到期 | OvrdLeft 到 0 | 0 | 事件 | — | C,V |
| S5 | Sensor fault / 传感器故障 | 信号超量程/断线（AI） | T_FltDb | 800 | 设备 MAINT | C,V |

### 4.3 抑制规则适用矩阵

| 报警类 | R1 组停抑制 | R2 启动抑制 | R3 本地确认 | R4 standby |
|---|---|---|---|---|
| 启动/停止失败、跳闸、首报 | ✗ 永不 | ✗ 永不 | ✗ 永不 | ✗ 不降 |
| 过程联锁、警告值 | ✓ | ✓（仅瞬态类） | ✓ | ✓ 降级 |
| 旁路、就地、检修、仿真 | — 事件 | — | — | — |

## 5. 首报链路（两级导航，数据表 p2/p4【核实】）

```
设备故障/联锁越限
  → 设备锁存 SigTag（哪个信号惹的）+ FirstFault=TRUE
  → 组锁存 FirstFaultTag（哪个设备惹的，按 StepNo 取最前）
  → 组面板大字显示 FirstFaultTag，点击 → 设备面板
  → 设备面板显示 SigTag，点击 → 信号面板
  → 信号面板显示阈值/延时/类型/旁路状态
```

五步之内从"组停了"定位到"哪个信号的哪个阈值"，全程鼠标点击，不翻代码。

## 6. 落地检查清单

1. [ ] 每个 FBT 内 AlarmCond 实例数 = 报警清单条数，实例在 Code 段被调用（防 Warning 1542【F163 §5.5】）
2. [ ] Severity 只用 800/500 两档，事件类用 SimpleEventDetector（停止事件需手动反逻辑 + prev_running 末尾更新【F163 §5.9】）
3. [ ] 每条报警按 §2 公式接抑制总线，不许有"裸"报警
4. [ ] 首报锁存/清除逻辑与 04 文档 §6 一致
5. [ ] 面板报警符号带形状（05 文档 §1）
6. [ ] AlarmCond 的 Ack 引脚、消息文本拼接能力——【需实测确认】后回填本节

## 7. 本篇结论

报警框架=**四条抑制规则（R1~R4）+ 一条首报链路 + 两档严重度**。写代码时每条报警先过 §2 的抑制公式再过 §4.3 的矩阵，两个都过才允许接 AlarmCond。目标：操作员在报警清单里看到的每一条，都是"现在真该处理的"。
