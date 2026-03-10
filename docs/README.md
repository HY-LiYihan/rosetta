# Rosetta Docs

本目录是 Rosetta 架构升级的唯一文档入口，遵循以下规则：

1. 先文档后代码。
2. 每个阶段必须有可执行步骤与验收标准。
3. 文档与代码同提交同步更新。

## 文档索引

- [ARCHITECTURE.md](./ARCHITECTURE.md): 系统架构、分层边界、模块契约、迁移策略。
- [DEPLOYMENT.md](./DEPLOYMENT.md): 服务器 Docker 部署、更新、备份、回滚。
- [TUTORIAL.md](./TUTORIAL.md): 开发者教程，包含本地开发与重构开发流程。
- [ROADMAP.md](./ROADMAP.md): Stage 0-6 迭代计划与每阶段验收口径。
- [CHANGELOG.md](./CHANGELOG.md): 文档与架构变更记录。

## 当前状态

- 当前执行阶段: Stage 1（代码结构重排，不改行为）。
- 当前部署策略: Docker（服务器）+ Conda（本地开发），脚本驱动运维。

## 阅读顺序（建议）

1. 先读 `ARCHITECTURE.md` 理解目标边界。
2. 再读 `DEPLOYMENT.md` 理解服务器落地路径。
3. 再读 `ROADMAP.md` 明确阶段里程碑。
4. 最后读 `TUTORIAL.md` 执行实际开发与验证。
