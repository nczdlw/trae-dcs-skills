# 计划：本地简化版 LangGraph 工作流引擎（minigraph）

## 一、摘要

参考 LangGraph 的核心架构（StateGraph / 节点 / 边 / 条件路由 / 共享状态 / Checkpointer / 中断恢复），开发一个**纯 Python 标准库、零依赖**的本地轻量工作流引擎，项目名 `minigraph`，落盘在 `/workspace/minigraph/`。

- **定位**（用户已确认）：通用工作流引擎（类似 Airflow/Temporal 的轻量本地版），节点是普通 Python 函数，不绑定 LLM。
- **技术栈**（用户授权推荐）：Python 3.10+，只用标准库（json/argparse/unittest 等），无第三方依赖，可直接拷到本地 Windows 机器运行。
- **已查经验**：`knowledge/INDEX.md` → 70 类《编排器-工作者模式调研报告》（含 LangGraph supervisor 一节）与本任务相关，其结论（无死循环防护是反面教材、状态外置可行）已吸收进本计划。

## 二、现状分析

- 工作区 `/workspace` 是文档/知识库型仓库（knowledge、AI任务管理、templates、两个 skill），**无任何现有代码**，无命名/架构冲突。
- 沙箱 Python 3.14.7 可用，满足开发验证。
- LangGraph 架构核心（从调研报告 + 公开认知提取，作为设计基准）：
  1. `StateGraph`：节点 = 函数，共享状态对象贯穿全图
  2. 边：固定边 + 条件边（路由函数返回下一个节点名）
  3. 状态合并：节点返回部分更新，按 reducer 合并进全局状态
  4. Checkpointer：每步后持久化，可断点续跑
  5. 中断/恢复：`interrupt_before/after` 实现人工介入（human-in-the-loop）
  6. `recursion_limit`：防条件边构成的循环死转

**明确不做**（简化边界）：异步执行、Pregel 超步并行模型、token 流式输出、子图嵌套、LLM/工具集成、多 Agent 协议。并行扇出支持，但按注册顺序**串行执行**（确定性优先，代价写进文档字符串）。

## 三、拟建文件与改动

目录结构（全部新建）：

```
/workspace/minigraph/
├── minigraph/
│   ├── __init__.py        # 公开 API：StateGraph, START, END, CheckpointStore, load_flow
│   ├── state.py           # 状态模式与 reducer 合并逻辑
│   ├── graph.py           # StateGraph 构建器 + compile() 校验
│   ├── engine.py          # CompiledGraph：执行循环、路由、max_steps、中断
│   ├── checkpoint.py      # JSON 落盘检查点：save/load/resume/list
│   ├── registry.py        # 节点函数注册表（供声明式流程引用）
│   ├── loader.py          # JSON 流程定义 → StateGraph
│   ├── cli.py             # 命令行：run / resume / list / mermaid
│   └── errors.py          # GraphError / InterruptSignal
├── examples/
│   ├── 01_linear_flow.py        # A→B→C 线性流
│   ├── 02_conditional_retry.py  # 条件边重试循环（检验计数→成功/失败分支）
│   ├── 03_approval_interrupt.py # 审批中断 → 人工补充状态 → resume 续跑
│   └── flows/retry_flow.json    # 声明式定义示例
└── tests/
    ├── test_graph.py      # 建图与编译校验
    ├── test_engine.py     # 执行/条件路由/循环/max_steps
    ├── test_checkpoint.py # 存取/恢复/中断续跑
    └── test_loader.py     # JSON 声明式加载 + CLI 冒烟
```

### 各模块要点

**state.py** — 状态与 reducer
- 状态 = 普通 `dict`；节点函数签名 `fn(state: dict) -> dict`，返回**部分更新**。
- reducer 表：`{key: callable(old, new) -> merged}`，未登记的键默认覆盖（对应 LangGraph 的默认 overwrite）；示例给 `lambda a,b: a+b` 实现列表追加（对应 `operator.add` 注解）。

