# Workflow (Developer)

更新时间: 2026-05-02

## 1. 开始任务前

1. 阅读 [AGENTS.md](../../AGENTS.md) 和 [CLAUDE.md](../../CLAUDE.md)。
2. 阅读 [docs/README.md](../README.md)，确认当前文档索引和阶段状态。
3. 阅读 [Research Claims](../ideas/RESEARCH_CLAIMS.md)，确认本次改动没有偏离 LLM agent vs PLM 的核心主张。
4. 阅读 [ARCHITECTURE.md](./ARCHITECTURE.md)。
5. 确认本次改动属于哪个 Stage 或 roadmap 版本。

## 2. 开发步骤

1. 先文档后代码。
2. 小步改动、小步提交。
3. UI 改动必须同步检查 [用户教程](../user/TUTORIAL.md)。
4. Workflow / agent / data 改动必须同步检查 [ARCHITECTURE.md](./ARCHITECTURE.md) 和相关 developer 文档。
5. 研究主张、实验指标或 PLM 对比相关改动必须同步检查 [Research Claims](../ideas/RESEARCH_CLAIMS.md) 和 [Bootstrap Experiments](./BOOTSTRAP_EXPERIMENTS.md)。
6. 每个可验收步骤至少执行：

```bash
python -m compileall app streamlit_app.py
python -m unittest discover -s tests -p 'test_*.py'
for f in $(find scripts -type f -name '*.sh'); do bash -n "$f"; done
```

## 3. 文档评审清单

重要文档或用户流程改动，需要用三类读者快速自评：

1. 传统语言学家：第一次接触数据标注的人能否知道下一步点哪里、填什么、导出什么。
2. PLM 研究者：能否看出实验主张、基线、指标和 Rosetta 不夸大的边界。
3. Rosetta 开发者：能否看出代码落点、数据流、runtime 产物和 legacy 边界。

## 4. 提交检查清单

1. [CHANGELOG.md](../../docs/CHANGELOG.md) 是否更新。
2. 如果影响用户使用，[README.md](../../README.md) 是否更新。
3. 文档中的路径引用是否为可点击链接。
4. 如果改动影响研究主张，[Research Claims](../ideas/RESEARCH_CLAIMS.md) 是否更新。
5. 如果改动影响页面或按钮，[app/ui/pages/Home.py](../../app/ui/pages/Home.py) 页脚版本是否更新。
6. `git status` 是否符合预期。

## 5. Git 策略

1. 默认只 commit，不 push（除非用户明确要求）。
2. 提交格式：`stageX-scope: summary`。
3. 禁止破坏性命令清理用户改动（`reset --hard` 等）。
