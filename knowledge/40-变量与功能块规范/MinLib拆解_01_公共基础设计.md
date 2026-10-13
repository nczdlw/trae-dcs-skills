---
title: MinLib拆解复用-公共基础设计V2（官方机制对齐）
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,PCC,GCC,LCC,联锁参数,IntlkType,Std_Type,仿真,命名规范]
summary: V2：官方四条总线机制、PCC联锁参数全表（IntlkType/IntlkDir/StartInhibit/LocStartOverride）、Std_Type报警禁用矩阵、仿真初始行为与安全规则、命名规范（官方CM命名+F163命名）
source: 02 Basic手册3BHS161556 RevD §2.2.3-2.2.5 + 00产品指南 §3 + 04手册p5-6
---

# 01 公共基础设计（V2）

> **V2 变更**：总线段落改为"官方机制+CL 落地"双栏。官方 Data Type 字段清单在 02/04 文档按对象展开，本篇聚焦**机制和参数体系**（这是官方手册里最值钱的部分）。
> 标注：【核实-手册】=官方写明带页码；【CL 适配】=落地设计。

## 1. 命名规范（官方实例 + F163 规则）

### 1.1 官方 CM 命名实例【核实-00手册p32/p42】

| 官方对象 | Control Module 名 | Module Parameter "Name" |
|---|---|---|
| DIS（流量开关） | `_562_BM1_FS1R` | `562-BM1.FS1R` |
| MOT1（磨主电机） | `_562_BM1_M1R` | `562-BM1.M1R` |
| AIS（轴承温度） | `_561T101_R` | `562TI101R` |
| GROUP（组） | `GR_562_2R` | `GR_562_2R` |
| PREBIN（预选1） | `GR_562_2R_P1` | `GR_562_2R_P1` |

规律：CM 内部名下划线前缀（`_` 开头防与工程变量撞名），对外显示名用"区域-设备.信号"点分格式；组用 `GR_` 前缀，预选挂在组名下 `_P1/_P2`。

### 1.2 CL 库命名【CL 适配，对齐官方风格+F163 §4.7】

- CM 类型：`MOT_C / VLV_C / GRP_C / PRE_C / STW_C / SIG_C / CHK_C`（对应官方 MOT1/VLV1/Group/Prebin/STW/DIS-AIS/CCF）；
- 工程实例：下划线前缀 + 设计院编号，如 `_N562_HD1_E01`（CM 名）/ `N562-HD1.E01`（Name 参数，显示用）；
- 组：`_N562_GR_G30` / `N562-GR.G30`；预选：`_N562_GR_G30_P1`；
- 变量命名仍按 F163 §4.7：`N<节点>_<系统>_<设备>_<信号>_<后缀>`。

## 2. 四条总线：官方机制 → CL 落地

### 2.1 总机制【核实-00手册p25-29】

- 模块间经**预定义接口的结构化变量**（control connection）交换数据：一根逻辑线=多变量；父子双向；连接数不限；
- 状态子→父、命令父→子或子→父都行；PCC 允许无限个信号作用于一个消费者【00手册p26】；
- 编程只在 Diagram Editor 里连线 + 配参数，**块间不写散代码**（"胶水逻辑"对操作员隐藏）【00手册p28-29】。

### 2.2 CL 落地的四条总线【CL 适配】

| CL 总线 | 对齐官方 | 连什么 | 字段定义在 |
|---|---|---|---|
| `GCC_ComData` | GCC | 组↔设备 | 04 文档 §2（官方 Group/Consumer 的 GCC 接口字段） |
| `PCC_ComData` | PCC | 信号↔设备 | 02 文档 §2 + 本篇 §3 |
| `LCC_LoopData` | LCC（LoopControlData） | 回路↔执行器 | 06 文档 §5（二期） |
| `CC_Base` | -CC 通用 | 父子状态/命令基础 | 各对象公共章 |

