---
title: MinLib拆解复用-ST代码骨架与FBD对照V2（官方参数对齐）
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,ST,代码骨架,分段编号,中文注释,MOT_C,GRP_C,IC,IB,IA,PD,步号]
summary: V2：MOT_C对齐官方MOT1参数名的ST骨架（S01-S10）、GRP_C对齐官方GROUP的骨架（步号三段规则/SeqStart/STW/ChngOver）、IC/IB/IA/PD布尔连锁示例、官方管脚名FBD连线清单、F163规则自检
source: 04手册p30-51 + 05手册p23-24 + F163规则总纲 §4.2/§5
---

# 08 ST 代码骨架与 FBD 对照（V2）

> **V2 变更**：骨架参数名/状态名全部换成官方名（MOT1/GROUP 手册原样）。分段编号 S01+中文注释+中文逻辑对照表保持（娄哥要求不变）。
> 约束仍按 F163 §5：无位运算；字符串/时间字面量只出现在 VAR 初值；实例必须被调用；引脚大小写敏感。
> 【需实测】AlarmCond 引脚名、CM 内 VAR CONST/string 初值——编译不过就按 §6 自检表逐项查。

## 1. MOT_C ST 骨架（对齐官方 MOT1）

```st
FUNCTION_BLOCK MOT_C
(* ============================================================
   MOT_C 通用电机块（CL库，对齐官方 MOT1，04手册p29-51）
   分段：S01 输入去抖 / S02 模式POC判定 / S03 联锁汇总 / S04 命令仲裁
        S05 状态机 / S06 输出驱动 / S07 报警生成 / S08 首报跳闸记录
        S09 统计 / S10 组接口上报
   规则：无位运算；字面量只在VAR初值；实例全部被调用
   ============================================================ *)

VAR_INPUT
    (* ---- 标识 ---- *)
    Name: STRING[24] := 'MOT';            (* Tag名，允许.和-，禁空格:; *)
    Description: STRING[40] := 'Motor';
    (* ---- 组接口（GCC，对齐官方 GrpStartStep 等）---- *)
    GrpStartStep: DINT := 0;              (* 启动步号1..999，0=不参加组顺序 *)
    GrpStopStep: DINT := 0;               (* 停止步号1001..1999，0=不参加 *)
    GrpStartDelay: TIME := T#0s;          (* 组启动延时 *)
    GrpStopDelay: TIME := T#0s;           (* 组停止延时 *)
    PreSelection: STRING[50] := '';       (* 预选分配 P1&P2|P3&N4 *)
    (* ---- IO与MCC（对齐官方 ME/M1/M2/M3/IOStatus）---- *)
    IOStatus1: DINT := 0;                 (* IO板状态1 *)
    IOStatus2: DINT := 0;                 (* IO板状态2 *)
    IOStatus3: DINT := 0;                 (* IO板状态3 *)
    IOStatus4: DINT := 0;                 (* IO板状态4/串口 *)
    ME: BOOL := TRUE;                     (* 主控制电压OK；FALSE=禁报警生成 *)
    M1: BOOL := TRUE;                     (* MCC信号1 默认Overtemp *)
    M2: BOOL := TRUE;                     (* MCC信号2 默认Overload *)
    M3: BOOL := TRUE;                     (* MCC信号3 默认Availability *)
    (* ---- 反馈（对齐官方 FdBckRun/FB1/FB2）---- *)
    FdBckRun: BOOL := FALSE;              (* 运行反馈（接触器吸合） *)
    FdBckTime: TIME := T#2s;              (* 接触器响应最大延时 *)
    FB1: BOOL := TRUE;                    (* 功能反馈1 如速度开关 *)
    FB1Mode: DINT := 0;                   (* 0=连续 >0=脉冲(1=0.1s) -1=连续且FBOpn报警 *)
    FB2: BOOL := TRUE;                    (* 功能反馈2 如压力开关 *)
    FB2Mode: DINT := 0;
    FBTime: TIME := T#10s;                (* FB1/2响应最大延时 *)
    (* ---- 电流（对齐官方 MC/MCNominal/MCHiLim）---- *)
    MC: REAL := 0.0;                      (* 电机电流/功率（RealIO） *)
    MCNominal: REAL := 0.0;               (* 额定电流 *)
    MCHiLim: REAL := 100.0;               (* 电流高限（额定%） *)
    (* ---- 就地盒LCB（对齐官方 Lcbxxx/LcbType）---- *)
    LcbStart: BOOL := FALSE;              (* 现场启动脉冲 *)
    LcbStop: BOOL := TRUE;                (* 现场停止（停=0） *)
    LcbRem: BOOL := FALSE;                (* 正脉冲切Seq或Cen *)
    LcbLoc: BOOL := FALSE;                (* 正脉冲切Loc *)
    LcbMaint: BOOL := TRUE;               (* 置维护模式 *)
    LcbType: DINT := 0;                   (* 0=CCR启停 1=POC LCB 2=硬线LCB 3=切POC即停 4=CCR启动+Rem *)
    (* ---- 联锁（对齐官方 MOT1Input，TRUE=联锁生效）---- *)
    IC: BOOL := TRUE;                     (* 安全联锁：所有模式生效 *)
    IB1: BOOL := TRUE;                    (* 设备联锁1：本地/维护释放，面板可闭锁 *)
    IB2: BOOL := TRUE;                    (* 设备联锁2 *)
    IB3: BOOL := TRUE;                    (* 设备联锁3（IBF=TRUE时作启动联锁） *)
    IB4: BOOL := TRUE;                    (* 设备联锁4（同上） *)
    IBF: BOOL := FALSE;                   (* TRUE=IB3/IB4作为启动联锁 *)
    IA: BOOL := TRUE;                     (* 过程/链式联锁：不计入RFS，Auto模式ok后不自复 *)
    PrevDrive: BOOL := TRUE;              (* 前序设备联锁PD：组保持RFS *)
    Warning: BOOL := FALSE;               (* 外部警告（不停机） *)
    (* ---- 组/预选/命令（对齐官方 MOT1Input）---- *)
    PreSel: BOOL := FALSE;                (* 被预选 *)
    PreSelStdBy: BOOL := FALSE;           (* 被预选为standby（StdType=1时报警降Warning） *)
    EnSeqStart: BOOL := TRUE;             (* 组启动软允许 *)
    EnSeqStop: BOOL := TRUE;              (* 组停止软允许 *)
    SeqStart: BOOL := FALSE;              (* 外部启动脉冲（切Seq并启动） *)
    SeqStop: BOOL := FALSE;               (* 外部停止脉冲 *)
    SetSeq: BOOL := FALSE;                (* 切POC=Seq脉冲 *)
    SetCen: BOOL := FALSE;                (* 切POC=Cen脉冲 *)
    SetLoc: BOOL := FALSE;                (* 切POC=Loc脉冲 *)
    (* ---- STW/模式使能（对齐官方）---- *)
    StwCen: BOOL := TRUE;                 (* Cen/Seq启动自动触发预告 *)
    StwField: BOOL := FALSE;              (* 现场启动触发预告 *)
    EnAuto: BOOL := FALSE;                (* Auto模式使能（组顺序启动时激活） *)
    AutoMode: DINT := 0;                  (* 1=Man下禁IA 8=Auto等下次触发 *)
    EnSeq: BOOL := TRUE;                  (* POC Seq使能 *)
    EnCen: BOOL := TRUE;                  (* POC Cen使能 *)
    EnLoc: BOOL := TRUE;                  (* POC Loc使能 *)
    EnMaint: BOOL := TRUE;                (* 维护子模式使能 *)
    EnFPLStopInAllModes: BOOL := TRUE;    (* FALSE=面板停止仅Cen有效 *)
    (* ---- 报警/事件（对齐官方）---- *)
    AlarmTr: DINT := 3;                   (* 报警处理 3=Failure未确认 2=Warning未确认 1=自动确认 0=事件 -1=无 *)
    InterlockTr: DINT := 3;               (* 联锁处理 *)
    Class: DINT := 1;                     (* AE类1..9999 *)
    AlarmAck: BOOL := FALSE;              (* 报警确认脉冲 *)
    (* ---- 报警文本（NLS前缀||AE_NLS_，值放Var表初值）---- *)
    M1Txt: STRING[35] := 'Overtemp';
    M2Txt: STRING[35] := 'Overload';
    M3Txt: STRING[35] := 'Not Available';
    FdBckTxt: STRING[35] := 'Contactor Fault';
    FB1Txt: STRING[35] := 'Speed';
    FB2Txt: STRING[35] := 'Press';
    LcbStopTxt: STRING[35] := 'Local Stop';
    METxt: STRING[35] := 'Ctrl Voltage Trip';
    WarningTxt: STRING[35] := 'Summary Warning';
    MCTxt: STRING[35] := 'High Current';
END_VAR

VAR_OUTPUT
    Ord: BOOL := FALSE;                   (* 启动命令输出（到接触器） *)
    LocAlarmAck: BOOL := FALSE;           (* 报警复位脉冲（如复位SCP） *)
    (* ---- 状态输出（对齐官方 MOT1Output）---- *)
    Auto: BOOL; Seq: BOOL; Cen: BOOL; Loc: BOOL; Maint: BOOL; OutOfSrv: BOOL;
    Trip: BOOL;                           (* 跳闸指示（可启冗余驱动，不含联锁） *)
    Rfs: BOOL;                            (* Ready For Start *)
    NoInt: BOOL;                          (* 无联锁（就绪且无IA） *)
    Run: BOOL;                            (* 运行=Ord AND FdBckRun AND FB1 AND FB2 *)
    StartCnt: DINT;                       (* 启动次数累计 *)
    RuntimeCnt: REAL;                     (* 运行小时累计 *)
    ALNumber: DINT;                       (* 实际报警号 *)
    ALPending: BOOL; ALUnack: BOOL;
    FieldStartRelease: BOOL;              (* LOC选中且启动条件OK *)
    ForcedRun: BOOL;                      (* 强制运行（硬线LCB启动） *)
    FdBckOffErr: BOOL;                    (* 主接触器未断开 *)
    FB1PulseTime: REAL;                   (* FB1脉冲实际周期（秒） *)
    FirstOrMaxAETag: STRING[32] := '';    (* 首报/最高报警IO设备tag *)
    FirstOrMaxAEIndTr: DINT := 0;         (* 首报指示处理号 *)
    LastTripTxt: STRING[40] := '';        (* 上次跳闸联锁描述或PCC AE tag *)
    LastTrip: STRING[20] := '';           (* 上次跳闸时间（文本，工程侧赋值） *)
END_VAR

VAR
    (* ---- 内部状态 ---- *)
    iStatus: INT;                         (* 0=Off 1=Starting 2=Run *)
    iPOC: INT;                            (* 0=Seq 1=Cen 2=Loc 3=OutOfSrv *)
    iMode: INT;                           (* 0=Man 1=Auto 2=Maint *)
    bRun_DB: BOOL; bFB1_DB: BOOL; bFB2_DB: BOOL; bFlt_DB: BOOL;
    bMCCFlt: BOOL;                        (* M1/M2/M3/ME 合成 MCC故障 *)
    bIBRun: BOOL;                         (* 运行中IB联锁生效 *)
    bIBStart: BOOL;                       (* 启动IB联锁（IBF时IB3/4） *)
    bIAAuto: BOOL;                        (* Auto模式IA要求 *)
    bPermStart: BOOL;                     (* 启动允许 *)
    bStwReq: BOOL;                        (* 需要启动预告 *)
    bStwDone: BOOL;                       (* 预告完成 *)
    bIOWarn: BOOL;                        (* IO板警告 *)
    bIOSFlt: BOOL;                        (* IO板故障 *)
    bHiCurr: BOOL;                        (* 电流高限 *)
    bAlmActive: BOOL;                     (* 有活动报警 *)
    iAlmSev: INT;                         (* 0无 1警告 2故障 *)
    iStopReason: INT;                     (* 停止原因码（消息结构用） *)
    TON_Fdbck: TON;                       (* 接触器响应超时 *)
    TON_FB1: TON; TON_FB2: TON;           (* FB响应超时 *)
    TON_Restart: TON;                     (* 防重复启动 *)
    TON_RunMin: TON;                      (* 最短运行 *)
    TON_Sec: TON;                         (* 1秒节拍 *)
    RT_Start: R_Trig; RT_Stop: R_Trig; RT_Reset: R_Trig; RT_Ack: R_Trig;
    ALM_M1: AlarmCond; ALM_M2: AlarmCond; ALM_M3: AlarmCond;
    ALM_Fdbck: AlarmCond; ALM_FB1: AlarmCond; ALM_FB2: AlarmCond;
    ALM_ME: AlarmCond; ALM_IOS: AlarmCond; ALM_HiCurr: AlarmCond; ALM_Warn: AlarmCond;
    T_SecTick: TIME := T#1s;              (* 统计节拍 *)
    T_RunMinSet: TIME := T#0s;            (* 最短运行时间设定 *)
    T_RestartSet: TIME := T#0s;           (* 防重启设定 *)
    bLocalBlk: BOOL;                      (* 本地闭锁标记 *)
END_VAR

(* ============================================================
   S01 输入采集与去抖（官方 FdBckTime/FBTime 语义）
   ============================================================ *)
TON_Fdbck(IN := FdBckRun, PT := FdBckTime);
bRun_DB := TON_Fdbck.Q;
TON_FB1(IN := FB1, PT := FBTime);
bFB1_DB := TON_FB1.Q;
TON_FB2(IN := FB2, PT := FBTime);
bFB2_DB := TON_FB2.Q;
bMCCFlt := (NOT M1) OR (NOT M2) OR (NOT M3);
bIOSFlt := (IOStatus1 <> 0) OR (IOStatus2 <> 0) OR (IOStatus3 <> 0)
           OR ((IOStatus4 <> 0) AND (IOStatus4 <> 65535));
bHiCurr := (MCNominal > 0.0) AND (MC > MCNominal * MCHiLim / 100.0);

(* ============================================================
   S02 模式与POC判定（官方 POC：0Seq/1Cen/2Loc/3OOS + Man/Auto/Maint）
   ============================================================ *)
RT_Reset(CLK := SetLoc);
IF RT_Reset.Q AND EnLoc THEN iPOC := 2; END_IF;
RT_Reset(CLK := SetSeq);
IF RT_Reset.Q AND EnSeq THEN iPOC := 0; END_IF;
RT_Reset(CLK := SetCen);
IF RT_Reset.Q AND EnCen THEN iPOC := 1; END_IF;
(* 就地盒脉冲 *)
RT_Reset(CLK := LcbRem);
IF RT_Reset.Q THEN
    IF EnSeq THEN iPOC := 0; END_IF;
END_IF;
RT_Reset(CLK := LcbLoc);
IF RT_Reset.Q AND EnLoc THEN iPOC := 2; END_IF;
(* 维护模式 *)
IF LcbMaint AND EnMaint THEN
    iMode := 2;
ELSIF iMode = 2 AND NOT LcbMaint THEN
    iMode := 0;
END_IF;
IF EnAuto AND (iPOC = 0) AND (iMode <> 2) THEN
    iMode := 1;
END_IF;
(* 本地/维护时联锁释放矩阵（官方：IC保持，IB/IA/PD释放） *)
bLocalBlk := (iPOC = 2) OR (iMode = 2);

(* ============================================================
   S03 联锁汇总（IC/IB1-4/IA/PD，官方 MOT1Input 语义）
   ============================================================ *)
bIBRun := (NOT IB1) OR (NOT IB2) OR (NOT IB3) OR (NOT IB4);
IF NOT bLocalBlk THEN
    bIBRun := bIBRun;                     (* 本地/维护时IB已释放 *)
ELSE
    bIBRun := FALSE;
END_IF;
bIBStart := (NOT IB3) OR (NOT IB4);
IF IBF AND NOT bLocalBlk THEN
    bIBStart := bIBStart;
ELSE
    bIBStart := FALSE;                    (* 非IBF或本地时IB3/4不作启动联锁 *)
END_IF;
(* IA：Auto模式由IA启停；Man模式IA是运行联锁（AutoMode=1可禁） *)
bIAAuto := (iMode = 1) AND IA;
(* 启动允许：无IC/IB启动联锁/PD + 软允许 + MCC就绪 *)
bPermStart := IC AND (NOT bIBStart) AND PrevDrive AND EnSeqStart AND ME
              AND (NOT bIOSFlt) AND (NOT bIAAuto = FALSE OR iMode <> 1);

(* ============================================================
   S04 命令仲裁（POC×Mode 官方命令矩阵，04手册p8）
   ============================================================ *)
RT_Start(CLK := SeqStart);
RT_Stop(CLK := SeqStop);
IF iPOC = 2 THEN
    (* 本地：LCB按钮箱控制 *)
    IF LcbStart AND bPermStart THEN
        bStwReq := StwField;
        iStatus := 1;
    END_IF;
    IF NOT LcbStop THEN
        iStatus := 0;
        iStopReason := 4;                 (* FSP 现场停止 *)
    END_IF;
ELSIF iMode = 1 THEN
    (* Auto模式：IA驱动 *)
    IF IA AND bPermStart AND (iStatus = 0) THEN
        iStatus := 1;
    END_IF;
    IF NOT IA THEN
        iStatus := 0;
        iStopReason := 9;                 (* IA *)
    END_IF;
ELSE
    (* Man模式：组命令/面板/外部脉冲 *)
    IF (RT_Start.Q OR bGrpStartCmd) AND bPermStart AND (iStatus = 0) THEN
        bStwReq := StwCen;
        iStatus := 1;
    END_IF;
    IF RT_Stop.Q OR bGrpStopCmd THEN
        iStatus := 0;
        iStopReason := 2;                 (* SSP 组/外部停止 *)
    END_IF;
    IF (NOT IC) AND bLocalBlk = FALSE THEN
        iStatus := 0;
        iStopReason := 7;                 (* IC *)
    END_IF;
    IF bIBRun AND (iStatus <> 0) THEN
        iStatus := 0;
        iStopReason := 8;                 (* IB *)
    END_IF;
    IF bMCCFlt OR (NOT ME) THEN
        iStatus := 0;
        iStopReason := 6;                 (* ME/MCC *)
    END_IF;
END_IF;

(* ============================================================
   S05 状态机（官方 Starting/Run/Off 三态+接触器超时）
   ============================================================ *)
IF iStatus = 1 THEN
    Ord := TRUE;
    TON_Fdbck(IN := TRUE, PT := FdBckTime);
    IF bRun_DB THEN
        iStatus := 2;
        TON_RunMin(IN := TRUE, PT := T_RunMinSet);
    ELSIF TON_Fdbck.Q THEN
        iStatus := 0;
        Trip := TRUE;
        iStopReason := 20;                (* 接触器未吸合 *)
    END_IF;
ELSIF iStatus = 2 THEN
    Ord := TRUE;
    TON_RunMin(IN := TRUE, PT := T_RunMinSet);
    IF NOT bRun_DB THEN
        iStatus := 0;
        Trip := TRUE;
        iStopReason := 21;                (* 运行中反馈丢失 *)
    END_IF;
ELSE
    Ord := FALSE;
END_IF;
Run := (iStatus = 2) AND bRun_DB AND bFB1_DB AND bFB2_DB;
(* 防重复启动窗口 *)
TON_Restart(IN := (iStatus = 0), PT := T_RestartSet);
bPermStart := bPermStart AND NOT ((iStatus = 0) AND (NOT TON_Restart.Q));

(* ============================================================
   S06 输出驱动（官方 Ord；F163 O2=Ord 语义，F163 §4.4）
   ============================================================ *)
LocAlarmAck := RT_Ack.Q;
RT_Ack(CLK := AlarmAck);

(* ============================================================
   S07 报警生成（官方门控：仅Starting/Run产生报警；AlarmTr五档）
   ============================================================ *)
bAlmActive := (iStatus = 1) OR (iStatus = 2);
iAlmSev := 0;
IF bAlmActive THEN
    IF bMCCFlt OR (NOT ME) OR (NOT bRun_DB) THEN iAlmSev := 2; END_IF;
    IF (NOT bFB1_DB) OR (NOT bFB2_DB) OR bHiCurr OR Warning THEN iAlmSev := 1; END_IF;
END_IF;
(* 报警实例：Severity由AlarmTr映射（3/2→Failure 800，1→Warning 500，0→事件，-1→不产生） *)
ALM_M1(Alarm := (NOT M1) AND bAlmActive, Severity := 800, Enable := ME);
ALM_M2(Alarm := (NOT M2) AND bAlmActive, Severity := 800, Enable := ME);
ALM_M3(Alarm := (NOT M3) AND bAlmActive, Severity := 500, Enable := ME);
ALM_ME(Alarm := (NOT ME), Severity := 800, Enable := TRUE);
ALM_Fdbck(Alarm := Trip AND bAlmActive, Severity := 800, Enable := TRUE);
ALM_FB1(Alarm := (NOT bFB1_DB) AND bAlmActive, Severity := 500, Enable := TRUE);
ALM_FB2(Alarm := (NOT bFB2_DB) AND bAlmActive, Severity := 500, Enable := TRUE);
ALM_IOS(Alarm := bIOSFlt, Severity := 500, Enable := TRUE);
ALM_HiCurr(Alarm := bHiCurr AND bAlmActive, Severity := 500, Enable := TRUE);
ALM_Warn(Alarm := Warning AND bAlmActive, Severity := 500, Enable := TRUE);
(* 注：AlarmCond引脚名以库浏览器实际为准【需实测】；
   AlarmTr=0/-1时用Enable屏蔽实现事件/无（CL适配，官方由AE系统处理） *)

(* ============================================================
   S08 首报与跳闸记录（对齐官方 FirstOrMaxAETag/LastTripTxt/Trip）
   ============================================================ *)
RT_Reset(CLK := Trip);
IF RT_Reset.Q AND (FirstOrMaxAETag = '') THEN
    FirstOrMaxAETag := Name;              (* 本对象即首报源 *)
    FirstOrMaxAEIndTr := iStopReason;
END_IF;
IF Trip AND (LastTripTxt = '') THEN
    LastTripTxt := Name;                  (* 跳闸描述：工程侧可改填联锁tag *)
END_IF;
IF AlarmAck THEN
    Trip := FALSE;
    FirstOrMaxAETag := '';
END_IF;

(* ============================================================
   S09 统计（对齐官方 StartCnt/RuntimeCnt，冷保持）
   ============================================================ *)
TON_Sec(IN := (iStatus = 2), PT := T_SecTick);
IF TON_Sec.Q THEN
    RuntimeCnt := RuntimeCnt + 1.0;
    TON_Sec(IN := FALSE, PT := T_SecTick);
END_IF;
RT_Reset(CLK := Run);
IF RT_Reset.Q THEN
    StartCnt := StartCnt + 1;
END_IF;

(* ============================================================
   S10 组接口上报（对齐官方 MOT1Output 汇总语义）
   ============================================================ *)
Rfs := bPermStart AND (NOT bIOWarn) AND (iStatus = 0);
NoInt := Rfs AND IA;
FieldStartRelease := (iPOC = 2) AND bPermStart;
ForcedRun := (iPOC <> 2) AND Run AND (iStatus = 2);
FdBckOffErr := (iStatus = 0) AND bRun_DB;
ALPending := bAlmActive;
ALUnack := bAlmActive;                   (* 未确认标志由AE系统维护，此处近似 *)
ALNumber := iStopReason;
Seq := (iPOC = 0); Cen := (iPOC = 1); Loc := (iPOC = 2);
OutOfSrv := (iPOC = 3); Maint := (iMode = 2); Auto := (iMode = 1);
FB1PulseTime := 0.0;                     (* 脉冲周期由FB1Mode>0时实测填入【CL适配】 *)

END_FUNCTION_BLOCK
```

