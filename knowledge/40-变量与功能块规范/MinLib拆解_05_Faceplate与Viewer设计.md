---
title: MinLib拆解复用-Faceplate与Viewer设计V2（官方对齐）
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,faceplate,VCO,ASM,GraphiXs,ProcessPanel,viewer,图形元素]
summary: V2：官方Faceplate八要素、Drive图形元素族与状态色、VCO三种显示模式与ASM灰度规范、Step/Status/PCC三viewer列定义、Process Panel P800对象清单与工程指南、CL面板落地映射
source: 00产品指南§2 + 04手册§2.3 + 12 Process Panel手册3BHS835707 RevD + 05手册§2.3
---

# 05 Faceplate 与 Viewer 设计（V2）

> **V2 变更**：全部改为官方手册内容。V1 自拟的"四区布局/三重编码表"保留为 CL 落地简化版，官方结构以本篇为准。
> 页码标注：[00手册pN]=产品指南，[04手册pN]=Consumer Objects，[12手册pN]=Process Panel，[05手册pN]=Group Objects。

## 1. Faceplate 官方八要素【核实-00手册p19】

| # | 要素 | 说明 |
|---|---|---|
| ❶ | 对象 Tag 名+描述 | |
| ❷ | **POC 指示** | Seq/Cen/Loc |
| ❸ | 对象状态指示 | |
| ❹ | 启动/停止按钮 | 停机/关阀永远允许 |
| ❺ | **切 POC 按钮** | Seq→Sequence / Cen→Central / Loc→Local |
| ❻ | 调报警列表/事件列表 | |
| ❼ | 报警确认 | 任一面板确认，经 GCC/PCC 双向传播 |
| ❽ | FP Normal View | |

电机默认视图还有：**Sim（整组仿真中，硬件信号忽略）/ Block（有联锁或信号被闭锁）/ 状态 / 报警指示 / 实际电流（额定%/实际值）**【04手册p40】。页签：Interlock / PCC / Alarm / Trend / Group【04手册p42】。

## 2. 图形元素族（流程画面上用）【核实-04手册p12-19】

| 元素 | 内容 |
|---|---|
| **Drive**（消费者主力元素，aspect 名=消费者对象名） | 状态+POC+模式+报警；IndicationType 分 S1_（Triangle/Lollipop/Diamond/Rectangle/Arrow/OpenArrow/StealthArrow/Oval/Line/TiltTriangle）、C1_（MotM/Pump/Fan/RotaryFeeder/GearWheelPump/Valve/ManValve/AutoValve/Generator/Heater/BucketElev/Conveyor/EP/AirSlideOutlet）、C2_（Diverter/LouvreDamper/AirSlide/PropRoller/Damper/AirSlideShut+Inv 镜像版/ValveLevelInd 等）、C3_（Diverter/3WayValve） |
| DriveCtrl | 控制信息+设定值直输；标签：操作模式（如 Setpoint External）/信号错误（信号质量）/偏差高-低/测量值闭锁-强制/测量值限值报警 |
| DriveFBTxt | FB1/FB2 故障文本（正常位灰隐、异常位红字、报警位红框） |
| DriveMCValue | 电机电流值 |
| Process Symbols | 行业设备符号（斗提、管弯、磨机等，变色型） |

**状态色（官方）**【04手册p14-15】：OFF 就绪=灰；OFF 联锁未就绪=灰+红底黑叉；OFF 联锁+对象报警=灰+实红框；RUN=绿；RUN 带警告（如 PCC）=绿+橙框；RUN 带高电流警告=绿+红框。
**标签（POC/模式）**：Sequence/Central/Local/Local Maintenance/Out of Service/Forced Run/Auto Mode/Manual Mode/External setpoint+Auto/Manual/Balancing Mode/Position/Run Direction/Operator Note/Blocked Interlock or Functional Back Signal【04手册p15】。

## 3. VCO 与 ASM（800xA 6.1 新图形体系）【核实-00手册p20-23 + 30手册】

- **VCO（Visual Control）**：6.1 引入，基于 6.0 的 EffectItems；**三种显示模式**：Start/stop（启停细节）、Production（活动设备彩色高亮）、**ASM（异常工况管理）**；
- **ASM 规范**：过程状态用**灰度**表示，**颜色只留给报警**——操作员一眼看到"哪里不对"；报警颜色使用一致且受约束；信息冗余编码（形状+颜色）；
- VCO 支持 MinLib 过程状态报警抑制 + 800xA alarm shelving；
- 主题：Minerals Standard / ASM Standard / VALE / Holcim（传统 GraphiXs 样式）；VCO 目前一个内置主题；**NLS 多语言**（描述/文本/报警消息按用户母语）；
- 详细 VCO faceplate 见 01 总览手册（3BHF004109）"VCO Faceplates"章 + 30 手册（VCO GraphiXs User Guide）。