> 官方 PCC 的结构化变量名在 Basic 手册参数表里已见到：**`PCCComData`**（引脚描述 "IN/OUT: Interlock Bus, PriorityCommand/Interlock"）【02手册p?（DIS 参数表）】。CL 版字段与官方 Data Type 的对应关系在 02/04 文档逐对象列。

## 3. PCC 联锁参数体系（官方全量，最值钱的一段）【核实-02手册p6-10】

### 3.1 联锁配置参数（配在信号对象上，不在设备上！）

| 参数 | 作用 |
|---|---|
| **IntlkType** | 联锁类别（见 3.2 表） |
| **IntlkDir** | 双向设备的方向相关配置（见 3.3 表） |
| **IntlkStartInhibit** | PCC 父对象（MOTx/VLVx）启动后**设定时间内旁路联锁**——应用：电机启动电流涌入（rush-in）误报 |
| **IntlkLocStartOverride** | **本地模式下持续按住 LCB 启动按钮时旁路联锁**（要求所有 PCC 父都在 LOC）——应用：皮带机本地纠偏时临时旁路跑偏开关 |

IntlkType/IntlkDir 是**按限值（limit-based）**配置的；IntlkStartInhibit/IntlkLocStartOverride 对对象全部限值生效【02手册p6】。

### 3.2 IntlkType 取值表【核实-02手册p7-8】

| 配置项 | 含义 |
|---|---|
| PCC_Disabled | PCC 总线上无报警无联锁转发 |
| No_Interlock | 不转发联锁，只转发报警 |
| PD_PrevDrive | 前序设备联锁，**组保持 Ready for Start** |
| IA_Process | 过程联锁；**Auto 模式下 ok 条件后不自动复位**，只能由另一 PCC 限值/信号的 Auto_Start 命令复位 |
| IA_Process_RFS | 过程联锁，组保持 RFS；Auto 行为同上 |
| IB_Equipment | 设备联锁 |
| IB_Equipment_RFS | 设备联锁，组保持 RFS |
| IC_Safety | 安全联锁 |
| IC_Safety_RFS | 安全联锁，组保持 RFS |
| Auto_Start | 仅 Auto 模式用：移除已保持的 IA 联锁（若已不激活）从而启动设备（IO.In.IA 也需 OK） |

> **RFS 后缀 = "组保持就绪"**：联锁动作只挡本设备，不挡组启动——这是官方处理"部分设备联锁但组仍可启"的标准机制，V1 自拟的 EnGrpHold 可以退役了。

### 3.3 IntlkDir 取值表（按信号 CM 类型支持矩阵）【核实-02手册p9-10】

| 组 | 取值 | 支持 |
|---|---|---|
| 基本方向 | DirX / DirY / DirXY | AIS AIC DIS DIC PCC_Com_Drive PCC_Threshold_AND3 PIDCtrl PIDAdvCtrl 全支持 |
| 启动后忽视 | DirXStart / DirYStart / DirXYStart | 同上；运行到位后该联锁被忽视 |
| 动态反馈 | DirFBX / DirFBY / DirFBXY | 信号作动态反馈（如 MOT1 的 FB1）：条件满足 IO.Out.RunX/Y 才激活；可带预警/报警/就绪延时；**PCC_Com_Drive 不支持** |
| 快速任务 | DirXFast / DirYFast / DirXYFast / DirFBXFast… | 仅 DIS（Alarm）；用于 MOT2 定位停止、MOTP 中停等需快速停止的场合 |
| noAck 变体 | DirXnoAck 等（含 Start/FB/Fast 组合） | 用 "Value" 代替 "Normal"：报警未确认但值恢复正常后仍可操作 |

### 3.4 PCC 扩展功能块【核实-02手册p6】

| 块 | 用途 |
|---|---|
| **PCC_Connect** | 一个信号接 2+ 消费者/组；可为每个消费者单独配"联锁转发掩码"（按限值决定哪些联锁被阻断）；还能覆盖消费者对信号的报警/事件使能 |
| **PCC_Threshold_AND3** | 复杂联锁：多个自定义条件相与后作为 PCC 总线上的联锁源 |
| **PCC_Intlk** | 通用联锁配置对象（参数同 AIC/AIS/DIC/DIS/PIDCtrl）【02手册p6】 |

