---
title: MinLib拆解复用-公共基础设计（命名/CC结构体/参数模板）
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,ControlConnection,STRUCT,命名规范,参数表]
summary: CL库命名规范、CC_Equip/CC_Signal/CC_Group三个控制连接结构体全字段定义、参数表六要素模板
source: 数据表 p2/p4/p5 + F163规则总纲 §3.5/§4.7/§5
---

# 01 公共基础设计

> 本篇是 CL 库（CEMENT_LIB）的"地基"：命名规范 + 三条 Control Connection 的完整字段定义 + 参数表模板。
> 除特别标注【核实】外，均为【自拟】设计（依据见 00 文档第 2 章）。

## 1. 库与命名规范

### 1.1 库信息

| 项 | 值 |
|---|---|
| 库名 | CEMENT_LIB |
| 版本 | 1.0.0（首个可用版），修订递增 1.0.x |
| 适用 | ABB 800xA 6.1.0 / Control Builder M（与 F163 现场一致【F163 §1】） |
| 目标 | 新增控制器/新组直接用；老 CementMill 程序不动 |

### 1.2 功能块类型命名（FBT）

| 类型名 | 用途 | 备注 |
|---|---|---|
| MOTOR_C | 开关型动力设备（电机、加热器、风机、泵）通用 | 对应现有 MOTOR1 的升级位 |
| VALVE_C | 阀门（开关阀/调节阀双模式） | 对应 VALVE1/PVALVE |
| GROUP_C | 组（顺序/周期/首报/汇总） | 对应 Group/GROUP1 的升级位 |
| SEL_C | 选择器（主备切换/路由） | 数据表 p2 selector 的落地 |
| SIG_C | 联锁信号（DI/AI/PID 输出联锁量） | 数据表 p4 PCC 的落地 |
| CHK_C | 调试检查框架块 | 官网 2019 commissioning check 的落地 |
| TDeb | 输入去抖辅助块（TON+TOF 封装） | 内部辅助，不直接拖 |

命名规则：全大写 + 下划线；设备类以 `_C`（Cement）结尾与旧库区分；辅助块小驼峰。**类型名大小写敏感**【F163 §5.6】。

### 1.3 实例与变量命名（工程侧，延续 F163 §4.7）

- FB 实例：`N<节点><系统><设备类型><编号>`，如 `N562HD1E01`（不变）；
- 变量：`N<节点>_<系统>_<设备>_<信号>_<后缀>`，如 `N562_HD1_T1_T_H`（不变）；
- **CC 连线变量**（本库新增）：`N<节点>_<系统>_<设备>_CC`（命令）+ `_CCS`（状态），如 `N562_HD1_E01_CC` / `N562_HD1_E01_CCS`；
- Description 格式不变：`英文描述 / 中文描述 - 莱歇编号`，如 `Raw Mill Fan / 原料磨风机 - 1632FN01`【F163 §3.8】。

### 1.4 状态枚举常量（全库统一，Int 表示）

800xA ST 无 enum，用 `VAR CONST` 定义命名常量（**是否允许在 FBT 内 VAR CONST 赋值需实测确认**；若不允许，把常量写进文档和面板配置，代码里直接用数字+注释）。

| 常量 | 值 | 含义（设备状态 Status） |
|---|---|---|
| ST_STOP | 0 | 停止 |
| ST_STARTING | 1 | 启动中 |
| ST_RUN | 2 | 运行 |
| ST_STOPPING | 3 | 停止中 |
| ST_FAULT | 4 | 故障 |
| ST_LOCAL | 5 | 本地 |
| ST_MAINT | 6 | 检修 |

| 常量 | 值 | 含义（报警等级 AlmLevel） |
|---|---|---|
| ALM_NONE | 0 | 无报警 |
| ALM_WARN | 1 | 警告 |
| ALM_FLT | 2 | 故障 |

