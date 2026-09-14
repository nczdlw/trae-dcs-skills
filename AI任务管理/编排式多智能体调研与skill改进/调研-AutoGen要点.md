# AutoGen（v0.4+ autogen-agentchat）编排调研要点

> 叶任务: L1-2.2 ｜ 日期: 2026-09-14 ｜ 用途: 并入 L1-3.1 汇总
> 来源: microsoft/autogen main 分支源码（GitHub API 直读核实）、官方文档 stable 版、论文 arXiv:2411.04468、官方博客 aka.ms/magentic-one-blog

## 核心源码位置（已核实）

- main 分支：`python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_magentic_one/` 目录（`_magentic_one_group_chat.py`、`_magentic_one_orchestrator.py`、`_prompts.py`）。注意：旧单文件 `_orchestrator.py`/`_magentic_one.py` 在 main 已不存在（404），勿引用旧路径。
- v0.4.4 原始实现（autogen-core 版，已归档）：`python/packages/autogen-magentic-one/src/autogen_magentic_one/agents/orchestrator.py`（LedgerOrchestrator）+ `orchestrator_prompts.py`。
- 文档：microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/{magentic-one,teams,termination,selector-group-chat,swarm,graph-flow}.html

## 1. 编排器角色定义

- `MagenticOneOrchestrator`（继承 BaseGroupChatManager），双循环：
  - **Outer loop（计划级）**：`handle_start` → ①GATHER FACTS（`ORCHESTRATOR_TASK_LEDGER_FACTS_PROMPT` 预调研四节）②CREATE A PLAN（`ORCHESTRATOR_TASK_LEDGER_PLAN_PROMPT`，"devise a short bullet-point plan"，明示"no requirement to involve all team members"）③`_reenter_outer_loop`：给全体发 GroupChatReset 重置、清空 message thread、广播 Task Ledger 全文（task+team+facts+plan，`ORCHESTRATOR_TASK_LEDGER_FULL_PROMPT`）。
  - **Inner loop（步骤级）**：`_orchestrate_step` 每轮让 LLM 产 Progress Ledger JSON，决定 next_speaker 与 instruction_or_question。
- 团队五 agent：Orchestrator/WebSurfer/FileSurfer/Coder/ComputerTerminal（文档 magentic-one.html）。

## 2. 任务拆解机制

- PLAN 生成：按团队构成+已知/未知事实生成简短 bullet-point 计划；粒度仅靠 prompt 措辞（short/concise）控制，无硬性参数。
- 执行中不改 plan（只在重规划时重写）；"步骤是否完成"由每轮 progress ledger 的 is_request_satisfied 判断。

## 3. 状态与进度存储

- 内存态：`self._task/_facts/_plan/_n_rounds/_n_stalls`；可序列化：`MagenticOneOrchestratorState`（message_thread/current_turn/task/facts/plan/n_rounds/n_stalls），save_state/load_state 全量存取。
- FACTS 四节（`_prompts.py`）：GIVEN OR VERIFIED FACTS／FACTS TO LOOK UP（须注明去哪查）／FACTS TO DERIVE／EDUCATED GUESSES。
- Progress Ledger（`ORCHESTRATOR_PROGRESS_LEDGER_PROMPT` + pydantic `LedgerEntry`）：五键各含 reason+answer：`is_request_satisfied`／`is_in_loop`／`is_progress_being_made`／`next_speaker`（限 {names}）／`instruction_or_question`。JSON 解析重试至多 10 次（`_max_json_retries`），键结构+next_speaker 合法性校验，单 agent 团队确定性指定。
- 注入：ledger 全文以消息形式广播给全员并入 message thread，成为下一轮上下文。
- 论文级描述（Figure 2 caption + 博客）：Task Ledger = facts/guesses/plan；Progress Ledger = current progress/task assignment。博客图 alt 文本给出决策流：Task complete?→是：终止；否→Progress being made?→是：移交 agent；否→Stall count>2?→是：回 outer loop 更新 Task Ledger；否：移交 agent。
- 用户点名的 "FACTS OF THE TASK / PLAN OF STEPS / OPINIONS OF PROGRESS / DECISION" 大写字段：在正文与代码 prompt 中均未查到（疑为论文图示图片内容，图片无法文本化读取）——如实记未查到。

## 4. worker 汇报与交接

- "request speak"：Orchestrator 向 next_speaker 的 topic 发 `GroupChatRequestPublish`，指令=instruction_or_question.answer；有进展时可选发 `SelectSpeakerEvent`。
- 回写：worker 响应经 `handle_agent_response` → update_message_thread → 检查 termination_condition → 再入 `_orchestrate_step`。worker 结果不直接改 facts/plan（facts 只在重规划时整体重写），而是留在共享消息线程供下轮 ledger 判断。

