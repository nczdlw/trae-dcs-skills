---
title: MinLib拆解复用-仿真与调试检查框架V2（官方对齐）
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,仿真,SimulationMode,ParameterError,CCF,CommissioningCheck,EBase,报告]
summary: V2：官方仿真机制（组级强制/0.8高限/MCC信号测试/热启动初值/断总线红线）、Parameter Error、CCF全量（5步工作流/5种结果/三类测试/EBase宏/权限/自定义/Excel报告）、CL落地映射
source: 04手册p9 + 05手册p7-8 + 02手册p11 + 22 CCF手册3BHS835707 RevE 全文 + 80 Tutorial
---

# 07 仿真与调试检查框架（V2）

> **V2 变更**：仿真和调试全部改为官方机制。V1 自拟的 CHK_C 状态机被官方 **CCF（Commissioning Check Framework）** 取代——官方方案更强（多用户、时间戳、EBase 上传、Excel 报告、KPI 图）。
> 页码标注：[04手册pN]=Consumer Objects，[05手册pN]=Group Objects，[02手册pN]=Basic Objects，[22手册pN]=CCF。

## 1. 仿真模式（官方）【核实-05手册p7-8 / 04手册p9 / 02手册p11】

### 1.1 机制

- **组置仿真→属下全部消费者和基础对象强制仿真**（操作员站上设置）；
- 仿真内容：反馈（run/open/close）和输入信号被仿真——**电机电流 MC 仿真到设定高限的 0.8 倍**；**命令和报警被禁用**；
- **MCC 信号仍可逐对象测试**：面板维护页签勾 "Allow Alarm In Simulation"；
- 基础对象（AIS/AIC/DIS/DIC）被阻塞并置正常值；
- **热启动后初始行为**（可改）：AIS=量程 50% 且输入阻塞；DIS=正常位且输入阻塞；DOS/AOS 不考虑硬件连接，但**若输出对象接了硬件，所有改动仍写进硬件**。

### 1.2 安全红线（官方原话级）

1. **仿真前必须断开 Profibus、Modbus 及一切到现场的接口**；
2. 仿真中消费者块会向所有 MCC 信号**写回 true**——像 ME 这类被多个块共用的信号，若只有部分块在仿真，其他块上的值可能因代码排序而错；**仿真只能在现场总线完全断开的控制器上启用**【05手册p8】。

### 1.3 已知问题【核实-Tutorial 截图99】

- **6.1.4 之前 GrpCycleCtr 的仿真不传递**（Simulation is not forwarded for GrpCycleCtr before 6.1.4）——F163 现场是 6.1.0，**周期组仿真要特别注意此坑**：GrpCycleCtrl 及其成员需逐个确认仿真状态，不能只置组。

### 1.4 CL 落地【CL 适配】

- 废弃 V1 自拟 EnSim/Sim_* 硬件屏蔽路径（官方不屏蔽输出，靠断总线）；
- CL 库仿真设计=官方机制复刻：组级强制+0.8 高限电流+Allow Alarm In Simulation 复选框+热启动初值参数化；
- 培训场景四课（启动失败/运行跳闸/联锁越限/主备切换）保留，但现象以官方面板（Sim 标签、PCC Viewer 红行）为准。

## 2. Parameter Error 机制【核实-04手册p9-10 / 02手册p11】

- CM 参数（本块或相连块）非法→图形元素和面板显示 **Parameter Error**——含义"应用程序需要修正"，**不是过程故障**；
- 官方警告：**不是所有图形元素都显示 Parameter Error，也不是所有参数都做范围校验**；无 Parameter Error 提示≠功能正确——新程序必须测试验证；
- CL 落地：参数表加范围检查+非法值触发 Parameter Error 指示；不静默钳位。

## 3. Commissioning Check Framework（CCF 官方全量）【核实-22手册全文】

### 3.1 定位与安装

- MinLib **6.0.1 及以后**自带；需 **Engineering Base 6.7.0 + 800xA Integration 2.0**；无需额外安装；
- 预置覆盖所有类型信号、消费者和 MinLib 元素的测试集，**可按项目调整扩展**；
- 只对工程师用户可见（操作员不打扰）【22手册p3-4】。

### 3.2 五步工作流【核实-22手册p4】

```
1) Edit Mapping（EBase 信号 ↔ 800xA 检查项映射）
2b) Create Aspects（在 Control Structure 实例上建 Commissioning Data 属性aspect）
2c) Set Visible Test Cases（按 EBase 定义过滤实际信号）
3) Record Test Results（调试期间在面板记录结果）
4) Upload Data from 800xA to EBase（上传）
5) Create / Update Excel Report（出报告）
```

### 3.3 面板操作（800xA 内）【核实-22手册p4-7】

- 所有信号/消费者/组元素的扩展视图带 **"Commiss." 页签**：左列 Tests、右列 Commiss.Progress；
- **左键**点右列单元格=写默认结果 "Ok"+当前日期+用户名；**右键**菜单选结果：**Ok / Failed / Simulated / Deferred / NotTested**（默认 5 种，可扩到 10 种）；
- 左列右键 "Disable this test"=写 "NA"（不计入 100% 范围）并隐藏；底部出现 "Show all tests" 复选框可恢复；
- 右键 "Edit…" 扩展输入：Detail Status 文本+可改状态/日期/用户；
- **三类测试**（左列背景色区分，属性前缀 A/B/C/D/ECheck）：**硬件类**（回路测试、硬件设置、量程标定）、**软件类**（参数化、报警限值、时间设置、组启动）、**工艺类**（冷/热运行、外部控制回路）【22手册p6】。

### 3.4 EBase 宏（CommissioningStateUpdate）【核实-22手册p8】