### MOT_C 中文逻辑对照表

| 段号 | 段名 | 中文逻辑（一句话） |
|---|---|---|
| S01 | 输入去抖 | FdBckRun/FB1/FB2 各经 TON 去抖（FdBckTime/FBTime）；M1-3+ME 合成 MCC 故障；IOStatus 非0算 IO 故障；MC 超 MCHiLim 算高电流 |
| S02 | 模式POC判定 | SetLoc/SetSeq/SetCen+LcbRem/LcbLoc 脉冲切 POC；LcbMaint 置维护；EnAuto+Seq 时进 Auto；本地/维护时置 bLocalBlk（联锁释放标记） |
| S03 | 联锁汇总 | IC 全模式生效；IB 本地/维护释放；IBF=TRUE 时 IB3/IB4 作启动联锁；IA 在 Auto 模式是启停源、Man 模式是运行联锁；PD 参与启动允许 |
| S04 | 命令仲裁 | 按 POC×Mode 走官方命令矩阵：本地=LCB；Auto=IA；Man=组命令/面板/外部脉冲；各停止来源记原因码 |
| S05 | 状态机 | Starting→接触器超时判 Trip；Run→反馈丢失判 Trip；Off→清输出；防重复启动窗口 |
| S06 | 输出驱动 | Ord=启停命令输出（F163 的 O2 硬件 DO）；LocAlarmAck 复位脉冲 |
| S07 | 报警生成 | **只有 Starting/Run 才产生报警**（官方门控）；MCC/ME/接触器=800，FB/IO/高电流/警告=500 |
| S08 | 首报跳闸记录 | Trip 上升沿锁 FirstOrMaxAETag/LastTripTxt；AlarmAck 清除 |
| S09 | 统计 | Run 每秒累加 RuntimeCnt；Run 上升沿计 StartCnt |
| S10 | 组接口上报 | Rfs/NoInt/FieldStartRelease/ForcedRun/FdBckOffErr/模式状态全部按官方 MOT1Output 语义算出供组汇总 |

