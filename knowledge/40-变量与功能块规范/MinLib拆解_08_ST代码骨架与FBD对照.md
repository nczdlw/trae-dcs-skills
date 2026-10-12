---
title: MinLib拆解复用-ST代码骨架与FBD对照
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,ST,代码骨架,分段编号,中文注释,MOTOR_C,GROUP_C,FBD]
summary: MOTOR_C与GROUP_C可直接抄的ST骨架（S01-S09分段编号+中文注释+中文逻辑对照表）、工程侧布尔连锁示例、FBD管脚连线清单、规则符合性自检
source: 02/04文档 + F163规则总纲 §4.1/§4.2/§5
---

# 08 ST 代码骨架与 FBD 对照

> 本篇是"拿过去用"的代码层。所有骨架遵守 F163 §5 全部编码规则（自检清单见 §5）。
> 骨架是**起点不是终点**：抄进 Control Builder 后先编译，按报错逐项修；标【需实测确认】的是我没有现场验证过的语法/引脚。

## 1. MOTOR_C ST 骨架（FBT 内部代码）

```st
FUNCTION_BLOCK MOTOR_C
(* ============================================================
   MOTOR_C 通用动力设备块（电机/风机/泵/加热器）
   库 CEMENT_LIB 1.0.0 | 设计依据 02-电机功能块拆解.md
   分段：S01 输入去抖 / S02 仿真注入 / S03 模式判定 / S04 联锁汇总
        S05 命令仲裁 / S06 状态机 / S07 输出驱动 / S08 报警生成 / S09 统计上报
   规则：无位运算；字符串/时间字面量只出现在 VAR 初值；
         引脚名大小写敏感；所有实例必须被调用
   ============================================================ *)

VAR_INPUT
    DI_RunFb: BOOL;                    (* 运行反馈（工程侧 DintIO.Value 接入） *)
    DI_Fault: BOOL;                    (* 故障跳闸 *)
    DI_Ready: BOOL;                    (* 就绪/远程 *)
    DI_Local: BOOL;                    (* 就地状态 *)
    Cmd_Start: BOOL;                   (* 启动命令（脉冲） *)
    Cmd_Stop: BOOL;                    (* 停止命令（脉冲） *)
    Cmd_Reset: BOOL;                   (* 故障复位（脉冲） *)
    Cmd_Maint: BOOL;                   (* 检修挂牌 *)
    ChkPass_In: BOOL;                  (* 调试检查通过（外部 CHK_C 实例写入） *)
    Lock_Start: BOOL;                  (* 启动联锁 TRUE=锁定 *)
    Lock_Process: BOOL;                (* 过程联锁 TRUE=锁定 *)
    Lock_Safety: BOOL;                 (* 安全联锁 TRUE=锁定 *)
    O2_Perm: BOOL;                     (* 输出允许（无独立回路时置 TRUE） *)
    EqCmd: CC_EqCmd;                   (* 组→设备命令通道（主父槽位） *)
    Grp: CC_Group;                     (* 所属组汇总（报警抑制数据源） *)
    Sig: ARRAY[1..8] OF CC_SigOut;     (* 联锁信号（0=未用槽位） *)
END_VAR

VAR_OUTPUT
    EqStat: CC_EqStat;                 (* 设备→组状态通道 *)
    SigIn: CC_SigIn;                   (* 回读给信号块 *)
    DO_Run: BOOL;                      (* 运行命令（工程侧赋硬件 DO） *)
    DO_Stop: BOOL;                     (* 停止脉冲输出 *)
END_VAR

VAR
    (* ===== 参数区（在 Control Builder 中把这些变量标记为 Parameter）===== *)
    T_StartMax: TIME := T#5s;          (* 启动反馈超时 *)
    T_StopMax: TIME := T#5s;           (* 停止反馈超时 *)
    T_FbDb: TIME := T#100ms;           (* 反馈去抖 *)
    T_FltDb: TIME := T#500ms;          (* 故障去抖 *)
    T_RunMin: TIME := T#0s;            (* 最短运行时间 *)
    T_Restart: TIME := T#0s;           (* 防重复启动延时 *)
    T_SafetyDb: TIME := T#1s;          (* 安全联锁确认延时 *)
    T_SecTick: TIME := T#1s;           (* 运行时长统计节拍 *)
    EnDOStop: BOOL := FALSE;           (* 启用独立停止输出 *)
    EnSim: BOOL := FALSE;              (* 本设备仿真开关 *)
    Sim_RunFb: BOOL := FALSE;          (* 仿真运行反馈 *)
    Sim_Fault: BOOL := FALSE;          (* 仿真故障注入 *)
    Sim_Local: BOOL := FALSE;          (* 仿真就地 *)
    P_StandbyMode: INT := 0;           (* 备用报警策略 0=降级 1=抑制 *)
    TagNo: STRING[32] := 'MOTOR';      (* 设备 tag（实例化时改） *)

    (* ===== 内部信号 ===== *)
    i: INT;                            (* 循环变量 *)
    iState: INT;                       (* 当前状态 0停1启中2运3停中4故5就6检 *)
    iFltCause: INT;                    (* 故障原因 1启动失败2跳闸3安全4停止失败 *)
    RunFb_DB: BOOL; Fault_DB: BOOL; Local_DB: BOOL;
    RunFb_Eff: BOOL; Fault_Eff: BOOL; Local_Eff: BOOL;
    bSim: BOOL; bLocal: BOOL; bMaint: BOOL;
    bSafetyAct: BOOL; RestartBusy: BOOL; StopAllowed: BOOL;
    Perm_Start: BOOL; Perm_Run: BOOL;
    StartCmd: BOOL; StopCmd: BOOL;
    SigInhibit: BOOL; SigTrip: BOOL; SigAlmFlt: BOOL;
    SigTagTmp: STRING[32];             (* 当前最高等级联锁信号 tag *)
    sSigTag: STRING[32];               (* 故障锁存的信号 tag *)
    DO_Run_Calc: BOOL; DO_Stop_Calc: BOOL;
    AlmStartFail: BOOL; AlmTrip: BOOL; AlmSafety: BOOL;
    AlmStopFail: BOOL; AlmProcess: BOOL; AlmInhibit: BOOL; AlmFlicker: BOOL;
    bInhibStop: BOOL; bInhibStart: BOOL; bAlmEnable: BOOL;
    iSevFlt: INT;                      (* 备用降级后的严重度 *)

    (* ===== 定时器实例 ===== *)
    TON_RunFb: TON;  TON_Flt: TON;  TON_Local: TON;
    TON_Start: TON;  TON_Stop: TON;  TON_Restart: TON;
    TON_RunMin: TON; TON_Safety: TON; TON_Sec: TON;
    RT_Reset: R_Trig;

    (* ===== 报警实例（Severity 800 重报警/500 警告，F163 §5.9）===== *)
    ALM_StartFail: AlarmCond;
    ALM_StopFail: AlarmCond;
    ALM_Trip: AlarmCond;
    ALM_Safety: AlarmCond;
    ALM_Process: AlarmCond;
    ALM_Inhibit: AlarmCond;
    ALM_Flicker: AlarmCond;
END_VAR

(* ============================================================
   S01 输入采集与去抖
   ============================================================ *)
TON_RunFb(IN := DI_RunFb, PT := T_FbDb);
RunFb_DB := TON_RunFb.Q;
TON_Flt(IN := DI_Fault, PT := T_FltDb);
Fault_DB := TON_Flt.Q;
TON_Local(IN := DI_Local, PT := T_FbDb);
Local_DB := TON_Local.Q;

(* ============================================================
   S02 仿真注入（EnSim 或组下发 EnSimDown 时用仿真值替换反馈）
   ============================================================ *)
bSim := EnSim OR EqCmd.EnSimDown;
RunFb_Eff := RunFb_DB;
Fault_Eff := Fault_DB;
Local_Eff := Local_DB;
IF bSim THEN
    RunFb_Eff := Sim_RunFb;
    Fault_Eff := Sim_Fault;
    Local_Eff := Sim_Local;
END_IF;

(* ============================================================
   S03 模式判定（本地/检修优先于一切命令）
   ============================================================ *)
bLocal := Local_Eff;
bMaint := Cmd_Maint;

(* ============================================================
   S04 联锁汇总（三 lock + 信号数组 + O2）
   ============================================================ *)
SigInhibit := FALSE;
SigTrip := FALSE;
SigAlmFlt := FALSE;
SigTagTmp := TagNo;
FOR i := 1 TO 8 BY 1 DO
    IF Sig[i].SigType <> 0 THEN
        IF Sig[i].AlmLevel = 2 THEN
            SigAlmFlt := TRUE;
            SigTagTmp := Sig[i].SigTag;
        END_IF;
        IF Sig[i].Interlock THEN
            CASE Sig[i].SigType OF
                1: SigInhibit := TRUE;      (* 启动禁止 *)
                2: SigTrip := TRUE;         (* 操作联锁 *)
                3: SigTrip := TRUE;         (* 保护联锁 *)
                4: SigInhibit := TRUE;      (* 保护性启动 *)
            END_CASE;
        END_IF;
    END_IF;
END_FOR;
TON_Safety(IN := Lock_Safety, PT := T_SafetyDb);
bSafetyAct := TON_Safety.Q;                (* 安全联锁持续超延时才动作 *)
TON_Restart(IN := NOT RunFb_Eff, PT := T_Restart);
RestartBusy := (NOT RunFb_Eff) AND (NOT TON_Restart.Q);
Perm_Start := NOT Lock_Start AND NOT SigInhibit AND NOT RestartBusy AND O2_Perm;
Perm_Run := NOT Lock_Process AND NOT SigTrip AND O2_Perm;

(* ============================================================
   S05 命令仲裁（组命令优先于操作员；本地/检修全屏蔽）
   ============================================================ *)
IF EqCmd.Enable AND NOT bLocal AND NOT bMaint THEN
    StartCmd := EqCmd.Start;
    StopCmd := EqCmd.Stop;
ELSE
    StartCmd := Cmd_Start;
    StopCmd := Cmd_Stop;
END_IF;
IF bLocal OR bMaint THEN
    StartCmd := FALSE;
    StopCmd := FALSE;
END_IF;

(* ============================================================
   S06 状态机（七态）
   ============================================================ *)
CASE iState OF
    0: (* STOP 停止 *)
        DO_Run_Calc := FALSE;
        IF bLocal THEN
            iState := 5;
        ELSIF bMaint THEN
            iState := 6;
        ELSIF StartCmd AND Perm_Start THEN
            iState := 1;
            TON_Start(IN := TRUE, PT := T_StartMax);
        END_IF;

    1: (* STARTING 启动中 *)
        DO_Run_Calc := TRUE;
        TON_Start(IN := TRUE, PT := T_StartMax);
        IF RunFb_Eff THEN
            iState := 2;
            TON_Start(IN := FALSE, PT := T_StartMax);
            TON_RunMin(IN := TRUE, PT := T_RunMin);
        ELSIF TON_Start.Q THEN
            iState := 4;
            iFltCause := 1;                (* 启动失败 *)
        END_IF;

    2: (* RUN 运行 *)
        DO_Run_Calc := TRUE;
        TON_RunMin(IN := TRUE, PT := T_RunMin);
        StopAllowed := TON_RunMin.Q;
        IF Fault_Eff THEN
            iState := 4;
            iFltCause := 2;                (* 运行中跳闸 *)
        ELSIF bSafetyAct THEN
            iState := 4;
            iFltCause := 3;                (* 安全联锁 *)
        ELSIF (StopCmd OR (NOT Perm_Run)) AND StopAllowed THEN
            iState := 3;
            TON_Stop(IN := TRUE, PT := T_StopMax);
        END_IF;

    3: (* STOPPING 停止中 *)
        DO_Run_Calc := FALSE;
        TON_Stop(IN := TRUE, PT := T_StopMax);
        IF NOT RunFb_Eff THEN
            iState := 0;
            TON_Stop(IN := FALSE, PT := T_StopMax);
        ELSIF TON_Stop.Q THEN
            iState := 4;
            iFltCause := 4;                (* 停止失败 *)
        END_IF;

    4: (* FAULT 故障（须复位） *)
        DO_Run_Calc := FALSE;
        RT_Reset(CLK := Cmd_Reset);
        IF RT_Reset.Q AND NOT bSafetyAct AND NOT Lock_Start THEN
            iState := 0;
            iFltCause := 0;
            sSigTag := TagNo;
        END_IF;

    5: (* LOCAL 就地 *)
        DO_Run_Calc := FALSE;
        IF NOT Local_Eff THEN
            iState := 0;
        END_IF;

    6: (* MAINT 检修 *)
        DO_Run_Calc := FALSE;
        IF NOT Cmd_Maint THEN
            iState := 0;
        END_IF;
END_CASE;

(* 故障锁存：进 FAULT 时记信号 tag（首报链路用） *)
IF (iState = 4) AND (iFltCause <> 0) AND (sSigTag = TagNo) THEN
    sSigTag := SigTagTmp;
END_IF;

(* ============================================================
   S07 输出驱动（含仿真隔离：仿真时物理输出强制关断）
   ============================================================ *)
DO_Stop_Calc := EnDOStop AND (iState = 3);
IF bSim THEN
    DO_Run := FALSE;
    DO_Stop := FALSE;
ELSE
    DO_Run := DO_Run_Calc AND O2_Perm;
    DO_Stop := DO_Stop_Calc;
END_IF;

(* ============================================================
   S08 报警生成（抑制总线 + AlarmCond，06 文档 §2）
   ============================================================ *)
bInhibStop := NOT Grp.GroupActive;                 (* R1 组停抑制 *)
bInhibStart := Grp.GroupStarting;                  (* R2 启动抑制 *)
AlmStartFail := (iState = 4) AND (iFltCause = 1);
AlmTrip := (iState = 4) AND (iFltCause = 2);
AlmSafety := (iState = 4) AND (iFltCause = 3);
AlmStopFail := (iState = 4) AND (iFltCause = 4);
AlmProcess := (iState = 2) AND (NOT Perm_Run);
AlmInhibit := (iState = 0) AND StartCmd AND (NOT Perm_Start);
AlmFlicker := (iState = 2) AND (NOT RunFb_Eff);

iSevFlt := 800;
IF EqCmd.EnStandby AND (P_StandbyMode = 0) THEN
    iSevFlt := 500;                                (* R4 备用降级 *)
END_IF;

(* 重报警类：不被启动抑制，只被组停抑制 *)
bAlmEnable := NOT bInhibStop;
ALM_StartFail(Alarm := AlmStartFail, Severity := iSevFlt, Enable := bAlmEnable);
ALM_StopFail(Alarm := AlmStopFail, Severity := iSevFlt, Enable := bAlmEnable);
ALM_Trip(Alarm := AlmTrip, Severity := iSevFlt, Enable := bAlmEnable);
ALM_Safety(Alarm := AlmSafety, Severity := iSevFlt, Enable := bAlmEnable);
(* 瞬态类：额外被启动抑制；本地确认由 EnAckLocal 处理 *)
bAlmEnable := NOT bInhibStop AND NOT bInhibStart;
ALM_Process(Alarm := AlmProcess, Severity := 500, Enable := bAlmEnable);
ALM_Inhibit(Alarm := AlmInhibit, Severity := 500, Enable := bAlmEnable);
ALM_Flicker(Alarm := AlmFlicker, Severity := 500, Enable := bAlmEnable);
(* 注：AlarmCond 引脚名以库浏览器实际为准【需实测确认】；
   本地自动确认（R3）若无 Ack 引脚，用 Enable 串 Local_Eff AND NOT EqCmd.EnAckLocal 等效 *)

(* ============================================================
   S09 统计与上报
   ============================================================ *)
TON_Sec(IN := (iState = 2), PT := T_SecTick);
IF TON_Sec.Q THEN
    EqStat.RunTime := EqStat.RunTime + T_SecTick;
    TON_Sec(IN := FALSE, PT := T_SecTick);
END_IF;

EqStat.Run := (iState = 2);
EqStat.Ready := (iState = 0) AND Perm_Start;
EqStat.Fault := (iState = 4);
EqStat.Warning := AlmProcess OR AlmFlicker OR AlmInhibit;
EqStat.Local := bLocal;
EqStat.Maint := bMaint;
EqStat.Status := iState;
EqStat.FirstFault := (iState = 4);
EqStat.FaultTag := TagNo;
EqStat.SigTag := sSigTag;
EqStat.AlmLevel := 0;
IF AlmStartFail OR AlmTrip OR AlmSafety OR AlmStopFail OR SigAlmFlt THEN
    EqStat.AlmLevel := 2;
ELSIF AlmProcess OR AlmFlicker OR AlmInhibit THEN
    EqStat.AlmLevel := 1;
END_IF;
EqStat.AlmActive := 0;
IF AlmStartFail THEN EqStat.AlmActive := EqStat.AlmActive + 1; END_IF;
IF AlmTrip THEN EqStat.AlmActive := EqStat.AlmActive + 1; END_IF;
IF AlmSafety THEN EqStat.AlmActive := EqStat.AlmActive + 1; END_IF;
IF AlmStopFail THEN EqStat.AlmActive := EqStat.AlmActive + 1; END_IF;
IF AlmProcess THEN EqStat.AlmActive := EqStat.AlmActive + 1; END_IF;
IF AlmInhibit THEN EqStat.AlmActive := EqStat.AlmActive + 1; END_IF;
IF AlmFlicker THEN EqStat.AlmActive := EqStat.AlmActive + 1; END_IF;
EqStat.ChkPass := ChkPass_In;

SigIn.Run := (iState = 2);
SigIn.Local := bLocal;
SigIn.Maint := bMaint;
SigIn.GroupActive := Grp.GroupActive;
SigIn.GroupStarting := Grp.GroupStarting;

END_FUNCTION_BLOCK
```

