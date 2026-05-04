# Agent Onboarding

更新时间: 2026-05-04

本文件是给后续大模型、代码 agent 和新维护者的快速上下文包。目标是在 5 分钟内理解 Rosetta 当前是什么、服务怎么跑、代码改哪里、不能踩哪些坑。

如果你是自动化 agent，先读根目录 [AGENTS.md](../../AGENTS.md) 的硬性执行约束，再读本文件。需要深入时再跳到 [Architecture](./ARCHITECTURE.md)、[LLM Service Runtime](./LLM_SERVICE_RUNTIME.md)、[Concept Bootstrap Pipeline](./BOOTSTRAP_PIPELINE.md) 和 [Workflow](./WORKFLOW.md)。

## 1. 一句话理解

Rosetta 是基于 Streamlit 的本地优先 Agentic Annotation Tool。它不是普通“上传文本调一次大模型”的工具，而是把一句话概念描述和 15 条金样例训练成可执行、可审计、可导出的标注流水线。

主流程：

```text
工作台
  -> 概念实验室
  -> 15 条金样例校准 / Prompt Training
  -> 批量标注
  -> 主动审核
  -> 导出与实验报告
```

当前研究主张：

```text
LLM agent 在低资源、概念可描述、边界会变化或任务不够常规的标注场景中，
应比 PLM-first 流程更快形成可用数据，并保留概念版本、候选分歧、人工审核和成本轨迹。
```

不要把它写成“LLM 在所有条件下无条件超过 PLM”。full-data PLM 是强上界，Rosetta 主要要赢 low-budget、快速定义、概念漂移和人机协作标注场景。

## 2. 当前服务是怎么实现的

Rosetta 目前不是 FastAPI / React / Celery / Redis 系统。当前整体服务是一个本地单机服务化架构：

```text
Streamlit UI
  -> app/workflows/*
  -> app/agents / app/data / app/runtime / app/infrastructure
  -> SQLite runtime store + runtime artifacts
  -> LLM provider APIs
```

### 2.1 UI 服务

入口是 [streamlit_app.py](../../streamlit_app.py)。它加载 5 个主页面：

1. [Home.py](../../app/ui/pages/Home.py)：工作台，显示项目状态和入口。
2. [Concept_Lab.py](../../app/ui/pages/Concept_Lab.py)：概念实验室，维护概念阐释、15 条金样例、概念自举和 prompt training。
3. [Batch_Run.py](../../app/ui/pages/Batch_Run.py)：批量标注，导入 TXT / JSONL / CSV，提交本地任务。
4. [Review_Queue.py](../../app/ui/pages/Review_Queue.py)：审核队列，逐条处理低置信、低自洽或抽检样本。
5. [Export_View.py](../../app/ui/pages/Export_View.py)：导出与可视化，输出 JSONL、报告和统计。

UI 只应该做输入、展示和调用 workflow。不要把复杂业务规则写进 Streamlit 页面。

### 2.2 Workflow 服务

用户可执行逻辑集中在 [app/workflows](../../app/workflows)：

| 目录 | 职责 |
| --- | --- |
| `app/workflows/bootstrap` | 概念阐释、金样例、概念自举、Prompt-as-Parameter、三方法 prompt training |
| `app/workflows/annotation` | 单条/批量标注、上下文构建、候选预测、SQLite job queue |
| `app/workflows/review` | 审核队列、候选选择、hard example、promote-to-gold |
| `app/workflows/evaluation` | 统计、报告、导出视图聚合 |
| `app/workflows/corpus` | corpus builder 兼容 workflow |

新增用户行为时，默认先放进 workflow，再让 UI 调 workflow。

### 2.3 LLM 服务运行时

LLM 调用服务化入口是 [app/infrastructure/llm/runtime.py](../../app/infrastructure/llm/runtime.py)。

核心对象：

1. `LLMProviderProfile`：记录 provider、model、默认并发、最大并发、超时、重试和价格信息。
2. `LLMServiceRuntime`：提供 `chat()`、`map_chat()`、provider 级共享 semaphore、重试、progress events、token 估算和耗时统计。
3. `LLMCallResult`：记录每次调用的 provider、model、tokens、耗时、retry 和 metadata。

当前默认：

