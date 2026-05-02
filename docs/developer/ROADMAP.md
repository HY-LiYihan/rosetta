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

## 下一阶段路线

1. `v4.3`：Prompt-as-Parameter 核心算法。当前已完成最小内核；后续补真实 Mask 重跑、对比替换、消融链路和跨轮 optimizer state。
2. `v4.4`：架构边界和 runtime store 优化。统一运行事实来源，补齐 prompt optimization trace、artifact、run manifest、token usage 和 progress event 的持久化边界。
3. `v4.5`：批量任务并发、队列和断点恢复。稳定 SQLite checkpoint、本地线程池、pause/resume/cancel、单条重试和整批重试。
4. `v4.6`：过程进度可视化与 token/cost 统计。工作台和批量页展示实时进度、吞吐、预计剩余、并发、token 和成本聚合。
5. `v4.7`：UI 简化、审核体验和教程优化。继续压缩页面噪声，强化“一条一条蹦出”的审核卡片，并重写 30 分钟最小闭环教程。
6. `v4.8`：完整项目测试。补齐 mock LLM 全电路、真实 API 小样本 smoke、UI smoke、Docker healthcheck 和文档教程验收。
7. `v4.9`：实验报告、PLM/LLM 对比和论文级导出。输出 loss 曲线、人工审核收益、token/cost、15/50/100 gold budget、PLM baseline 对比和 ablation 表。
8. `v5.0`：论文级实验包。提供可复现实验配置、报告模板、图表、数据集转换和 ablation runner。

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