### MOTOR_C 中文逻辑对照表（给娄哥的"查段表"）

| 段号 | 段名 | 代码位置（关键字） | 中文逻辑（一句话） |
|---|---|---|---|
| S01 | 输入去抖 | TON_RunFb/TON_Flt/TON_Local | 三个硬件信号各经一个 TON 去抖，防抖动误报 |
| S02 | 仿真注入 | bSim / RunFb_Eff | 本人仿真开关或组下发仿真开→反馈全换仿真值 |
| S03 | 模式判定 | bLocal/bMaint | 就地或检修时命令全屏蔽 |
| S04 | 联锁汇总 | FOR i 1..8 / Perm_Start/Perm_Run | 8 个联锁信号扫一遍合成"禁止启动/跳停"；安全联锁经 TON_Safety 延时确认；防重复启动窗口 |
| S05 | 命令仲裁 | EqCmd.Enable | 组接管时用组的启停，否则用操作员的；本地/检修强制清零 |
| S06 | 状态机 | CASE iState OF 0..6 | 七态转移：见 02 文档 §4 表；进故障记原因码 |
| S07 | 输出驱动 | bSim / DO_Run_Calc | 仿真时物理输出强制关断；正常时 DO_Run=计算值 AND O2 允许 |
| S08 | 报警生成 | bInhibStop/bInhibStart | 组停抑制+启动抑制+备用降级后送 AlarmCond（800/500） |
| S09 | 统计上报 | EqStat.* / SigIn.* | 运行时长每秒累加；状态/首报/报警计数填 CC 通道回组 |