| 常量 | 值 | 含义（联锁类型 SigType，对齐 F163 §6.2） |
|---|---|---|
| ITL_ALM | 0 | 仅报警（不动作） |
| ITL_STA | 1 | 启动禁止（STAITL） |
| ITL_OPR | 2 | 操作联锁（OPITL，运行中动作） |
| ITL_PRT | 3 | 保护联锁（PRTITL，跳闸） |
| ITL_PST | 4 | 保护性启动（PSTITL） |

## 2. Control Connection 结构体定义

三条 CC 都是普通 STRUCT，按 F163 §3.5 **先建数据类型再建 FBT**（STRUCT 路线先行）。所有字段带中文注释；字段名大小写敏感【F163 §5.6】。

### 2.1 CC_EqCmd —— 组→设备 命令通道（父→子，单向）

| 字段 | 类型 | 说明 |
|---|---|---|
| Enable | Bool | TRUE=本设备参与本组。FALSE=断开连接（MinLib "运行时可增删设备"的落地：改 Enable 即把设备挂/摘出组，不用改代码）【参照数据表 p2】 |
| Start | Bool | 启动命令（组按步序逐个给，见 04 文档） |
| Stop | Bool | 停止命令 |
| StepNo | Int | 启动步号（1..N）。**改这个参数就改了启动顺序**，下装即生效【参照数据表 p2】 |
| StepNoStop | Int | 停止步号（默认与 StepNo 相同，停止默认反序） |
| DelayStart | Time | 到本步后延时多久再发启动命令（躲开同时启动冲击） |
| DelayStop | Time | 停止步间延时 |
| EnStandby | Bool | TRUE=本设备在该组是备用。备用设备报警自动降级【数据表 p5】 |
| EnAckLocal | Bool | TRUE=本地模式时该设备报警自动确认【数据表 p5】 |
| EnCyclic | Bool | TRUE=组按周期模式运行时本设备随周期启停（见 04 文档） |
| EnSimDown | Bool | 组级仿真下发标志（组 EnSim=TRUE 时经此字段把仿真传到每台设备，见 07 文档 §1.1） |

### 2.2 CC_EqStat —— 设备→组 状态通道（子→父，单向）

| 字段 | 类型 | 说明 |
|---|---|---|
| Run | Bool | 运行反馈已确认 |
| Ready | Bool | 就绪（无禁止、无故障，可启动） |
| Fault | Bool | 故障（需复位） |
| Warning | Bool | 警告（未故障） |
| Local | Bool | 本地模式（面板操作无效，供组显示） |
| Maint | Bool | 检修模式（挂牌） |
| Status | Int | 状态枚举，见 1.4 表 |
| RunTime | Time | 本次连续运行时长（主备均衡切换的依据，SEL_C 用） |
| FirstFault | Bool | TRUE=我是导致组失败的首报设备（组只认第一个，见 04 文档） |
| FaultTag | String[32] | 自身 tag，故障时由组记录并在组面板显示+超链接【数据表 p2】 |
| SigTag | String[32] | 引发本次故障的**联锁信号 tag**（设备面板显示+超链接）【数据表 p4】 |
| AlmLevel | Int | 当前最高报警等级（0/1/2） |
| AlmActive | Int | 活动报警条数 |
| ChkPass | Bool | 本设备调试检查已通过（CHK_C，组级汇总用） |

> String 字段注意：FBT 内部变量 string 初值是否允许直接赋值**需实测确认**；若报错，改为外部参数注入（FaultTag 在实例化时由工程变量赋值）。

### 2.3 CC_SigOut —— 信号→设备 联锁通道（父→子，单向）

一个信号块（SIG_C）可同时联锁多台设备：每台设备一个独立 CC_SigOut 实例。

| 字段 | 类型 | 说明 |
|---|---|---|
| AlmLevel | Int | 0无/1警告/2故障（阈值+延时+设备状态算出） |
| Interlock | Bool | 联锁动作输出（按 SigType 语义执行） |
| SigType | Int | 联锁类型，见 1.4 表 |
| InhibitStart | Bool | 启动禁止计时中（倒计时期间禁止启动，数据表 p4 "start inhibit time"） |
| Override | Bool | TRUE=临时旁路（维修/异常工况用，**联锁 viewer 必须显示**【数据表 p4】） |
| OvrdLeft | Time | override 剩余时间（0=无限期，>0=到时自动解除） |
| SigTag | String[32] | 信号 tag（设备面板显示+超链接） |
| ThrWarn | Real | 警告阈值（在线可改，面板显示） |
| ThrFlt | Real | 故障阈值（在线可改，面板显示） |
| DelayWarn | Time | 警告延时（数据表 p4 "warning delay"） |
| DelayFlt | Time | 故障延时（数据表 p4 "failure delay"） |

