# Developer Workflow

## 1. 任务开始前

1. 阅读 `CLAUDE.md`。
2. 阅读 `docs/developer/ARCHITECTURE.md`。
3. 明确当前 Stage 和目标验收标准。

## 2. 开发步骤

1. 先文档后代码。
2. 小步提交，每个可验收子步骤一个 commit。
3. 每次改动至少执行：

```bash
python -m compileall app pages streamlit_app.py api_utils.py
python -m unittest discover -s tests -p 'test_*.py'
```

## 3. 提交检查清单

1. 代码改动是否同步 `docs/CHANGELOG.md`。
2. 用户使用方式变更是否同步 `README.md`。
3. 新增脚本是否通过 `bash -n`。
4. 提交信息是否符合 `stageX-scope: summary`。

## 4. Git 规则

1. 默认只 commit，不 push（除非用户明确要求）。
2. 避免一次性大提交。
3. 不可使用破坏性 git 命令清理用户改动。