| 区 | 功能 |
|---|---|
| Prepare | **Delete Aspects**（清 800xA 配置，**已填结果会丢**）/ **Create Aspects**（按 Template Aspect 给 Control Structure 子对象建实例）/ **Set Available Properties**（把 EBase 里没有的信号置 NA 过滤）/ **Edit Mapping** |
| Reporting | **Upload Data from 800xA**（General Properties 回读 EBase 属性，空值不上传）/ **Update Excel Report** |

宏用 Function 的 **800xAID 属性**映射到 800xA Aspect 对象；须在**已导出的对象**（Application/Plant Function 或 Diagram）上运行【22手册p8-9】。

### 3.5 存储与映射【核实-22手册p9-13】

- 检查项=General Properties 类别 Aspect（名 "Commissioning Data"）上的 **string 属性**；模板 Aspect 随系统扩展提供；
- EBase 结构与 800xA 不同（EBase 每个信号是独立对象，800xA 一个 CM 含多信号）→ 用信号的 **"Typical Copy Merge Index" 属性**+宏设置表映射（如 ACheck_Run ↔ s_R）；该索引通常与应用导出模板用的是同一个【22手册p12-13】。

### 3.6 权限与可见性【核实-22手册p13-14】

- Classic PG2 面板：Commiss. 页签按 **"Application Engineer" 角色**过滤；改值需 **Tune 权限**；
- VCO 面板：`FPCommissioningCheckTabVisible`：0=禁/隐藏，1=全员可见，2=仅 Application Engineer 可见。

### 3.7 自定义【核实-22手册p14-18】

| 改什么 | 在哪改 |
|---|---|
| 结果文本（可加第 6-10 种） | NLS Resource Manager：Library Structure → Preferences & Customizations → MineralsLib KPI Commiss. NLS（TestResult07-11 默认 disabled） |
| 结果/类别背景色 | ResourceLibraries → MineralsLib KPI Commiss. Resources 的 brushes（TestResultxx_yy、Test_CatUnknown 等） |
| 加检查项 | 对象类型的 Commissioning Data aspect Config View → Add Property After；**属性名必须以 ACheck_/BCheck_/CCheck_/DCheck_/ECheck_ 开头**（决定类别色和排序）→ 删旧建新 aspect → 扩 EBase 映射 |
| 给项目自有库类型加 CCF | 对象类型建 "Commissioning Data"（Basic Property Properties/General Properties）+ Template Aspect Key；**每 Aspect 类别只允许一个 Template Aspect**；可从 Commissioning Data FullSet 拷贝 |

### 3.8 报告【核实-22手册p11/19-20】

- 模板 `Commissioning Progress Report.xlsx`（Configurations → Commissioning Progress Folder）；默认报信号回路检查进度+Load Tag 检查；
- EBase "Progress Report (Functions)" 工作表数据→报告 "EBase Data" 表；**Named Ranges**（Definitions 表）：Area List/Area Names/Area Definitions（"Part Of" 前缀过滤）需按项目调；
- 报告含数量+图表（KPI）；改工作表模板只向右加列保兼容；
- **宏不支持数据透视表等高级 Excel 功能**（生成时会被删）——需要就手工拷 "EBase Data" 到第二个文件；
- 图形化进度总览（00手册p50-51 Figure 26/27：CCF Tab + KPI Graph）。

## 4. CL 落地映射【CL 适配】

| CL 设计 | 对齐官方 | 说明 |
|---|---|---|
| CHK_C 块 | **废弃**，改官方 CCF 机制 | 面板 Commiss. 页签+EBase 宏+Excel 报告比自拟状态机强一个量级 |
| 检查项 | ACheck_/BCheck_/CCheck_ 前缀属性 | 硬件/软件/工艺三类；每对象类型预置（MOT1=Run/NotAvailable/Overload…） |
| 结果 | Ok/Failed/Simulated/Deferred/NotTested | CL 中文 NLS：Ok=通过/Failed=失败/Simulated=仿真/Deferred=暂缓/NotTested=未测 |
| 权限 | Application Engineer+Tune | 与现场用户角色体系对齐 |
| 无 EBase 的项目 | 退化方案 | 只用面板页签记录（800xA 内集中存储仍有效），报告手工导出 General Properties |

**F163 现场注意**：F163 无 EBase（用 Excel+腾讯文档工作流）→ CCF 的 EBase 宏链路用不了，但 **800xA 内的 Commiss. 页签+集中存储+多用户仍可用**；报告侧退化为导出 General Properties。这是 CL 库复用官方 CCF 时必须接受的降级，写进 09 文档核对清单。

## 5. V1→V2 关键差异

| V1 自拟 | V2 官方 |
|---|---|
| EnSim 屏蔽硬件输出 | 官方不屏蔽输出，**先断现场总线** |
| 无 MCC 测试概念 | Allow Alarm In Simulation 逐对象测试 MCC 信号 |
| 仿真电流无定义 | MC 仿真到 0.8×高限 |
| CHK_C 状态机 | CCF：面板页签+5 结果+3 类别+时间戳+用户+多用户 |
| 无报告 | EBase 宏上传+Excel 模板报告+KPI 图 |
| 无权限控制 | Application Engineer 角色+Tune 权限+VCO 开关 |
| 检查项写死在文档 | 对象类型 aspect 属性+前缀类别，可在线扩展 |

## 6. 本篇结论

官方两件套的用法：**仿真=组一键全仿+断总线保平安+面板维护页签测 MCC；调试=面板 Commiss. 页签随手记+定期上传出 Excel**。F163 没有 EBase，CCF 的 800xA 侧照样能用、报告侧降级——这比 V1 自拟的 CHK_C 实用得多。周期组仿真记住 6.1.4 前的坑（截图99）。
