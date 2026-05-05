# LLM Service Runtime Vision

更新时间: 2026-05-04

## 1. 目标

Rosetta 后续应把每一次大模型调用都视为一次可排队、可限流、可追踪、可计费、可复现的服务调用，而不是在 workflow 中直接调用 provider 函数。

这条设计的目标很明确：

1. 每个平台都有自己的参数、限流、默认模型、token 统计和成本估算。
2. 所有 workflow 共用同一套 LLM service runtime，不再各自实现并发、重试和日志。
3. 概念验证、prompt 优化、自举循环、批量标注、LLM-as-a-judge、语料生成都能显示清晰进度。
4. 用户能看到当前做到哪一步、还剩多少、预计多久结束、用了多少 token、花了多少钱。
5. 开发者能从 runtime store 和 artifacts 复现每一次模型调用。

当前文档既是愿景与设计契约，也记录 `v4.5.2` 的最小实现边界：`app/infrastructure/llm/runtime.py` 已提供 `LLMServiceRuntime`、`LLMProviderProfile`、provider 级共享 semaphore、重试、内存进度事件、token 估算和耗时统计；`app/runtime/progress.py` 已提供 `ProgressRecorder`，并把提示词优化训练的阶段事件与 provider call 事件写入 SQLite `run_progress_events`。定义与规范的提示词优化训练已经通过后台线程和 SQLite 轮询显示实时进度；批量标注的任务队列仍在逐步迁移到同一事件层。

## 2. 核心原则

### 2.1 大模型调用是服务，不是函数

每次调用都应被包装成 `LLMCall`：

```text
LLMCall
  -> provider profile
  -> model config
  -> request payload
  -> queue policy
  -> retry policy
  -> token/cost accounting
  -> progress event
  -> response artifact
```

workflow 只能提交调用请求并消费结果，不应该直接关心 HTTP 细节、限流策略、token 估算或重试。

### 2.2 平台参数必须显式

每个平台都应有自己的 `LLMProviderProfile`。至少包含：

1. `provider_id`: 例如 `deepseek`、`kimi`、`bigmodel`、`qwen`。
2. `display_name`: UI 展示名。
3. `default_model`: 默认模型，例如 `deepseek-v4-pro`。
4. `max_concurrency`: 平台允许的最大并发。
5. `default_concurrency`: 用户不设置时的默认并发。
6. `requests_per_minute`: 每分钟请求上限，如果未知则为空。
7. `tokens_per_minute`: 每分钟 token 上限，如果未知则为空。
8. `timeout_seconds`: 单次调用超时。
9. `max_retries`: 失败重试次数。
10. `retry_backoff_seconds`: 退避策略。
11. `supports_streaming`: 是否支持流式响应。
12. `supports_json_mode`: 是否支持 JSON mode 或结构化输出。
13. `cost_table`: 输入、输出、缓存 token 的价格。
14. `token_counter`: provider 返回 usage 时优先使用 provider usage；否则使用本地估算器。

平台 profile 是系统默认能力边界；workflow 不能绕过它单独设无限并发。

### 2.3 默认并发上限为 50

Rosetta 的全局默认策略：

```text
global_default_max_concurrency = 50
```

含义：

1. 默认情况下，任何单个 provider 的并发上限不超过 50。
2. UI 可以允许用户选择并发，但最大值应受 provider profile 与全局上限共同限制。
3. 如果某个平台明确限流更低，则使用更低值。
4. 这里的 `50` 是 Rosetta 默认上限，不是绕过平台限流；rate limit 由 provider profile、重试和退避策略处理。
5. 同一 provider 下多个 workflow 同时运行时，应共享 provider 级 semaphore，避免多个页面叠加后实际并发超过上限。

推荐默认值：

| 场景 | 默认并发 | 上限 |
| --- | --- | --- |
| 概念验证 15 条金样例 | 50 | 50 |
| Prompt training 三方法验证 | 50 | 50 |
| 概念自举候选评估 | 50 | 50 |
| 批量标注真实 API | 50 | 50 |
| 批量标注本地 mock | 50 | 50 |
| LLM-as-a-judge | 50 | 50 |
| 语料生成 | 50 | 50 |

这里的上限是产品默认，不是所有平台实际都能承受。实现时必须允许平台 profile 覆盖。

## 3. 统一调用生命周期

每次 LLM 调用都应经过以下状态：

