---
title: MinLib功能块拆解与自定义库复用设计-总览与库架构V2
date: 2026-10-13
project: F163
type: 开发说明
device: ABB 800xA
tags: [MinLib,800xA,水泥,库架构,POC,GCC,PCC,LCC,VCO,CCF]
summary: 基于ABB官方27份手册重写的总览：官方架构（CM类型/九大类对象/四控制连接/POC模式/GCC组行为/LCC回路）、CL库V2三层架构、V1→V2差异
source: 00产品指南3BHS161554 RevH（6.1/5）+ 04/05/02/22手册 + D:\800xA\MinLib Documentation
---

# 00 总览与库架构设计（V2）

> **V2 变更（2026-10-13）**：拿到 ABB 官方手册 27 份后整体重写。V1 的【自拟】设计升级为【核实-手册页码】；官方没有覆盖的 F163 适配层保留【CL 适配】标注。
> 手册台账与检索地图见同目录《官方手册索引.md》；手册文本在 `D:\800xA\tmp\minlib_docs\`。

## 1. 可信度标注规则（V2 三级）

| 标注 | 含义 |
|---|---|
| 【核实-手册】 | ABB 官方手册明确写明，附文档号+页码（如 [04手册p5]=3BHS161557 第5页） |
| 【CL 适配】 | 官方机制向 F163/自建库落地时的设计选择（官方未规定具体字段名） |
| 【需实测】 | 现场环境验证项（原 U 项，收敛后见 09 文档） |

## 2. MinLib 官方架构（核实）

### 2.1 库的物理形态【核实-00手册p25】

- 模块用 **Control Builder M Professional** 开发，形态是 **Control Module Types（CM 控制模块类型）**，不是普通 FB；
- 支持 **Diagram Editor（FD）图形编程**，跑在 **800xA 6.1**——和 F163 现场（Control Builder M / 6.1.0）完全一致；
- 以 **System Extension** 形式安装进 800xA（System Installer），兼容性看生命周期计划 3BHF004108【00手册p24/p54】；
- 块覆盖水泥矿山**约 90% 用例**，靠参数化选功能；为特殊功能加的"胶水逻辑"对操作员隐藏【00手册p28-29】。

### 2.2 九大类对象【核实-00手册p25】

| 类 | 对象（已核实到的） | 手册 |
|---|---|---|
| Basic 基础 | AI(AIS/AIC)、AO(AOS/AOC)、DI(DIS/DIC)、DO(DOS/DOC)、PCC_Connect_6 | 02 (3BHS161556) |
| Consumer 设备 | MOT1、MOT1_VVVF、MOT2、MOT2_VVVF、MOTP、VLV1、VLVNO1、Actuator | 04 (3BHS161557) |
| Group 组 | Group、SubGroup、DriveGroup、GrpCycleCtrl、Prebin、STW、GroupConnect_2/4/8 | 05 (3BHS161561) |
| Loop 回路 | PID 回路对象（LCC 用） | 03 (3BHS161562) |
| Dosing 配料 | 喂料秤/计量 | 06 (3BHS161558) |
| Communication 通讯 | — | 07 (3BHS161559) |
| Power Monitoring 配电监测 | — | 08 (3BHS253000) |
| Report 报表 | — | 09 (3BHS161560) |
| Energy Mgmt 电能管理 | — | 13 (3BHS259592) |

### 2.3 四大控制连接（-CC 体系）【核实-00手册p25-29/p47】

| 连接 | 全称 | 连什么 | 干什么 |
|---|---|---|---|
| **-CC** | Control Connection 总体系 | 全部 | 预定义接口的结构化变量"数据高速公路"，父子双向，一根逻辑线传多变量 |
| **PCC** | Process Control Connection | 信号↔设备 | 联锁与过程控制信号接进设备；**联锁行为由信号对象上的参数定义** |
| **GCC** | Group Control Connection | 设备↔组 | 组按给定/动态顺序启停设备；汇总设备状态；预选路由/主备 |
| **LCC** | Loop Control Connection | 电机/执行器↔PID | 模拟回路控制；设定值前送+**实际值回传（backtracking）**；无扰切换与防积分饱和 |

- LCC 的结构化数据类型 `LoopControlData` 随 Loop 对象和若干 Consumer 对象提供；LCC 继承标准 AC800M 控制库的 ControlConnection 特性（详见 3BSE035981）【00手册p47】；
- 连接在程序中"自动可见"于 PCC Viewer / Group Step Viewer【00手册p29】。

### 2.4 控制点 POC（Point Of Control）【核实-00手册p15-17】

四个 POC，操作员站上可选；**停机/关阀永远允许，不管什么模式**（安全底线）：

| POC | 谁控制 | 要点 |
|---|---|---|
| **SEQ** Sequence | 上位程序（组序列/DriveGroup） | 可由操作员站或应用程序置入 |
| **CEN** Central | 操作员站面板按钮 | 也可接受上位程序启停；CEN 只能从 Workplace 置入 |
| **LOC** Local | 现场 LCB 按钮箱 | 需中控室给 local release；**联锁除安全 IC 外全部释放**；点住启动按钮时 FB1/FB2 速度反馈也释放；**本地模式报警禁用**（无需中控确认） |
| **OOS** Out Of Service | 谁都不能启 | **组顺序运行时该设备被跳过**；需专门用户权限 |

SEQ/CEN 下还有两个子模式：**Man**（默认，启停命令驱动）和 **Auto**（由 IA 过程输入驱动，如温度/液位开关控制，操作员不能再启停，但永远可停）【00手册p16】。

### 2.5 GCC 组行为（官方全量）【核实-00手册p37-46】

- **启动条件**：预选设备全部 Ready for Start + 预选设置正确 + 无组启动联锁；初启动只能从 Off/RFS；重启可从 Stopping/Hold/Running；
- **启动过程**：STW 启动预告（声音，可配置为逐设备前预告）→ 组显"Starting/PreWarning" → 预告时间到 → 按编程顺序+预选逐台启动，**面板实时显示当前步号和设备 tag** → 全起来显 Running；启动中重要设备失败→组显 **Hold / Drive(s) not Ready**；
- **Unconditional Start**（扩展面板）：设备未就绪也启动，组启到该设备的步即停；组启动联锁激活时此功能无效；
- **Hold**：组部分运行；按 Stop 按停止序列停剩余，或按 Start 续启；
- **Manual Hold**：任何时刻按 Hold 按钮中断启/停/快停流程；
- **Quick Stop / Instant Stop**：无视停止顺序同时停全部；执行器/回路在快停时的动作可单独设定；**停止联锁激活时也能发**；
- **停止**：无停止联锁才允许顺序停；任何状态（含 Starting）可停；停完显 Off/RFS；
- **预选（Pre-selection）**：操作员设/复位决定下次启动哪些对象参与；支持运行中 on-the-fly 改；状态：Off / Selected to Start / Selected and Running / Selected to Stop / Off not RFS；单选互斥时自动 radio-button；**缺失/错误预选组合阻止组启动**；启停过程中禁止改预选；
- **报警/警告经 GCC+PCC 转发**：组面板文字显示"第一个不运行的消费者"，状态 viewer 显示全组状态+经消费者连入的信号状态；下钻：组→消费者→信号，面板文字点击直达【00手册p44-46】。

### 2.6 PCC 联锁与 viewer【核实-00手册p31-36 + 04手册p5】

- 每台设备的联锁信号经 PCC 接入，**信号对象上的参数**定义联锁行为（阈值/延时/类型/方向 X/Y）；
- 四类联锁：**IC** Safety（安全，运行或启动禁止）、**IB** Equipment（设备，运行或启动禁止）、**IA** Process（过程，运行/启动禁止/自动启动）、**PD** Previous Drive in Sequence（前序设备）；信号数不限【04手册p5】；
- **PCC Viewer**：面板内一张表，列出一台消费者全部生效联锁（实际原因红行高亮）；报警可在任一面板确认——组面板确认会经消费者下传到信号级【00手册p31/p34】；
- 下钻导航：电机面板点跳闸原因文字→流量开关面板（根因）【00手册p35】。

### 2.7 报警与 HMI【核实-00手册p9/p20-23 + 04手册p5-6】

- 面板元素全部预定义 aspect；父子面板**双向动态链接**；viewer 直接导航到对象【00手册p9】；
- **VCO（Visual Control）**：800xA 6.1 引入的新图形体系，基于 6.0 的 EffectItems；三种显示模式：Start/stop、Production、**ASM（异常工况管理）**——ASM 用灰度表示过程状态、**颜色只留给报警**；报警颜色使用一致且受约束、信息冗余编码（形状+颜色）【00手册p20-22】；
- **报警禁用三条件**（按工况）：组活动或停止、消费者活动或停止、消费者远程或本地【04手册p6】；
- 首报检测（对象+全部联锁信号）、可选启动报警抑制、信号报警自动转发消费者、动态报警优先级【04手册p6】；
- 支持 800xA 的 alarm shelving 和 MinLib 过程状态报警抑制【00手册p21】；
- 样式主题：Minerals Standard / ASM Standard / VALE / Holcim；**NLS 多语言**（描述/文本/报警消息按用户母语）【00手册p23】。

### 2.8 调试与工程【核实-00手册p50-51 + 22手册p3】

- **CCF（Commissioning Check Framework）**：所有 MinLib 对象面板带 commissioning 页签（仅调试期可见）；现场做信号检查时**直接在面板记录结果**；集中多用户、带时间戳+用户名；测试例随对象类型预定义、可扩展；上传 EBase 出 Excel+图形化进度报告【00手册p50/22手册p3】；
- **EBase 批量工程**：Aucotec Engineering Base 双向接口（消费者/信号表导入、消费者-信号关系导出、应用回传）【00手册p49】；
- **Knowledge Manager 集成**：对象 aspect 内嵌浏览器直达 KM 报表/长趋势【00手册p51】；
- **Process Panel P800**：面板对象经单一访问变量交换数据，支持 AIS/AOS/DIS/DOS/AIC/AOC/DIC/DOC/MOT1/MOT1VVVF/MOT2/MOT2VVVF/MOTP/VLV1/VLVNO1/GROUP/DriveGroup/PREBIN【00手册p53】。

## 3. CL 库（CEMENT_LIB）V2 架构【CL 适配】

三层不变（接口层/功能块层/面板层），但**命名与语义全面对齐官方**：

```
第3层 面板层：FP_Mot/FP_Vlv/FP_Grp/FP_Sig（对齐官方 Faceplate 八要素，05文档）
        + PCC Viewer + Group Step Viewer + CCF 调试页签
