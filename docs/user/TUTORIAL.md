# 用户教程（网站使用版）

更新时间: 2026-04-29

本教程面向直接使用 Rosetta 网站的用户。Rosetta 当前是本地优先的 Agentic Annotation Tool。

## 1. 使用流程总览

推荐路径：

```text
Projects -> Guidelines -> Annotate -> Review -> Runs -> Export
```

如果需要先生成语料，进入 `Corpus Builder`。

## 2. Dashboard

首页用于查看：

1. 概念数量、标注历史、平均标注长度。
2. 主要 workflow 入口。
3. 最近使用的概念与最近标注记录。

## 3. Projects

`Projects` 用于创建一个标注项目。项目保存到本地 SQLite runtime store。

需要填写：

1. 项目名称。
2. 项目说明。
3. 任务类型：span、relation、classification、choice、document。
4. 标签集合。

## 4. Guidelines

`Guidelines` 是概念描述和金样例的入口。

当前版本保留旧「概念管理」页面作为兼容入口。后续会把 15 个金样例、概念描述迭代、自洽性分析和专家复核队列整合到本页。

## 5. Annotate

`Annotate` 用于对单条文本运行 agent-assisted annotation。

流程：

1. 选择平台、模型和 temperature。
2. 选择 guideline / concept。
3. 输入待标注文本。
4. 点击开始标注。
5. 查看 JSON、标注统计和可视化结果。

当前 `Annotate` 已通过统一 `AgentKernel` 执行，内部会记录工具步骤，后续会逐步写入 `Runs`。

## 6. Review

`Review` 用于集中处理：

1. 低置信样本。
2. 多次采样不一致样本。
3. 冲突候选。
4. 需要专家选择的候选。

目标是把人工工作从开放式标注变成优先选择题式复核。

## 7. Corpus Builder

`Corpus Builder` 是数据工厂 workflow，不再作为独立 research pipeline。

适用场景：从一句话 brief 生成指定领域、题材、语言的语料。

步骤：

1. 输入 brief，并补充语言、领域、体裁、受众、文章数量和目标长度。
2. 生成标题候选、策略摘要和样稿方向。
3. 人工微调标题与策略。
4. 生成少量样稿。
5. 批量生成完整语料。
6. 运行 judge，查看评分、问题和修改建议。

## 8. Runs

`Runs` 展示本地 workflow run。

CLI 使用 `--record` 或后续页面 workflow 写入 runtime store 后，可以在这里看到：

1. workflow 类型。
2. 运行状态。
3. 输出目录。
4. summary 和 metadata。

## 9. Export

`Export` 导出 Prodigy-compatible JSONL。

Rosetta 长期标注存储使用：

```text
text / tokens / spans / relations / label / options / accept / answer / meta
```

## 10. Settings

`Settings` 展示：

1. Runtime 目录。
2. SQLite 数据库路径。
3. artifacts / exports / indexes 路径。
4. 已注册模型平台。

## 11. 标注格式

LLM 运行时仍使用易读 markup：

1. 显性标注：`[原文片段]{概念标签}`
2. 隐含义标注：`[!隐含义]{概念标签}`

长期存储格式见 [Annotation JSONL Format](../developer/ANNOTATION_JSONL_FORMAT.md)。