| 项 | 值 |
| --- | --- |
| 默认 provider | `deepseek` |
| 默认真实模型 | `deepseek-v4-pro` |
| 默认并发上限 | `20` |
| usage | provider 未返回 usage 时用字符比例估算，并标记 `estimated=true` |

注意：并发 `20` 是本地 runtime 上限，不是绕过平台限流。所有真实 API 调用应该共享 provider semaphore。

### 2.4 存储服务

本地事实来源是 [app/runtime/store.py](../../app/runtime/store.py) 的 SQLite store。

默认路径：

| 场景 | 路径 |
| --- | --- |
| 本地 | `.runtime/rosetta.sqlite3` |
| Docker | `/opt/rosetta/runtime/rosetta.sqlite3` |
| 隔离实验 | `.runtime/experiments/.../runtime/rosetta.sqlite3` |

关键表：

```text
projects
tasks
predictions
reviews
runs
artifacts
agent_steps
concept_guidelines
gold_example_sets
concept_versions
jobs
job_items
job_events
```

大文件、完整 trace 和报告通常写到 runtime artifacts，不要把大模型原始响应塞进 UI state。

### 2.5 CLI 服务

统一 CLI 是 [scripts/tool/rosetta_tool.py](../../scripts/tool/rosetta_tool.py)。当前重要命令：

```bash
conda run -n rosetta-dev python scripts/tool/rosetta_tool.py prompt-training-experiment \
  --case hard-science \
  --provider deepseek \
  --model deepseek-v4-pro \
  --concurrency 20 \
  --candidate-count 3 \
  --patience-rounds 5 \
  --max-rounds 30 \
  --output-dir .runtime/experiments/prompt_training_hard_science \
  --record
```

它会在隔离 runtime 目录里跑三方法真实对比实验，并输出：

```text
comparison_report.md
comparison_result.json
prompt_evolution.jsonl
```

## 3. 核心算法电路

### 3.1 概念自举

概念实验室保存：

1. `ConceptGuideline`：概念阐释、标签、边界规则、负例规则、输出格式。
2. `GoldExampleSet`：目标 15 条金样例。
3. `ConceptVersion`：每轮候选、loss、失败摘要、是否接受、最终干净提示词。

自举原则：

```text
当前提示词
  -> 标注 15 条 gold
  -> 计算 gold loss
  -> 生成候选提示词
  -> 净化候选
  -> 防背答案检查 / 去语料化修复
  -> 回测 15 条 gold
  -> 只接受 loss 下降的候选
```

最终 `ConceptVersion.description` 只能保存干净 operational prompt。失败样例编号、漏标、多标、raw response 和诊断解释只能进 metadata 或 artifact。

### 3.2 Prompt Training 三方法

文件：[app/workflows/bootstrap/prompt_training.py](../../app/workflows/bootstrap/prompt_training.py)。

三种方法：

| 方法 | 给模型什么 | 用途 |
| --- | --- | --- |
| `llm_optimize_only` | 只给当前提示词，要求“优化提示词” | 最弱 baseline |
| `llm_reflection` | 给当前提示词 + 批改参考 + 失败摘要 | 普通 LLM 反思 baseline |
| `text_gradient_adamw` | 给当前提示词 + 批改参考 + 文本梯度 + 长度惩罚方向 | Rosetta 方法候选 |

停止口径：

1. 达到 `15/15` 立即 `reached_target`。
2. 否则连续 `5` 轮 loss 无下降时 `no_loss_improvement_patience`。
3. 默认最多 `30` 轮，达到上限则 `max_rounds`。

重要细节：method result 中的 `best_loss / best_pass_count / best_description / best_round_index` 使用历史最优接受版本，不使用最后一轮快照。真实 LLM 即使 temperature 为 0 也可能有波动。

最近一次真实 DeepSeek 硬科学实验结论：

| 方法 | 历史最佳 | 最佳 loss | 最佳轮次 | 停止原因 |
| --- | ---: | ---: | ---: | --- |
| `llm_optimize_only` | 9/15 | 46.3289 | 12 | `max_rounds` |
| `llm_reflection` | 7/15 | 86.6844 | 5 | `no_loss_improvement_patience` |
| `text_gradient_adamw` | 10/15 | 41.9069 | 6 | `max_rounds` |

这说明当前方法还不能稳定通过 15 gold，但 `text_gradient_adamw` 在该实验中历史最优最好。不要把这写成泛化结论。

