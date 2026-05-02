# Architecture (Developer)

更新时间: 2026-05-03

## 1. 目标定位

Rosetta 是一个基于 Streamlit 的本地优先 Agentic Annotation Tool。

当前架构不再把 `research` / `corpusgen` 作为产品边界。它们只作为历史兼容层保留；新功能应进入 `core / workflows / agents / data / runtime`。

架构必须服务一个研究主张：Rosetta 通过 agentic concept bootstrap，在低资源、概念可描述、任务边界会变化或任务不够常规的场景中，提供比 PLM-first 标注流程更高的样本效率、可审计性和迭代速度。这个主张的边界见 [Research Claims](../ideas/RESEARCH_CLAIMS.md)。

核心目标：

1. Streamlit 是唯一正式 UI 基石。
2. 标注任务、预测、复核、运行记录有统一领域模型。
3. LLM 标注、检索、judge、JSON repair、批量任务和导出通过 workflow / agent tools 编排。
4. 长期标注格式保持 Prodigy-compatible JSONL。
5. Docker 部署稳定，运行数据统一挂载到 `/opt/rosetta/runtime`。

## 2. 代码结构

```text
rosetta/
  streamlit_app.py
  app/
    ui/                  # Streamlit 页面和组件
    core/                # Project / AnnotationTask / Prediction / ReviewTask / WorkflowRun / AgentStep
    workflows/           # 用户可执行流程
      annotation/
      bootstrap/
      corpus/
      evaluation/
    agents/              # AgentKernel / ToolRegistry / ContextEngine / Skill
    data/                # Prodigy JSONL / Label Studio edge adapter
    runtime/             # RuntimePaths / SQLite RuntimeStore
    infrastructure/      # LLM provider / config / debug
    services/            # 旧 UI flow service 兼容层，逐步变薄
    domain/              # 旧概念数据校验和 inline annotation parser
    research/            # legacy compatibility
    corpusgen/           # legacy compatibility
  scripts/
    tool/rosetta_tool.py # 新统一 CLI
    research/            # legacy entrypoints
    corpusgen/           # legacy entrypoints
    deploy/
    ops/
    data/
```

## 3. 分层职责

| 层 | 职责 | 规则 |
| --- | --- | --- |
| `app/ui` | 页面、组件、展示状态 | 不实现复杂业务规则 |
| `app/core` | 稳定领域模型 | 不依赖 Streamlit、不依赖 LLM provider |
| `app/workflows` | 用户可执行流程 | 新功能优先进入这里 |
| `app/agents` | agent kernel、tool registry、context engine | 不直接读写 UI state |
| `app/data` | 标注格式与外部格式桥接 | Prodigy JSONL 是主格式 |
| `app/runtime` | 本地路径、SQLite store、artifact/run/trace | 运行数据进入 `.runtime` 或 `/opt/rosetta/runtime` |
| `app/infrastructure` | LLM、embedding、config、debug | provider 可插拔 |
| `app/services` | 旧页面 flow 兼容入口 | 逐步收敛为 UI controller |
| `app/research`, `app/corpusgen` | 旧实现 | 不再作为新架构边界 |

## 3.1 主数据流

```text
ConceptGuideline + GoldExampleSet
  -> bootstrap workflow
  -> ConceptVersion + failure memory
  -> annotation context builder
  -> k Prediction per AnnotationTask
  -> consistency / confidence / rule risk
  -> ReviewTask or auto-accepted task
  -> export / report / experiment comparison
```

这个流向是后续开发的硬约束。任何新功能如果不能说明自己处于这条链路的哪一段，就应该先写设计文档再实现。

## 3.2 User / Developer 双视角

用户看到的是 5 个页面：

```text
工作台 -> 概念实验室 -> 批量标注 -> 审核队列 -> 导出与可视化
```

开发者维护的是 5 类能力：

```text
core models -> workflows -> agents/tools -> data formats -> runtime store
```

两者的对应关系：

| 用户页面 | 主要 workflow | 主要数据 |
| --- | --- | --- |
| 概念实验室 | `app/workflows/bootstrap` | `ConceptGuideline / GoldExampleSet / ConceptVersion` |
| 批量标注 | `app/workflows/annotation` | `AnnotationTask / Prediction / BatchJob` |
| 审核队列 | `app/workflows/review` | `ReviewTask / hard examples / gold-like feedback` |
| 导出与可视化 | `app/workflows/evaluation`、`app/data` | JSONL exports / report / manifest |

## 4. 核心数据模型

1. `Project`: 标注项目，包含 schema、labels、guidelines、metadata。
2. `AnnotationTask`: Prodigy-compatible task，支持 `text/tokens/spans/relations/label/options/accept/answer/meta`。
3. `Prediction`: LLM 或规则生成的候选标注，类似 Label Studio pre-annotation。
4. `ReviewTask`: 面向人类专家的选择题/修正题。
5. `WorkflowRun`: bootstrap、annotation、corpus、evaluation 等运行记录。
6. `AgentStep`: 每一步 tool 调用、检索、judge、repair 的 trace。
7. `ConceptGuideline / GoldExampleSet / ConceptVersion`: 概念阐释、金样例库和修订历史。
8. `PromptOptimizationTrace`: Prompt-as-Parameter 自举过程中的文本梯度、候选 loss、长度变化和接受/拒绝轨迹。
9. `BatchJob / BatchJobItem`: 本地批量标注队列与 checkpoint。

