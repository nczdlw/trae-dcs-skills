# 计划：本地简化版 LangGraph 工作流引擎（minigraph）v2

> 本版已按《评估意见一》逐条修订：P0 四项（扇出/汇聚语义、JSON 序列化约束、loader import 闭环、失败处理）全部落入设计；P1 八项落入 API 契约与 docstring 要求；P2 落入工程约定。评估中认可的既有取舍（零依赖、compile 强校验、max_steps、对照表、测试+三示例）保持不变。

## 一、摘要

参考 LangGraph 核心架构（StateGraph / 节点 / 条件边 / 共享状态 / Checkpointer / 中断恢复），开发**纯 Python 标准库、零依赖**的本地轻量通用工作流引擎 `minigraph`，落盘 `/workspace/minigraph/`。

- 定位：通用工作流引擎（轻量本地版 Airflow/Temporal），节点 = 普通 Python 函数，不绑 LLM。
- 技术栈：Python 3.10+，仅标准库（json/pathlib/argparse/unittest/logging/importlib/os.replace/traceback/hashlib）。
- 经验来源：`knowledge/INDEX.md` → 70 类《编排器-工作者模式调研报告》（LangGraph supervisor 无死循环防护为反面教材、Magentic-One 证明状态全量落盘可行），已吸收。

## 二、现状分析

- `/workspace` 为文档/知识库仓库，无任何现有代码，无冲突。沙箱 Python 3.14.7 可用于开发验证。
- 评估指出的原方案四处硬伤及对策：
  1. **扇出串行污染 + 汇聚未定义** → 改超步批次模型（见三.1），不等长分支汇聚编译期拒绝；
  2. **自由 dict 状态 vs JSON 落盘矛盾** → 硬约束声明 + 可读报错 + encoder/decoder 钩子（见三.4）；
  3. **JSON 流程的函数来源闭环缺失** → `imports` 字段 + importlib（见三.5）；
  4. **节点失败处理缺失** → 失败现场落盘 + 从失败节点 resume（见三.6）。

## 三、核心设计（修订后）

### 1. 执行语义：超步批次模型（修正 P0-1，引擎最高优先级约定）

```
每个超步（superstep）：
  snapshot = 当前状态的浅拷贝快照
  pending  = current 集合按节点注册顺序排序（确定性）
  for node in pending:
      node in interrupt_before → 存检查点(next_nodes=含本节点的剩余批次) → 抛 InterruptSignal(run_id)
      try: result = nodes[node](snapshot)     # 同批次全部读同一快照，分支间零污染
      except Exception → 见三.6 失败处理
      收集 (node, result) 到 writes
      node in interrupt_after → 存检查点(next_nodes=本节点后继∪剩余批次，不含本节点) → 抛 InterruptSignal
  批次全部跑完后，按 pending 顺序统一走 reducer 合并进 state   # 先执行后合并，屏障式
  写检查点(step+1, next_nodes=current, state)
  current = ⋃ 后继(pending) 去重                              # 菱形汇聚天然只触发一次
  current 为空 或 == {END} → 标记 done，返回 state
超步数达 max_steps（默认 100，按超步计数，与 LangGraph recursion_limit 口径一致）→ GraphError
```

- **不等长分支汇聚**（A→B→C 与 A→D→E→C 这类）：v0.1 不做 token 计数，**compile() 静态检测**——从同一扇出点出发、经不同长度路径到达同一汇聚节点的图，编译报错并提示"显式声明不支持不等长分支汇聚"；检测不到的动态情形（条件边 mapping 目标）在 docstring 写明限制。
- 检测算法：对每个出度>1 的节点做 BFS 记录其后代汇合点与各路径长度，长度不一致即报错；条件边按 mapping 声明的目标集参与分析。

### 2. API 契约（补全 P1-5/8/9/12，写进 docstring）

```python
graph = StateGraph(reducers: dict[str, Callable[[old, new], merged]] | None = None)
graph.add_node(name: str, fn: Callable[[dict], dict])
graph.add_edge(a: str, b: str)                      # START/END 为哨兵常量
graph.add_conditional_edges(a: str, router: Callable[[dict], str | list[str]],
                            mapping: dict[str, str] | None = None)
compiled = graph.compile()                          # 校验失败抛 GraphError

compiled.invoke(input: dict | None = None, *, run_id: str | None = None,
                checkpoint_dir: str | Path = ".checkpoints",
                interrupt_before: Iterable[str] = (), interrupt_after: Iterable[str] = (),
                max_steps: int = 100,
                encoder: Callable | None = None, decoder: Callable | None = None) -> dict
compiled.resume(run_id: str, *, state_update: dict | None = None, ...) -> dict
compiled.to_mermaid() -> str                        # 代码建图同样可导出；条件边带 mapping 键标签
```