### 3.3 防背答案与去语料化

文件：[app/workflows/bootstrap/memorization.py](../../app/workflows/bootstrap/memorization.py)。

训练反馈可以包含原文、标准答案和模型自己的错误回答，因为它是“批改参考”。但 learned operational prompt 不能复制：

1. gold 原文。
2. gold span。
3. runtime annotation。
4. model span。
5. 可识别答案片段或样例编号。

如果候选泄露，不是立刻拒绝，而是先进入 `repair_leaked_prompt()`，要求模型删除具体词和答案片段，只保留抽象规则。修复后仍泄露才拒绝。

## 4. 批量标注与审核电路

批量标注的目标不是页面停留等待，而是本地任务队列：

```text
TXT / JSONL / CSV
  -> ingestion
  -> sentence split / tokenize
  -> AnnotationTask
  -> BatchJob / BatchJobItem
  -> k Prediction
  -> consistency / confidence / rule risk
  -> auto_accepted 或 needs_review
```

当前不引入 Celery / Redis。第一版是 SQLite checkpoint + 本地线程池。长任务需要 busy guard 和进度显示。

审核页应保持“一条一条蹦出”的卡片体验：

```text
ReviewTask
  -> 候选选择 / 轻量编辑
  -> error_type / hard_example / promote_to_gold
  -> reviews
  -> feedback pool
```

导出仍以 Prodigy-compatible JSONL 为主。

## 5. 目录速查

| 你要改什么 | 去哪里 |
| --- | --- |
| 页面标题、按钮、表单、语言 | `app/ui/pages/*`、`app/ui/i18n.py` |
| 概念自举、prompt training | `app/workflows/bootstrap/*` |
| 批量标注、任务队列 | `app/workflows/annotation/*` |
| 审核队列 | `app/workflows/review/*` |
| 导出、统计、报告 | `app/workflows/evaluation/*`、`app/data/*` |
| 领域模型 | `app/core/models.py` |
| SQLite store | `app/runtime/store.py` |
| LLM provider/runtime | `app/infrastructure/llm/*` |
| CLI | `scripts/tool/rosetta_tool.py` |
| 用户教程 | `docs/user/TUTORIAL.md` |
| 架构/开发文档 | `docs/developer/*` |

## 6. 不要踩的坑

1. 不要把 `app/research` 或 `app/corpusgen` 当新产品边界；它们是 legacy compatibility。
2. 不要在 UI 页面里实现复杂业务逻辑；页面只调 workflow。
3. 不要推翻 Prodigy-compatible JSONL；只能增强 project/run/session/job 层。
4. 不要让最终提示词包含 gold 原文、答案片段、样例编号或失败摘要。
5. 不要把失败详情拼进 `ConceptVersion.description`；它只能进 metadata/artifact。
6. 不要把真实 API 并发绕过 `LLMServiceRuntime`。
7. 不要声称 15 gold 训练结果证明 held-out 泛化。
8. 不要引入 React / FastAPI / Celery / Redis，除非用户明确要求进入下一架构阶段。

## 7. 常用验证命令

```bash
conda run -n rosetta-dev python -m compileall app streamlit_app.py scripts/tool/rosetta_tool.py
conda run -n rosetta-dev python -m unittest discover -s tests -p 'test_*.py'
for f in $(find scripts -type f -name '*.sh'); do bash -n "$f"; done
conda run -n rosetta-dev mkdocs build --strict --clean
git diff --check
```

## 8. 接手任务时的最短路径

1. 读 [AGENTS.md](../../AGENTS.md)，确认执行规则。
2. 读本文件，建立项目地图。
3. 根据任务类型跳到对应文档：
   - UI：读 [用户教程](../user/TUTORIAL.md)。
   - 架构：读 [Architecture](./ARCHITECTURE.md)。
   - LLM 并发/服务：读 [LLM Service Runtime](./LLM_SERVICE_RUNTIME.md)。
   - 概念训练：读 [Concept Bootstrap Pipeline](./BOOTSTRAP_PIPELINE.md)。
   - 研究表述：读 [Research Claims](../ideas/RESEARCH_CLAIMS.md)。
4. 改代码前先定位 workflow；除非纯展示，不要直接从 UI 开始写业务逻辑。
5. 改完同步 [CHANGELOG.md](../CHANGELOG.md)，跑最小验证。
