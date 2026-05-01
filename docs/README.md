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
工作台 -> 概念实验室 -> 批量标注 -> 审核队列 -> 导出与可视化
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

1. v4.2.1 修正概念自举修订：最终提示词只保存干净概念阐释，失败摘要、样例编号和模型原始响应只进入日志与 metadata。
2. v4.2.0 将主工作流升级为 concept bootstrap loop：15 条金样例校准、概念版本、失败摘要、增强上下文标注和主动审核反馈。
3. v4.1.2 为长耗时按钮增加运行中禁用状态，避免重复触发验证、批量提交和审核保存。
4. Streamlit 仍是唯一正式 UI。
5. 工作台收敛为轻量状态入口，概念实验室内置“硬科学科普术语标注”可填表示例。
6. 概念实验室负责概念自举，批量标注负责 TXT/JSONL/CSV 导入和本地任务队列。
7. 审核队列按置信度、抽检和错误类型逐条展示待审核样本，并沉淀 hard examples。
8. Prodigy-compatible JSONL 不推翻，只增强 project/run/session/job 层。
9. 旧 `research/corpusgen` 暂不删除，作为 compatibility wrapper 的实现来源。

## 维护规则

1. 代码或行为变更必须同步更新 [CHANGELOG.md](./CHANGELOG.md)。
2. 用户使用方式变化必须同步更新根目录 [README.md](https://github.com/HY-LiYihan/rosetta#readme)。
3. 文档站导航由 [mkdocs.yml](../mkdocs.yml) 维护。
4. 每个可验收子步骤一个 commit，commit message 使用 `stageX-scope: summary`。