这些模型还承担实验记录职责：

1. `ConceptVersion.metadata` 必须能复现每轮概念修订、loss、失败样例、文本梯度、长度惩罚和候选选择。
2. `Prediction.meta` 必须能复现每次采样、上下文样例、解析风险和自洽性。
3. `ReviewTask.meta` 必须能复现人类选择、错误类型、疑难样例和 gold-like 晋升。
4. `WorkflowRun / AgentStep` 必须能复现模型调用、工具调用、失败修复和成本信息。

## 5. Agent 执行模型

`AgentKernel.run(goal, context, tools, policy)` 是新 workflow 的统一执行入口：

1. `AgentPolicy`: 模型、温度、多次采样、重试、人工确认策略。
2. `ToolRegistry`: 注册并调用 `annotate_text`、`retrieve_examples`、`judge_prediction`、`repair_json`、`export_jsonl` 等工具。
3. `ContextEngine`: 用 fresh tail、summary、retrieved chunks 组成有限预算上下文。
4. `AgentResult`: 返回 `WorkflowRun`、最终 state、`AgentStep` trace 和错误信息。

旧单条 `Annotate` 兼容页仍通过 `app.workflows.annotation.run_agentic_annotation` 进入 agent kernel；新主流程的“批量标注”通过 `app.workflows.annotation.batch` 写入本地队列。

## 6. 数据与存储

长期标注存储：

1. 主格式：Prodigy-compatible JSONL。
2. Schema version：`rosetta.prodigy_jsonl.v1`。
3. 模型运行时 markup 与落盘格式解耦。

本地 runtime store：

1. 默认数据库：`.runtime/rosetta.sqlite3`。
2. Docker 默认数据库：`/opt/rosetta/runtime/rosetta.sqlite3`。
3. 表：`projects / tasks / predictions / reviews / runs / artifacts / agent_steps / concept_guidelines / gold_example_sets / concept_versions / jobs / job_items / job_events`。

## 7. 用户流程

```text
工作台
  -> 概念实验室
  -> 概念自举校准
  -> 批量标注
  -> 审核队列
  -> 导出与可视化
```

页面职责：

1. `工作台`: 展示核心指标、最近任务、最近审核状态和一个继续下一步入口。
2. `概念实验室`: 创建项目，维护 15 条金样例，运行 concept bootstrap loop，用 gold loss 比较当前概念与候选概念，只接受变好的干净版本，并将失败摘要与原始修订响应保存为日志。
3. `批量标注`: 导入 TXT/JSONL/CSV，分句、tokenize，并用概念版本、相似样例、边界远例和失败记忆构建标注上下文。
4. `审核队列`: 按阈值、抽检和路由原因逐条展示候选，让专家选择或修正，并记录错误类型、hard example 和 gold-like 反馈。
5. `导出与可视化`: 导出 Prodigy-compatible JSONL、实验报告和运行清单，展示统计图。

概念自举闭环不新增顶层产品边界，优先落在 `app/workflows/bootstrap`、`app/workflows/annotation`、`app/workflows/review` 和 `app/workflows/evaluation`。`app/research` 的 consistency、contrastive retrieval、label statistics、reflection 仍可作为算法参考或兼容实现，但不再作为主入口。

`Corpus Builder` 是高级数据工厂 workflow，保留兼容页面，但不进入默认主导航。

## 8. 兼容策略

1. `app/research/*` 和 `app/corpusgen/*` 保留，避免旧测试和脚本回归。
2. 新入口放在 `app/workflows/*`。
3. 旧 CLI 会打印迁移提示，并转发到新 workflow wrappers。
4. UI 默认导航使用 `工作台 / 概念实验室 / 批量标注 / 审核队列 / 导出与可视化`。
5. 等新 UI 和 CLI 完全覆盖旧功能后，再删除或冻结 legacy 目录。

## 9. 修改建议

1. 新领域对象写到 `app/core`。
2. 新 LLM 流程写到 `app/workflows`，并通过 `app/agents` 编排。
3. 新文件导入导出写到 `app/data`。
4. 新持久化写到 `app/runtime`。
5. 页面只做输入、展示和调用 workflow。

## 10. 架构不变量

1. Streamlit 是正式 UI；不在当前阶段引入 React / FastAPI 主界面。
2. Prodigy-compatible JSONL 是主导出格式；LLM runtime markup 只是运行时便利格式。
3. 概念自举必须有可计算 loss；候选概念不能无条件覆盖当前概念。
4. 人类审核必须沉淀为后续检索和概念修订资产，而不是只改一条输出。
5. Legacy 目录不可承载新产品边界；需要迁移时通过 `app/workflows` 包装。
