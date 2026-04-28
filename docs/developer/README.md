# Developer Docs

本页是 Rosetta 开发与维护入口。当前主线是 Agentic Annotation Tool 架构。

## 必读顺序

1. [Architecture](./ARCHITECTURE.md)
2. [Workflow](./WORKFLOW.md)
3. [Scripts](./SCRIPTS.md)
4. [Deployment](./DEPLOYMENT.md)

## 文档分组

### 新架构

| 文档 | 用途 |
| --- | --- |
| [Architecture](./ARCHITECTURE.md) | `core/workflows/agents/data/runtime` 分层边界 |
| [Workflow](./WORKFLOW.md) | 开发、验证、提交规则 |
| [Scripts](./SCRIPTS.md) | 统一 CLI 与 legacy scripts |
| [Deployment](./DEPLOYMENT.md) | Docker / runtime 目录 / 健康检查 |

### 标注格式

| 文档 | 用途 |
| --- | --- |
| [Annotation Format](./ANNOTATION_FORMAT.md) | LLM runtime markup |
| [Annotation JSONL Format](./ANNOTATION_JSONL_FORMAT.md) | Prodigy-compatible JSONL 存储格式 |

### Workflow 与兼容层

| 文档 | 用途 |
| --- | --- |
| [Concept Bootstrap Pipeline](./BOOTSTRAP_PIPELINE.md) | Guideline bootstrap 的历史与算法说明 |
| [Bootstrap Experiments](./BOOTSTRAP_EXPERIMENTS.md) | ACTER 等实验配置和指标 |
| [Research Pipeline](./RESEARCH_PIPELINE.md) | Legacy research runner 说明 |
| [Corpus Pipeline](./CORPUS_PIPELINE.md) | Corpus Builder 的 legacy generation 实现 |
| [Core Annotation Bootstrap](../ideas/CORE_ANNOTATION_BOOTSTRAP.md) | 核心研究想法归档 |

## 当前状态

1. v4.1.2 默认 UI 对长耗时按钮使用运行中禁用状态，避免重复触发验证、批量提交和审核保存。
2. v4.1.1 默认 UI 保持 5 个主页面，并让导航与正文固定文案同步支持中文 / English。
3. 工作台收敛为轻量状态入口，概念实验室内置“硬科学科普术语标注”填表示例。
4. 本地批量任务队列使用 SQLite 存储 `jobs / job_items / job_events`。
5. 概念阐释与金样例模型使用 `concept_guidelines / gold_example_sets / concept_versions` 存储。
6. `Annotate` 单条旧流程保留为兼容页面；新主流程优先走 `app.workflows.annotation.batch`。
7. Bootstrap 和 Corpus 通过 `app.workflows.*` 包装 legacy 实现。
8. 统一 CLI 为 [scripts/tool/rosetta_tool.py](../../scripts/tool/rosetta_tool.py)。
9. `app/research` 与 `app/corpusgen` 不再作为新功能边界，只做兼容层。

## 修改建议

| 如果要改 | 优先位置 |
| --- | --- |
| 标注/复核/运行记录模型 | `app/core` |
| LLM agent 编排 | `app/agents` |
| 用户可执行流程 | `app/workflows` |
| JSONL / 外部格式 | `app/data` |
| SQLite / runtime artifacts | `app/runtime` |
| Streamlit 页面 | `app/ui` |
| LLM provider | `app/infrastructure/llm` |

## 提交前检查

```bash
python -m compileall app streamlit_app.py
python -m unittest discover -s tests -p 'test_*.py'
for f in $(find scripts -type f -name '*.sh'); do bash -n "$f"; done
mkdocs build --strict --clean
```