## 2. GROUP_C ST 骨架（FBT 内部代码）

```st
FUNCTION_BLOCK GROUP_C
(* ============================================================
   GROUP_C 组功能块（顺序/周期/首报/汇总）
   库 CEMENT_LIB 1.0.0 | 设计依据 04-组功能块拆解.md
   分段：S01 输入与模式 / S02 命令仲裁 / S03 设备使能 / S04 启动步进
        S05 停止步进 / S06 周期控制 / S07 首报与汇总 / S08 上报
   顺序数据唯一来源=组参数数组（StepNoTab 等）， viewer 也读它
   ============================================================ *)

VAR_INPUT
    CON: BOOL;                         (* 远程组启动（单周期脉冲，F163 §4.6） *)
    COFF: BOOL;                        (* 远程组停止（单周期脉冲，F163 §4.6） *)
    Cmd_Start: BOOL;                   (* 面板启动 *)
    Cmd_Stop: BOOL;                    (* 面板停止 *)
    Cmd_Reset: BOOL;                   (* 组故障复位 *)
    ParentCmd: CC_EqCmd;               (* 上级组命令（本组作为子设备） *)
    EqStats: ARRAY[1..16] OF CC_EqStat;(* 设备状态回读 *)
END_VAR

VAR_OUTPUT
    EqCmds: ARRAY[1..16] OF CC_EqCmd;  (* 设备命令下发 *)
    GroupStat: CC_EqStat;              (* 向上级组上报 *)
    GrpOut: CC_Group;                  (* 向画面/viewer 汇总 *)
END_VAR

VAR
    (* ===== 参数区 ===== *)
    EnCyclic: BOOL := FALSE;           (* 周期组 *)
    T_CycleRun: TIME := T#10m;         (* 周期运行时长 *)
    T_CycleIdle: TIME := T#10m;        (* 周期间歇时长 *)
    T_StepMax: TIME := T#30s;          (* 步超时（0=无限等） *)
    EnGrpHold: BOOL := TRUE;           (* 步失败保持组 *)
    T_GrpFltAck: TIME := T#0s;         (* 组故障自动复位延时 *)
    EnSim: BOOL := FALSE;              (* 组级仿真（下发所有设备） *)
    TagNo: STRING[32] := 'GROUP';      (* 组 tag *)
    (* 顺序表：第 i 槽设备的启动步号/停止步号/步间延时/备用标志 *)
    StepNoTab: ARRAY[1..16] OF INT := [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
    StepNoStopTab: ARRAY[1..16] OF INT := [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
    DelayStartTab: ARRAY[1..16] OF TIME := [T#0s,T#0s,T#0s,T#0s,T#0s,T#0s,T#0s,T#0s,
                                            T#0s,T#0s,T#0s,T#0s,T#0s,T#0s,T#0s,T#0s];
    DelayStopTab: ARRAY[1..16] OF TIME := [T#0s,T#0s,T#0s,T#0s,T#0s,T#0s,T#0s,T#0s,
                                           T#0s,T#0s,T#0s,T#0s,T#0s,T#0s,T#0s,T#0s];
    EnStandbyTab: ARRAY[1..16] OF BOOL := [FALSE,FALSE,FALSE,FALSE,FALSE,FALSE,FALSE,FALSE,
                                           FALSE,FALSE,FALSE,FALSE,FALSE,FALSE,FALSE,FALSE];

    (* ===== 内部 ===== *)
    i: INT; j: INT;
    iGState: INT;                      (* 0停1启中2运3停中4故 *)
    bAct: ARRAY[1..16] OF BOOL;        (* 槽位有效 *)
    bRunOK: ARRAY[1..16] OF BOOL;      (* 该槽已确认运行 *)
    bStarted: ARRAY[1..16] OF BOOL;    (* 该槽已发启动命令 *)
    bStopped: ARRAY[1..16] OF BOOL;    (* 该槽已确认停止 *)
    bStartOK: ARRAY[1..16] OF BOOL;    (* 前沿可启动 *)
    bStopOK: ARRAY[1..16] OF BOOL;     (* 前沿可停止 *)
    bStepTmo: ARRAY[1..16] OF BOOL;    (* 步超时 *)
    EquipActive: INT; EquipRun: INT;
    bGrpStartLatch: BOOL; bGrpStopLatch: BOOL;
    bFirstFault: BOOL; sFirstTag: STRING[32]; iFirstStep: INT;
    GroupActive: BOOL; GroupStarting: BOOL;
    StartCmd: BOOL; StopCmd: BOOL;
    RT_CON: R_Trig; RT_COFF: R_Trig;
    TON_Dly: ARRAY[1..16] OF TON;      (* 每槽启动延时 *)
    TON_Step: ARRAY[1..16] OF TON;     (* 每槽步超时 *)
    TON_CycleRun: TON; TON_CycleIdle: TON; TON_FltAck: TON;
END_VAR

(* ============================================================
   S01 输入与模式
   ============================================================ *)
IF iGState = 1 OR iGState = 3 THEN
    GroupStarting := TRUE;
ELSE
    GroupStarting := FALSE;
END_IF;
GroupActive := (iGState <> 0) AND (iGState <> 4);

(* ============================================================
   S02 命令仲裁（ParentCmd 最高优先，然后 CON/COFF 脉冲，然后面板）
   ============================================================ *)
RT_CON(CLK := CON);
RT_COFF(CLK := COFF);
IF RT_CON.Q AND (iGState = 0) THEN
    bGrpStartLatch := TRUE;
END_IF;
IF RT_COFF.Q THEN
    bGrpStartLatch := FALSE;
    bGrpStopLatch := TRUE;
END_IF;
IF ParentCmd.Enable THEN
    StartCmd := ParentCmd.Start;
    StopCmd := ParentCmd.Stop;
ELSE
    StartCmd := bGrpStartLatch OR Cmd_Start;
    StopCmd := bGrpStopLatch OR Cmd_Stop;
END_IF;

(* ============================================================
   S03 设备使能 + 每槽命令通道刷新
   ============================================================ *)
EquipActive := 0;
EquipRun := 0;
FOR i := 1 TO 16 BY 1 DO
    bAct[i] := (StepNoTab[i] > 0);
    EqCmds[i].Enable := bAct[i] AND GroupActive;
    EqCmds[i].StepNo := StepNoTab[i];
    EqCmds[i].StepNoStop := StepNoStopTab[i];
    EqCmds[i].DelayStart := DelayStartTab[i];
    EqCmds[i].DelayStop := DelayStopTab[i];
    EqCmds[i].EnStandby := EnStandbyTab[i];
    EqCmds[i].EnSimDown := EnSim;
    IF bAct[i] THEN
        EquipActive := EquipActive + 1;
        IF EqStats[i].Run THEN
            EquipRun := EquipRun + 1;
        END_IF;
    END_IF;
END_FOR;

(* ============================================================
   S04 启动步进（前沿法：低步号全运行才允许高步号启；同步号并列同启）
   ============================================================ *)
FOR i := 1 TO 16 BY 1 DO
    bStartOK[i] := bAct[i] AND NOT bRunOK[i] AND NOT EqStats[i].Fault;
    FOR j := 1 TO 16 BY 1 DO
        IF (j <> i) AND bAct[j] AND (StepNoTab[j] < StepNoTab[i]) AND NOT EqStats[j].Run THEN
            bStartOK[i] := FALSE;
        END_IF;
    END_FOR;
    IF bStartOK[i] AND NOT bStarted[i] THEN
        TON_Dly[i](IN := TRUE, PT := DelayStartTab[i]);
        IF TON_Dly[i].Q THEN
            EqCmds[i].Start := TRUE;
            bStarted[i] := TRUE;
            TON_Step[i](IN := TRUE, PT := T_StepMax);
            TON_Dly[i](IN := FALSE, PT := DelayStartTab[i]);
        END_IF;
    ELSE
        TON_Dly[i](IN := FALSE, PT := DelayStartTab[i]);
    END_IF;
    IF bStarted[i] THEN
        IF EqStats[i].Run THEN
            EqCmds[i].Start := FALSE;
            bRunOK[i] := TRUE;
        ELSE
            EqCmds[i].Start := TRUE;
            IF (T_StepMax > T#0s) AND TON_Step[i].Q THEN
                bStepTmo[i] := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_FOR;

(* ============================================================
   S05 停止步进（按停止步号反序：高步号全停才允许低步号停）
   ============================================================ *)
FOR i := 1 TO 16 BY 1 DO
    IF StepNoStopTab[i] > 0 THEN
        bStopOK[i] := bAct[i] AND NOT bStopped[i] AND EqStats[i].Run;
        FOR j := 1 TO 16 BY 1 DO
            IF (j <> i) AND bAct[j] AND (StepNoStopTab[j] > StepNoStopTab[i]) AND EqStats[j].Run THEN
                bStopOK[i] := FALSE;
            END_IF;
        END_FOR;
    ELSE
        bStopOK[i] := bAct[i] AND NOT bStopped[i] AND EqStats[i].Run;
        FOR j := 1 TO 16 BY 1 DO
            IF (j <> i) AND bAct[j] AND (StepNoTab[j] > StepNoTab[i]) AND EqStats[j].Run THEN
                bStopOK[i] := FALSE;
            END_IF;
        END_FOR;
    END_IF;
    IF bStopOK[i] THEN
        TON_Dly[i](IN := FALSE, PT := DelayStopTab[i]);
        EqCmds[i].Stop := TRUE;
        IF NOT EqStats[i].Run THEN
            EqCmds[i].Stop := FALSE;
            bStopped[i] := TRUE;
        END_IF;
    ELSE
        EqCmds[i].Stop := FALSE;
    END_IF;
END_FOR;

(* ============================================================
   S06 周期控制
   ============================================================ *)
TON_CycleRun(IN := (iGState = 2) AND EnCyclic, PT := T_CycleRun);
TON_CycleIdle(IN := (iGState = 0) AND EnCyclic AND (EquipActive > 0), PT := T_CycleIdle);
IF TON_CycleRun.Q THEN
    bGrpStopLatch := TRUE;
    TON_CycleRun(IN := FALSE, PT := T_CycleRun);
END_IF;
IF TON_CycleIdle.Q THEN
    bGrpStartLatch := TRUE;
    TON_CycleIdle(IN := FALSE, PT := T_CycleIdle);
END_IF;

(* ============================================================
   S07 首报与汇总
   ============================================================ *)
bFirstFault := FALSE;
IF NOT bFirstFault THEN
    FOR i := 1 TO 16 BY 1 DO
        IF bAct[i] AND (EqStats[i].Fault OR bStepTmo[i]) THEN
            bFirstFault := TRUE;
            sFirstTag := EqStats[i].FaultTag;
            iFirstStep := StepNoTab[i];
        END_IF;
    END_FOR;
END_IF;
(* 组状态机 *)
CASE iGState OF
    0: (* STOP *)
        bGrpStopLatch := FALSE;
        bFirstFault := FALSE;
        sFirstTag := TagNo;
        FOR i := 1 TO 16 BY 1 DO
            bStarted[i] := FALSE; bRunOK[i] := FALSE; bStopped[i] := FALSE; bStepTmo[i] := FALSE;
        END_FOR;
        IF StartCmd AND (EquipActive > 0) THEN
            iGState := 1;
        END_IF;
    1: (* STARTING *)
        IF bFirstFault AND EnGrpHold THEN
            iGState := 4;
        ELSIF (EquipRun >= EquipActive) AND (EquipActive > 0) THEN
            iGState := 2;
        END_IF;
    2: (* RUN *)
        IF StopCmd OR bFirstFault THEN
            iGState := 3;
        END_IF;
    3: (* STOPPING *)
        IF EquipRun = 0 THEN
            iGState := 0;
        END_IF;
    4: (* FAULT *)
        TON_FltAck(IN := TRUE, PT := T_GrpFltAck);
        IF Cmd_Reset OR (TON_FltAck.Q AND (T_GrpFltAck > T#0s)) THEN
            iGState := 0;
            TON_FltAck(IN := FALSE, PT := T_GrpFltAck);
        END_IF;
END_CASE;

(* ============================================================
   S08 上报
   ============================================================ *)
GroupStat.Run := (iGState = 2);
GroupStat.Ready := (iGState = 0) AND (EquipActive > 0) AND (EquipRun = 0);
GroupStat.Fault := (iGState = 4);
GroupStat.Status := iGState;
GroupStat.FirstFault := bFirstFault;
GroupStat.FaultTag := sFirstTag;
GrpOut.GroupRun := (iGState = 2);
GrpOut.GroupReady := GroupStat.Ready;
GrpOut.GroupFault := (iGState = 4);
GrpOut.FirstFaultTag := sFirstTag;
GrpOut.EquipTotal := EquipActive;
GrpOut.EquipRun := EquipRun;
GrpOut.ChkDone := 0;                   (* 由 CHK 汇总写入，见 07 文档 §2.4 *)
GrpOut.ChkTotal := 0;

END_FUNCTION_BLOCK
```

