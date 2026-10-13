---
title: MinLib官方手册索引（27份文档台账）
date: 2026-10-13
project: F163
type: 数据表
device: ABB 800xA
tags: [MinLib,800xA,官方手册,台账,文档号,3BHS]
summary: MinLib Documentation文件夹27份官方PDF的文档号/版次/页数/用途分类台账与检索地图
source: D:\800xA\MinLib Documentation\ 实际文件 + 各手册首页/目录（文本提取于 D:\800xA\tmp\minlib_docs\）
---

# 官方手册索引（MinLib Documentation 台账）

> 用途：拆解/复查时按本表直达源头手册。文本版在 `D:\800xA\tmp\minlib_docs\`（与原 PDF 同名 .txt，页标记 `===== PAGE n =====`）。
> 版本说明：多为 ABB 800xA **6.1** 版手册（与 F163 现场 6.1.0 匹配）；个别 5.x 版手册是设备专用扩展，用时注意版本差。

## 1. 核心手册（拆解主依据，11 份）

| # | 文件名 | 文档号 | 版次 | 页数 | 内容 | 本套件用在哪 |
|---|---|---|---|---|---|---|
| 00 | MinLib Product Guide | 3BHS161554 | Rev H（6.1/5） | 71 | 产品总览、操作概念 POC、**-CC/PCC/GCC/LCC 四大控制连接**、CCF、性能数据、许可证 | 00/01 文档架构章 |
| 01 | MinLib Overview/Getting Started/Configuration | 3BHF004109 | Rev G（6.1） | 249 | 库总览、入门、配置、工程流程 | 00 总览、09 实施 |
| 02 | MinLib Basic Objects | 3BHS161556 | Rev D（6.1/3） | 121 | AI/AO/DI/DO 信号对象（AIS/AIC/AOS/AOC/DIS/DIC/DOS/DOC）、PCC_Connect_6、**PCC Interlock Bus** | 01/06 联锁与报警 |
| 03 | MinLib Loop Objects | 3BHS161562 | Rev E（6.1/3） | 103 | PID 回路对象、LCC 回路控制连接 | 06/08 回路联锁（二期） |
| 04 | MinLib Consumer Objects | 3BHS161557 | Rev D（6.1/3） | 264 | **MOT1/MOT1_VVVF/MOT2/MOT2_VVVF/MOTP/VLV1/VLVNO1/Actuator** 全参数/数据类型/面板/报警 | 02/03 文档主体 |
| 05 | MinLib Group Objects | 3BHS161561 | Rev D（6.1/3） | 142 | **Group/SubGroup/DriveGroup/GrpCycleCtrl/Prebin/STW/GroupConnect_2/4/8** | 04 文档主体 |
| 12 | MinLib Process Panel | 3BHS835707 | 6.1/5 | 79 | 过程面板（操作台面板）功能与用法 | 05 面板章 |
| 16 | MinLib GraphiXs User Guide | 3BHS294896 | 6.0/3 | 70 | 图形系统 GraphiXs（VCO 前代） | 05 面板章 |
| 22 | MinLib Commissioning Check Framework | 3BHS835707 | Rev E（6.1/2） | 21 | **调试检查框架（CCF）**：面板跟踪、状态/日期/用户名、EBase 上传、Excel 报告、自定义检查 | 07 文档调试章 |
| 30 | VCO GraphiXs User Guide | 3BHF004110 | Rev D（6.1/3） | 95 | Visual Control Objects 图形（新一代 HMI） | 05 面板章 |
| 80 | MinLib Tutorial | 4HCH010884 | Rev B（6.1） | 43 | 官方教程：从建工程到仿真下载全流程 | 09 实施章 |

## 2. 设备/子系统专用（按需查，9 份）

| # | 文件名 | 文档号 | 页数 | 内容 |
|---|---|---|---|---|
| 06 | Dosing Objects | 3BHS161558 Rev Q | 52 | 配料/计量对象（喂料秤闭环） |
| 07 | Communication Objects | 3BHS161559 Rev L | 28 | 通讯对象 |
| 08 | Power Distribution Monitoring Objects | 3BHS253000 | 73 | 配电监测对象（EEM） |
| 09 | Report Objects | 3BHS161560 Rev C | 31 | 报表对象 |
| 10 | Basic S400 Board & Objects | 3BHS261746 | 26 | S400 板卡与对象（5.0 版） |
| 11 | AB PLC 5 IO Interface Objects | 3BHS227801 | 64 | 老 PLC5 IO 接口（5.0 版） |
| 13 | Minerals Library EnergyMgmt | 3BHS259592 | 51 | 电能管理（5.1 版） |
| 14 | Wrapper Objects | 3BHS259604 Rev I | 13 | 包装对象 |
| 15 | MNSiS MBTCP | 3BHS259605 | 36 | MNSiS 开关柜 Modbus TCP（5.1 版） |
| 17 | UMC100 | 3BHS356296 Rev D | 58 | UMC100 综合保护器对象 |
| 18 | ACS8x0 | 3BHS512349 Rev F | 42 | ACS800/880 传动对象 |
| 19 | LCBType | 3BHS539410 Rev E | 36 | LCB 类型对象 |
| 21 | OPC Interface Definition | 3BHS509774 Rev B | 13 | OPC 接口定义 |
| 32 | Knowledge Manager Integration | 3BHS839267 Rev G | 19 | 与 800xA Knowledge Manager 集成 |
| 36 | HardwareViewer | 4HCH500451 Rev 1 | 12 | 硬件查看器 |
| 70 | Cyber Security | 4HCH017230 Rev A | 2 | 网络安全说明 |

> 注：08/10/11/13/15/16 的首页版式与标准表不同，版次字段未能从文本提取（16 的 GraphiXs 文内页脚见 Version 6.0/3；12 见 6.1/5）；引用时以原 PDF 首页为准。

## 3. Tutorial 附属材料（子文件夹 MinLib Tutorial）

| 文件 | 用途 |
|---|---|
| MinLibTutorial_615_SV70_2026_02_27.afw（19.7MB） | 官方教程 800xA 工程文件（6.1.5/SV70，2026-02-27）——**可直接作 CL 库工程模板参考** |
| 10/20/21 - ImportControlStructure/ImportFunctionalStructure/ResultOffline.png | 工程结构导入步骤截图 |
| 30 - SoftController OPCServer.png | 软控制器 OPC 服务器配置 |
| 31 - ApplicationDownload.png | 应用下载 |
| 40 - MinLibSimulation.png | MinLib 仿真 |
| 41/42/43 - Workplace...png |  Workplace 报警确认/运行/全对象显示 |
| 80 - MakeSureYouDidTheCorrectSettings_GettingStartedChapter9.4_BadExample.png | 常见错误示例 |
| 99 - KnownIssue...SimulationIsNotForwardedForGrpCycleCtr_Before6.1_4.png | **已知问题：6.1.4 之前 GrpCycleCtr 仿真不传递**（版本相关坑） |

## 4. 检索地图（拆哪部分查哪份）

| 要查的东西 | 去哪份 |
|---|---|
| 控制连接总机制（-CC/PCC/GCC/LCC） | 00 产品指南 §3 |
| 电机对象参数/面板/报警 | 04 Consumer §2（公共）+§3/5/7（MOT1/MOT2/MOTP） |
| 阀门对象 | 04 Consumer §8/9/10 |
| 组对象/步进/viewer | 05 Group §2-5 |
| 周期组/预选/启动预告 | 05 Group §6-8 |
| 联锁信号（AI/DI） | 02 Basic §2.2.3 + §3/5 |
| PID 回路联锁 | 03 Loop |
| 面板/图形元素/指示规范 | 04 §2.3、12 Process Panel、30 VCO |
| 报警禁用/首报/优先级 | 04 §2.4 + 各对象 Alarm&Event List |
| 仿真模式 | 02/04/05 各 §2.2.x Simulation Mode + 80 Tutorial |
| 调试检查框架 | 22 CCF 全文 |
| 工程流程（建库/导入/编译/下载） | 01 总览 + 80 Tutorial + PNG 截图 |
| 性能/容量/许可证 | 00 产品指南 §6 |