- **入口唯一风格**：只保留 `add_edge(START, x)`，不设 `set_entry_point()`（P1-9）。
- `mapping=None` 时 router 返回值即节点名；router 返回 `list[str]` 表示扇出（有 mapping 时逐元素查表）（P1-8）。
- 同一节点的**固定出边与条件边互斥**，compile 校验报错（P1-8）。
- `resume(state_update=...)` 的合并**走与节点返回值相同的 reducer 路径**，单一语义（P1-12）。
- reducer 未登记的键默认覆盖；docstring 给 `lambda a, b: a + b` 列表追加示例。
- "可达 END"校验口径写明：条件边按 mapping 目标集做**保守 BFS**；`mapping=None` 的边不做端点保证，compile 给警告不报错（P1-10）。
- `interrupt_after` 检查点的 `next_nodes` 存**后继而非本节点**，resume 不重跑已执行节点（P1-5），专项测试覆盖。

### 3. compile() 校验清单

有 START 边；所有边端点（含 mapping 值）已注册或为 END；固定/条件出边互斥；不可达节点报错；无可达 END 路径报错（条件边按三.2 口径）；不等长分支汇聚报错（三.1）。

### 4. 状态与 JSON 序列化硬约束（P0-2）

- 文档/docstring/README 明确声明：**状态必须 JSON 可序列化**（str/int/float/bool/None/list/dict）。
- checkpoint 保存时捕获 `TypeError`，包装为 `GraphError`，消息带**节点名 + 键名 + 值的类型**。
- `invoke/resume` 暴露 `encoder`/`decoder` 钩子（底层即 `json.dumps(default=...)` / `object_hook`），供高级用户扩展 datetime/Path 等类型。

### 5. 声明式加载闭环（P0-3）

```json
{
  "imports": ["examples.nodes.retry_nodes"],
  "nodes": ["extract", "check", "report"],
  "edges": [["START", "extract"], ["extract", "check"], ["report", "END"]],
  "conditional_edges": [{"from": "check", "router": "route_check",
                         "mapping": {"retry": "extract", "ok": "report"}}],
  "reducers": {"log": "reducers.append"}
}
```

- `imports`：loader 对每个条目用 `importlib.import_module`；若以 `.py` 结尾则按文件路径用 `importlib.util.spec_from_file_location` 加载。导入副作用触发 `@register`（节点/路由/reducer 统一注册表）。
- CLI 同时提供 `--nodes module_or_path` 追加导入（可多次）。
- 未注册名 → GraphError 指明缺哪个、已被谁引用。

### 6. 节点失败处理（P0-4，v0.1 最小集）

- 节点抛异常 → 引擎捕获 → 写**失败检查点**（`status="failed"`，`error={node, exc_type, message, traceback}`，`next_nodes=含失败节点的剩余批次`）→ meta 置 `failed` → 抛 `GraphError("节点 <name> 失败: ...")`（链式 `raise ... from`）。
- `resume(run_id)` 检测到 failed 状态 → 从失败节点（含）重跑；自动重试/退避留 v0.2，README 写明。

### 7. 检查点与运行生命周期（P1-6/7）

```
.checkpoints/<run_id>/
├── meta.json          # {schema_version, status: created|running|interrupted|failed|done,
│                      #  engine_version, graph_hash, created, updated}
└── step_NNNN.json     # {schema_version, step, next_nodes, state, ts, status?, error?}
```

- **原子写**：先写 `*.tmp` 再 `os.replace`；损坏 JSON 在 load 时报可读错误（P1-7）。
- `graph_hash` = 排序后 (节点名, 边, mapping) 的 sha256 前 12 位；resume 时与当前图不一致 → 警告（不阻断，因用户可能只改函数体）（P1-6）。
- resume 后续写 step 从**最大现存编号 +1** 续编，不覆盖历史（P1-7）。
- `list` 命令按 meta.status 分类展示，已完成 run 不列为"可恢复"（P1-6）。
- 保留策略：`invoke(..., keep_last=N)`（默认 None=全留），超限时删最旧 step 文件（P2）。