### GROUP_C 中文逻辑对照表

| 段号 | 段名 | 中文逻辑（一句话） |
|---|---|---|
| S01 | 输入与模式 | 启停中=Starting；非停非故=活动（供设备报警抑制 R1/R2） |
| S02 | 命令仲裁 | 上级组命令 > CON/COFF 脉冲锁存 > 面板；COFF 清启动锁存置停止锁存 |
| S03 | 设备使能 | 扫 16 槽：步号>0=有效；每槽刷新 CC 命令字段（含仿真下发）；数运行/总数 |
| S04 | 启动步进 | 前沿法：比本槽步号低的槽全运行才放本槽启；同步号并列同启；DelayStart 到才发命令；T_StepMax 超时记 bStepTmo |
| S05 | 停止步进 | 反序：比本槽停止步号高的槽全停才放本槽停 |
| S06 | 周期控制 | 周期组：运行够 T_CycleRun→自动停；停够 T_CycleIdle→自动启 |
| S07 | 首报与汇总 | 扫槽找第一个故障/超时设备锁存 tag；组状态机四态 |
| S08 | 上报 | 填 GroupStat/GrpOut 给上级组和 viewer |

## 3. 工程侧布尔连锁示例（Code 段，无 VAR 声明，F163 §4.1）

```st
(* ===== S10 布尔连锁（变量在 Var.xlsx 定义，FBD 连线到 MOTOR_C 引脚）===== *)
(* 语义对齐 F163 §4.4：三个 lock TRUE=锁定，直接赋值不取反 *)
N562_FN1_E01_PL := N562_FN1_T1_T_H OR N562_FN1_P1_P_H;   (* 轴承温度高或压力高→过程联锁 *)
N562_FN1_E01_SL := NOT N562_GB1_SafeOK;                  (* 安全OK取反→安全联锁锁定（块内经T_SafetyDb延时置故障） *)
N562_FN1_E01_RS := NOT N562_SR1_91_Run;                  (* 选粉机没转→启动联锁锁定 *)
N562_FN1_E01_O2 := NOT N562_FN1_90_MaintSW;              (* 检修开关合→O2不允许 *)
```

