---
title: MinLib拆解复用-仿真与调试检查框架
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,仿真,softcontroller,培训,commissioning,调试检查,CHK_C]
summary: 三级仿真设计（设备/组/系统）、硬件屏蔽路径、四个故障注入演练场景；CHK_C调试检查状态机、组级进度汇总、升级重验机制
source: 数据表 p5 + ABB官网2019 + F163规则总纲 §3.6
---

# 07 仿真与调试检查框架

> MinLib 两件上线神器：**内置仿真**（数据表 p5：built-in simulation on soft controller；operator training with built-in simulation【核实】）和 **commissioning check framework**（官网 2019：缩短调试时间、跟踪现场进度、保证升级演进【核实】）。本篇给出两者的【自拟】落地设计。

## 1. 仿真模式设计

### 1.1 三级仿真

| 级 | 开关 | 范围 | 用途 |
|---|---|---|---|
| 设备级 | MOTOR_C/VALVE_C 的 `EnSim` | 单台设备 | 单点调试 |
| 组级 | GROUP_C 的 `EnSim` | 整组（下传所有 Enable 设备） | 组态演练、操作员培训 |
| 系统级 | 800xA soft controller 全仿真 | 整个控制器 | FAT/出厂测试、大规模演练 |

组级 EnSim 是源：置 TRUE 时组通过 EqCmds 把所有设备 `EnSim` 置 TRUE（链路：组 S01→EqCmds[i] 扩展字段 `EnSimDown`——加进 CC_EqCmd，01 文档 §2.1 补一个字段）。

### 1.2 硬件屏蔽路径（核心：仿真时一根输出都不许碰现场）

每个 FBT 的输出段（S07）统一模式：

```
(* 仿真隔离：所有物理输出只在本设备非仿真时写 *)
IF NOT EnSim THEN
    物理DO_Run  := DO_Run_Calc;
    物理DO_Stop := DO_Stop_Calc;
    物理AO_Out  := AO_Out_Calc;
ELSE
    物理DO_Run  := FALSE;      (* 仿真=输出强制关断 *)
    物理DO_Stop := FALSE;
    物理AO_Out  := 0.0;
END_IF;
```

- 输入侧（S02）反向替换：`RunFb_Eff := EnSim ? Sim_RunFb : RunFb_DB;`
- **双保险**：面板仿真指示（⚠）+ 组级 GrpOut 里带仿真计数，任何设备仿真中在组面板和总貌上可见；
- 掉电保持：`EnSim` 是否 retain【需实测确认】——若不 retain，断电重启自动退出仿真（更安全，推荐）；若 retain，启动段加"上电仿真提醒"事件。

### 1.3 故障注入演练场景（培训四课）

| 课 | 场景 | 操作 | 学员应看到 |
|---|---|---|---|
| 1 | 启动失败 | 组启动，某设备 EnSim+Sim_RunFb=FALSE | 启动超时报警 A1→组首报→组面板 tag→超链接到设备 |
| 2 | 运行中跳闸 | 运行中置 Sim_Fault=TRUE | A3 报警→状态 FAULT→组 G3→首报链路→联锁 viewer 显示 |
| 3 | 联锁越限跳停 | 信号仿真值超 ThrFlt | 信号 S2→设备跳停→A4/A5→viewer 旁路列状态 |
| 4 | 主备切换 | SEL_C 主设备 Sim_Fault | 自动切备→G5 备用在运→旧主 FirstFault 锁存 |

每课配"期望现象清单"，学员对照打勾——培训记录直接进调试检查档案（§3）。

### 1.4 仿真纪律（红线）

1. 仿真标志**上画面**：任何设备/组仿真中，总貌和组面板有显著 ⚠ 标识；
2. **下载前全清**：09 文档核对清单有专列"所有 EnSim=FALSE"；
3. 仿真参数（Sim_*）在线可改但**改后必须改回**，参数表里 Sim_* 默认值全部为安全态（FALSE/0/关位）；
4. F163 现场纪律不变：未经仿真验证不得在线下载【F163 §3.6】。

## 2. CHK_C 调试检查框架

### 2.1 官网核实功能 → 落地

| 官网 2019【核实】 | 落地 |
|---|---|
| 缩短调试时间 | 检查项预定义在库里，现场只执行不编写 |
| 跟踪现场进度 | CHK_C 状态机 + 组级 ChkDone/ChkTotal 进度 |
| 保证升级演进 | 检查项带库版本号，升级后重置待重验（§2.5） |

