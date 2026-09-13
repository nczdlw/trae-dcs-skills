# TRAE DCS 技能与配置备份（跨设备恢复包）

本仓库是 TRAE（SOLO CN）上沉淀的 DCS 工程方法论备份，用于重装系统、换电脑后恢复。

## 跨设备分工（最终版）

| 内容 | 跨设备方案 | 说明 |
|------|-----------|------|
| 用户规则（含第6条强制任务树） | **TRAE 云端规则** | 跟账号走，登录即生效，无需本仓库恢复 |
| skill（2个） | **本仓库** | GitHub 是唯一源头，恢复见下方步骤 |
| 任务树模板 / DCS全流程总纲 | **本仓库** | templates/ 目录 |
| 跨项目记忆 user_profile | 本仓库 config-backup/ 兜底 | 若 TRAE 记忆有云同步则优先用云端 |

## 仓库内容

| 目录 | 内容 | 恢复到哪里 |
|------|------|------------|
| complex-task-decompose/ | 通用方法论 skill（任务树+检索目录+收割机制） | %USERPROFILE%\.trae-cn\skills\ |
| interlock-analysis/ | 连锁分析 skill（PDF→FBD管脚连接说明） | %USERPROFILE%\.trae-cn\skills\ |
| templates/ | 任务树模板、DCS项目全流程总纲、演示任务树+SVG导图 | 工程根目录 AI任务管理\ |
| config-backup/ | 用户规则、跨项目记忆（**仅离线兜底**：云端规则不可用时才用） | TRAE 设置 / .trae-cn\memory\ |

## 新电脑恢复步骤（按顺序）

1. 安装 TRAE 并登录账号——**云端规则自动生效，无需操作**
2. 恢复 skill（二选一）：
   - 方式A：TRAE 设置 → 规则和技能 → 技能仓库 → 添加仓库，粘贴本仓库地址 https://github.com/nczdlw/trae-dcs-skills （若你的版本有此入口）
   - 方式B：`git clone https://github.com/nczdlw/trae-dcs-skills.git`，把 complex-task-decompose 和 interlock-analysis 两个文件夹复制到 `C:\Users\<用户名>\.trae-cn\skills\`
3. 模板：把 templates\ 下文件复制到工程根目录 `AI任务管理\`
4. 记忆：若 TRAE 记忆未云同步，把 config-backup\user_profile.md 内容并入 `.trae-cn\memory\user_profile.md`
5. 兜底：若云端规则不可用，把 config-backup\rule-*.md 内容逐条粘贴到 TRAE 用户规则

## 维护约定

- **skill 内容更新**：只改本仓库里的文件 → 提交推送 → 再复制到 `%USERPROFILE%\.trae-cn\skills\` 和各工作区 `.trae\skills\`
- **规则更新**：改 TRAE 云端规则为准 → 同步更新本仓库 config-backup\rule-*.md（保持兜底副本一致）
- 本仓库是 skill 与模板的唯一源头（single source of truth），其他位置都是副本，改动方向永远是 仓库 → 副本
