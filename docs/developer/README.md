# Developer Docs

更新时间: 2026-05-02

本页是 Rosetta 开发与维护入口。当前主线是 Agentic Annotation Tool 架构：用 Streamlit 提供本地优先 UI，用 `core / workflows / agents / data / runtime` 组织程序，用 concept bootstrap loop 连接概念校准、批量标注、主动审核和实验报告。

## 必读顺序

1. [Research Claims](../ideas/RESEARCH_CLAIMS.md)：先确认 Rosetta 要证明什么，尤其是 LLM agent 与 PLM 的比较边界。
2. [Prompt-as-Parameter](../ideas/PROMPT_AS_PARAMETER.md)：确认文本梯度估算和 prompt 优化器的核心方法边界。
3. [Architecture](./ARCHITECTURE.md)：确认运行结构、目录分层和数据流。
4. [Workflow](./WORKFLOW.md)：确认开发、验证、提交和文档评审规则。
5. [Scripts](./SCRIPTS.md)：确认 CLI、部署和 legacy 入口。
6. [Deployment](./DEPLOYMENT.md)：确认 Docker、runtime 目录和运维方式。

如果只改 UI，请至少读 [用户教程](../user/TUTORIAL.md) 和 [Architecture](./ARCHITECTURE.md)。如果只改算法，请至少读 [Research Claims](../ideas/RESEARCH_CLAIMS.md)、[Core Annotation Bootstrap](../ideas/CORE_ANNOTATION_BOOTSTRAP.md) 和 [Concept Bootstrap Pipeline](./BOOTSTRAP_PIPELINE.md)。

## 文档分组

### 新架构

| 文档 | 用途 |
| --- | --- |
| [Research Claims](../ideas/RESEARCH_CLAIMS.md) | LLM agent vs PLM 的研究主张、创新点和实验边界 |
| [Prompt-as-Parameter](../ideas/PROMPT_AS_PARAMETER.md) | Text Gradient、Prompt Optimizer 和 `LLM-AdamW` 方法框架 |
| [Architecture](./ARCHITECTURE.md) | `core/workflows/agents/data/runtime` 分层边界 |
| [Workflow](./WORKFLOW.md) | 开发、验证、提交规则 |
| [Scripts](./SCRIPTS.md) | 统一 CLI 与 legacy scripts |
| [Deployment](./DEPLOYMENT.md) | Docker / runtime 目录 / 健康检查 |
| [Documentation Review Iterations](./DOCS_REVIEW_ITERATIONS.md) | 三类读者、6 轮文档评审和本轮优化记录 |

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

1. v4.2.4 将 Prompt-as-Parameter、Text Gradient 和 `LLM-AdamW` 写成核心方法框架；当前只是文档升级，不宣称优化器已完整实现。
2. v4.2.3 文档主线已整理为 user / developer / research claims 三条入口，并加入三角色评审记录。
3. v4.2.2 概念自举使用 loss-guided candidate search，只接受 gold loss 下降的干净概念版本。
4. v4.2.1 修正概念修订边界：`ConceptVersion.description` 只保存干净提示词，失败摘要和原始响应进入 `metadata`。
5. v4.2.0 默认主线是 concept bootstrap loop：15 条金样例校准、概念版本、失败摘要、增强上下文标注和主动审核反馈。
6. 工作台收敛为轻量状态入口，概念实验室内置“硬科学科普术语标注”填表示例。
7. 本地批量任务队列使用 SQLite 存储 `jobs / job_items / job_events`。
8. 概念阐释与金样例模型使用 `concept_guidelines / gold_example_sets / concept_versions` 存储。
9. `Annotate` 单条旧流程保留为兼容页面；新主流程优先走 `app.workflows.annotation.batch`。
10. Bootstrap 和 Corpus 通过 `app.workflows.*` 包装 legacy 实现。
11. 统一 CLI 为 [scripts/tool/rosetta_tool.py](../../scripts/tool/rosetta_tool.py)。
12. `app/research` 与 `app/corpusgen` 不再作为新功能边界，只做兼容层。

## 研究主张到代码的映射

| 研究问题 | 代码落点 | 产物 |
| --- | --- | --- |
| 15 条金样例能否校准概念 | `app/workflows/bootstrap` | `concept_versions`、failure summary、loss |
| prompt 哪些片段应被优化 | `app/workflows/bootstrap` | PromptOptimizationTrace、Text Gradient、loss delta |
| LLM agent 是否比普通 few-shot 更稳 | `app/workflows/annotation` | k 次候选、span-F1、自洽性分数 |
| 人类专家是否更省力 | `app/workflows/review` | selected candidate、edit type、hard example |
| PLM / LLM 对比是否可复现 | `app/workflows/evaluation`、`scripts/tool` | `report.md`、manifest、JSONL exports |
| 非标准任务是否能快速落地 | `app/ui/pages/Concept_Lab.py`、`Batch_Run.py` | guideline、gold examples、batch jobs |

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

新增功能时的默认判断：

1. 只影响显示：放在 `app/ui`，并同步用户教程。
2. 影响业务流程：放在 `app/workflows`，页面只调用 workflow。
3. 影响模型调用策略：放在 `app/agents` 或 `app/infrastructure/llm`。
4. 影响文件格式：放在 `app/data`，并同步格式文档。
5. 影响实验报告：放在 `app/workflows/evaluation`，并同步研究主张或实验文档。

## 提交前检查

```bash
python -m compileall app streamlit_app.py
python -m unittest discover -s tests -p 'test_*.py'
for f in $(find scripts -type f -name '*.sh'); do bash -n "$f"; done
mkdocs build --strict --clean
```