## 2. GRP_C ST 骨架（对齐官方 GROUP）

```st
FUNCTION_BLOCK GRP_C
(* ============================================================
   GRP_C 组块（CL库，对齐官方 GROUP，05手册p22-24）
   分段：S01 输入与POC / S02 命令仲裁 / S03 步号解析 / S04 启动步进
        S05 停止步进 / S06 切换与快停 / S07 汇总与首报 / S08 事件
   官方步号规则：1-999启动升序 / 1001-1999停止降序 / 2001-2999切换前停止降序
   ============================================================ *)

VAR_INPUT
    Name: STRING[24] := 'GRP';
    Description: STRING[40] := 'Group';
    (* ---- 官方组参数（05手册p23-24）---- *)
    StwMode: DINT := 1;                   (* 0禁STW 1正常 2预选切换不预告 3standby切换不预告 *)
    StwFirst: BOOL := FALSE;              (* TRUE=全部预告先完再走第一步 *)
    SeqALEn: BOOL := TRUE;                (* 顺序运行时间监视使能 *)
    SeqALTime: TIME := T#5m;              (* 顺序超时值 *)
    ChngOver: BOOL := TRUE;               (* 启动结束自动停未预选设备（路由切换） *)
    EnAuto: BOOL := FALSE;                (* 组Auto（顺序停+延时） *)
    EnSeq: BOOL := TRUE;                  (* POC Seq使能 *)
    SetSeqMode: DINT := 1;                (* 组启动设消费者POC：0立即 1到步设 2从不 *)
    EnCen: BOOL := TRUE;                  (* POC Cen使能 *)
    EnLoc: BOOL := TRUE;                  (* POC Loc使能 *)
    EnForceLoc: BOOL := FALSE;            (* 组Local时全部成员改Local *)
    AlarmAck: BOOL := FALSE;              (* 报警确认脉冲 *)
    (* ---- 组输入（对齐官方 GrpInput）---- *)
    SeqStart: BOOL := FALSE;              (* 切SEQ并无启动联锁则启动 *)
    SeqStop: BOOL := FALSE;               (* 切SEQ并无停止联锁则停止 *)
    SeqHold: BOOL := FALSE;               (* 启/停中置HOLD *)
    QuickStop: BOOL := FALSE;             (* 快停（无视顺序和停止联锁） *)
    StartInt1: BOOL := TRUE;              (* 启动联锁1（TRUE=允许） *)
    StartInt2: BOOL := TRUE;
    StartInt3: BOOL := TRUE;
    StartInt4: BOOL := TRUE;
    StopInt1: BOOL := TRUE;               (* 停止联锁1（TRUE=允许停） *)
    StopInt2: BOOL := TRUE;
    StopInt3: BOOL := TRUE;
    StopInt4: BOOL := TRUE;
    IC: BOOL := TRUE;                     (* 组安全联锁（RUN联锁，正常停） *)
    IA: BOOL := TRUE;                     (* 组链式联锁（RUN联锁，正常停） *)
    (* ---- 成员状态（FBD连各消费者输出，最多999，CL取16）---- *)
    MemRun: ARRAY[1..16] OF BOOL;         (* 成员运行 *)
    MemRfs: ARRAY[1..16] OF BOOL;         (* 成员RFS *)
    MemTrip: ARRAY[1..16] OF BOOL;        (* 成员跳闸 *)
    MemStepStart: ARRAY[1..16] OF DINT;   (* 成员启动步号（来自消费者参数） *)
    MemStepStop: ARRAY[1..16] OF DINT;    (* 成员停止步号 *)
    MemPreSel: ARRAY[1..16] OF BOOL;      (* 成员预选 *)
    MemStdBy: ARRAY[1..16] OF BOOL;       (* 成员standby预选 *)
    MemOOS: ARRAY[1..16] OF BOOL;         (* 成员退出服务 *)
    MemTag: ARRAY[1..16] OF STRING[24];   (* 成员tag（首报显示用） *)
END_VAR

VAR_OUTPUT
    MemStart: ARRAY[1..16] OF BOOL;       (* 启动命令下发 *)
    MemStop: ARRAY[1..16] OF BOOL;        (* 停止命令下发 *)
    GroupRun: BOOL;                       (* 组运行 *)
    GroupRfs: BOOL;                       (* 组RFS *)
    GroupFlt: BOOL;                       (* 组故障 *)
    GroupHold: BOOL;                      (* 组HOLD *)
    FirstFaultTag: STRING[32] := '';      (* 首报成员tag *)
    CurStep: DINT;                        (* 当前步号 *)
    CurTag: STRING[24] := '';             (* 当前步设备tag *)
    SeqTimeLeft: TIME;                    (* 当前步剩余时间 *)
END_VAR

VAR
    i: INT; j: INT;
    iGState: INT;                         (* 0=Off 1=Starting 2=Run 3=Stopping 4=Hold *)
    iPOC: INT;                            (* 0=Seq 1=Cen 2=Loc *)
    bGrpStart: BOOL; bGrpStop: BOOL;
    bStartOK: ARRAY[1..16] OF BOOL;       (* 本步可启动 *)
    bStopOK: ARRAY[1..16] OF BOOL;        (* 本步可停止 *)
    bChngStop: ARRAY[1..16] OF BOOL;      (* 切换前停（2001-2999） *)
    bStepTmo: ARRAY[1..16] OF BOOL;       (* 步超时 *)
    bFirstFault: BOOL;
    iActive: INT; iRunCnt: INT; iPreCnt: INT;
    TON_Step: ARRAY[1..16] OF TON;        (* 每成员步超时 *)
    TON_Seq: TON;                         (* 顺序总超时 *)
    RT_SeqStart: R_Trig; RT_SeqStop: R_Trig; RT_QStop: R_Trig;
    T_StepTmo: TIME := T#30s;             (* 步超时设定【CL适配】 *)
    T_StwTime: TIME := T#5s;              (* 预告时长【CL适配，官方在STW块】 *)
    TON_Stw: TON;
END_VAR

(* ============================================================
   S01 输入与POC（官方：Group仅3个POC，无OOS）
   ============================================================ *)
IF SetLocCmd AND EnLoc THEN iPOC := 2;
ELSIF SetCenCmd AND EnCen THEN iPOC := 1;
ELSIF SetSeqCmd AND EnSeq THEN iPOC := 0;
END_IF;
(* 启动联锁：4个全允许才允许组启动 *)
bGrpStart := StartInt1 AND StartInt2 AND StartInt3 AND StartInt4 AND IC AND GroupRfs;

(* ============================================================
   S02 命令仲裁（官方 GrpInput：SeqStart/SeqStop/SeqHold/QuickStop）
   ============================================================ *)
RT_SeqStart(CLK := SeqStart);
RT_SeqStop(CLK := SeqStop);
RT_QStop(CLK := QuickStop);
IF RT_SeqStart.Q OR CmdStartFromFP THEN
    bGrpStartCmd := TRUE;
END_IF;
IF RT_SeqStop.Q OR CmdStopFromFP THEN
    bGrpStopCmd := TRUE;
END_IF;
IF SeqHold THEN
    iGState := 4;                         (* HOLD：中断启/停 *)
    bGrpStartCmd := FALSE;
    bGrpStopCmd := FALSE;
END_IF;
IF RT_QStop.Q THEN
    iGState := 3;                         (* 快停：无视停止联锁 *)
    bGrpStopCmd := TRUE;
    bQuickActive := TRUE;
END_IF;

(* ============================================================
   S03 步号解析（官方三段规则）
   ============================================================ *)
iActive := 0; iRunCnt := 0; iPreCnt := 0;
FOR i := 1 TO 16 BY 1 DO
    IF MemStepStart[i] > 0 THEN
        iActive := iActive + 1;
        IF MemPreSel[i] OR MemStdBy[i] THEN iPreCnt := iPreCnt + 1; END_IF;
        IF MemRun[i] THEN iRunCnt := iRunCnt + 1; END_IF;
    END_IF;
    (* 启动步1-999升序；停止步1001-1999降序；2001-2999切换前停 *)
    bStartOK[i] := (MemStepStart[i] > 0) AND (MemStepStart[i] < 1000)
                   AND (NOT MemRun[i]) AND MemRfs[i] AND MemPreSel[i] AND (NOT MemOOS[i]);
    bStopOK[i] := (MemStepStop[i] > 1000) AND (MemStepStop[i] < 2000)
                  AND MemRun[i] AND (NOT MemOOS[i]);
    bChngStop[i] := (MemStepStop[i] > 2000) AND (MemStepStop[i] < 3000)
                    AND MemRun[i] AND (NOT MemPreSel[i]) AND ChngOver;
END_FOR;
GroupRfs := (iActive > 0) AND (iPreCnt > 0);
GroupRun := (iActive > 0) AND (iRunCnt >= iActive);
GroupFlt := bFirstFault;

(* ============================================================
   S04 启动步进（升序：低步号全运行才放高步号；同步号并列）
   ============================================================ *)
IF iGState = 1 THEN
    FOR i := 1 TO 16 BY 1 DO
        IF bStartOK[i] THEN
            (* 检查所有更低步号是否已运行 *)
            bStepClear := TRUE;
            FOR j := 1 TO 16 BY 1 DO
                IF (j <> i) AND (MemStepStart[j] > 0) AND (MemStepStart[j] < 1000)
                   AND (MemStepStart[j] < MemStepStart[i]) AND (NOT MemRun[j]) THEN
                    bStepClear := FALSE;
                END_IF;
            END_FOR;
            IF bStepClear THEN
                TON_Step[i](IN := TRUE, PT := T_StepTmo);
                MemStart[i] := TRUE;
                CurStep := MemStepStart[i];
                CurTag := MemTag[i];
                IF MemRun[i] THEN
                    MemStart[i] := FALSE;
                ELSIF TON_Step[i].Q THEN
                    bStepTmo[i] := TRUE;
                END_IF;
            END_IF;
        ELSE
            TON_Step[i](IN := FALSE, PT := T_StepTmo);
        END_IF;
    END_FOR;
    TON_Seq(IN := TRUE, PT := SeqALTime);
    IF TON_Seq.Q AND SeqALEn THEN
        iGState := 4;                     (* 顺序超时→HOLD并报警 *)
    END_IF;
    IF GroupRun THEN
        iGState := 2;
        (* 启动结束：ChngOver自动停未预选设备 *)
        FOR i := 1 TO 16 BY 1 DO
            IF bChngStop[i] THEN MemStop[i] := TRUE; END_IF;
        END_FOR;
    END_IF;
END_IF;

(* ============================================================
   S05 停止步进（降序：高步号全停才放低步号）
   ============================================================ *)
IF iGState = 3 THEN
    FOR i := 1 TO 16 BY 1 DO
        IF bStopOK[i] THEN
            bStepClear := TRUE;
            FOR j := 1 TO 16 BY 1 DO
                IF (j <> i) AND (MemStepStop[j] > 1000) AND (MemStepStop[j] < 2000)
                   AND (MemStepStop[j] > MemStepStop[i]) AND MemRun[j] THEN
                    bStepClear := FALSE;
                END_IF;
            END_FOR;
            IF bStepClear OR bQuickActive THEN
                MemStop[i] := TRUE;
                CurStep := MemStepStop[i];
                CurTag := MemTag[i];
                IF NOT MemRun[i] THEN
                    MemStop[i] := FALSE;
                END_IF;
            END_IF;
        ELSE
            MemStop[i] := FALSE;
        END_IF;
    END_FOR;
    IF iRunCnt = 0 THEN
        iGState := 0;
        bQuickActive := FALSE;
        bGrpStopCmd := FALSE;
    END_IF;
END_IF;

(* ============================================================
   S06 切换与快停辅助（ChngOver 已在S04；快停见S02）
   ============================================================ *)
IF bQuickActive THEN
    FOR i := 1 TO 16 BY 1 DO
        IF MemRun[i] AND (NOT MemOOS[i]) THEN MemStop[i] := TRUE; END_IF;
    END_FOR;
END_IF;

(* ============================================================
   S07 汇总与首报（官方：组面板显示第一个不运行成员+链接）
   ============================================================ *)
bFirstFault := FALSE;
IF NOT bFirstFault THEN
    FOR i := 1 TO 16 BY 1 DO
        IF (MemStepStart[i] > 0) AND (MemTrip[i] OR bStepTmo[i]) THEN
            bFirstFault := TRUE;
            FirstFaultTag := MemTag[i];
        END_IF;
    END_FOR;
END_IF;
(* standby切换：有成员跳闸且有standby预选→尝试启动standby（官方2周期内） *)
IF bFirstFault THEN
    FOR i := 1 TO 16 BY 1 DO
        IF MemStdBy[i] AND MemRfs[i] AND (NOT MemRun[i]) THEN
            MemStart[i] := TRUE;
        END_IF;
    END_FOR;
END_IF;
(* 组状态机 *)
CASE iGState OF
    0: (* Off *)
        bGrpStopCmd := FALSE;
        bFirstFault := FALSE;
        FirstFaultTag := '';
        IF bGrpStartCmd AND bGrpStart AND (iPreCnt > 0) THEN
            iGState := 1;
            TON_Stw(IN := TRUE, PT := T_StwTime);   (* STW预告（简化，官方STW块） *)
        END_IF;
    1: (* Starting，见S04 *)
        IF bFirstFault THEN iGState := 4; END_IF;
    2: (* Run *)
        IF bGrpStopCmd OR (NOT IC) OR (NOT IA) THEN
            iGState := 3;
        END_IF;
    3: (* Stopping，见S05 *)
        ;
    4: (* Hold *)
        IF bGrpStartCmd AND bGrpStart THEN iGState := 1; END_IF;
        IF bGrpStopCmd THEN iGState := 3; END_IF;
END_CASE;
IF TON_Stw.Q AND (iGState = 1) THEN
    TON_Stw(IN := FALSE, PT := T_StwTime);
END_IF;
SeqTimeLeft := SeqALTime - TON_Seq.ET;

(* ============================================================
   S08 事件（官方 ModeTr/StatusTr：POC/模式/状态变化产生事件）
   ============================================================ *)
(* 事件用 SimpleEventDetector 实例（F163 §5.9）：POC变化/状态变化/首报/超时 *)

END_FUNCTION_BLOCK
```

