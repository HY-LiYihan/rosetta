# Workflow (Developer)

## 1. 开始任务前

1. 阅读 [CLAUDE.md](/Users/liyh/rosetta/CLAUDE.md)。
2. 阅读 [ARCHITECTURE.md](/Users/liyh/rosetta/docs/developer/ARCHITECTURE.md)。
3. 确认本次改动属于哪个 Stage。

## 2. 开发步骤

1. 先文档后代码。
2. 小步改动、小步提交。
3. 每个可验收步骤至少执行：

```bash
python -m compileall app streamlit_app.py
python -m unittest discover -s tests -p 'test_*.py'
for f in $(find scripts -type f -name '*.sh'); do bash -n "$f"; done
```

## 3. 提交检查清单

1. [CHANGELOG.md](/Users/liyh/rosetta/docs/CHANGELOG.md) 是否更新。
2. 如果影响用户使用，[README.md](/Users/liyh/rosetta/README.md) 是否更新。
3. 文档中的路径引用是否为可点击链接。
4. `git status` 是否符合预期。

## 4. Git 策略

1. 默认只 commit，不 push（除非用户明确要求）。
2. 提交格式：`stageX-scope: summary`。
3. 禁止破坏性命令清理用户改动（`reset --hard` 等）。