**graph.py** — 建图
- API：`add_node(name, fn)`、`add_edge(a, b)`、`add_conditional_edges(a, router, mapping=None)`、`set_entry_point(name)`（= START 边）、`set_finish_point(name)`（= END 边）。
- `START` / `END` 哨兵常量。
- `compile()` 时校验：有入口；所有边端点已注册；存在可达 END 的路径；不可达节点报错。校验失败抛 `GraphError`，不静默通过。

**engine.py** — 执行循环（核心简化决策）
- 步进模型：每步执行一个节点 → reducer 合并 → 计算下一节点集 → 存检查点。下一节点多于一个时按注册顺序串行跑完（简化 Pregel）。
- 终止：下一节点集为空或到达 `END`。
- `max_steps`（默认 100，可配）：超限抛 `GraphError`——补上调研报告指出的 LangGraph supervisor"无死循环防护"短板。
- 中断：`interrupt_before` / `interrupt_after` 节点名单；命中即存检查点并以 `InterruptSignal` 返回，携带 `run_id` 供恢复。
- `invoke(input, run_id, checkpoint_dir, ...)` / `resume(run_id, state_update=None)`：恢复时允许附加状态更新（对应 LangGraph 的 `Command(resume=...)` 简化版）。

**checkpoint.py** — 检查点
- 每步后写 `.checkpoints/<run_id>/step_<NNNN>.json`：内容 = `{step, next_nodes, state, ts}`。
- `resume` 读最新步恢复；`list_runs()` 供 CLI 列出可恢复运行。纯 JSON，人可读、可 git diff。

**registry.py + loader.py** — 声明式流程
- `@register("name")` 装饰器登记节点/路由函数；JSON 定义 `{nodes, edges, conditional_edges, entry, finish}` 引用登记名，`load_flow(path)` 编译成图。

**cli.py**
- `python -m minigraph run flow.json --input '{}' [--run-id x]`
- `python -m minigraph resume <run_id> [--update '{}']`
- `python -m minigraph list` / `python -m minigraph mermaid flow.json`（导出 Mermaid 图，方便贴进任务树/文档）

### 与 LangGraph 对照表（写进 `__init__.py` 模块 docstring）

| LangGraph | minigraph | 说明 |
|---|---|---|
| StateGraph | graph.StateGraph | 同名同义 |
| 条件边 add_conditional_edges | 同名 | router 返回键→mapping 查下一节点 |
| Annotated[key, reducer] | state schema dict | 简化，不用类型注解魔法 |
| Checkpointer(Sqlite 等) | JSON 文件 | 零依赖，可读 |
| interrupt_before/after | 同名 | 静态名单式中断 |
| Command(resume=) | resume(state_update) | 恢复时补状态 |
| recursion_limit | max_steps | 同名语义 |
| Pregel 超步并行 | 注册序串行 | **显式简化** |

## 四、假设与决策

1. 项目落在 `/workspace/minigraph/`（本仓库目前无代码区，顶层新建不冲突）；README 不单建（遵循"不主动建文档"规则），用法写在模块 docstring + examples 自注释。
2. 零第三方依赖、同步执行、单进程——符合"本地简化版"定位。
3. 并行扇出只做确定性串行，真并行（线程池）留作后续扩展，不在本期。
4. 执行期按用户规则 6 先建任务树（complex-task-decompose），按用户规则 7 开工查 INDEX（已做）；
   收尾时把引擎使用要点整理成知识条目入 `knowledge/70-工具与工作方法/` 并更新 INDEX、git 提交推送（规则 7），**提交前会先向你确认 commit 范围**。

## 五、验证步骤

1. `python3 -m unittest discover minigraph/tests -v` 全绿。
2. 三个 example 逐个跑通：
   - 线性流输出符合预期；
   - 重试循环在 max_steps 内收敛，且构造死循环时被 max_steps 拦下；
   - 审批流：首次运行中断在 approve 前 → `resume` 带审批结论 → 跑到 END。
3. CLI 冒烟：`run` 一个 JSON 流程 → 强制中断 → `list` 看到 run → `resume` 完成；`mermaid` 输出图语法。
4. 抽查一个检查点 JSON 文件，确认人可读、含 state/next_nodes/step。
