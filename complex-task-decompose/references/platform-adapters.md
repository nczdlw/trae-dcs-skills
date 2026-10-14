# 平台适配说明（complex-task-decompose 可选扩展）

> 本文件是 complex-task-decompose 的**平台适配**：安装本技能、评估平台支持时读。
> 各平台实测状态（发现/触发/引用/权限/核验日期）以 `docs/通用方法论迭代/02-平台兼容矩阵.md` 为唯一记录，本文件不重复维护状态，只给操作方法。
> 2026-10-14 实测环境：Windows，TRAE SOLO CN 3.4.3，WorkBuddy 5.8.2.0。

## 一、安装（仓库 → 平台副本，单向刷新）

技能包 = `complex-task-decompose/` 整个目录（SKILL.md + references/）。**仓库是唯一源头**，任何平台副本都由仓库生成/刷新，禁止在副本侧直接修改后不回传。

### TRAE SOLO CN

1. 复制 `complex-task-decompose/` 到 `%USERPROFILE%\.trae-cn\skills\complex-task-decompose\`（覆盖旧文件）；
2. 或在 TRAE 设置 → 规则和技能 → 技能仓库 → 添加本仓库（若版本有此入口）；
3. 刷新后该技能出现在可用技能列表即被发现（`~/.trae-cn/skill-config.json` 的 managedSkills 登记）。

### WorkBuddy

1. 用户级（所有项目可用）：复制到 `%USERPROFILE%\.workbuddy\skills\complex-task-decompose\`；
2. 项目级（仅当前工程）：复制到 `<工程目录>\.workbuddy\skills\complex-task-decompose\`；
3. 下次会话启动时进入可用技能清单即被发现（本会话为安装后首会话，触发验证见 02 矩阵待办）。

### 其他平台

未实测的平台（Claude Code 等）不提供安装步骤；按 Agent Skills 规范（目录含 SKILL.md，frontmatter 核心字段 name/description）自行放置到各自技能目录，**列为未验证**，不得声称已验证支持。

## 二、刷新纪律（防副本漂移）

1. 只改仓库侧文件 → 提交推送（需授权）→ 再复制到各平台副本；
2. 每次刷新后核对副本与仓库一致（MD5 或行数）；
3. 已知漂移实例（2026-10-14）：TRAE 副本曾比仓库少 37 行（旧版缺 R7-R10 等）——人工多副本必然漂移，所以刷新必须作为改动流程的固定收尾步，而不是"想起来再同步"。

## 三、平台差异备忘（实测）

| 平台 | 技能目录 | 发现机制 | 已知限制 |
|---|---|---|---|
| TRAE SOLO CN | `~/.trae-cn/skills/` | 设置中上传/仓库添加，skill-config.json 登记 | 旧版入口为 `.trae/skills` 的说法不准确，本机实际为 `.trae-cn/skills` |
| WorkBuddy | `~/.workbuddy/skills/`（用户级）或 `<工程>/.workbuddy/skills/`（项目级） | 会话启动注入技能清单；插件缓存目录亦加载 | 新装技能要下一会话才进清单；references/ 与随附脚本格式受支持（有实例） |

## 四、脚本与权限边界

- 本技能包只含 Markdown（SKILL.md + references/*.md），无可执行脚本，安装无需提权；
- 若未来扩展加入脚本：遵循最小权限，安装说明中写明脚本作用与触发条件，不静默执行。