第2层 功能块层（CM 类型，FD 图形为主）：
        MOT_C   ←→ 官方 MOT1/MOT2（按设备复杂度二选一）
        VLV_C   ←→ 官方 VLV1/VLVNO1/Actuator
        GRP_C   ←→ 官方 Group/SubGroup/GrpCycleCtrl
        PRE_C   ←→ 官方 Prebin（预选/主备/路由）
        STW_C   ←→ 官方 STW（启动预告）
        SIG_C   ←→ 官方 DIS/DIC/AIS/AIC（信号+联锁参数）
        CHK_C   ←→ 官方 CCF 机制
第1层 接口层：四条总线对齐官方
        GCC 总线（组↔设备，含 step/预选/汇总）
        PCC 总线（信号↔设备，联锁四类 IC/IB/IA/PD）
        LCC 总线（回路↔执行器，含 backtracking）
        -CC  父子上行下行通用规则
```

**双轨制**：官方事实一律用官方名（MOT1/VLV1/Group/Prebin/DIS…）；CL 落地块保留 `_C` 后缀以示自建，文档中逐项标注对应官方对象。**如果现场能买到 MinLib 授权，直接用官方库，CL 库仅作无授权时的替代+学习样本**——这是 V2 最重要的结论。

## 4. V1 → V2 差异总表

| 项 | V1（自拟） | V2（官方核实） |
|---|---|---|
| 库形态 | FBT 功能块类型 | **Control Module Types（CM）**，Control Builder M + Diagram Editor【00手册p25】 |
| 控制连接 | 3 个 STRUCT 自拟 | **-CC/PCC/GCC/LCC 四总线**，结构化变量【00手册p25-29】 |
| 模式 | 自拟 LOCAL/MAINT | **POC 四点（SEQ/CEN/LOC/OOS）+ Man/Auto 子模式**；本地释放联锁规则明确【00手册p15-17】 |
| 联锁 | 自拟三 lock | **IC/IB/IA/PD 四类**，参数在信号对象上【04手册p5】 |
| 组行为 | 自拟前沿法 | 官方：STW预告→步进(步号+tag可视)→Hold/无条件启动/快停/手动Hold/预选五态【00手册p37-46】 |
| 主备 | 自拟 SEL_C | 官方 **Prebin**（预选即主备/路由机制）【00手册p40-42】 |
| 报警 | 自拟四抑制 | 官方三条件禁用+首报+启动抑制+动态优先级+VCO ASM 灰度/颜色规范【04手册p6/00手册p20-22】 |
| 仿真 | 自拟 EnSim | 官方 Simulation Mode（各对象手册 §2.2.x）+ soft controller【04/05/02手册】 |
| 调试 | 自拟 CHK_C | 官方 **CCF**（面板页签+时间戳+用户+EBase Excel 报告）【22手册】 |
| 面板 | 自拟四区 | 官方 Faceplate 八要素（tag/POC/状态/启停/切POC/报警事件列表/确认/Normal View）【00手册p19】 |
| 周期组 | 自拟 EnCyclic | 官方 **GrpCycleCtrl**（且 6.1.4 前有仿真不传递的已知问题，见 Tutorial 截图99）【05手册§6】 |

## 5. 套件文档索引（V2）

| 文件 | 状态 |
|---|---|
| 00-总览与库架构设计.md（本文件） | V2 已完成 |
| 官方手册索引.md | 新增（27份台账+检索地图） |
| 01-公共基础设计.md | V2 已完成（官方四总线机制+IntlkType/IntlkDir全表+Std_Type矩阵） |
| 02-电机功能块拆解.md | V2 已完成（MOT1全77参数+MOT1Data+报警消息结构） |
| 03-阀门功能块拆解.md | V2 已完成（VLV1全71参数+FBErrorMode位掩码） |
| 04-组功能块拆解.md | V2 已完成（GROUP全34参数+步号三段规则+七对象） |
| 05-Faceplate与Viewer设计.md | V2 已完成（八要素+VCO/ASM+三viewer+P800） |
| 06-报警处理框架.md | V2 已完成（Std_Type矩阵+AlarmTr五档+联锁不是报警） |
| 07-仿真与调试检查框架.md | V2 已完成（官方仿真+CCF全量+6.1.4坑） |
| 08-ST代码骨架与FBD对照.md | V2 已完成（MOT_C/GRP_C官方参数名骨架） |
| 09-实施步骤与核对清单.md | V2 已完成（Tutorial afw导入+五套清单+U项销项） |

## 6. 一句话结论

官方手册把 V1 的所有"猜"变成了"查"：**CM 类型+FD 编程、四总线、POC 四模式、IC/IB/IA/PD 四联锁、STW+步进+预选的组行为、VCO/ASM 报警、CCF 调试**——CL 库 V2 就是把这七件事按 800xA 6.1.0 复刻，买得到授权就直接用官方库。
