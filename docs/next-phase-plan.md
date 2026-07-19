# 下一阶段优化详细方案（感知 → 编排 → LLM 优化 → 智能体化）

> 定位不变：Web = 复盘+规划指挥室，安卓 = 执行终端。
> 目标：把「神经中枢」接给 LLM 和自动化编排，让系统从"你按了才动"升级为"感知数据 → 主动决策 → 自动行动 → 反馈验证"。

---

## 阶段 1 · 感知层：学习画像汇总（PR 1，最优先）

### 现状问题（对着代码盘点）
- 周计划 `scheduling/ai_week.py::generate_ai_week_plan` 只喂：已排定计划 + 薄弱知识点（`get_problem_insights`）。
- 周复盘 `retro/service.py::_build_context` 喂得更全一点：周统计 + 各科画像 + 薄弱点 + 掌握度缺口，但仍看不到聊天、单词、背诵、作文。
- 聊天（ChatLearning）是最大数据孤岛：你问了很多某科的问题 = 强薄弱信号，但完全不回流。
- 单词/背诵各自 SM-2 闭环，`vocab_stats.due_count`（欠账数）已有现成接口，但周计划不看。

### 设计：`profile/learning_snapshot.py`（新模块）
一个纯聚合函数，不新增表（除聊天打标外，见阶段 3）：

```python
async def build_learning_snapshot(session, week_start) -> LearningSnapshot:
    # 复用已有 service：
    # - get_weekly_stats           → 执行率、计划/实际耗时
    # - get_study_profile          → 各科掌握度/覆盖/预估分
    # - list_mastery_gaps          → 掌握度缺口 TopN
    # - get_problem_insights       → 错题热点、遗忘率
    # - vocab_stats                → due_count（单词欠账）、总进度
    # - recitation_stats           → 背诵到期/进度
    # - essay 最近批改得分          → 作文水平趋势
    # - chat_topics（阶段3落地后）  → 近 7 天聊天高频知识点
```

输出统一为一段结构化中文文本 `snapshot_text()`（沿用 `_context_text` 的风格），插入两处 prompt：
1. `generate_ai_week_plan` 的 user_text（替换现在只有薄弱点那一段）；
2. `retro/_build_context`（补充单词/背诵/作文/聊天四类信号）。

### 验收标准
- 单词欠账 > 阈值时，AI 周计划的 daily_focus / review_suggestions 中能看到词汇相关建议；
- 快照生成 < 500ms（全部是本地 PG 聚合查询）；
- 单测：各模块空数据时快照仍能生成（冷启动不炸）。

### 工作量：小（1 个 PR，纯后端 + prompt 调整，不改前端/安卓）

---

## 阶段 2 · 编排层：定时自动化（PR 2~3）

### 技术选型
- 后端进程内 **APScheduler**（AsyncIOScheduler），FastAPI lifespan 启动/关闭；单实例部署无分布式锁问题。
- 新表 `automation_runs`：`id, job_name, run_at, status(success/failed/skipped), detail JSON` —— 每次执行留痕，静默失败可查。
- 失败重试：每个 job 内部 try/except + 一次重试；连续失败写 `failed` 记录，Web 驾驶舱显示最近自动化状态。

### Job 清单
| job | 触发 | 行为 | 边界 |
|---|---|---|---|
| `weekly_plan_draft` | 周日 21:00 | 若下周无 AiWeekPlan → 调 `generate_ai_week_plan` 生成**草稿**（新增 `status=draft` 字段），不直接生效 | 你在 Web/安卓一键确认后才 persist；避免"替你决定" |
| `daily_mastery_watch` | 每日 06:00 | 扫描 kp_mastery：某知识点连续 2 次打卡后掌握度下降 → 向今日任务插入一条 30min 复习任务（来源标注 auto） | 每日最多插 1~2 条；已有同知识点任务则跳过 |
| `daily_backlog_check` | 每日 06:00 | `vocab_stats.due_count` > 阈值（如 100）或错题到期堆积 → 生成提醒记录（新表或复用 detail），安卓今日页顶部显示 | 只提醒不强改计划 |
| `retro_reminder` | 周日 20:00 | 本周复盘未发起 → 提醒 | |

### 需要的配套改动
- `AiWeekPlan` 加 `status`（draft/confirmed）+ 确认 API；
- 今日任务 API 返回 `source`（manual/scheduled/auto），安卓/Web 用小标签区分自动插入的任务；
- Web 驾驶舱加一张「自动化」卡片：最近 job 运行状态 + 待确认草稿入口。