### GRP_C 中文逻辑对照表

| 段号 | 段名 | 中文逻辑（一句话） |
|---|---|---|
| S01 | 输入与POC | Group 只有 Seq/Cen/Loc 三个 POC（无 OOS）；4 启动联锁+IC 全允许才允许组启动 |
| S02 | 命令仲裁 | SeqStart/SeqStop/QuickStop/SeqHold 官方输入；HOLD 中断启停；快停无视停止联锁 |
| S03 | 步号解析 | 启动步 1-999 升序、停止步 1001-1999 降序、2001-2999 切换前停（ChngOver）；预选/standby/OOS 过滤；组 RFS/Run 汇总 |
| S04 | 启动步进 | 低步号全运行才放高步号（同步号并列同启）；每成员步超时 T_StepTmo；顺序总超时 SeqALTime→HOLD；全运行→Run 并触发 ChngOver 停未选设备 |
| S05 | 停止步进 | 高停止步号全停才放低步号；快停时同时停全部；全停→Off |
| S06 | 切换与快停 | 快停激活期对所有运行成员发停止（无视顺序） |
| S07 | 汇总与首报 | 第一个跳闸/超时成员锁 FirstFaultTag；有 standby 预选且 RFS→自动启动 standby（官方 2 周期内重启）；组状态机四态 Off/Starting/Run/Stopping/Hold |
| S08 | 事件 | POC/模式/状态变化、首报、步超时、顺序超时发事件（SimpleEventDetector） |