### 2.4 CC_SigIn —— 设备→信号 回读通道（子→父，单向）

信号块要靠设备状态决定是否报警/抑制【数据表 p4："signals read the process equipment status"】：

| 字段 | 类型 | 说明 |
|---|---|---|
| Run | Bool | 设备运行中 |
| Local | Bool | 设备本地模式（此状态下部分联锁自动确认/降级） |
| Maint | Bool | 设备检修（此状态下联锁屏蔽，viewer 显示） |
| GroupActive | Bool | 设备所属组是否活动（组停=不报，数据表 p5 规则1） |
| GroupStarting | Bool | 组正在启动（启动抑制期，数据表 p5 规则2） |

### 2.5 CC_Group —— 组→上层 汇总通道（组→组/组→系统）

| 字段 | 类型 | 说明 |
|---|---|---|
| GroupRun | Bool | 组运行（全部应运行设备在跑） |
| GroupReady | Bool | 组就绪 |
| GroupFault | Bool | 组故障 |
| FirstFaultTag | String[32] | 首报设备 tag（组面板+上级组用） |
| EquipTotal | Int | 组内设备总数（Enable=TRUE 计数） |
| EquipRun | Int | 运行中设备数 |
| ChkDone | Int | 调试检查已通过项数 |
| ChkTotal | Int | 调试检查总项数 |

## 3. 参数表模板（每个 FBT 一份，工程时填）

每功能块的参数按此模板列全（02/03/04 文档直接用它）：

| 参数名 | 类型 | 默认值 | 范围/单位 | 在线可改 | 面板显示 | 中文说明 |
|---|---|---|---|---|---|---|
| 例：T_StartMax | Time | T#5s | 0~60s | 是 | 是 | 启动反馈超时：发出启动命令后多久收不到运行反馈即报"启动失败" |

六要素缺一不可；**现场可变数值（延时/量程/阈值/联锁）一律参数化，改参数不改代码**【用户既定原则】。

## 4. 800xA 落地注意事项（编译防错清单）

1. **先建 STRUCT 再建 FBT**（F163 §3.5 导入顺序：STRUCT → VAR → PAR → FUN → ST → FBD → 整程序编译）；
2. CC 结构体变量在工程 VAR 表声明，**Initial Value 列保持空**（结构体聚合写初值会报 Error 1340【F163 §4.5】），需要非零初值的在 ST 初始化段逐个成员赋值；
3. `in_out` 管脚不带 retain（Error 1005）；`in` 管脚不赋值（Error 1034）【F163 §5.7】；
4. 引脚名/类型名大小写敏感，`TOf`/`R_Trig`/`AlarmCond` 按官方大小写【F163 §5.6】；
5. Code 内禁字符串/时间字面量——时间用 `T#5s` 赋给参数默认值，string 放 VAR 表初值或外部注入【F163 §5.4】；
6. 禁位运算，拆字节用 `/2^n MOD 2`，打包用 IF 累加【F163 §5.3】；
7. FBT 内实例化的辅助 FB（TOf/R_Trig/AlarmCond/TDeb）必须在 FBT 的 Code 段被调用，否则 Warning 1542【F163 §5.5】。

## 5. 本篇结论

三条 CC（CC_EqCmd/CC_EqStat/CC_SigOut+CC_SigIn/CC_Group）就是 CL 库的全部"散线替代品"：组与设备之间只剩两根结构体线，信号与设备之间两根，组向上汇总一根。字段设计原则就一条——**凡是最初可能想写死在代码里的判断依据，都提成字段或参数**。