### 风险与对策
- 容器重启错过定时点 → APScheduler `misfire_grace_time` + 启动时补跑当日未执行 job；
- 自动插任务打乱手排计划 → 只插不删、上限约束、来源可见、可一键撤销。

### 工作量：中（2 个 PR：① 调度框架+weekly_plan_draft；② 每日 watch/backlog + 端上展示）

---

## 阶段 3 · LLM 优化（穿插做，每项独立小 PR）

### 3a. 聊天滚动摘要压缩
- 现状：`chat/service.py` 取最近 20 条硬截断（HISTORY_LIMIT=20）。
- 方案：`chat_conversations` 加 `summary TEXT + summary_upto_message_id`；当历史超 20 条时，异步（对话响应后）让模型把「summary + 被挤出的旧消息」压缩成新 summary；下次请求 payload = system + summary（作为一条 system 补充）+ 最近 20 条。
- 注意：压缩调用用低 reasoning effort + 便宜；失败不影响正常聊天（降级为现状截断）。

### 3b. 聊天主题打标（阶段 1 的数据源）
- 新表 `chat_topic_tags`：`message_id, subject_id, knowledge_point_id?, confidence`。
- 每次 assistant 回复落库后，异步再调一次模型：输入本轮 Q/A + 考纲知识点候选（按科目过滤），输出命中的知识点 JSON。
- `build_learning_snapshot` 聚合近 7 天 tag 频次 → 「聊天高频主题」信号；频次高 + 掌握度低 = 强化建议权重。
- 成本控制：只对含学科内容的消息打标（先规则粗筛：消息长度/含公式/含科目关键词），闲聊跳过。

### 3c. prompt 前缀稳定化 + 成本
- 审查各调用点：system prompt 固定文本放最前、动态数据放 user 消息尾部，尽量吃中转站 prompt caching；
- 保持现有分级：周计划/复盘高 reasoning effort，判题/识题/打标/压缩低档；
- `ai_client` 记录每次调用的 token 用量入库（中转站返回 usage 字段），Web 加一个简单的成本页（可选）。

### 工作量：3a 小、3b 中、3c 小

---

## 阶段 4 · 智能体化：带工具的周计划 Agent（等 1~3 跑稳）

- 复用 PR #83 的 function calling 框架（`ai/client.py` 循环 + 工具注册）。
- 给周计划模型暴露只读工具：`query_mastery_gaps(subject?)`、`query_wrong_problems(kp?)`、`query_backlog()`、`query_recent_chats(subject?)`；写入仍走既有 persist 流程（模型只输出建议 JSON，不直接写库——保守起步）。
- 收益：模型自己决定"要看什么数据"，不再受快照篇幅限制；代价：慢（多轮）、贵。所以先用阶段 1 的静态快照验证信号价值，确认哪些数据真的影响计划质量，再上 agent。
- 判断标准：如果静态快照已让计划质量满意，阶段 4 可以无限期推迟。

---

## 独立小项（可随时插队）
1. **PDF 阅读行为埋点**：安卓阅读器上报「文件+页码+停留时长」，补上"看教材"类任务的真实投入盲区；数据进 snapshot。
2. **papers 页搜索/分组**：Web 英语阅读训练列表加搜索框 + 按年份/来源折叠（纯前端，体验债）。
3. **驾驶舱图表继续强化**：掌握度变化曲线（需要 kp_mastery 历史快照表——目前只存当前值，改动别忽视）。

## 建议执行顺序
```
PR1  阶段1 学习画像快照（含 vocab/recitation/essay 信号，聊天信号留接口）   ✅ #85 已合并
PR2  阶段2 APScheduler 框架 + weekly_plan_draft + automation_runs          ✅ #86 已合并
PR3  阶段2 daily watch/backlog + 端上自动化展示                            ✅ #87 已合并
PR4  阶段3b 聊天打标（回填阶段1的聊天信号）                                ✅ #88 已合并
PR5  阶段3a 滚动摘要压缩                                                   ⏳ 待做
随时 阶段3c / 独立小项
之后 评估是否需要阶段4 agent 化
```
每个 PR 合并后照旧部署服务器实测；涉及安卓的（自动任务标签、提醒）需重装 APK。
