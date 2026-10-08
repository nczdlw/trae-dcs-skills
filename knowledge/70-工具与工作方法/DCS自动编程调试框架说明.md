---
title: DCS自动编程调试框架说明
date: 2026-10-08
project: dcs-auto-framework
type: 开发说明
tags: [DCS,自动编程,调试,IR,800xA,三平台,框架]
summary: dcs-auto-framework 三平台 DCS 自动编程调试框架说明：IR 统一中间表示 + 800xA Adapter + 调试工具链（T1-T9 模块清单），T10 端到端试点通过
source: /workspace/dcs-auto-framework/README.md + AI任务管理/T2~T9 任务树产物 + T10 端到端试点
---

# DCS 自动编程调试框架说明（dcs-auto-framework）

> 框架 T10 收尾时的框架总览条目。代码/模块细节以 /workspace/dcs-auto-framework/ 为准，
> 本文是给后续任务开工时快速定位模块用的检索入口。

## 一、框架定位

dcs-auto-framework 在现有 DCS 项目全流程总纲（P1 资料搜集 → P2 基准确认 → P3 系统设计
→ P4 逐组编程 → P5 核对复查 → P6 交付）之上扩展，面向水泥项目主流 DCS（ABB 800xA /
西门子 PCS7 / ABB Freelance）的自动编程调试框架：

- 用统一中间表示（IR：点位表 + 功能块逻辑）承载设计与现场数据，屏蔽平台差异；
- 平台侧用 Profile（IO 表格模板 / 功能块库）+ Adapter（IR ↔ 平台格式）接入；
- 调试侧用横向工具链（OPC UA 通道 / 快速响应 / 字节序 / 仿真 / AI 工作流）闭环；
- 先打通 800xA，PCS7 / Freelance 标"待核实"（T5 接口桩）。

## 二、目录结构

```
dcs-auto-framework/
├── dcsaf/                  # Python 包
│   ├── ir/                 # 统一中间表示（IR）
│   │   ├── point_table.py  # 点位表模型 + 校验器（tag/signal_type/量程/报警/DP 标记）
│   │   ├── logic_model.py  # 功能块逻辑模型 + 校验器（Fb/Pin/source 引用）
│   │   ├── io.py           # IR 读写（YAML/JSON：save_ir/load_ir）
│   │   ├── diff.py         # IR diff（diff_points/diff_logic）
│   │   └── version.py      # 版本目录管理（VersionManager）
│   ├── profiles/           # 平台 Profile（io_template.py / fb_library.py 校验器）
│   ├── adapters/           # 平台 Adapter（base.py + ab800xa.py + pcs7/freelance 桩）
│   └── tools/              # 横向工具（opcua_channel / quick_response / simulator / ai_workflow）
├── profiles/io_templates/  # 三平台 IO 表格模板（ab800xa/freelance/pcs7）
├── libs/                   # 三平台功能块库 YAML（ab800xa 28 类 / pcs7 23 类 / freelance 21 类）
├── docs/                   # 文档（report_templates.md 五类报告模板、总纲扩展评估）
├── samples/                # 示例素材（t4/t7/t8/t9 自测 + e2e_pilot 端到端试点）
└── AI任务管理/             # 各任务任务树（T2/T3/T7/T8/T9/T10）
```

## 三、已实现模块清单（T1-T9）与功能一句话