### 2.2 CHK_C 块设计

**管脚**

| 管脚 | 方向 | 类型 | 说明 |
|---|---|---|---|
| Cmd_Start | in | Bool | 开始当前检查项（脉冲） |
| Cmd_Pass | in | Bool | 人工判定通过（脉冲） |
| Cmd_Fail | in | Bool | 人工判定失败（脉冲，须填原因） |
| Cmd_Skip | in | Bool | 跳过（脉冲，须填原因） |
| Cmd_Abort | in | Bool | 中止（脉冲） |
| ChkState | out | Int | 0 IDLE/1 RUNNING/2 PASS/3 FAIL/4 SKIP |
| ChkStep | out | Int | 当前检查项号（1..N） |
| ChkTotal | out | Int | 检查项总数 |
| ChkNote | out | String[60] | 失败/跳过原因（人工输入） |

**参数**：`LibVer`（String[16]，库版本，如 "1.0.0"）、`EnRec`（是否记录事件）。

**状态机**：`IDLE --Cmd_Start--> RUNNING --Cmd_Pass--> PASS(记事件,Step+1,回IDLE)`；RUNNING 可 Cmd_Fail→FAIL（停留待处理）或 Cmd_Skip→SKIP 或 Cmd_Abort→IDLE；FAIL 后 Cmd_Start 重跑本项。

### 2.3 检查项库（预定义，每设备 10 项，内容见 02/03/04 文档 §10）

检查项存放在 CHK_C 外挂的"检查卡"（每 FBT 一份 MD 卡 + 面板上的当前项文字提示）：CHK_C 的 `ChkStep` 对应卡上第 N 项，面板显示当前项的"操作步骤+通过判据"，执行完人工按 Pass/Fail。

```
面板示意（调试模式）：
┌───────────────────────────────┐
│ 调试检查 3/10   [库版本 1.0.0]   │
│ 本项：C3 启动超时               │
│ 步骤：T_StartMax 设 2s，启动，   │
│       不给运行反馈               │
│ 判据：A1 启动失败报警出现，状态   │
│       =FAULT                    │
│ [通过] [失败+原因__] [跳过__]    │
└───────────────────────────────┘
```

### 2.4 组级进度汇总

- 组扫描 16 槽位各设备的 ChkState：`ChkDone = count(PASS or SKIP)`、`ChkTotal = Σ 各设备项数`；
- 组 viewer 加"调试"列（PASS✓/FAIL✗/进行中/SKIP-）；
- 现场日报直接看组 viewer 底部：`调试 27/40｜失败 2｜跳过 1`——失败项双击跳该设备检查卡。

### 2.5 升级重验机制（ensure upgrade evolution【核实】）

1. 每个 FBT 带 `LibVer` 参数；CHK_C 启动时比对"当前库版本"与"上次通过时的版本"（存事件/历史里）；
2. 版本不一致 → 该设备全部 ChkState 重置 IDLE，viewer 显示"待重验"；
3. 重验只跑**受升级影响的检查项**（升级说明里列出影响项号），不用全跑；
4. 全部 PASS 后版本戳更新——升级闭环。

### 2.6 检查记录

- 每次 Pass/Fail/Skip 发一条事件（SimpleEventDetector，文本含 TagNo+项号+结果+原因【F163 §5.9】）；
- 记录落 800xA 事件/历史库，调试报告按时间过滤导出【导出格式需实测确认】；
- CHK 记录与报警记录分开类型，方便筛。

## 3. 仿真 × 调试联动（典型现场流程）

```
① 到场：soft controller 上电，整组 EnSim
② 单机：逐台设备跑 C1~C10（仿真注入）
③ 组态：CON 脉冲启组，验证顺序/首报/周期
④ 联锁：信号仿真值扫阈值，验证 viewer 与抑制
⑤ 培训：操作员过四课（§1.3）
⑥ 摘仿真：逐个设备 EnSim=FALSE，核对清单打勾
⑦ 真机：从 C1 重跑到全 PASS（真信号）
⑧ 移交：viewer 调试列全 ✓，报告导出
```

## 4. 本篇结论

仿真解决"**不敢动**"——软控制器上把故障演一遍，操作员见过才不怕；调试检查解决"**没验过**"——每台设备 10 项、每组一张 viewer、每次升级一次重验。两件都内置在库里，现场只执行不开发。CC_EqCmd 记得补 `EnSimDown` 字段（01 文档 §2.1）。