## 4. FBD 管脚连线清单（MOTOR_C 实例 N562_FN1_E01）

| FBT 引脚 | 连到 | 方向 | 说明 |
|---|---|---|---|
| DI_RunFb | `N562_FN1_90_Run.Value` | 入 | DintIO→.Value→Bool【F163 §5.1】 |
| DI_Fault | `N562_FN1_90_Flt.Value` | 入 | |
| DI_Local | `N562_FN1_90_Loc.Value` | 入 | |
| DI_Ready | `TRUE` 常量或就绪信号 | 入 | |
| DO_Run | `N562_FN1_90_O2.Value` | 出 | Bool→DintIO【F163 §5.1】 |
| Cmd_Start | 画面按钮变量 / 组 EqCmds[2].Start | 入 | 二选一，别双连 |
| Lock_Process | `N562_FN1_E01_PL` | 入 | S10 布尔连锁变量 |
| Lock_Safety | `N562_FN1_E01_SL` | 入 | |
| Lock_Start | `N562_FN1_E01_RS` | 入 | |
| O2_Perm | `N562_FN1_E01_O2` | 入 | |
| EqCmd | `G30.EqCmds[2]` | 入 | 组第 2 槽 |
| EqStat | `G30.EqStats[2]` | 出 | |
| Grp | `G30.GrpOut` | 入 | |
| Sig[1] | `N562_FN1_T1.SigOut` | 入 | 温度联锁信号 |
| Sig[2] | `N562_FN1_P1.SigOut` | 入 | 压力联锁信号 |
| Sig[3..8] | 不连（SigType=0） | — | 空槽自动忽略 |
| ChkPass_In | `N562_FN1_E01_CHK.ChkPass` | 入 | CHK_C 实例 |

