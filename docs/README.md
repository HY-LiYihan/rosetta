# Rosetta Docs

在线文档站：[https://hy-liyihan.github.io/rosetta/](https://hy-liyihan.github.io/rosetta/)

本目录是 Rosetta 的文档源文件，使用 MkDocs Material 构建。文档目标是让第一次使用者能快速找到入口，让开发者能明确分层边界，让科研实验能回到同一套可复核流程。

## 入口总览

| 你要做什么 | 先读 | 然后读 |
| --- | --- | --- |
| 第一次使用页面 | [用户教程](./user/TUTORIAL.md) | [标注运行时格式](./developer/ANNOTATION_FORMAT.md) |
| 了解项目整体 | [根 README](https://github.com/HY-LiYihan/rosetta#readme) | [架构总览](./developer/ARCHITECTURE.md) |
| 做 Concept Bootstrap 实验 | [核心想法](./ideas/CORE_ANNOTATION_BOOTSTRAP.md) | [Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md) |
| 跑 ACTER / 数据集实验 | [Bootstrap Experiments](./developer/BOOTSTRAP_EXPERIMENTS.md) | [Research Pipeline](./developer/RESEARCH_PIPELINE.md) |
| 生成指定领域语料 | [Corpus Pipeline](./developer/CORPUS_PIPELINE.md) | [用户教程中的 Corpus Studio](./user/TUTORIAL.md) |
| 确认数据格式 | [Annotation JSONL Format](./developer/ANNOTATION_JSONL_FORMAT.md) | [Annotation Format](./developer/ANNOTATION_FORMAT.md) |
| 部署或运维 | [Deployment](./developer/DEPLOYMENT.md) | [Scripts](./developer/SCRIPTS.md) |
| 改代码或提交 | [Workflow](./developer/WORKFLOW.md) | [Changelog](./CHANGELOG.md) |

## 用户路径

如果你只想打开系统并完成一次标注或语料生成，按这个顺序读：

1. [用户教程](./user/TUTORIAL.md)
2. [标注运行时格式](./developer/ANNOTATION_FORMAT.md)
3. [Annotation JSONL 存储格式](./developer/ANNOTATION_JSONL_FORMAT.md)

用户侧最重要的区分是：大模型运行时可以输出易读的 `[原文]{标签}`，但长期保存、评测和人工复核统一使用 Prodigy-compatible JSONL。

## 科研路径

Rosetta 目前有两条隔离的科研 pipeline。

| Pipeline | 目录 | 说明 |
| --- | --- | --- |
| Concept Bootstrap / Research | `app/research/` | 从概念描述和金样例出发，做 LLM 标注、自洽性分析、人工复核、检索增强、报告输出 |
| Corpus Generation / Corpus Studio | `app/corpusgen/` | 从领域 brief 出发，做标题规划、样稿确认、批量生成、judge 评审 |

Research 相关文档：

- [核心研究想法](./ideas/CORE_ANNOTATION_BOOTSTRAP.md)
- [Concept Bootstrap Pipeline](./developer/BOOTSTRAP_PIPELINE.md)
- [Bootstrap Experiments](./developer/BOOTSTRAP_EXPERIMENTS.md)
- [Research Pipeline](./developer/RESEARCH_PIPELINE.md)

Corpus Generation 相关文档：

- [Corpus Pipeline](./developer/CORPUS_PIPELINE.md)
- [用户教程](./user/TUTORIAL.md)

## 数据与标注格式

| 格式 | 用途 | 结论 |
| --- | --- | --- |
| LLM runtime inline markup | prompt 和模型输出解析 | 使用 `[原文]{标签}` / `[!隐含义]{标签}` |
| Prodigy-compatible JSONL | 长期存储、复核、评测、导入导出 | 使用 `text / tokens / spans / relations / label / options / accept / answer / meta` |
| INCEpTION `jsoncas` | 未来与 INCEpTION 交换 | 不作为内部主格式，只在导入导出边界转换 |

详细规范见：

- [Annotation Format](./developer/ANNOTATION_FORMAT.md)
- [Annotation JSONL Format](./developer/ANNOTATION_JSONL_FORMAT.md)

## 开发与维护路径

开发者先读三份文档：

1. [Architecture](./developer/ARCHITECTURE.md)
2. [Workflow](./developer/WORKFLOW.md)
3. [Developer README](./developer/README.md)

然后按任务类型进入：

| 类型 | 文档 |
| --- | --- |
| 改 Streamlit 页面 | [Architecture](./developer/ARCHITECTURE.md) |
| 改脚本入口 | [Scripts](./developer/SCRIPTS.md) |
| 改部署流程 | [Deployment](./developer/DEPLOYMENT.md) |
| 改研究 pipeline | [Research Pipeline](./developer/RESEARCH_PIPELINE.md) |
| 改语料生成 pipeline | [Corpus Pipeline](./developer/CORPUS_PIPELINE.md) |
| 确认阶段规划 | [Roadmap](./developer/ROADMAP.md) |

## 当前阶段

1. Stage 1-5 已完成。
2. Stage 6 研究增强正在推进，核心是 Concept Bootstrap。
3. Stage 8 文档与格式规范正在收敛，长期标注存储已转向 Prodigy-compatible JSONL profile。
4. `research` 与 `corpusgen` 必须保持代码与脚本入口隔离。
5. Docker / container 部署链路保持稳定，不在研究 pipeline 调整中随意破坏。

## 维护规则

1. 代码或行为变更必须同步更新 [CHANGELOG.md](./CHANGELOG.md)。
2. 用户使用方式变化必须同步更新根目录 [README.md](https://github.com/HY-LiYihan/rosetta#readme)。
3. 文档站导航由 [mkdocs.yml](../mkdocs.yml) 维护。
4. 每个可验收子步骤一个 commit，commit message 使用 `stageX-scope: summary`。