```text
created
  -> queued
  -> running
  -> succeeded
  -> failed
  -> retried
  -> cancelled
```

每个状态变化都写入 progress event。最小事件集合：

| 事件 | 含义 |
| --- | --- |
| `run_started` | workflow run 开始 |
| `call_queued` | 单次模型调用入队 |
| `call_started` | 单次模型调用开始 |
| `call_succeeded` | 单次模型调用成功 |
| `call_failed` | 单次模型调用失败 |
| `call_retried` | 单次模型调用重试 |
| `item_scored` | 样本或候选已评分 |
| `candidate_generated` | prompt 候选已生成 |
| `candidate_evaluated` | prompt 候选已完成 gold loss 验证 |
| `item_routed` | 样本进入自动通过或审核与修正 |
| `run_completed` | workflow run 完成 |
| `run_cancelled` | 用户取消 |

事件字段建议：

```json
{
  "run_id": "run-...",
  "workflow": "concept_bootstrap",
  "event_type": "call_succeeded",
  "provider": "deepseek",
  "model": "deepseek-v4-pro",
  "item_id": "gold-00001",
  "stage": "gold_validation",
  "completed": 8,
  "total": 15,
  "running": 5,
  "queued": 2,
  "failed": 0,
  "retry_count": 0,
  "elapsed_seconds": 34.2,
  "estimated_remaining_seconds": 29.8,
  "eta_confidence": "medium",
  "prompt_tokens": 1200,
  "completion_tokens": 180,
  "cost_cny": 0.004,
  "message": "已完成第 8 / 15 条金样例验证"
}
```

## 4. Workflow 中的并发策略

### 4.1 概念验证

当前问题：概念验证 15 条金样例串行执行，真实 API 会明显等待。

目标行为：

1. 用户点击“验证概念”后，系统创建 `WorkflowRun`。
2. 15 条金样例转换成 15 个 `LLMCall`。
3. 调度器按 provider profile 并发执行，默认并发 50，上限 50。
4. 每条样例完成后立刻更新进度、通过/失败/不稳定数量和 ETA。
5. 全部完成后写入 `Prediction`、`ConceptVersion` 和验证摘要。

UI 应显示：

1. 当前阶段：`正在验证 15 条金样例`。
2. 进度条：`8 / 15`。
3. 当前并发：例如 `50 个调用运行中`。
4. 预计剩余时间：例如 `约 30 秒`。
5. 已用 token / 估算成本。
6. 失败重试提示。

### 4.2 概念自举循环

概念自举不是一个简单列表，而是嵌套循环：

```text
round
  -> evaluate current prompt on 15 gold examples
  -> estimate text gradients
  -> generate N candidate prompts
  -> evaluate each candidate on 15 gold examples
  -> accept/reject
```

如果粗暴并发，实际调用数会快速膨胀。调度器必须使用共享 provider semaphore，保证任意时刻真实 API 调用不超过上限。

推荐执行策略：

1. 当前 prompt 的 15 条 gold validation 可以并发。
2. 候选 prompt 生成通常只有 1-5 次，可以并发或串行，取决于 provider profile。
3. 候选评估可以并发，但所有候选共享同一 provider semaphore。
4. 每轮结束后更新 round 级进度、loss、loss delta、接受候选和下一轮 ETA。
5. 如果某轮无候选改善 loss，应尽快停止，不继续消耗 API。

UI 应显示两层进度：

1. 总进度：`第 2 / 5 轮`。
2. 当前阶段：`正在评估候选 2 / 3 的金样例表现`。
3. 当前阶段进度：`11 / 15`。
4. 本轮已用 token / 成本。
5. 总 token / 成本。
6. 预计剩余时间。
7. 当前最优 loss 和候选 loss。

### 4.3 批量标注

批量标注已经有本地线程池，但应迁移到统一 LLM service runtime：

1. 用户上传 TXT / JSONL / CSV 后，系统生成 `BatchJob`。
2. 每个 job item 会生成 `sample_count` 次 LLM call。
3. 调度器按 provider profile 控制并发，真实 API 默认并发 50。
4. 每个 item 的多个候选完成后，立即计算自洽性、模型自评、规则风险和路由结果。
5. 高置信进入自动通过池，低置信进入审核与修正。

UI 应避免变成后台管理表格，而是展示足够直接的运行状态：

