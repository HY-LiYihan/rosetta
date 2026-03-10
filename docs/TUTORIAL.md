# Developer Tutorial

更新时间: 2026-03-10

## 1. 本地开发启动（Conda）

### 1.1 创建环境

```bash
conda env create -f environment.yml
conda activate rosetta-dev
```

### 1.2 启动应用

```bash
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
```

## 2. 重构开发流程（必须遵循）

1. 先更新 `docs/`（架构、路线图、教程、变更记录）。
2. 再做最小代码改动。
3. 改动后执行基础验证。
4. 把通过项、风险项写回文档或提交说明。

## 3. Stage 1 开发边界

允许:

1. 新建 `app/state`、`app/services` 并迁移重复代码。
2. 页面改为调用 service/state。
3. 保持现有页面路径和交互动作。

不允许:

1. 大改 UI 结构。
2. 更改用户操作路径。
3. 同时引入大量新功能。

## 4. 推荐本地验证命令

```bash
python -m compileall app pages streamlit_app.py api_utils.py
python test_concepts.py
```

可选检查:

```bash
python -m pytest -q
```

## 5. 建议提交流程

```bash
git status
git add docs/ app/ pages/
git commit -m "stage1: extract state/service with docs update"
git push origin <your-branch>
```

要求:

1. 每个可验收子步骤结束后都执行上述流程。
2. 不允许累积多个阶段后再一次性推送。

## 6. 代码组织约定

1. 页面逻辑只保留展示和事件触发。
2. 业务编排进入 `app/services`。
3. 状态初始化进入 `app/state`。
4. 可复用常量进入模块级常量文件。

## 7. 常见问题

1. 页面报 `KeyError`：检查是否在页面入口调用 `ensure_session_state()`。
2. 模型列表为空：检查 `secrets.toml` 与平台探测逻辑。
3. 导入 JSON 失败：先执行 schema 校验，再查看错误字段提示。

## 8. Stage 1 验收自检清单

1. 三页面可正常渲染。
2. 概念增删改与导入导出可用。
3. 标注流程与历史记录可用。
4. 无明显行为回归。
5. 文档已同步更新。

## 9. 双环境一致性检查

1. `requirements.txt` 与 `environment.yml` 同步更新。
2. 本地 Conda 能启动，Docker 也能构建通过。
3. Python 主版本保持一致（当前为 3.11）。

## 10. 样式修改流程（TOML First）

1. 优先在 `.streamlit/config.toml` 修改主题参数。
2. 若需求属于交互态或选择器级控制，再在 `streamlit_app.py` 补最小 CSS。
3. 禁止先写大段 CSS 再回填 TOML，避免样式治理失控。
