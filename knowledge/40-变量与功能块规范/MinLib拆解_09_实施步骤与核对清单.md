---
title: MinLib拆解复用-实施步骤与核对清单V2（官方工作流对齐）
date: 2026-10-13
project: F163
type: 实施说明
device: ABB 800xA
tags: [MinLib,800xA,实施,核对清单,Tutorial,afw,CCF,编译错误,U项销项]
summary: V2：官方环境安装与Tutorial afw导入流程、工程顺序、Viewer上传前置、CCF五步工作流（F163无EBase降级）、仿真FAT红线、五套核对清单、编译错误速查、U1-U10销项表
source: 80 Tutorial手册4HCH010884 RevB + 00手册§2.5/§5 + 22 CCF手册 + F163规则总纲 §3/§5 + afw文件实测
---

# 09 实施步骤与核对清单（V2）

> **V2 变更**：实施路线按官方 Tutorial 工作流重写；V1 的 U1-U10 待实测项大部分被官方手册解决（§6 销项表）。
> 按本篇走，每步打勾，打不了勾就停在原地排查。

## 1. 总体路线（V2 八步）

```
① 环境与安装 → ② 导入官方Tutorial工程 → ③ 建CL库（CM+STRUCT）→ ④ 编译
 → ⑤ 面板与Viewer（含上传）→ ⑥ 仿真FAT → ⑦ CCF调试 → ⑧ 新组试点推广
```

| 步 | 内容 | 门禁 |
|---|---|---|
| ① | 800xA 6.1.0 + 对应版本 MinLib（SharePoint 下载，System Installer 安装） | 版本匹配（生命周期计划 3BHF004108）；设置总表 3BHF005419 过一遍 |
| ② | 导入 `MinLibTutorial_615_SV70_2026_02_27.afw`（18.9MB，已实测为真 800xA Control Builder 工程导出） | Tutorial 工程能开、能编译 |
| ③ | CL 库：STRUCT→CM 类型（对齐 01/02/03/04 官方字段） | CM 编译通过 |
| ④ | 测试程序整编译 | 0 error，Warning 逐条看 |
| ⑤ | FP_* 面板+三 viewer；**跑 Name/Function Uploader** | 面板能开、viewer 有数据 |
| ⑥ | 仿真 FAT（断总线红线） | 四课现象全中 |
| ⑦ | CCF 调试记录 | 面板 Commiss. 页签可记、报告可出 |
| ⑧ | 新组试点（不动 CementMill）→推广 | 每组过 ⑥⑦ 门禁 |

## 2. ① 环境与安装【核实-00手册p24 + 80手册p5-6】

- [ ] 800xA 6.1.0（与 F163 现场一致）；
- [ ] MinLib 对应版本从 **MinLib SharePoint** 下载（`abb.sharepoint.com/sites/MineralsLibrary`，官方安装源+各历史版本）；
- [ ] **System Installer** 安装 MinLib（多个 System Extension）；
- [ ] 版本兼容性核对 **3BHF004108 MinLib LifeCyclePlan**；
- [ ] **3BHF005419 MinLib Settings.xlsx**（设置总表）过一遍——MinLib 各级配置都在这；
- [ ] 术语表 MinLibGlossaryAbbreviations.xlsx 存档（和 ABB 支持对话用）。

## 3. ② 导入官方 Tutorial 工程【核实-80手册p6 + afw 实测】

官方五步准备（Tutorial §2 Preparation）：

- [ ] 从 SharePoint 拿最新 Tutorial（本文件夹已存：`MinLibTutorial_615_SV70_2026_02_27.afw`，Version MinLib Tutorial 615，SV70，2026-02-27，实测文件头 `***AFW***`、内含 "MinLib Tutorial Application" 描述——**与 F163 现场导出的 .afw 同格式，可直接作 Control Builder 导入模板**）；
- [ ] 导入 AFW；
- [ ] 标准准备：controller switch → **simulate hardware** → task definition → connect application；
- [ ] Download，确认 **OPC server 运行**、控制器已连接（截图30 SoftController OPCServer/31 ApplicationDownload 对照）；
- [ ] Tutorial 画面过一遍：三组（Ore Transport / Mill Lubrication / Mill Feed）+ 全部图形元素详情视图（截图43 WorkplaceShowingAllObjects）。

