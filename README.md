# TRAE DCS 技能与配置备份（跨设备恢复包）

本仓库是 TRAE（SOLO CN）上沉淀的 DCS 工程方法论备份，用于重装系统、换电脑后一键恢复。

## 仓库内容

| 目录 | 内容 | 恢复到哪里 |
|------|------|------------|
| complex-task-decompose/ | 通用方法论 skill（任务树+检索目录+收割机制） | %USERPROFILE%\.trae-cn\skills\ |
| interlock-analysis/ | 连锁分析 skill（PDF→FBD管脚连接说明） | %USERPROFILE%\.trae-cn\skills\ |
| templates/ | 任务树模板、DCS项目全流程总纲、演示任务树+SVG导图 | 工程根目录 AI任务管理\ |
| config-backup/ | TRAE 用户规则（rule-*.md，含第6条强制任务树）、跨项目记忆 user_profile.md | TRAE 设置→用户规则 / 记忆 |

## 新电脑恢复步骤（按顺序）

1. 安装 TRAE 并登录账号
2. 恢复 skill（二选一）：
   - 方式A：TRAE 设置 → 规则和技能 → 技能仓库 → 添加仓库，粘贴本仓库地址（若你的版本有此入口）
   - 方式B：把 complex-task-decompose 和 interlock-analysis 两个文件夹复制到 C:\Users\<用户名>\.trae-cn\skills\
3. 恢复规则：打开 config-backup\rule-*.md，把内容逐条粘贴到 TRAE 设置 → 用户规则（或放到 .trae-cn\user_rules\）
4. 恢复记忆：把 config-backup\user_profile.md 内容并入 .trae-cn\memory\user_profile.md
5. 模板：把 templates\ 下文件复制到工程根目录 AI任务管理\

## 维护约定

- skill 内容更新时：改本仓库里的文件 → 提交推送 → 再同步到 %USERPROFILE%\.trae-cn\skills\ 和各工作区 .trae\skills\
- 本仓库是唯一源头（single source of truth），其他位置都是副本
