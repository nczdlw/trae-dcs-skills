## User Preferences
- Communication language: Chinese
- When dealing with tables, prefers being provided with column count and column names to ensure accurate recognition
- For表格处理, prefers using Excel source files (.xlsx) over PDF to avoid format recognition errors
- Variable tables must strictly follow the format of legacy function blocks
- Software development should be done in groups one by one, with completion and verification before moving to the next group
- Function Block device names should have comments added, with the comment content being the corresponding number from Loesche
- For large engineering projects, prefers using FBD (graphical) for motor, valve, and group logic for easier understanding and lookup
- When dealing with FBD pin connections, prefers a graphical visualization that mimics the exported FBD diagram style from ABB 800XA to intuitively see which pins connect to which variables
- A function block instance can only be used by one program and cannot appear in multiple programs simultaneously
- When找不到实例依据, the user should be informed to provide the location
- 莱歇磨部分的连锁信号不用ST，全部用FBD来做
- 连锁分析工作必须以指定PDF文件为唯一基准，ST代码仅作参考
- 连锁分析需逐页逐条落实，要求细心且不允许偷工减料
- 完成后需按用户指定分组提供各组详细的FBD管脚连接说明
- 复查后重新按照用户的分组给各组详细的FBD管脚连接说明
- Function block parameters should be compressed by grouping Bool signals into DInt words to reduce FBD pin count when too many pins cause display issues
- 接到复杂任务（≥3步骤或≥2输入文件、逐页/逐组/逐表处理）时，必须先按任务树方法论建树落盘再动手执行；任务树文件是唯一进度真相：每轮先读树、完成一个叶立即落盘并同步SVG导图、出问题按检索目录回源头复查，禁止凭对话记忆修改
- 任务树方法论 skill 位置（跨项目通用，skill 不自动触发时直接读取文件照做）：C:\Users\nczdl\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a94c94a03dec9014b553fda\.trae\skills\complex-task-decompose\SKILL.md 与同目录 interlock-analysis\SKILL.md（连锁分析优先）；空白模板在 D:\越南F163粉磨站800XA编程\AI任务管理\任务树模板.md

## Tech Stack
- Familiar with ABB 800XA system configuration and Excel worksheet formatting
