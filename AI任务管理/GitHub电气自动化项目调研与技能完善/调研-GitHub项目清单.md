# GitHub电气自动化编程项目调研清单

> 调研日期: 2026-09-14 | 检索工具: GitHub search API（star降序）
> 筛选标准: 见任务树 L1-1.2（相关性必须；star≥30参考，小众领域<30有独特价值可入选并注明；活跃度看近1年commit；质量看README/文档/示例）

## 1. 方向A：PLC/IEC 61131-3 编程框架与规范类

| 项目 | star | 语言 | 活跃 | 简介 | 与本仓库相关性 |
|------|------|------|------|------|----------------|
| [beremiz/beremiz](https://github.com/beremiz/beremiz) | 436 | Python | ✅2026-09 | 开源机器自动化IDE（matiec编译器，支持61131-3五语言） | 低（IDE本身） |
| [johannesPettersson80/trust-platform](https://github.com/johannesPettersson80/trust-platform) | 220 | Rust | ✅2026-09 | truST：ST工具套件（LSP语言服务器/调试器/VS Code扩展） | 低-中 |
| [vscode-st](https://github.com/Serhioromano/vscode-st) | 204 | TS | ✅ | VS Code的ST语言扩展 | 低 |
| [iec-checker](https://github.com/iec-checker/iec-checker) | 107 | OCaml | ✅2026-09 | IEC 61131-3程序静态分析（未用变量/命名/类型检查） | **中-高（复查规则参考）** |
| [stefanbesler/struckig](https://github.com/stefanbesler/struckig) | 104 | ST | ✅ | ruckig在线轨迹生成库的完整ST移植 | 中（FB库工程化范例） |
| [Aliazzzz/OOP-Concept-Examples-in-CODESYS-V3](https://github.com/Aliazzzz/OOP-Concept-Examples-in-CODESYS-V3) | 75 | ST | ✅ | 61131-3第三版OOP范式实战示例 | 中（设计模式） |
| [61131/echidna](https://github.com/61131/echidna) | 71 | C | ✅2026-07 | 61131-3语言编译器+虚拟机运行时 | 低 |
| [runtimevic/OOP-IEC61131-3--Curso-Youtube](https://github.com/runtimevic/OOP-IEC61131-3--Curso-Youtube) | 69 | ST | ✅ | ST设计模式视频课程配套代码 | 中（设计模式） |
| [klauer/blark](https://github.com/klauer/blark) | 69 | Python | ✅ | TwinCAT ST解析器（Lark/Earley） | 低 |
| [WengerAG/structured-text-utilities](https://github.com/WengerAG/structured-text-utilities) | 64 | ST | ✅ | ST工具函数库 | 中 |
| [FellowWithLaptop/FB_CaseStateMachine](https://github.com/FellowWithLaptop/FB_CaseStateMachine) | 43 | ST | ✅ | CASE状态机FB：补足entry/exit步、超时、日志 | 中（FB设计模式） |
| [tkucic/UniTest](https://github.com/tkucic/UniTest) | 40 | ST | ✅ | 仅用IEC 61131标准特性写的跨平台PLC单元测试库 | **中-高（测试方法论）** |
| [sbwtw/stc-rs](https://github.com/sbwtw/stc-rs) | 38 | Rust | ✅2026-05 | Rust写的ST编译器 | 低 |

## 2. 方向B：工业自动化标准库与实践类

| 项目 | star | 语言 | 活跃 | 简介 | 与本仓库相关性 |
|------|------|------|------|------|----------------|
| [tcunit/TcUnit](https://github.com/tcunit/TcUnit) | 417 | C#/ST | ✅2026-09 | TwinCAT 3单元测试框架（PLC测试事实标准） | **高（测试方法论→P5核对复查）** |
| [RWTH-EBC/AixOCAT](https://github.com/RWTH-EBC/AixOCAT) | 101 | ST | ✅2026-07 | RWTH亚琛：OSCAT社区+自动化通信结构组合库 | 中（FB库组织方式） |
| [eclipse-4diac/4diac-ide](https://github.com/eclipse-4diac/4diac-ide) + [4diac-forte](https://github.com/eclipse-4diac/4diac-forte) | 79/72 | Java/C++ | ✅ | Eclipse 4diac：IEC 61499（FBD为中心的分布式自动化标准）开源IDE+运行时 | 中（FBD接口形式化模型：事件/数据管脚、WITH关联） |
| [arduino_plclib](https://github.com/stlehmann/arduino_plclib) | 28 | C++ | ✅ | IEC 61131-3基本FB（TON/TOF/CTU/RS等）参考实现 | 中（标准FB语义参考） |
| [stefandreyer/OSCAT-BASIC](https://github.com/stefandreyer/OSCAT-BASIC) | 16 | ST | ✅ | OSCAT基础库CODESYS V2.3→V3移植 | 中 |
| [PLC-lang/oscat](https://github.com/PLC-lang/oscat) | 10 | ST | ✅2026-09 | OSCAT Basic库可读ST源码（PLC-lang组织） | **中-高（FB接口设计/命名/文档规范）** |
| Scada-LTS / PyScada / Serial-Studio / dgiot | 1004/651/7194/4844 | 多 | ✅ | 开源SCADA/HMI/IIoT平台 | 低（偏离DCS编程规则主线） |
| ISA-88 batch / ISA-18.2 alarm 检索 | ≤2 | - | - | 仅课程作业级小项目 | 低 |

## 3. 方向C：AI辅助工业/PLC编程类（本仓库AI辅助主线的对照系）

| 项目 | star | 语言 | 活跃 | 简介 | 与本仓库相关性 |
|------|------|------|------|------|----------------|
| [hkoziolek/control-logic-generation-prompts](https://github.com/hkoziolek/control-logic-generation-prompts) | 55 | Python | ✅2026-03 | LLM控制逻辑工程prompt集（Kiel大学） | **高（连锁分析prompt化对照）** |
| [hkoziolek/Spec2Control](https://github.com/hkoziolek/Spec2Control) | 40 | Python | ✅2026-09 | LLM工作流：控制叙述→IEC 61131-3 FBD | **极高（与连锁分析PDF→FBD同构）** |
| [hkoziolek/LLM-CodeGen-TestGen](https://github.com/hkoziolek/LLM-CodeGen-TestGen) | 37 | ST | ✅2026-09 | LLM生成PLC控制逻辑测试用例 | **高（测试生成→复核方法论）** |
| [hkoziolek/LLM-CodeGen-RAG](https://github.com/hkoziolek/LLM-CodeGen-RAG) | 24 | ST | ✅2026-05 | 检索增强（RAG）的PLC控制代码生成 | 中-高 |
| [hkoziolek/LLM-CodeGen-Image](https://github.com/hkoziolek/LLM-CodeGen-Image) | 22 | - | ✅2026-07 | P&ID管道仪表图+GPT-4V生成控制逻辑 | 中（图纸→逻辑，PDF连锁图同类输入） |
| [TechIndustryX/twincat-agent](https://github.com/TechIndustryX/twincat-agent) | 27 | 多 | ✅2026-09 | Infosys TechIndustryX：TwinCAT编码代理（Claude Code），含ST严格规则、命名规范、语法检查、安全项目验证工作流 | **极高（与TRAE skill+规则体系同构）** |
| [zbest1000/mcptoolkit-for-codesys](https://github.com/zbest1000/mcptoolkit-for-codesys) | 15 | Python | ✅ | MCP server驱动CODESYS IDE（项目/POU/编译/在线控制） | 中 |
| [HeytalePazguato/plc-st-review](https://github.com/HeytalePazguato/plc-st-review) | 14 | TS | ✅2026-08 | ST确定性语义linter：80检查项，映射PLCopen/MISRA-C/IEC 61508/62443，CI原生 | **高（复查清单来源）** |
| [feelautom/tia-copilot-genai-bridge](https://github.com/feelautom/tia-copilot-genai-bridge) | 18 | PS | ✅ | TIA Portal的MCP桥（SCL/FBD/梯形图探索与生成） | 中 |
| [hkoziolek/IO-AutoMapper](https://github.com/hkoziolek/IO-AutoMapper) | 0 | Python | 2025-04 | IO信号清单（电子表格）→库功能块自动映射工具 | **极高（与点号表→VAR/FUN表同构；star<30注明，学术工具独特价值）** |
| [coder007rahul/gxworks3-mcp-bridge](https://github.com/coder007rahul/gxworks3-mcp-bridge) | 2 | C# | ✅ | 三菱GX Works3 MCP：写操作带preview→confirm安全层 | 中（AI写IDE的安全模式） |
| [Codyte/Tia-Portal-CLI](https://github.com/Codyte/Tia-Portal-CLI) | 2 | 多 | ✅2026-09 | TIA Openness CLI（240+动词，默认dry-run，Claude Code skill） | 中 |
| [mongolyy/gen-ai-ladder-program-sample](https://github.com/mongolyy/gen-ai-ladder-program-sample) | 1 | Python | 2026-07 | Claude Code skill：自然语言→梯形图/ST+静态安全检查+GX Works3导出 | **中-高（同样是"skill"形态，star<30注明）** |

## 4. 方向D：ABB 800xA/DCS/水泥行业类

| 项目 | star | 活跃 | 简介 | 与本仓库相关性 |
|------|------|------|------|----------------|
| [Tonny72/PyOpcHda](https://github.com/Tonny72/PyOpcHda) | 3 | 2026-02 | 从ABB 800xA读OPC HDA历史数据的Python脚本 | 低 |
| [MartinNorberg/LarmLogger800xA](https://github.com/MartinNorberg/LarmLogger800xA) | 0 | 2020 | 800xA报警事件采集（C#，不活跃） | 低 |
| "DCS programming" / "cement plant automation" 检索 | ~0 | - | 仅1个论文级NodeJS DCS、1个PowerPlatform KPI项目 | 无 |

**方向D结论（如实记录）**：专有DCS生态（ABB 800xA/Siemens PCS7/Emerson DeltaV）基本不开源到GitHub，水泥行业DGS编程无可借鉴的公开工程实践。该方向的价值只能从方向A/B/C的IEC 61131-3通用实践迁移。

## 5. 重点项目筛选（进入L1-3深入研究，共8个）

按筛选标准（相关性优先、热度参考、活跃度、质量信号）选出：

| # | 项目 | star | 入选理由（对照标准） |
|---|------|------|----------------------|
| 1 | hkoziolek/Spec2Control | 40 | 与连锁分析skill同构：控制叙述→FBD的完整LLM工作流；学术严谨有论文；活跃 |
| 2 | hkoziolek/control-logic-generation-prompts | 55 | 控制逻辑生成的prompt模式集合，可对照连锁分析任务的提示词设计 |
| 3 | hkoziolek/LLM-CodeGen-TestGen | 37 | 从ST/需求生成测试用例，可补强P5核对复查阶段"怎么验"的方法论 |
| 4 | hkoziolek/IO-AutoMapper | 0(<30注明) | IO点表→FB映射与"点号表→VAR/FUN表"流程直接同构，独特价值高 |
| 5 | TechIndustryX/twincat-agent | 27(<30注明) | 与本仓库"TRAE skill+规则"同构的Claude Code工程化实践：规则分层/命名/安全验证工作流 |
| 6 | HeytalePazguato/plc-st-review | 14(<30注明) | 80项ST语义检查目录（PLCopen/MISRA-C/IEC 61508/62443映射），可直接转化为复查清单素材 |
| 7 | PLC-lang/oscat | 10(<30注明) | OSCAT经典FB库可读源码：FB接口设计/命名/头注释文档规范 |
| 8 | tcunit/TcUnit | 417 | PLC单元测试事实标准：测试FB组织、断言模式，为P5测试化核对提供范式 |

落选说明：iec-checker/UniTest/twincat相关并入上述项目研究时顺带覆盖；SCADA平台类偏离主线；方向D无实质项目。