## 5. 验证与失败处理

- 每轮 progress assessment：is_request_satisfied=True → `_prepare_final_answer`（`ORCHESTRATOR_FINAL_ANSWER_PROMPT` 从对话合成终答）+ 终止信号。
- Loop detection（main）：无进展或循环 → `_n_stalls+=1`；有进展 → `_n_stalls=max(0,_n_stalls-1)`（可恢复递减）；`_n_stalls >= max_stalls`（`MagenticOneGroupChat` 默认 3，另有 max_turns=20）→ `_update_task_ledger`（`ORCHESTRATOR_TASK_LEDGER_FACTS_UPDATE_PROMPT`：重写 fact sheet，guesses 升级为 verified，且必须新增/更新至少一条 educated guess；`ORCHESTRATOR_TASK_LEDGER_PLAN_UPDATE_PROMPT`：先解释 root cause 再出新计划并"避免重蹈覆辙"）+ `_reenter_outer_loop`。
- v0.4.4 更严：stall_counter>max_stalls_before_replan(3) 触发 replan，replan_counter>max_replans(3) 直接终止（"Replan counter exceeded... Terminating"）；main 版无 max_replans 上限。
- TerminationCondition 体系（docs termination.html）：MaxMessage/TextMention/TokenUsage/Timeout/Handoff/SourceMatch/External/StopMessage/TextMessage/FunctionCall/Functional；`|`/`&` 组合；按增量消息评估、run 后自动 reset；组播团队每 agent 响应后调用一次。

## 6. 团队编排器（其他，已核实）

- RoundRobinGroupChat：固定轮转+全员广播。
- SelectorGroupChat：LLM 按上下文选下一位；selector_prompt 变量 {participants}/{roles}/{history}；allow_repeated_speaker 默认 False 防连任；selector_func/candidate_func 覆盖；max_selector_attempts=3。
- Swarm：下一位=最近一条 `HandoffMessage` 的 target；agent 用 `handoffs=[...]` 生成 transfer_to_<name> 工具调用移交；共享消息上下文、无中心编排器；`HandoffTermination(target="user")` 人机环。
- GraphFlow/DiGraphBuilder：DiGraph 有向图执行（顺序/并行 fan-out/条件边（字符串关键词或 callable）/带安全出口的循环）；自动算 source/leaf 节点，从 source 起跑，无剩余节点时 DiGraphStopAgent 出 StopMessage 终止；官方标注 experimental（API 随时变）；微软迁移指南将其对应到 Agent Framework 的 Workflow API。
- TextMentionSelector：仓库代码搜索 0 结果，未查到（现行机制为 selector_func 自定义函数）。

## 借鉴要点清单（对文件外置任务树）

1. FACTS↔检索目录："FACTS TO LOOK UP（注明在哪查）"对应叶任务"输入：绝对路径+精确定位"；可在树头加事实节（已核实/待查/推测三栏）防失忆重查。
2. Progress Ledger 五问↔状态字段：每完成一叶先答"完成？在循环？有进展？下一步谁？给什么指令？"（各带 reason），对应"状态/问题"要素；is_in_loop 直接对应"重复劳动检测"。
3. stall 计数器↔进度行未决问题数：无进展+1、有进展-1、连续≥3 强制重规划——对应"未决问题数连续 N 轮不降则该叶升级 ❌ 进复查区重拆"，并设 max_replans 防死循环。
4. DECISION/next_speaker↔"下一步叶编号"：进度行固化"下一步编号+执行者+指令"，跨会话从该行恢复现场。
5. 状态外置+重规划仪式感：MagenticOneOrchestratorState 证明 ledger 全量落盘可行；且重规划=先重置全员、清空线程、整文重写广播新计划——对应"修改计划必须整树重写落盘，禁止对话内静默改"。

## 来源清单

- 源码（GitHub API）: microsoft/autogen @ main, python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_magentic_one/{_magentic_one_group_chat.py,_magentic_one_orchestrator.py,_prompts.py}; teams/__init__.py
- 源码（v0.4.4 归档）: python/packages/autogen-magentic-one/src/autogen_magentic_one/agents/{orchestrator.py,orchestrator_prompts.py}; README.md
- 文档: https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/magentic-one.html ; tutorial/teams.html ; tutorial/termination.html ; selector-group-chat.html ; swarm.html ; graph-flow.html
- 论文: arXiv:2411.04468（Figure 2）; 博客: https://aka.ms/magentic-one-blog
