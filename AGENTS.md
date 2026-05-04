# AGENTS.md

本文件是 Rosetta 仓库内的执行约束文档。每次开始任务前必须先阅读。

## 1. 任务前必做

1. 阅读 [docs/README.md](/Users/liyh/rosetta/docs/README.md)，确认当前文档索引与阶段状态。
2. 阅读 [docs/developer/ARCHITECTURE.md](/Users/liyh/rosetta/docs/developer/ARCHITECTURE.md)，确认分层边界。
3. 阅读 [docs/developer/WORKFLOW.md](/Users/liyh/rosetta/docs/developer/WORKFLOW.md)，确认提交流程和检查清单。
4. 如果需要快速建立项目上下文，阅读 [docs/developer/AGENT_ONBOARDING.md](/Users/liyh/rosetta/docs/developer/AGENT_ONBOARDING.md)。

## 2. 提交前必做

1. 代码改动必须同步更新文档（至少 [docs/CHANGELOG.md](/Users/liyh/rosetta/docs/CHANGELOG.md)）。
2. 如果改动影响用户使用方式，必须同步更新 [README.md](/Users/liyh/rosetta/README.md)。
3. 每次功能或行为变更后，必须同步更新页面底部版本号与更新日期（至少 [app/ui/pages/Home.py](/Users/liyh/rosetta/app/ui/pages/Home.py) 的页脚版本信息）。
4. 运行最小验证（至少编译检查 + 相关测试）。
5. 确认 `git status` 干净后再结束当前任务。

## 3. 提交规范

1. 每个可验收子步骤一个 commit。
2. commit message 格式：`stageX-scope: summary`。
3. 默认仅本地 commit；是否 push 由用户明确指定。

## 4. 文档分类约定

1. `docs/developer/`：开发与架构文档。
2. `docs/user/`：面向用户的使用教程。

## 5. 当前 Prompt Training 报告要点

1. 当前可分享报告为 [/Users/liyh/rosetta/.runtime/experiments/prompt_training_hard_science/comparison_report.pdf](/Users/liyh/rosetta/.runtime/experiments/prompt_training_hard_science/comparison_report.pdf)，由同目录 `comparison_report.md` 生成。
2. 该报告是 DeepSeek `deepseek-v4-pro` 真实运行结果，不是 mock；默认并发上限为 `20`，总调用 `4289`，估算总 token `1511759`。
3. 三方法对比均从同一句简单硬科学术语概念描述和同一批 15 条 gold 出发；达到 `15/15` 提前停止，否则按连续 5 轮 loss 无下降或 `max_rounds=30` 停止。
4. 报告中的最佳方法、最佳 loss 和最佳提示词按历史最优接受版本计算，而不是最后一轮快照；当前历史最优为 `text_gradient_adamw`，第 6 轮达到 `10/15`，loss 为 `41.9069`。
5. 当前实验只证明这 15 条 gold 内的训练表现和防背答案情况，不声明 held-out 泛化；后续论文级结论必须补充 held-out 或外部数据集。
6. 该 PDF 是需要分享和保留的实验产物；不要把它从 git 管理中移除，也不要新增 ignore 规则来排除它。如果 `.runtime/` 被 `.gitignore` 忽略，提交该 PDF 时应显式使用 `git add -f`。
