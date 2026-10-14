# SVG 思维导图规范（可选能力）

> 本文件是 complex-task-decompose 的可选能力规范：仅当任务启用图形导图时使用。
> 启用判断：任务跨多轮、叶数多（如 >8）、需要向他人展示全局进度时；简单任务不生成。
> 从 SKILL.md 第七节迁出（2026-10-14 解耦），内容与原规范一致，仅去强制性措辞。

## 位置与命名

- 与任务树同目录，文件名 `任务树导图.svg`，浏览器直接打开
- SVG 是文本文件，每次任务树 .md 落盘时**整体重写**，不做增量修改

## 布局

横向思维导图：左侧根节点（任务名 + 进度 n/N）→ 向右展开 L1 主分支 → L1 下挂 L2 叶节点。
图内只放任务名和状态，检索目录不进图（太长，看 .md）。

## 状态色块（叶节点左侧小方块）

| 状态 | 颜色 |
|------|------|
| ⬜ 未开始 | 灰 `#9E9E9E` |
| 🔶 进行中 | 黄 `#F5A623` |
| ✅ 完成已核对 | 绿 `#34A853` |
| ❌ 有问题待复查 | 红 `#EA4335` |

## 最小结构示例

```svg
<svg xmlns="http://www.w3.org/2000/svg" font-family="Microsoft YaHei, sans-serif">
  <!-- 根节点 -->
  <rect x="20" y="340" width="220" height="56" rx="10" fill="#1a73e8"/>
  <text x="130" y="364" fill="#fff" text-anchor="middle" font-size="17" font-weight="bold">任务名</text>
  <text x="130" y="386" fill="#fff" text-anchor="middle" font-size="12">进度 0/13</text>
  <!-- 连线：根 → L1（贝塞尔） -->
  <path d="M240,368 C280,368 280,108 320,108" stroke="#bbb" fill="none"/>
  <!-- L1 分支节点 -->
  <rect x="320" y="88" width="200" height="40" rx="8" fill="#e8f0fe"/>
  <text x="420" y="113" fill="#174ea6" text-anchor="middle" font-size="15" font-weight="bold">L1 阶段名</text>
  <!-- 叶节点：状态色块 + 文本框 -->
  <rect x="620" y="48" width="14" height="14" fill="#9E9E9E"/>
  <rect x="640" y="44" width="360" height="32" rx="6" fill="#f5f5f5"/>
  <text x="652" y="65" fill="#333" font-size="14">L2 叶任务名</text>
  <!-- 图例（底部） -->
</svg>
```

## 工程建议

- 叶数多且更新频繁时，用脚本从 任务树.md 解析生成 SVG（解析进度行、`- [ ] L1-x.y` 叶行和 `状态:` 字段），比手写可靠；本任务参考实现见 `AI任务管理\通用方法论迭代\gen_svg.py`（任务材料，不随技能包分发）。
- 同步规则：树 .md 落盘即重写 SVG；SVG 中的进度数字以「状态 = ✅」的叶计数，与进度行一致。