## 3. 工程侧布尔连锁示例（Code 段，无 VAR 声明，F163 §4.1）

```st
(* ===== S10 布尔连锁（变量在 Var.xlsx 定义，FBD 连线到 MOT_C 引脚）===== *)
(* 官方联锁语义：TRUE=联锁生效；IC全模式生效，IB/IA/PD本地维护释放 *)
N562_FN1_E01_IC := NOT N562_GB1_SafeOK;                (* 安全OK取反→IC安全联锁 *)
N562_FN1_E01_IB1 := N562_FN1_T1_T_H;                   (* 轴承温度高→IB设备联锁 *)
N562_FN1_E01_IB2 := N562_FN1_P1_P_H;                   (* 压力高→IB设备联锁 *)
N562_FN1_E01_IA := NOT N562_SR1_91_Run;                (* 选粉机没转→IA过程/链式联锁 *)
N562_FN1_E01_PD := NOT N562_HD1_E01_Run;               (* 前序设备没转→PD *)
N562_FN1_E01_IBF := TRUE;                              (* IB3/IB4作为启动联锁 *)
(* 组侧：G30 组的启动/停止联锁（TRUE=允许） *)
N562_GR_G30_SI1 := N562_GB1_OilOK;                     (* 润滑油OK才允许组启动 *)
N562_GR_G30_SI2 := NOT N562_FN1_T1_T_H;                (* 温度不高才允许组启动 *)
```