### 8. 可观测性（P2）

- 标准库 `logging`，logger 名 `minigraph`：INFO=节点进入/路由结果/超步号，DEBUG=耗时与状态键差异。CLI 加 `-v` 开关。零配置默认不输出。

## 四、目录结构（全部新建）

```
/workspace/minigraph/
├── README.md                  # 最小版：CLI 用法、JSON 可序列化硬约束、不等长汇聚限制、失败重跑说明
├── minigraph/
│   ├── __init__.py            # 公开 API 导出 + 与 LangGraph 对照表（模块 docstring）
│   ├── state.py               # reducer 合并（单一路径，节点返回与 resume 更新共用）
│   ├── graph.py               # StateGraph + compile 校验（含不等长汇聚检测）
│   ├── engine.py              # 超步执行循环、中断、失败处理、resume
│   ├── checkpoint.py          # 原子写、meta 生命周期、graph_hash、保留策略
│   ├── registry.py            # @register 节点/路由/reducer 统一注册表
│   ├── loader.py              # imports 闭环 + JSON → StateGraph
│   ├── cli.py                 # run / resume / list / mermaid，-v
│   └── errors.py              # GraphError / InterruptSignal
├── examples/
│   ├── nodes/
│   │   ├── __init__.py
│   │   └── retry_nodes.py     # JSON 流程引用的节点/路由/reducer 函数
│   ├── flows/retry_flow.json
│   ├── 01_linear_flow.py
│   ├── 02_conditional_retry.py
│   └── 03_approval_interrupt.py   # interrupt_before 审批 → resume(state_update) 续跑
└── tests/
    ├── test_state.py          # reducer 合并顺序、默认覆盖
    ├── test_graph.py          # 编译校验全项（含互斥、不等长汇聚）
    ├── test_engine.py         # 超步快照隔离、菱形汇聚单次触发、max_steps、interrupt_after 不重跑
    ├── test_checkpoint.py     # 原子写/损坏恢复/meta 状态机/graph_hash 警告/keep_last
    └── test_loader.py         # imports 闭环、CLI 冒烟
```

## 五、开发顺序与里程碑（P2，按依赖链串行）

- **M1** state.py + graph.py → test_state/test_graph 绿
- **M2** engine.py + checkpoint.py（执行核心，难点集中）→ test_engine/test_checkpoint 绿
- **M3** registry.py + loader.py + cli.py → test_loader 绿 + CLI 冒烟
- **M4** 三示例 + README → 全量验证（见六）

编码约定：pathlib 全程、不写死路径分隔符（可拷到 Windows 直接用）；避免 3.11+ 特性（tomllib/异常组/3.12 泛型语法），保持 3.10 兼容（P2）。

## 六、验证步骤

1. `cd /workspace/minigraph && python3 -m unittest discover -s tests -t . -v` 全绿（cwd 写法如左，Windows 同命令可跑）。
2. 三示例逐个跑通：线性流输出正确；重试循环在 max_steps 内收敛且构造死循环被拦（按超步计数）；审批流中断在 approve 前 → `resume` 带审批结论 → 到 END，且 approve 前节点**不重跑**。
3. CLI 冒烟：`run flows/retry_flow.json` → 中断 → `list` 按状态分类 → `resume` 完成 → `mermaid` 输出带条件边标签的图。
4. 专项核对：扇出两分支读同一快照（互不污染）；菱形汇聚只触发一次；状态塞 `set` 报可读 GraphError；kill 掉写盘进程不产生半截 JSON（tmp+replace）；失败 run 可 resume 重跑。
5. 抽查一个 step JSON：人可读、含 schema_version/next_nodes/state。

## 七、假设与决策

1. 在沙箱 `/workspace/minigraph/` 开发，成品拷到本地 Windows 直接用（纯 stdlib + pathlib 保证可移植）；不单建 Windows 侧路径。
2. 保留最小 README.md（评估意见：工具型产物的最小 README 属产物本身）。
3. 自动重试/退避、真并行（线程池）、子图——明确留 v0.2，本期不做。
4. 执行期按用户规则 6 先建任务树（complex-task-decompose，按 M1–M4 拆叶）；规则 7 开工查 INDEX（已做）；收尾把引擎要点整理入 `knowledge/70-工具与工作方法/`、更新 INDEX 并 git 提交推送，**提交前先向你确认范围**。
