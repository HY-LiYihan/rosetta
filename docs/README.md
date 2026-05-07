# Rosetta Docs

更新时间: 2026-05-08

## 官方入口

| 入口 | 地址 | 说明 |
| --- | --- | --- |
| 官方文档站 | [https://hy-liyihan.github.io/rosetta/](https://hy-liyihan.github.io/rosetta/) | 对外使用、阅读教程和查看开发文档的主入口 |
| Demo 页面 | [https://rosetta-stone.xyz/](https://rosetta-stone.xyz/) | 在线体验入口 |
| GitHub 项目 | [https://github.com/HY-LiYihan/rosetta](https://github.com/HY-LiYihan/rosetta) | 源码、issue、部署文件、提交记录和项目协作入口 |

## 项目简介

Rosetta 是基于 Streamlit 的本地优先智能体式标注工具。它面向需要快速建立标注任务的研究者、语言学家、数字人文团队和领域专家。

它的核心不是“上传文本然后调一次大模型”，而是把一句话概念描述和 15 条金样例，迭代压缩成可执行、可复现、可审计的标注流水线：

```text
项目总览 -> 定义与规范 -> 批量标注 -> 审核与修正 -> 结果与导出
```

Rosetta 会把概念阐释、金样例、定义优化、批量标注、人工审核、运行记录和导出报告连成一个闭环。15 条金样例用于启动、校准和演示，不等于充分训练集，也不保证外部语料泛化。它要检验的是低资源、概念可描述、任务边界会迭代的场景中，大模型智能体是否能更快形成可审计的数据生产流程；它不声称在完整高质量训练集条件下无条件超过 PLM。

“本地优先”指项目数据、运行记录、导出文件和调试产物优先落在本机或你部署的运行目录中；它不等于默认离线，也不等于不会调用云端大模型。选择真实 provider 时，文本和 prompt 会按对应平台配置发送给模型服务。

文档分为用户教程、研究说明和开发者文档。用户教程帮助你完成首次标注流程；研究说明解释 Rosetta 要检验的假设和边界；开发者文档说明架构、数据流、运行产物和部署方式。

## 第一次只读这三页

如果你只是想跑通一次标注，不需要先读完整研究和架构文档：

1. 先读 [用户教程](./user/TUTORIAL.md) 的第 0-3 节，理解概念阐释、金样例、提示词验证和定义优化。
2. 再读 [提示词构成](./user/PROMPT_COMPOSITION.md)，确认界面语言、用户输入、运行时 prompt 和冻结输出协议各自是什么。
3. 最后按 [用户教程](./user/TUTORIAL.md) 的“完整使用案例：专业命名实体标注”跑官方样例：打开“定义与规范”做格式验证，到“批量标注”粘贴几句文本，用“本地模拟”提交，再到“结果与导出”下载 JSONL 和报告。

## 入口总览

| 你要做什么 | 先读 | 然后读 |
| --- | --- | --- |
| 第一次使用页面 | [用户教程](./user/TUTORIAL.md) | [Annotation JSONL](./developer/ANNOTATION_JSONL_FORMAT.md) |
| 理解模型实际看到的 prompt | [提示词构成](./user/PROMPT_COMPOSITION.md) | [Annotation Format](./developer/ANNOTATION_FORMAT.md) |
| 快速了解项目结构 | [架构总览](./developer/ARCHITECTURE.md) | [开发者入口](./developer/README.md) |
| 理解 Rosetta 要证明什么 | [研究主张](./ideas/RESEARCH_CLAIMS.md) | [Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md) |
| 理解新架构 | [开发者入口](./developer/README.md) | [架构总览](./developer/ARCHITECTURE.md) |
| 设计大模型调用并发与进度 | [LLM 服务运行时](./developer/LLM_SERVICE_RUNTIME.md) | [路线图](./developer/ROADMAP.md) |
| 理解本地 embedding 检索 | [Embedding Retrieval](./developer/EMBEDDING_RETRIEVAL.md) | [架构总览](./developer/ARCHITECTURE.md) |
| 本机排查 LLM prompt | [Deployment Debug 模式](./developer/DEPLOYMENT.md) | [LLM 服务运行时](./developer/LLM_SERVICE_RUNTIME.md) |
| 做 guideline / bootstrap | [核心想法](./ideas/CORE_ANNOTATION_BOOTSTRAP.md) | [Concept Bootstrap](./developer/BOOTSTRAP_PIPELINE.md) |
| 理解冻结输出协议和格式修复 | [Annotation Format](./developer/ANNOTATION_FORMAT.md) | [Concept Bootstrap](./developer/BOOTSTRAP_PIPELINE.md) |
| 设计 PLM / LLM 对比实验 | [研究主张](./ideas/RESEARCH_CLAIMS.md) | [Bootstrap Experiments](./developer/BOOTSTRAP_EXPERIMENTS.md) |
| 生成语料 | [Corpus Pipeline](./developer/CORPUS_PIPELINE.md) | [用户教程](./user/TUTORIAL.md) |
| 跑统一 CLI | [Scripts](./developer/SCRIPTS.md) | [Workflow](./developer/WORKFLOW.md) |
| 部署 Docker | [Deployment](./developer/DEPLOYMENT.md) | [Scripts](./developer/SCRIPTS.md) |

## 核心主张

Rosetta 当前要检验的核心假设是：LLM agent 在低资源、概念可描述、任务边界会迭代或任务不够常规的标注场景中，是否能比 PLM-first 流程更快形成可用数据，并且保留完整的概念版本、候选分歧、人工审核和成本轨迹。

这不等于声称 LLM 在完整高质量训练集条件下必然超过 PLM。更准确的比较方式是：用 full-data PLM 作为强上界，用 15 / 50 / 100 gold 的 low-budget PLM 作为主要对照，再比较 Rosetta 的概念自举、上下文检索、自洽性路由和主动审核是否带来稳定收益。

当前版本的主要能力包括：提示词验证、定义优化、后台训练进度、top-k 相似参考样例检索、人工审核反馈、调试追踪和 Prodigy-compatible JSONL 导出。详细版本变化见 [变更记录](./CHANGELOG.md)。

定义优化只调整概念语义：任务定义、概念定义、边界规则和排除规则。标签、JSON 字段、标注格式和格式检查由 Rosetta 固定，确保同一批金样例上的比较条件一致。三种自动优化方法为 `sgd_candidate_search / critic_adamw_optimizer / mask_guided_optimization`。

## 用户路径

```text
项目总览 -> 定义与规范 -> 批量标注 -> 审核与修正 -> 结果与导出
```

页面说明见 [用户教程](./user/TUTORIAL.md)。

## 数据格式

| 格式 | 用途 | 文档 |
| --- | --- | --- |
| LLM runtime inline markup | prompt 与响应解析 | [Annotation Format](./developer/ANNOTATION_FORMAT.md) |
| Prodigy-compatible JSONL | 长期存储、复核、评测、导出 | [Annotation JSONL Format](./developer/ANNOTATION_JSONL_FORMAT.md) |
| SQLite runtime store | 本地 project/run/artifact/trace | [Architecture](./developer/ARCHITECTURE.md) |
