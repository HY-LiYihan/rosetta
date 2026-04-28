# Developer Docs

本页是 Rosetta 开发与维护文档入口。先确认分层边界，再进入具体 pipeline 或脚本。

## 必读顺序

1. [Architecture](./ARCHITECTURE.md)
2. [Workflow](./WORKFLOW.md)
3. [Roadmap](./ROADMAP.md)

这三份文档分别回答：

| 文档 | 回答的问题 |
| --- | --- |
| [Architecture](./ARCHITECTURE.md) | 哪些代码属于 UI、service、domain、research、corpusgen、infrastructure |
| [Workflow](./WORKFLOW.md) | 开始任务、验证、提交、push 的规则是什么 |
| [Roadmap](./ROADMAP.md) | 当前阶段在哪里，后续功能按什么顺序推进 |

## 文档分组

### 工程架构与流程

| 文档 | 用途 |
| --- | --- |
| [Architecture](./ARCHITECTURE.md) | 分层边界、核心数据流、技术债 |
| [Workflow](./WORKFLOW.md) | 开发流程、验证命令、提交规范 |
| [Roadmap](./ROADMAP.md) | 阶段计划和版本演进 |
| [Scripts](./SCRIPTS.md) | `scripts/` 下部署、运维、数据、研究脚本职责 |

### 标注与数据格式

| 文档 | 用途 |
| --- | --- |
| [Annotation Format](./ANNOTATION_FORMAT.md) | LLM 运行时标注格式，主要用于 prompt 与响应解析 |
| [Annotation JSONL Format](./ANNOTATION_JSONL_FORMAT.md) | 长期存储格式，参考 Prodigy task JSON 并扩展到 span、relation、分类和选择题 |

核心约束：LLM 运行时格式和最终存储格式不要求一致。运行时优先简单易标的行内 markup，落盘统一为 Prodigy-compatible JSONL。

### 科研流水线

| 文档 | 用途 |
| --- | --- |
| [Core Annotation Bootstrap](../ideas/CORE_ANNOTATION_BOOTSTRAP.md) | 核心科研想法归档 |
| [Concept Bootstrap Pipeline](./BOOTSTRAP_PIPELINE.md) | 15 个金样例、概念描述优化、自洽性、人工复核、动态检索 |
| [Bootstrap Experiments](./BOOTSTRAP_EXPERIMENTS.md) | ACTER 等实验数据、baselines、指标与报告建议 |
| [Research Pipeline](./RESEARCH_PIPELINE.md) | 通用 research runner、preview / audit / batch / build-index |
| [Corpus Pipeline](./CORPUS_PIPELINE.md) | 独立语料生成 pipeline、memory 压缩、CPU index、judge |

### 部署与运维

| 文档 | 用途 |
| --- | --- |
| [Deployment](./DEPLOYMENT.md) | Docker 部署、更新、回滚、备份、健康检查 |
| [Scripts](./SCRIPTS.md) | 运维脚本、研究脚本和数据脚本的职责边界 |

## 当前状态

1. Stage 1-5 已完成。
2. Stage 6 正在推进 Concept Bootstrap 研究增强。
3. Stage 8 正在收敛文档、数据格式和实验入口。
4. 长期标注存储使用 `rosetta.prodigy_jsonl.v1` / `rosetta.prodigy_candidate.v1`。
5. `app/research/*` 与 `app/corpusgen/*` 必须保持平行隔离，不能互相 import。
6. 默认协作策略是本地 commit，不 push，除非用户明确要求。

## 修改建议

| 如果要改 | 优先位置 | 注意 |
| --- | --- | --- |
| 页面展示 | `app/ui/pages/`, `app/ui/viewmodels/` | 不要把复杂业务规则写进页面 |
| 页面流程 | `app/services/` | service 负责流程编排和 LLM 调用 |
| 标注 schema | `app/domain/` | 必须同步更新格式文档和测试 |
| 标注研究算法 | `app/research/` | 不依赖 `app/corpusgen/` |
| 语料生成算法 | `app/corpusgen/` | 不依赖 `app/research/` |
| 模型平台 | `app/infrastructure/llm/` | 保持 OpenAI-compatible provider 抽象 |
| CLI | `scripts/` | 同步更新 [Scripts](./SCRIPTS.md) |

## 提交前检查

```bash
python -m compileall app streamlit_app.py
python -m unittest discover -s tests -p 'test_*.py'
for f in $(find scripts -type f -name '*.sh'); do bash -n "$f"; done
```

提交还需要确认：

1. [CHANGELOG.md](../CHANGELOG.md) 已更新。
2. 如果影响用户使用方式，根目录 [README.md](https://github.com/HY-LiYihan/rosetta#readme) 已更新。
3. `git status` 中没有误提交数据集、PDF、runtime 缓存或密钥。
