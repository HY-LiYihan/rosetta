# Roadmap (Developer)

更新时间: 2026-05-03

## 阶段状态

1. `v4.0.0`：Agentic Annotation Tool 架构落地，新增 `core / workflows / agents / data / runtime`。
2. `v4.1.x`：中文优先 5 页面 UI、完整案例、长耗时按钮防重复提交。
3. `v4.2.0`：Concept bootstrap loop 接入主工作流。
4. `v4.2.1`：概念修订提示词净化，日志与最终提示词解耦。
5. `v4.2.2`：Loss-guided concept refinement，避免越优化越差。
6. `v4.2.3`：文档架构重排，明确 user / developer / research claims 三条入口。
7. `v4.2.4`：Prompt-as-Parameter 文档升级，明确 Text Gradient 和 `LLM-AdamW` 是下一阶段核心方法。
8. `v4.3.0`：Prompt-as-Parameter 最小实现，接入 prompt 分段、Mask 启发式文本梯度、LLM-AdamW trace、长度惩罚和 gold loss validation。
9. `v4.3.1`：LLM service runtime 愿景文档，明确每次大模型调用都是服务调用，provider profile 管理平台参数，并要求 UI 展示进度、ETA、token 和成本。
10. `v4.4.0`：提示词优化训练实验，比较 `llm_optimize_only / llm_reflection / text_gradient_adamw`。
11. `v4.5.0`：提示词训练接入 LLM service runtime，DeepSeek 默认 `deepseek-v4-pro`，provider 并发上限默认 20，候选泄露先去语料化修复再决定接受或拒绝。
12. `v4.5.1`：三方法真实对比实验使用“连续 5 轮 loss 无下降”停止条件，并输出 `comparison_report.md / comparison_result.json / prompt_evolution.jsonl`。

## 下一阶段路线

1. `v4.6`：把批量标注真实 provider 调用完全迁入 `LLMServiceRuntime`，补齐 pause/resume/cancel、单条重试、整批重试和 checkpoint 恢复。
2. `v4.7`：过程进度可视化与 token/cost 统计。概念实验室、工作台和批量页展示实时进度、吞吐、预计剩余、当前并发、token 和成本聚合。
3. `v4.8`：UI 简化、审核体验和教程优化。继续压缩页面噪声，强化“一条一条蹦出”的审核卡片，并重写 30 分钟最小闭环教程。
4. `v4.9`：完整项目测试与实验报告。补齐 fake provider 全电路、真实 API 小样本 smoke、Docker healthcheck、PLM/LLM 对比、loss 曲线、人工审核收益和 ablation 表。
5. `v5.0`：论文级实验包。提供可复现实验配置、报告模板、图表、数据集转换和 ablation runner。

## 优先级判断

1. 先证明主工作流闭环，再扩展复杂 UI。
2. 先把实验指标和 LLM 调用事实落盘，再追求模型调用花样。
3. 先保证文档和代码结构一致，再大规模重构目录。
4. 先让传统语言学家能用，再让 PLM 研究者信服，最后让开发者维护起来不痛苦。

## 验收口径

1. 用户能按教程从概念、15 条金样例走到导出数据。
2. 研究者能从报告中比较 Rosetta 与 PLM baseline。
3. 开发者能从 Architecture 判断新增代码该放哪里。
4. 每次运行都能回放概念版本、候选、审核和导出产物。
5. `mkdocs build --strict --clean` 和核心测试通过。