**CL 库的第一用途**：Tutorial 工程里每个官方对象（MOT1/GROUP/PREBIN/PCC_Threshold_AND3/RecipeCtrl/…）都是活样本——做 CL 块时逐个对照官方实例的参数和面板。

## 4. ③④ 建库与编译（F163 顺序不变）【F163 §3.5】

- [ ] STRUCT 先行（CL 的 GCC/PCC 结构体，字段对齐官方 GrpDrvCon/PCCComData）；
- [ ] CM 类型（MOT_C/VLV_C/GRP_C/PRE_C/STW_C/SIG_C）按 08 骨架；
- [ ] VAR → PAR → FUN → ST → FBD；
- [ ] **编译整个测试程序**（非单页）；编译日志存档；
- [ ] 报错按 §5 速查表处理。

## 5. ⑤ 面板与 Viewer 上传（官方前置条件）【核实-05手册p18 + 80手册§4】

- [ ] FP_* 面板按 05 文档八要素搭；
- [ ] **Name Uploader / Function Structure Uploader 必须跑**（viewer 显示数据的前提：对象名唯一+上传器执行+应用已下载+OPC 可用）【80手册p35-36】；
- [ ] 三个 viewer 验证：Interlock Viewer / Group Step Viewer / Status Viewer（80手册§4.2-4.4）+ Hardware Viewer（§4.5）；
- [ ] Process Panel（如有 P800）按 12 手册工程指南配（Panel Builder→控制器→报警事件→弹屏→访问变量→tag 自动导入）。

## 6. ⑥⑦ 仿真 FAT 与 CCF 调试

### 6.1 仿真 FAT【核实-04手册p9/05手册p7-8】

- [ ] **先断 Profibus/Modbus 及一切现场接口**（红线）；
- [ ] 组置仿真→全部成员强制仿真确认；
- [ ] MC 电流仿真到 0.8×MCHiLim 确认；
- [ ] "Allow Alarm In Simulation" 逐对象测 MCC 信号；
- [ ] **周期组（GrpCycleCtrl）仿真逐个确认**——6.1.4 前仿真不传递（Tutorial 截图99），F163 是 6.1.0 必须防；
- [ ] 四课培训场景（启动失败/运行跳闸/联锁越限/主备切换）；
- [ ] FAT 后**全部退出仿真**（核对清单专列）。

### 6.2 CCF 调试【核实-22手册p4】

- [ ] 面板 Commiss. 页签可见（Application Engineer 角色/Tune 权限/VCO 开关 FPCommissioningCheckTabVisible）；
- [ ] 五结果会用（Ok/Failed/Simulated/Deferred/NotTested），NA 禁用测试；
- [ ] **F163 无 EBase 的降级方案**：800xA 内页签记录+集中存储照用；报告侧手工导出 General Properties 或让业主方 EBase 环境上传（22手册的 EBase 宏链路在 F163 用不了，明确降级不假装完成）；
- [ ] 检查项三类（硬件/软件/工艺）按项目裁剪，新增检查项用 ACheck_/BCheck_/CCheck_ 前缀。

## 7. 核对清单（五套汇总）

**A 库与编译**：STRUCT 先行 / CM 命名对齐官方 / 参数默认值与官方一致 / 整程序编译 0 error / 日志存档。
**B 联锁与报警**：IC/IB/IA/PD 语义正确 / RFS 后缀用法 / 报警只在 Starting/Run 产生 / AlarmTr 档位 / 文本 NLS 前缀。
**C 面板与 viewer**：八要素齐全 / 三 viewer 有数据（上传器已跑）/ 首报链接可跳 / Sim 指示醒目。
**D 仿真与调试**：断总线 / 组级仿真 / 周期组仿真逐个确认 / CCF 页签可记 / 报告可出。
**E 上线前**：全部 EnSim 退出 / F163 §3.6 下载禁令（接口补齐+离线编译+仿真验证+用户确认）/ 老程序未动。