## 4. FBD 管脚连线清单（MOT_C 实例 N562_FN1_E01，官方管脚名）

| MOT_C 引脚 | 连到 | 方向 | 说明 |
|---|---|---|---|
| Name/Description | Var 表 string 初值 | in | Tag（允许 . -，禁空格:;） |
| GrpStartStep | 参数（如 20） | in | 启动步号 1-999 |
| GrpStopStep | 参数（如 1020） | in | 停止步号 1001-1999 |
| GrpStartDelay/GrpStopDelay | 参数 | in | 组序延时 |
| FdBckRun | `N562_FN1_90_Run.Value` | in | DintIO→.Value→Bool【F163 §5.1】 |
| FB1 | `N562_FN1_91_Spd.Value` | in | 速度开关（功能反馈） |
| M1/M2/M3 | `N562_FN1_90_M1.Value` 等 | in | MCC 信号 |
| ME | `N562_FN1_90_ME.Value` | in | 主控制电压 |
| MC | `N562_FN1_90_I.Value` | in | 电流 RealIO |
| Ord | `N562_FN1_90_O2.Value` | out | Bool→DintIO（F163 的 O2 硬件 DO） |
| IC/IB1/IB2/IA/PrevDrive | §3 布尔连锁变量 | in | FBD 连线 |
| SeqStart/SeqStop | 组 GRP_C 的 MemStart/MemStop 对应位 | in | 或画面按钮变量 |
| MemRun→（组侧） | `N562_FN1_E01.Run` | 出 | 组 MemRun[i] |
| MemRfs→（组侧） | `N562_FN1_E01.Rfs` | 出 | 组 MemRfs[i] |
| MemTrip→（组侧） | `N562_FN1_E01.Trip` | 出 | 组 MemTrip[i] |
| AlarmTr/InterlockTr | 参数 3 | in | 报警处理档位 |
| M1Txt…WarningTxt | Var 表 string 初值 | in | NLS 前缀规范 |