```text
总数 1000
已完成 230
运行中 10
待处理 760
失败 0
待审核 41
吞吐 18.4 条/分钟
预计剩余 41 分钟
已用 120 万 tokens
估算成本 0.62 元
```

### 4.4 Prompt 优化与 Text Gradient

Prompt-as-Parameter 的每次扰动、候选生成和验证都应被拆成可视化步骤：

1. `segment_prompt`: 已切分哪些片段。
2. `estimate_gradient`: 哪些片段影响度最高。
3. `generate_candidate`: 生成了几个候选。
4. `evaluate_candidate`: 每个候选的 gold loss。
5. `select_candidate`: 是否接受。
6. `write_trace`: 写入 `PromptOptimizationTrace`。

UI 不应只显示最终 prompt，而应允许用户展开“优化过程”：

| 字段 | 展示 |
| --- | --- |
| 片段 | `boundary_rules` |
| 梯度方向 | `expand_recall_boundary` |
| 当前 loss | `42.5` |
| 候选 loss | `28.1` |
| loss delta | `14.4` |
| 长度变化 | `+86 chars` |
| 是否接受 | `accepted` |

## 5. ETA 计算

ETA 不需要一开始很精确，但必须持续更新，并标记可信度。

推荐第一版公式：

```text
avg_seconds_per_completed_call = elapsed_seconds / completed_calls
remaining_seconds = remaining_calls / max(1, effective_throughput)
effective_throughput = completed_calls / elapsed_seconds
```

后续可以加入更稳定的滑动窗口：

```text
recent_throughput = completed_calls_in_last_60s / 60
eta = remaining_calls / recent_throughput
```

ETA 可信度：

| 可信度 | 条件 |
| --- | --- |
| low | 完成调用少于 3 次 |
| medium | 完成调用不少于 3 次，但最近有重试或限流 |
| high | 完成调用不少于 10 次，最近无重试 |

UI 文案应避免假装精确：

1. `预计剩余约 2 分钟`。
2. `预计剩余约 40 秒，当前估算可信度较低`。
3. `等待 provider 限流恢复，ETA 暂不稳定`。

## 6. Token 与成本统计

每次模型调用都应记录 `TokenUsage`：

```json
{
  "run_id": "run-...",
  "call_id": "call-...",
  "provider": "deepseek",
  "model": "deepseek-v4-pro",
  "prompt_tokens": 1200,
  "completion_tokens": 180,
  "total_tokens": 1380,
  "cached_tokens": 0,
  "estimated": false,
  "cost_cny": 0.004,
  "cost_usd": 0.0006
}
```

统计规则：

1. provider 返回 usage 时，优先使用真实 usage。
2. provider 不返回 usage 时，用本地估算器，并设置 `estimated=true`。
3. cost 由 provider profile 的价格表计算。
4. 所有报告必须区分真实 usage 和估算 usage。
5. 导出页应能按 project、run、workflow、provider、model 聚合。

## 7. UI 进度显示规范

所有长任务按钮必须满足：

1. 点击后立即进入 disabled 状态。
2. 文案变为“正在处理...”或具体阶段名。
3. 鼠标 hover 不应表现为可点击。
4. 如果任务支持后台运行，用户可以离开页面。
5. 如果任务必须前台等待，页面应显示进度条、当前阶段、ETA 和失败重试。

推荐组件：

1. `RunProgressCard`: 总进度、状态、ETA、token/cost。
2. `StageProgressList`: 分阶段进度，例如 `验证金样例 / 生成候选 / 候选评估 / 写入版本`。
3. `ProviderStatusBadge`: provider、model、当前并发、限流状态。
4. `TokenCostMeter`: token、费用、是否估算。
5. `EventLogExpander`: 详细事件日志，仅在展开时显示。

`v4.5.2` 的定义与规范已落地第一版 UI：

1. 点击“开始优化训练”后创建 `WorkflowRun(status=running)`，按钮进入禁用运行态。
2. 后台 daemon thread 重新创建 `RuntimeStore` 与 `LLMServiceRuntime`，不共享 Streamlit 上下文。
3. 页面每 2 秒轮询 `run_progress_events`，展示状态、阶段、进度条、ETA、已完成调用、运行中调用、token、重试、修复次数和当前最佳方法。
4. 最近事件、候选评估事件、provider 调用事件和错误事件统一放入折叠区，并支持下载 `run_events.jsonl`。
5. 超过 120 秒没有 heartbeat 的 running run 会被 UI 标记为“可能中断”，但第一版还不提供 pause/resume/cancel。