## 5. 规则符合性自检（F163 §5 逐条）

| # | 规则 | 本骨架执行 |
|---|---|---|
| 1 | 硬件 IO 经 .Value | 引脚用 Bool，.Value 转换在工程侧变量/FBD（§4 表） |
| 2 | Code 无 FB/VAR 声明 | 工程 Code（§3）只有执行语句；FBT 内部按 ST 规范声明 |
| 3 | 禁位运算 | 拆字节/打包一处未用；报警计数用 IF 累加 |
| 4 | 禁字符串/时间字面量 | 字面量只在 VAR 初值（参数区）；Code 内清空用 TagNo 代替 '' |
| 5 | 实例必须被调用 | TON_*/RT_*/ALM_* 全部在 Code 段调用 |
| 6 | 引脚大小写 | TON/TOF/R_Trig/AlarmCond 按官方大小写 |
| 7 | in_out 无 retain / in 不赋值 | CC 结构体走 VAR_INPUT/VAR_OUTPUT，无 in_out |
| 8 | AlarmCond 800/500 | S08 只用 800/500 两档 |
| 9 | 启动抑制只压瞬态类 | S08 分两组 Enable |

## 6. 本篇结论

两个骨架 + 一张连锁示例 + 一张连线清单 = 一个新组的全部代码工作量。**先抄 MOTOR_C，编译过再抄 GROUP_C**；引用 CC 字段时以 01 文档 §2 的字段表为准（含后补的 EnSimDown）。报错先查 §5 自检表，再查 09 文档核对清单。