## 8. 编译错误速查（F163 §5 实战）

| 错误码 | 含义 | 解法 |
|---|---|---|
| 1030 | 硬件型未走 .Value | DintIO/RealIO 全部 .Value |
| 1116 | Code 混入声明段 | 工程 Code 只放执行语句 |
| 1055/1108 | 位运算 | 比较和 IF 累加替代；Bit31 用 -2147483647-1 |
| 1000 | 名称重复（大小写不敏感） | VAR+PAR 合并查重 |
| 1005 | in_out 带 retain | 去 retain |
| 1034 | in 参数被赋值 | 输入只读 |
| 1340 | 结构体聚合初值 | 初值留空，ST 初始化段逐个成员赋 |
| 1542 | 实例未调用 | 删或补调用 |
| 编译报已有变量 | 与现场重复 | 按 F163 §3.7 从增量表移除并更新去重基线 |

## 9. U1-U10 销项表（V1 待实测项 → V2 状态）

| # | 事项 | V2 状态 |
|---|---|---|
| U1 | FBT/CM 内 VAR CONST/string 初值 | **已证实**：官方 CM 参数表 Initial Val 列大量 string/时间初值（如 Name:='Name'、FdBckTime:2s）【04手册p30】 |
| U2 | CM 引脚用硬件型 | **已证实**：官方 MC 为 RealIO、IOStatus 为 dint【04手册p31】 |
| U3 | AlarmCond 引脚名 | **官方方案替代**：MinLib 不用 AlarmCond，用 AE 系统+AlarmTr 五档；CL 库若仍用 AlarmCond 仍需实测引脚名 |
| U4 | 报警文本拼接 | **已解决**：官方 NLS Txt 参数+ALP1/2/3 后缀+FB On/Trip/Off/Frc 后缀【04手册p23/51】 |
| U5 | Aspect 超链接属性名 | **官方机制证实**（父子双向动态链接+aspect link，00手册p9/19）；CL 具体属性名仍需实测 |
| U6 | 面板闪烁 | **已证实**：官方 PanelLinkConsumer.Blink 字段【04手册p36】 |
| U7 | Viewer 实现方式 | **已解决**：官方 Interlock/Step/Status/Hardware 四个 viewer 都是 aspect，配 Name Uploader 使用【80手册§4】 |
| U8 | EnSim 掉电保持 | **行为已知**：官方仿真热启动初值有明确定义（AIS 50%/DIS 正常位/输入阻塞）【02手册p11】 |
| U9 | 调试记录导出 | **官方有链**（EBase 宏+Excel）但 **F163 无 EBase→降级**：800xA 内记录+手工导出 |
| U10 | MinLib 官方参数命名 | **已解决**：本任务全量拆解，01-08 文档全部官方化 |

## 10. V1→V2 关键差异

| V1 | V2 |
|---|---|
| 自建库从零开始 | 先导入官方 Tutorial 工程当样本 |
| 无安装来源说明 | SharePoint+System Installer+LifeCyclePlan+Settings 总表 |
| 仿真自拟机制 | 官方组级仿真+断总线红线+6.1.4 坑 |
| CHK_C 自拟 | 官方 CCF（EBase 链在 F163 降级） |
| viewer 自建显示 | 官方四 viewer aspect+上传器前置 |
| U1-U10 全未决 | 8 项解决/证实，2 项降级或留实测 |

## 11. 本篇结论

V2 实施的主线：**Tutorial 工程（afw）是最好的老师——导入它，每个官方对象都是活的对照样本**；两条红线记住：仿真前断现场总线、下载前过 F163 §3.6 禁令。CCF 在 F163（无 EBase）降级使用，不假装完整。