UI 默认只展示用户需要知道的状态，不把 raw prompt、raw response、trace 全部铺开。详细 trace 放进折叠日志。

## 8. Runtime Store 契约

后续 runtime store 至少需要支持：

1. `llm_calls`: 单次 LLM 调用记录。
2. `llm_call_events`: 调用状态事件。
3. `token_usage`: token 与成本。
4. `run_progress_events`: workflow 级进度事件；`v4.5.2` 已在 SQLite runtime store 中实现，字段为 `id / run_id / workflow / event_type / stage / message / progress / completed / total / running / failed / payload / created_at`。
5. `provider_profiles`: 平台参数快照。
6. `run_manifests`: 每次运行的配置、输入、输出和 artifact。

如果第一阶段不新增表，也必须把这些信息写进现有 `runs / artifacts / job_events / metadata`，并保持字段结构稳定，方便后续迁移到正式表。

## 9. 错误、重试与限流

LLM service runtime 应把错误分层：

| 错误类型 | 处理 |
| --- | --- |
| `rate_limited` | 指数退避，更新 provider 状态和 ETA |
| `timeout` | 重试，超过次数后标记 item failed |
| `invalid_json` | 调用 JSON repair 或重新请求 |
| `provider_error` | 记录 raw error，可重试 |
| `user_cancelled` | 停止排队任务，运行中任务尽量等待返回 |
| `budget_exceeded` | 停止新调用，提示用户调整预算 |

所有错误都必须能在 UI 中被用户理解：

1. “平台限流，正在等待重试。”
2. “第 7 条样例返回格式错误，已尝试修复。”
3. “本轮预算已用完，剩余任务暂停。”

## 10. 分阶段落地

### v4.4: Provider Profiles 与 Runtime 边界

1. 定义 `LLMProviderProfile`。
2. 将 DeepSeek / Kimi / BigModel / Qwen 的默认模型、并发、超时、重试、价格表写入配置。
3. 建立 `LLMCall` 与 `TokenUsage` 数据契约。
4. 保持现有 UI 行为不大改。

### v4.5: Bounded Scheduler 与并发统一

1. 已新增 provider 级 semaphore 和 `LLMServiceRuntime` 最小实现。
2. 提示词优化训练的 gold validation、候选回测和方法对比已走 runtime-backed predictor；批量标注默认并发已调到 50，后续继续把 provider 调用完全迁入 runtime。
3. 默认并发上限改为 50。
4. 已支持失败重试和 progress event；pause / resume / cancel 仍是后续任务。

### v4.6: 进度、ETA、Token/Cost UI

1. 新增 `RunProgressEvent`。
2. 定义与规范显示自举轮次、当前阶段、ETA、并发、token/cost。
3. 批量页显示实时吞吐、失败、待审核、预计剩余。
4. 导出页增加 `usage_report.csv` 和 `usage_report.md`。

### v4.8: 全电路测试

1. mock LLM 固定延迟，测试 ETA 和并发上限。
2. mock provider 返回 usage，测试 token/cost 聚合。
3. 模拟 rate limit 和 timeout，测试重试与 UI 事件。
4. 真实 API 小样本 smoke：10 条语料、采样 1、并发 1。

## 11. 验收标准

实现完成后，至少满足：

1. 概念验证 15 条金样例不再串行，默认并发 50，上限 50。
2. 批量标注真实 API 默认并发 50，并受 provider profile 限制。
3. 同一 provider 多个 workflow 并发时，总调用数不超过 provider 上限。
4. 概念自举每轮能显示阶段、已完成、总数、ETA、token/cost。
5. 批量标注能显示吞吐、预计剩余、失败、待审核、成本。
6. 每次 LLM 调用都有可回放 trace、raw response、usage 和错误信息。
7. 用户可以在 UI 中判断任务是否还在运行、是否卡在限流、是否值得取消。

## 12. 非目标

当前阶段不要求：

1. 引入 Celery / Redis / FastAPI / React。
2. 将 Streamlit 替换成新前端。
3. 实现跨机器分布式调度。
4. 对所有 provider 做完全准确的 token 计算。
5. 一次性完成所有平台的价格表。

第一版仍应保持本地优先：SQLite checkpoint、本地线程池、provider profile 和清晰 UI 进度已经足够支撑 Rosetta 的核心工作流。
