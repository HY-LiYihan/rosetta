# Annotation Format (Developer)

更新时间: 2026-03-11

## 1. 目标

1. 统一标注字符串格式，支撑后续可视化渲染与自动检查。
2. 明确区分“原文显性标注”与“语义隐含标注”。

## 2. 格式规范（V2）

1. 显性原文：`[原文片段]{概念标签}`
2. 隐含语义：`[!隐含义]{概念标签}`

约束：
1. `annotation` 至少包含一个合法标注片段。
2. 不再接受旧格式 `[...] (...)`。
3. `!` 仅用于隐含语义，且 `!` 后必须有内容。

## 2.1 存储格式（Annotation JSONL）

LLM 运行时仍优先输出行内标注字符串，但长期存储统一使用可扩展 JSONL。每行一条文档：

```json
{
  "schema_version": "rosetta.annotation_jsonl.v1",
  "id": "sample-001",
  "text": "Patients with heart failure may receive ventricular assist devices.",
  "annotation": {
    "version": "3.1",
    "kind": "document_annotation",
    "text": "Patients with heart failure may receive ventricular assist devices.",
    "layers": {
      "spans": [
        {
          "id": "T1",
          "start": 14,
          "end": 27,
          "text": "heart failure",
          "label": "Specific_Term",
          "implicit": false,
          "features": {}
        }
      ],
      "relations": [],
      "attributes": [],
      "comments": [],
      "document_labels": []
    },
    "provenance": {}
  },
  "metadata": {}
}
```

约束：
1. `annotation.layers.spans[*].start` 包含，`end` 不包含。
2. 显性 span 必须满足 `text[start:end] == span.text`。
3. `relations / attributes / comments / document_labels` 先允许为空数组，用于后续扩展。
4. 旧的顶层 `spans` JSONL 只作为兼容输入，不再作为新写出格式。

## 3. 示例数据规范

`concepts[*].examples[*]` 必填字段：
1. `text: str`
2. `annotation: str`（必须符合 V2 格式）
3. `explanation: str`（必填且非空）

## 4. 代码落点

1. 标注格式解析/校验：
- [annotation_format.py](../../app/domain/annotation_format.py)
2. 导入校验（examples 强校验）：
- [validators.py](../../app/domain/validators.py)
3. 标注响应校验：
- [annotation_service.py](../../app/services/annotation_service.py)

## 5. 兼容策略

1. 数据版本提升为 `2.0`。
2. 历史样例应迁移到 `[] {}` 格式并补齐 `explanation`。
3. 对不符合规范的导入数据，返回结构化错误：`field/reason/hint`。