## 4. 报警禁用矩阵（官方 Std_Type）【核实-02手册p6-7】

自动禁用 AIS/DIS 报警的规则，由工程常量决定：

| 设置 | 规则 |
|---|---|
| `cBMI.Std_Type = 0`（默认） | 电机未运行、NC 阀关闭、NO 阀开启、接组时组未启动 → **该信号的报警自动禁用** |
| `cBMI.Std_Type = 1` | 同 0，但**组已启动且消费者被预选时一律报警**；若消费者是 standby 预选，**报警优先级自动从 Failure 降为 Warning** |
| `PCCAEListFrcEn = true` | 关闭自动禁用——用于需要独立于父状态报警的信号（如料位） |

**这一张表就是 V1"四条抑制规则"的官方正解**：组停抑制=Std_Type 0；备用降级=Std_Type 1；独立信号=PCCAEListFrcEn；本地自动确认见 §5。

## 5. 报警确认与首报【核实-02手册p6 + 00手册p31/p44-46】

- **双向报警确认**：AIS/DIS ↔ Consumer/Group 任一面板确认；组面板确认会下传到信号级；典型用法=消费者 Local 控制时自动确认；
- **首报检测**：信号侧自动首报检测，首报信号显示在消费者和组面板上，**带链接按钮直达源信号**；
- 组面板文字显示"第一个不运行的消费者"+下钻到设备+设备下钻到信号（00 手册p44-46 实例）。

## 6. 仿真模式（官方规则）【核实-02手册p11】

| 项 | 官方行为 |
|---|---|
| 可仿真对象 | DIS、AIS、DOS、AOS（Consumer/Group 的 Simulation Mode 见 07 文档） |
| 硬件错误连接 | 仿真模式下**不考虑** |
| 热启动后初始行为 | AIS：值=量程 50%、输入阻塞；DIS：值=正常位、输入阻塞；DOS/AOS：不考虑硬件连接 |
| 输出对象的坑 | **DOS/AOS 若接了硬件，所有改动仍会写进硬件**——仿真不等于输出被屏蔽！ |
| 安全红线 | 启用仿真前**必须先断开 Profibus、Modbus 及其他硬件接口** |

> V1 自拟的"仿真时物理输出强制关断"与官方不同：官方输出对象仿真不屏蔽硬件写入，靠"先断总线"保平安。CL 版按官方来，别自己发明。

## 7. Parameter Error 机制【核实-02手册p11】

- CM 参数（本块或相连块）非法时，图形元素和面板显示 **Parameter Error**——含义是"应用程序需要修正"，不是过程故障；
- CL 库每条参数加范围检查，非法值触发 Parameter Error 指示而不是默默钳位。

## 8. 参数表模板（V2）

| 参数名 | 类型 | 默认值 | 范围 | 在线可改 | 面板显示 | 中文说明 |
|---|---|---|---|---|---|---|
| 例：IntlkType | Enum | PCC_Disabled | 见 §3.2 | 是 | 是 | 联锁类别（信号对象参数） |

> V2 起参数表优先采用官方参数名（IntlkType/IntlkDir/IntlkStartInhibit/IntlkLocStartOverride/cBMI.Std_Type/PCCAEListFrcEn…），CL 新增参数才用自拟名并标注【CL 适配】。

## 9. 本篇结论

01 的 V2 核心是三张官方表：**IntlkType 九项、IntlkDir 五组、Std_Type 报警禁用矩阵**，外加两个官方扩展块（PCC_Connect/PCC_Threshold_AND3）和一条仿真安全红线（先断总线再仿真）。写 CL 库时这些名字直接照抄官方，现场和 ABB 支持人员对话时零翻译成本。