## 4. 三个 Viewer（官方列定义）

| Viewer | 位置 | 列 | 来源 |
|---|---|---|---|
| **PCC Viewer** | 消费者面板内图标 | 一台消费者全部生效联锁一览表，实际原因**红行高亮**；点行跳信号面板 | 【00手册p33-36】 |
| **Group Step Viewer** | 组面板顶部 Aspect Link | Object Name/Description/Status（含预选）/Step/Delay Time；默认只显预选步 | 【05手册p18-19】 |
| **Group Status Viewer** | 组扩展面板 | Name/Description/Type/Status/Alarm/Intlk/Blk/Control/Mode；'+'展开子对象；点名跳面板 | 【05手册p20-21】 |

**Viewer 前置条件**（Step Viewer）：Functional Structure 需先用 **Uploader** 灌入——对象名唯一 + Name Uploader 执行 + 应用已下载控制器 + OPC 数据可用【05手册p18】。

## 5. 报警在画面上的表示【核实-04手册p13 + 00手册p21】

- 图形元素报警/警告时背景从透明变报警处理色；tag 名显示受 EnableTagName 总控；
- VCO ASM 模式灰度+报警色（§3）；
- 面板报警列表（ExtendedInfo 位 2）/事件列表（位 4）按需开；
- **报警确认双向传播**：组面板确认→经消费者→信号级【02手册p6】。

## 6. Process Panel P800（现场操作面板）【核实-12手册 + 00手册p53】

- BMI 标准符号库随 MinLib 安装；**经单一访问变量交换数据**；支持对象：AIS/AOS/DIS/DOS/AIC/AOC/DIC/DOC/MOT1/MOT1VVVF/MOT2/MOT2VVVF/MOTP/VLV1/VLVNO1/GROUP/DriveGroup/PREBIN；
- 面板对象类型（V6 面板）：MOT1/MOT1_VVVF/MOT2/MOT2_VVVF/DAMPER/GATE/FAN/PUMP/VLV1/VLV1NO/ANALOG CONTROL VALVE/AIS/AIC/AOS/AOC/DIS/DIC/DOS/DOC/GROUP/DRIVE GROUP/PREBIN【12手册p6-31】；
- 工程指南：Panel Builder 设置→控制器设置→报警事件设置→弹屏→访问变量→tag 编辑→数据类型→**tag 自动导入**→元件库→对象配置（combobox/faceplate 控制）【12手册p34-52】；
- 公共功能：面板手动控制（命令+输入框）、状态与操作指示、模式选择、单访问变量数据交换【00手册p53】。

## 7. CL 落地映射【CL 适配】

| CL 设计 | 对齐官方 | 说明 |
|---|---|---|
| FP_Mot 八要素 | 00手册p19 八要素 | V1 的"四区"映射：头=❶❷❸、主体=❹❼❽、参数区=页签 Alarm/Interlock、导航=❻+viewer 链接 |
| 三重编码 | 官方状态色+形状标签 | V1 七态表保留为 CL 简化版；官方规范以形状+标签+ASM 灰度为准则 |
| FP_Sig | 官方信号面板（02手册） | 阈值/延时/联锁类型/方向/闭锁状态全显示 |
| DV_StepViewer / DV_StatusViewer / DV_PCCViewer | 官方三 viewer | 列定义照抄；**上传 Functional Structure 步骤写进实施清单** |
| 仿真指示 | 官方 Sim 标签 | 组仿真时全部成员显示 Sim |
| 多语言 | 官方 NLS（`\|\|AE_NLS_`/`\|\|IL_NLS_` 前缀） | CL 全部 Txt 参数按前缀规范命名，现场可切语言 |

## 8. V1→V2 关键差异

| V1 自拟 | V2 官方 |
|---|---|
| 四区 ASCII 布局 | 八要素+页签结构 |
| 七态形状表 | Drive 元素 IndicationType 体系（S1/C1/C2/C3 数十种）+官方状态色 |
| 无 ASM 概念 | VCO 三模式+ASM 灰度/报警色分离 |
| viewer 列自拟 | PCC/Step/Status 三 viewer 官方列定义 |
| 无 Process Panel | P800 面板对象清单+工程指南 |
| 无 NLS | 官方 NLS 前缀规范 |

## 9. 本篇结论

CL 面板落地就三条：**①按八要素摆 FP；②流程画面用 Drive 元素族（形状+状态色）；③三个 viewer 列定义照抄+记得先跑 Name Uploader**。ASM 灰度规范是操作员体验的分水岭——颜色只给报警，别拿颜色表示生产过程状态。
