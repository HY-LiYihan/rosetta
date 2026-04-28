# Architecture (Developer)

更新时间: 2026-04-29

## 1. 目标定位

Rosetta 是一个基于 Streamlit 的本地优先 Agentic Annotation Tool。

当前架构不再把 `research` / `corpusgen` 作为产品边界。它们只作为历史兼容层保留；新功能应进入 `core / workflows / agents / data / runtime`。

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

## 4. 核心数据模型

1. `Project`: 标注项目，包含 schema、labels、guidelines、metadata。
2. `AnnotationTask`: Prodigy-compatible task，支持 `text/tokens/spans/relations/label/options/accept/answer/meta`。
3. `Prediction`: LLM 或规则生成的候选标注，类似 Label Studio pre-annotation。
4. `ReviewTask`: 面向人类专家的选择题/修正题。
5. `WorkflowRun`: bootstrap、annotation、corpus、evaluation 等运行记录。
6. `AgentStep`: 每一步 tool 调用、检索、judge、repair 的 trace。
7. `ConceptGuideline / GoldExampleSet / ConceptVersion`: 概念阐释、金样例库和修订历史。
8. `BatchJob / BatchJobItem`: 本地批量标注队列与 checkpoint。

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
  -> 批量标注
  -> 审核队列
  -> 导出与可视化
```

页面职责：

1. `工作台`: 展示核心指标、最近任务、最近审核状态和一个继续下一步入口。
2. `概念实验室`: 创建项目，编辑概念阐释，维护金样例，验证并修订概念。
3. `批量标注`: 导入 TXT/JSONL/CSV，分句、tokenize、提交本地 SQLite 任务队列。
4. `审核队列`: 按阈值、抽检和路由原因逐条展示候选，让专家选择或修正。
5. `导出与可视化`: 导出 Prodigy-compatible JSONL、报告和运行清单，展示统计图。

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
