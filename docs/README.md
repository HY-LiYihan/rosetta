# Rosetta Docs

更新时间: 2026-05-04

在线文档站：[https://hy-liyihan.github.io/rosetta/](https://hy-liyihan.github.io/rosetta/)

Rosetta 是基于 Streamlit 的本地优先 Agentic Annotation Tool。它的核心不是“上传文本然后调一次大模型”，而是把一句话概念描述和 15 条金样例，迭代压缩成可执行、可复现、可审计的标注流水线。

文档面向两类主要读者：

1. **User**：第一次使用工具的人，尤其是传统语言学、数字人文、领域专家和需要快速构建语料标注任务的研究者。文档要简单直接，告诉你应该填什么、点什么、导出什么。
2. **Developer**：维护 Rosetta 的开发者和研究工程人员。文档要清楚说明运行结构、文件架构、数据流、workflow 边界和实验产物。

## 入口总览

| 你要做什么 | 先读 | 然后读 |
| --- | --- | --- |
| 第一次使用页面 | [用户教程](./user/TUTORIAL.md) | [Annotation JSONL](./developer/ANNOTATION_JSONL_FORMAT.md) |
| 让大模型快速接手项目 | [Agent Onboarding](./developer/AGENT_ONBOARDING.md) | [架构总览](./developer/ARCHITECTURE.md) |
| 理解 Rosetta 要证明什么 | [研究主张](./ideas/RESEARCH_CLAIMS.md) | [Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md) |
| 理解新架构 | [开发者入口](./developer/README.md) | [架构总览](./developer/ARCHITECTURE.md) |
| 设计大模型调用并发与进度 | [LLM 服务运行时](./developer/LLM_SERVICE_RUNTIME.md) | [路线图](./developer/ROADMAP.md) |
| 做 guideline / bootstrap | [核心想法](./ideas/CORE_ANNOTATION_BOOTSTRAP.md) | [Concept Bootstrap](./developer/BOOTSTRAP_PIPELINE.md) |
| 设计 PLM / LLM 对比实验 | [研究主张](./ideas/RESEARCH_CLAIMS.md) | [Bootstrap Experiments](./developer/BOOTSTRAP_EXPERIMENTS.md) |
| 生成语料 | [Corpus Pipeline](./developer/CORPUS_PIPELINE.md) | [用户教程](./user/TUTORIAL.md) |
| 跑统一 CLI | [Scripts](./developer/SCRIPTS.md) | [Workflow](./developer/WORKFLOW.md) |
| 部署 Docker | [Deployment](./developer/DEPLOYMENT.md) | [Scripts](./developer/SCRIPTS.md) |

## 核心主张

Rosetta 最需要证明的是：LLM agent 在低资源、概念可描述、任务边界会迭代或任务不够常规的标注场景中，能比 PLM-first 流程更快形成可用数据，并且保留完整的概念版本、候选分歧、人工审核和成本轨迹。

这不等于声称 LLM 在完整高质量训练集条件下必然超过 PLM。更准确的比较方式是：用 full-data PLM 作为强上界，用 15 / 50 / 100 gold 的 low-budget PLM 作为主要对照，再比较 Rosetta 的概念自举、上下文检索、自洽性路由和主动审核是否带来稳定收益。

`v4.5.0` 将 [Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md) 从“能比较优化方法”推进到真实服务化训练路径：默认真实模型为 DeepSeek `deepseek-v4-pro`，LLM service runtime 用 provider 级共享 semaphore 把默认并发上限提升到 `20`，并记录调用进度、token、耗时和重试。训练反馈可以包含原文、标准答案和模型回答；候选提示词若复制语料词、gold span、模型 span 或可识别答案片段，会先进入去语料化修复，修复后仍泄露才拒绝。当前结论仍只限于 15 条 gold 内的训练表现，不宣称跨样本泛化。

`v4.5.1` 将三方法 prompt training 变成可交付的对比实验：`llm_optimize_only / llm_reflection / text_gradient_adamw` 从同一简单提示词和同一批 15 条硬科学 gold 出发，达到 `15/15` 即成功，否则连续 5 轮 loss 无下降才停止，默认最多 30 轮。报告中的最佳方法、最佳 loss 和最佳提示词按历史最优接受版本计算，不用最后一轮快照误导方法排名。统一 CLI 会输出 Markdown 报告、完整 JSON trace 和提示词演化 JSONL。

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
6. `app/infrastructure/llm`: provider profile、模型服务参数、token/cost 和限流边界。

旧目录：

1. `app/research`: legacy bootstrap / evaluation implementation。
2. `app/corpusgen`: legacy corpus generation implementation。
3. `scripts/research` 和 `scripts/corpusgen`: legacy CLI，保留兼容。

开发文档的基本约束：

1. UI 只负责输入和展示，不承载复杂业务规则。
2. workflow 是用户可执行流程的主入口。
3. agent / data / runtime 是 workflow 的支撑层。
4. legacy 目录只能做兼容和迁移参考，不再作为新功能边界。

## 数据格式

| 格式 | 用途 | 文档 |
| --- | --- | --- |
| LLM runtime inline markup | prompt 与响应解析 | [Annotation Format](./developer/ANNOTATION_FORMAT.md) |
| Prodigy-compatible JSONL | 长期存储、复核、评测、导出 | [Annotation JSONL Format](./developer/ANNOTATION_JSONL_FORMAT.md) |
| SQLite runtime store | 本地 project/run/artifact/trace | [Architecture](./developer/ARCHITECTURE.md) |

## 当前阶段

1. v4.5.1 已实现三方法真实对比实验：每个方法连续 5 轮 loss 无下降才停止，默认最多 30 轮；CLI 输出 `comparison_report.md / comparison_result.json / prompt_evolution.jsonl`，并按历史最优接受版本汇总最佳提示词。
2. v4.5.0 已接入统一 LLM service runtime：DeepSeek 默认 `deepseek-v4-pro`，默认 provider 并发上限 `20`，提示词训练和批量标注记录调用、token、耗时和修复统计。
3. v4.4.1 已实现提示词优化训练防背答案检查：训练反馈可看批改对照，learned operational prompt 必须无语料和答案片段泄露。
4. v4.4.0 已实现提示词优化训练：同一批 15 条金样例比较 `llm_optimize_only / llm_reflection / text_gradient_adamw`。
5. v4.3.1 文档化 LLM service runtime 愿景：每次大模型调用都应作为服务调用被限流、排队、追踪、计费和可视化，默认并发上限后续收敛为 20。
6. v4.3.0 已实现 Prompt-as-Parameter 最小内核：prompt 分段、Mask 文本梯度、LLM-AdamW trace、长度惩罚和 loss 验证。
7. v4.2.4 将 Prompt-as-Parameter、Text Gradient 和 `LLM-AdamW` 写成核心方法框架。
8. v4.2.3 将文档重构为 user / developer / research claims 三条入口，并记录 6 轮三角色文档评审。
9. v4.2.2 将概念自举升级为 loss-guided candidate search：每轮比较当前概念和候选概念的 gold loss，只接受变好的版本。
10. v4.2.1 修正概念自举修订：最终提示词只保存干净概念阐释，失败摘要、样例编号和模型原始响应只进入日志与 metadata。
11. Streamlit 仍是唯一正式 UI。
12. 工作台收敛为轻量状态入口，概念实验室内置“硬科学科普术语标注”可填表示例。
13. 概念实验室负责概念自举和提示词优化训练，批量标注负责 TXT/JSONL/CSV 导入和本地任务队列。
14. 审核队列按置信度、抽检和错误类型逐条展示待审核样本，并沉淀 hard examples。
15. Prodigy-compatible JSONL 不推翻，只增强 project/run/session/job 层。
16. 旧 `research/corpusgen` 暂不删除，作为 compatibility wrapper 的实现来源。

## 维护规则

1. 代码或行为变更必须同步更新 [CHANGELOG.md](./CHANGELOG.md)。
2. 用户使用方式变化必须同步更新根目录 [README.md](https://github.com/HY-LiYihan/rosetta#readme)。
3. 文档站导航由 [mkdocs.yml](../mkdocs.yml) 维护。
4. 文档重大调整要按 [Documentation Review Iterations](./developer/DOCS_REVIEW_ITERATIONS.md) 的三角色方式检查。
5. 每个可验收子步骤一个 commit，commit message 使用 `stageX-scope: summary`。