| 任务 | 模块 | 功能一句话 |
|---|---|---|
| T1 | dcsaf/ir/ | 统一中间表示：点位表（含 DP 字节序标记）与功能块逻辑模型、校验、读写、diff、版本管理 |
| T2 | profiles/io_templates/ | 三平台 IO 表格模板（输入侧 IR 标准列 + 导入侧 VAR/PAR/FUN 列定义，逐列标来源） |
| T3 | libs/*_fb_library.yaml | 三平台功能块库（800xA 28 类从 knowledge 文档提取，管脚/参数标来源或"推断"） |
| T4 | dcsaf/adapters/ab800xa.py | 800xA Adapter：IR ↔ VAR/FUN xlsx（generate_var_excel/generate_fun_excel/parse_800xa_export/dedupe_increment） |
| T5 | dcsaf/adapters/pcs7.py、freelance.py | PCS7/Freelance 官方接口桩（CFC 格式 / Control Builder 工程格式，待核实未实现） |
| T6 | dcsaf/tools/opcua_channel.py | OPC UA 统一调试通道（OpcUaChannel / readback_check，asyncua 实现） |
| T7 | dcsaf/tools/quick_response.py | 调试快速响应：detect_change（点表变更→受影响 FB）/ regenerate_affected（重建说明）/ byte_order_fix（字节序处理） |
| T8 | dcsaf/tools/simulator.py | 仿真调试回环：probe_simulator_800xa（探测）/ inject_test_signals / verify_interlocks（实测或静态推导） |
| T9 | dcsaf/tools/ai_workflow.py | AI 工作流编排：draft_from_requirement / review_draft / generate_from_approved（草稿→人工审核→生成 xlsx） |

## 四、待核实项

1. **PCS7 / Freelance 官方接口**：T5 仅为接口桩，CFC 文件格式、WinCC 变量表格式、
   Freelance Control Builder 工程格式的官方定义未核实；对应模板/功能块库虽已建（pcs7 23 类
   / freelance 21 类），但未与官方格式联调。
2. **800xA 虚拟控制器接入**：T8 中 probe_simulator_800xa 为 OPC UA 探测实现，真实 800xA
   虚拟控制器在本环境不可得，调研登记项（调研_800xa_virtual_controller / 调研_plcsim /
   调研_freelance_sim）全部 status="待核实"，禁止编造接入细节；结论核实后落盘 knowledge 再回填。
3. **DP 字节序取值**：knowledge 文档仅明确 HAVER 包装机为 Big-Endian，VFD/皮带秤等设备
   字节序文档未给，试点中标注"推断/待核实"，最终以设备通讯表为准。
4. **800xA 官方批量导入表列结构**：VAR/PAR/FUN 列名取自 knowledge 文档（中压变频器_开发规则.md），
   未与 800xA 官方手册逐列核对；BDM 列因 knowledge 无依据未设。

## 五、端到端试点结果摘要（T10）

samples/e2e_pilot.py 用现有素材（中压变频器频率/电流/温度/状态字、大布袋差压、皮带秤流量，
位号加"示例"）走通五步闭环，运行输出"T10 端到端试点通过"：

1. 点表导入：构造 11 点 IR 点表（8 个 DP 设备点含字节序标记），校验 0 错误；
2. 逻辑生成：7 个功能块（SignalInReal 监测 ×2、MOTOR1、SMOTOR_PROV、RS 连锁 ×2、ABBMVVVF），
   校验 0 错误（连接只在消费侧表达，Q1 输出不写 source）；
3. 组态产出：生成 e2e_pilot_Var.xlsx（11 行，7 列）/ e2e_pilot_Fun.xlsx（7 行，5 列），
   类型全部在 800xA 功能块库中，无警告；
4. 回读校验：parse_800xa_export 回读后 diff，30 条点位差异 + 50 条逻辑差异，全部归因于
   VAR/FUN 表列结构（DO/AO 方向丢失、量程/单位/报警/DP 字段不回读、Fb.pins 整体不回读）；
5. 调试变更响应：模拟 DP 增点（功率/累积量2）+ 高低字节反转修正（VFD 频率/电流/温度
   low_high→high_low），detect_change 报 5 个变更点 / 3 个受影响 FB，regenerate_affected
   生成重建说明，byte_order_fix 出 6 条处理清单 + 4 条警告（byte_order=none 需人工核对）。

报告模板（docs/report_templates.md）已定义五类：点表一致性报告、逻辑生成差异报告、下装回读报告、
仿真结果报告、调试变更报告。
