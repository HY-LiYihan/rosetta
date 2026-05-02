# Roadmap (Developer)

更新时间: 2026-05-02

## 阶段状态

1. `v4.0.0`：Agentic Annotation Tool 架构落地，新增 `core / workflows / agents / data / runtime`。
2. `v4.1.x`：中文优先 5 页面 UI、完整案例、长耗时按钮防重复提交。
3. `v4.2.0`：Concept bootstrap loop 接入主工作流。
4. `v4.2.1`：概念修订提示词净化，日志与最终提示词解耦。
5. `v4.2.2`：Loss-guided concept refinement，避免越优化越差。
6. `v4.2.3`：文档架构重排，明确 user / developer / research claims 三条入口。
7. `v4.2.4`：Prompt-as-Parameter 文档升级，明确 Text Gradient 和 `LLM-AdamW` 是下一阶段核心方法。

## 下一阶段路线

1. `v4.3`：Prompt-as-Parameter 实现。补齐 `PromptSegmenter / TextGradientEstimator / PromptOptimizer / PromptOptimizationTrace`。
2. `v4.4`：实验闭环。补齐 PLM / LLM 对比报告字段，支持 15 / 50 / 100 gold budget 汇总。
3. `v4.5`：检索增强。把轻量 lexical retrieval 替换或扩展为本地 CPU embedding index，并保留可解释 fallback。
4. `v4.6`：LLM-as-a-judge。引入候选评审、错误类型归因和 judge disagreement。
5. `v4.7`：主动学习报告。输出人工审核收益曲线、自动通过抽检误差和 hard example 贡献。
6. `v4.8`：跨任务格式扩展。稳定支持 span、relation、句子级、段落级、文章级标注任务。
7. `v4.9`：数据集级实验 runner。支持 ACTER、NCBI-disease、BC2GM、CoNLL03 等数据转换与批量评测。
8. `v5.0`：论文级实验包。提供可复现实验配置、报告模板、图表和 ablation runner。

## 优先级判断

1. 先证明主工作流闭环，再扩展复杂 UI。
2. 先把实验指标落盘，再追求模型调用花样。
3. 先保证文档和代码结构一致，再大规模重构目录。
4. 先让传统语言学家能用，再让 PLM 研究者信服，最后让开发者维护起来不痛苦。

## 验收口径

1. 用户能按教程从概念、15 条金样例走到导出数据。
2. 研究者能从报告中比较 Rosetta 与 PLM baseline。
3. 开发者能从 Architecture 判断新增代码该放哪里。
4. 每次运行都能回放概念版本、候选、审核和导出产物。
5. `mkdocs build --strict --clean` 和核心测试通过。
