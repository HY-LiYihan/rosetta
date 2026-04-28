# Rosetta Docs

在线文档站：[https://hy-liyihan.github.io/rosetta/](https://hy-liyihan.github.io/rosetta/)

Rosetta 是基于 Streamlit 的本地优先 Agentic Annotation Tool。文档不再以 `research / corpusgen` 作为主入口，而是围绕 annotation tool 的用户路径和工程分层组织。

## 入口总览

| 你要做什么 | 先读 | 然后读 |
| --- | --- | --- |
| 第一次使用页面 | [用户教程](./user/TUTORIAL.md) | [Annotation JSONL](./developer/ANNOTATION_JSONL_FORMAT.md) |
| 理解新架构 | [架构总览](./developer/ARCHITECTURE.md) | [开发者入口](./developer/README.md) |
| 做 guideline / bootstrap | [核心想法](./ideas/CORE_ANNOTATION_BOOTSTRAP.md) | [Concept Bootstrap](./developer/BOOTSTRAP_PIPELINE.md) |
| 生成语料 | [Corpus Pipeline](./developer/CORPUS_PIPELINE.md) | [用户教程](./user/TUTORIAL.md) |
| 跑统一 CLI | [Scripts](./developer/SCRIPTS.md) | [Workflow](./developer/WORKFLOW.md) |
| 部署 Docker | [Deployment](./developer/DEPLOYMENT.md) | [Scripts](./developer/SCRIPTS.md) |

## 用户路径

```text
Projects -> Guidelines -> Annotate -> Review -> Runs -> Export
```

页面说明见 [用户教程](./user/TUTORIAL.md)。

## 工程路径

新代码优先进入：

1. `app/core`: 稳定领域模型。
2. `app/workflows`: 用户可执行流程。
3. `app/agents`: agent kernel、tool registry、context engine。
4. `app/data`: Prodigy JSONL 与外部格式桥接。
5. `app/runtime`: SQLite store、runtime paths、artifact/run/trace。

旧目录：

1. `app/research`: legacy bootstrap / evaluation implementation。
2. `app/corpusgen`: legacy corpus generation implementation。
3. `scripts/research` 和 `scripts/corpusgen`: legacy CLI，保留兼容。

## 数据格式

| 格式 | 用途 | 文档 |
| --- | --- | --- |
| LLM runtime inline markup | prompt 与响应解析 | [Annotation Format](./developer/ANNOTATION_FORMAT.md) |
| Prodigy-compatible JSONL | 长期存储、复核、评测、导出 | [Annotation JSONL Format](./developer/ANNOTATION_JSONL_FORMAT.md) |
| SQLite runtime store | 本地 project/run/artifact/trace | [Architecture](./developer/ARCHITECTURE.md) |

## 当前阶段

1. v4.0.0 开始把 Rosetta 重构为 Agentic Annotation Tool。
2. Streamlit 仍是唯一正式 UI。
3. Docker 部署保留，运行数据统一挂载到 `/opt/rosetta/runtime`。
4. Prodigy-compatible JSONL 不推翻，只增强 project/run/session 层。
5. 旧 `research/corpusgen` 暂不删除，作为 compatibility wrapper 的实现来源。

## 维护规则

1. 代码或行为变更必须同步更新 [CHANGELOG.md](./CHANGELOG.md)。
2. 用户使用方式变化必须同步更新根目录 [README.md](https://github.com/HY-LiYihan/rosetta#readme)。
3. 文档站导航由 [mkdocs.yml](../mkdocs.yml) 维护。
4. 每个可验收子步骤一个 commit，commit message 使用 `stageX-scope: summary`。