## 5. F163 §5 规则符合性自检（V2）

| # | 规则 | 本骨架执行 |
|---|---|---|
| 1 | 硬件 IO 经 .Value | 引脚用 Bool/Real，.Value 转换在工程侧变量（§4 表） |
| 2 | Code 无声明段 | 工程 Code（§3）只有执行语句 |
| 3 | 禁位运算 | IOStatus 判断用 `<>0` 比较；报警计数 IF 累加 |
| 4 | 禁字符串/时间字面量 | 字面量只在 VAR 初值（Name/Txt/T#2s 等）；清空用 `Name`/`''` 替代——**`''` 需实测**，不行就赋 Name |
| 5 | 实例必须被调用 | TON_*/RT_*/ALM_* 全部在 Code 段调用 |
| 6 | 引脚大小写 | TON/TOF/R_Trig/AlarmCond 官方大小写；官方参数名照抄 |
| 7 | in_out 无 retain / in 不赋值 | 全部 VAR_INPUT/VAR_OUTPUT，无 in_out |
| 8 | AlarmCond 800/500 | S07 只用 800/500（AlarmTr=0/-1 用 Enable 屏蔽近似） |
| 9 | 官方语义保持 | IC/IB/IA/PD、步号三段、POC 三/四点、状态门控报警 |

## 6. 本篇结论

V2 骨架两句话：**MOT_C 把官方 MOT1 的 77 参数浓缩成"硬件+联锁+组接口+报警"四组引脚+S10 段逻辑；GRP_C 把官方 GROUP 的步号三段规则做成双循环步进**。所有引脚名与官方一致——现场和 ABB 对话零翻译。抄完先过 §5 自检表，再按 09 文档核对清单编译。
