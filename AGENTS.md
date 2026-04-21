# AGENTS.md

本文件是 Rosetta 仓库内的执行约束文档。每次开始任务前必须先阅读。

## 1. 任务前必做

1. 阅读 [docs/README.md](/Users/liyh/rosetta/docs/README.md)，确认当前文档索引与阶段状态。
2. 阅读 [docs/developer/ARCHITECTURE.md](/Users/liyh/rosetta/docs/developer/ARCHITECTURE.md)，确认分层边界。
3. 阅读 [docs/developer/WORKFLOW.md](/Users/liyh/rosetta/docs/developer/WORKFLOW.md)，确认提交流程和检查清单。

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
