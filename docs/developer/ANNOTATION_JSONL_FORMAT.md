# Annotation JSONL Format

更新时间: 2026-05-02

## 1. 结论

Rosetta 的长期标注存储格式采用 **Prodigy-compatible JSONL profile**：

1. 每行是一条 JSON task。
2. 顶层字段尽量沿用 Prodigy 的任务结构：`text / tokens / spans / relations / label / options / accept / answer / meta`。
3. span 偏移采用 spaCy / Prodigy 常见的字符 offset：`start` 包含，`end` 不包含。
4. LLM 运行时仍优先使用 `[原文]{标签}` 行内 markup，解析后再转换为 Prodigy-compatible JSONL。

Rosetta 的 schema 名称：

1. Gold / normalized sample：`rosetta.prodigy_jsonl.v1`
2. Model candidate：`rosetta.prodigy_candidate.v1`

这个格式服务两个目标：

1. 让传统语言学家和领域专家可以从简单行内标注开始，不需要手算 offset。
2. 让开发者和 PLM 研究者拿到稳定 JSONL，用于训练、评测、复核和跨工具转换。

## 2. 来源

### 2.1 Prodigy annotation task JSON

主要参考：

1. [Prodigy API Interfaces](https://prodi.gy/docs/api-interfaces)
2. [Prodigy support: named entity recognition](https://prodi.gy/docs/named-entity-recognition)
3. [Prodigy support: relations](https://prodi.gy/docs/relations)

Prodigy 的界面与 recipe 都围绕 JSON task 工作：输入 task 带 `text`、`spans`、`relations`、`options` 等字段；标注完成后通常会带 `answer`，表示用户对该任务的处理结果。

### 2.2 spaCy span offsets

主要参考：

1. [spaCy training data format](https://spacy.io/api/data-formats)
2. [spaCy Span API](https://spacy.io/api/span)

Rosetta 沿用字符 offset 表达 span 边界，方便和 spaCy / Prodigy 数据互转，也便于离线评测 span precision / recall / F1。

### 2.3 INCEpTION exchange format

主要参考：

1. [INCEpTION formats](https://inception-project.github.io/releases/31.3/docs/user-guide.html#sect_formats)

INCEpTION 推荐复杂项目交换使用 `UIMA CAS JSON`，format id 是 `jsoncas`。Rosetta 不把 `jsoncas` 作为内部主格式；如需接入 INCEpTION，只在导入导出边界做 `prodigy_jsonl <-> jsoncas` 转换。

## 3. 顶层字段

`id`: Rosetta 样本 ID。必须稳定，不能依赖行号。

`text`: 被标注文本。可以是一句话、段落或整篇文章。

`tokens`: token 列表。当前可为空数组；后续做 relation 标注时可填入 token offset。

`spans`: 文本片段标注。用于实体、术语、概念片段、嵌套概念。

`relations`: span / token 之间的关系。用于因果、包含、修饰、引用、治疗等。

`label`: 单标签分类结果。适合句子级、段落级或文章级单选分类。

`options`: 可选项列表。适合多选分类、选择题、人类复核候选。

`accept`: 已选择的 option id 列表。适合多标签分类或候选选择。

`answer`: 标注任务状态。沿用 Prodigy 语义，常用值是 `accept / reject / ignore`；未经过人类最终确认的模型候选可为 `null`。

`meta`: 元数据。放数据集、领域、语言、split、来源、模型、置信度、文档 ID、段落编号等。

Rosetta 约定：所有与实验可复现相关但不属于标注本身的信息，都优先放入 `meta` 或 runtime store，而不是污染 `text`、`spans` 或最终概念阐释。例如 concept version、source pool、confidence、route reason、human edit type 和 model cost。

## 4. Gold / Normalized Sample

最小 gold sample：

```json
{
  "schema_version": "rosetta.prodigy_jsonl.v1",
  "id": "sample-001",
  "text": "Patients with heart failure may receive ventricular assist devices.",
  "tokens": [],
  "spans": [
    {
      "id": "T1",
      "start": 14,
      "end": 27,
      "text": "heart failure",
      "label": "Specific_Term",
      "implicit": false
    }
  ],
  "relations": [],
  "answer": "accept",
  "meta": {
    "dataset": "ACTER",
    "language": "en",
    "domain": "heart_failure",
    "unit": "sentence"
  }
}
```

约束：

1. 显性 span 必须满足 `text[start:end] == span.text`。
2. `spans[*].id` 在同一条 task 内必须唯一。
3. 如果无 span，`spans` 写空数组，不省略。
4. 如果无 relation，`relations` 写空数组，不省略。
5. gold 数据的 `answer` 默认为 `accept`。

## 5. Model Candidate

模型候选是 Prodigy-compatible 的扩展 task。它保留 Prodigy 可读字段，同时保留 LLM 原始行内标注：

```json
{
  "schema_version": "rosetta.prodigy_candidate.v1",
  "sample_id": "sample-001",
  "candidate_id": "run-001",
  "text": "Patients with heart failure may receive ventricular assist devices.",
  "tokens": [],
  "spans": [
    {
      "id": "T1",
      "start": 14,
      "end": 27,
      "text": "heart failure",
      "label": "Specific_Term",
      "implicit": false
    }
  ],
  "relations": [],
  "runtime_annotation": {
    "format": "inline_markup.v1",
    "annotation_markup": "[heart failure]{Specific_Term}"
  },
  "answer": null,
  "explanation": "The phrase names a domain-specific medical condition.",
  "model_confidence": 0.82,
  "uncertainty_reason": "Boundary is clear.",
  "meta": {
    "model": "glm-5",
    "temperature": 0.7
  }
}
```

约束：

1. `runtime_annotation.annotation_markup` 是 LLM 运行时格式，不是长期评测主格式。
2. 写入 normalized candidate 时必须同步写入解析后的 `spans`。
3. 模型候选未经人工确认时，`answer` 保持 `null`。
4. 专家接受某个候选后，可将 `answer` 改为 `accept`，也可把该候选提升为 gold sample。

## 6. 标注类型

### 6.1 Span 标注

用于术语、实体、概念片段。

```json
{
  "id": "s1",
  "text": "heart failure treatment",
  "tokens": [],
  "spans": [
    {"id": "T1", "start": 0, "end": 13, "text": "heart failure", "label": "Disease", "implicit": false},
    {"id": "T2", "start": 14, "end": 23, "text": "treatment", "label": "Intervention", "implicit": false}
  ],
  "relations": [],
  "answer": "accept",
  "meta": {"unit": "phrase"}
}
```

### 6.2 Relation 标注

用于实体关系、因果关系、概念关系。Prodigy relation 常使用 `head / child / label` 表达 token 关系；Rosetta 在 span 任务中优先使用 `head_span_id / child_span_id`，避免 tokenization 改变导致关系漂移。

```json
{
  "id": "s2",
  "text": "Aspirin reduces inflammation.",
  "tokens": [],
  "spans": [
    {"id": "T1", "start": 0, "end": 7, "text": "Aspirin", "label": "Drug", "implicit": false},
    {"id": "T2", "start": 16, "end": 28, "text": "inflammation", "label": "Condition", "implicit": false}
  ],
  "relations": [
    {"id": "R1", "head_span_id": "T1", "child_span_id": "T2", "label": "TREATS"}
  ],
  "answer": "accept",
  "meta": {"unit": "sentence"}
}
```

### 6.3 概念包含 / 层级关系

概念包含是 relation 的一种，统一用 `CONTAINS / PART_OF / SUBTYPE_OF` 等标签表达。

```json
{
  "id": "s3",
  "text": "MOF synthesis condition includes reaction temperature.",
  "tokens": [],
  "spans": [
    {"id": "T1", "start": 0, "end": 23, "text": "MOF synthesis condition", "label": "Concept", "implicit": false},
    {"id": "T2", "start": 33, "end": 53, "text": "reaction temperature", "label": "Subconcept", "implicit": false}
  ],
  "relations": [
    {"id": "R1", "head_span_id": "T1", "child_span_id": "T2", "label": "CONTAINS"}
  ],
  "answer": "accept",
  "meta": {"unit": "sentence"}
}
```

### 6.4 句子级标注

单标签分类使用 `label`：

```json
{
  "id": "sent-001",
  "text": "This sentence describes a heart failure treatment.",
  "label": "Relevant",
  "answer": "accept",
  "meta": {"unit": "sentence"}
}
```

多标签分类使用 `options + accept`：

```json
{
  "id": "sent-002",
  "text": "The article discusses symptoms and treatment.",
  "options": [
    {"id": "SYMPTOM", "text": "Symptom"},
    {"id": "TREATMENT", "text": "Treatment"},
    {"id": "DIAGNOSIS", "text": "Diagnosis"}
  ],
  "accept": ["SYMPTOM", "TREATMENT"],
  "answer": "accept",
  "meta": {"unit": "sentence"}
}
```

### 6.5 段落级标注

段落级任务仍然是一条 task，`meta.unit` 标成 `paragraph`。如果段内还有 span，可同时使用 `spans`。

```json
{
  "id": "para-001",
  "text": "This paragraph introduces the synthesis route.",
  "options": [
    {"id": "METHOD", "text": "Method"},
    {"id": "BACKGROUND", "text": "Background"}
  ],
  "accept": ["METHOD"],
  "spans": [
    {"id": "T1", "start": 31, "end": 46, "text": "synthesis route", "label": "Method_Term", "implicit": false}
  ],
  "relations": [],
  "answer": "accept",
  "meta": {"unit": "paragraph", "doc_id": "paper-001", "paragraph_index": 3}
}
```

### 6.6 文章级标注

整篇文章标注用 `meta.unit = document`。质量评分、来源、生成参数放入 `meta`。

```json
{
  "id": "doc-001",
  "text": "Full article text...",
  "options": [
    {"id": "KEEP", "text": "Keep"},
    {"id": "REJECT", "text": "Reject"},
    {"id": "NEEDS_REVIEW", "text": "Needs review"}
  ],
  "accept": ["KEEP"],
  "answer": "accept",
  "meta": {
    "unit": "document",
    "domain": "hard_science_news",
    "quality_score": 0.87,
    "source": "generated"
  }
}
```

## 7. 当前代码实现

主要落点：

1. [app/research/bootstrap_io.py](../../app/research/bootstrap_io.py)
- `sample_from_dict()`: 读取 Prodigy-compatible JSONL，并兼容旧顶层 `spans`、旧 `annotation.layers.spans`、旧 `gold_annotation`。
- `sample_to_dict()`: 写出 `rosetta.prodigy_jsonl.v1`。
- `candidate_from_dict()`: 读取模型候选，优先解析 `runtime_annotation.annotation_markup`，并兼容旧 `annotation_markup`。
- `candidate_to_dict()`: 写出 `rosetta.prodigy_candidate.v1`。

2. [app/research/bootstrap_contracts.py](../../app/research/bootstrap_contracts.py)
- `BootstrapSpan`: 内部 span 契约。
- `BootstrapSample`: 内部 gold / sample 契约。
- `BootstrapCandidate`: 内部模型候选契约。
- `validate_span_against_text()`: 校验 offset 与原文一致。

3. [app/domain/annotation_doc.py](../../app/domain/annotation_doc.py)
- 继续负责旧 UI / 概念样例的 AnnotationDoc 结构和行内 markup 互转。
- Concept Bootstrap 的新 JSONL 写出不再使用 `annotation.layers` 作为主格式，但读取层保持兼容。

## 8. 兼容策略

读取时兼容：

1. `rosetta.prodigy_jsonl.v1`
2. 旧顶层 `spans`
3. 旧 `annotation.layers.spans`
4. 旧 `gold_annotation`
5. 旧 `annotation_markup`

写出时统一：

1. samples: `rosetta.prodigy_jsonl.v1`
2. candidates: `rosetta.prodigy_candidate.v1`

## 8.1 与 PLM 对比的字段建议

如果导出数据用于 PLM / LLM 对比实验，建议在 `meta` 中保留：

1. `concept_version_id`
2. `source_pool`: `gold / pseudo_high_confidence / reviewed / hard_example`
3. `route`: `auto_accept / review / audit / reject`
4. `score`
5. `agreement`
6. `avg_confidence`
7. `reviewed`
8. `human_edit_type`
9. `model`
10. `run_id`

这些字段不改变 Prodigy-compatible 顶层结构，但能支持后续样本效率、人工审核收益和模型成本分析。

## 9. LLM 运行时格式

模型运行时仍使用更容易输出的行内 markup：

```text
[heart failure]{Specific_Term} [ventricular assist devices]{Specific_Term}
```

原因：

1. 模型不需要计算字符 offset。
2. 标签贴近原文，人工也容易读。
3. 解析后可以确定性转换为 `spans` 并校验边界。

长期落盘时，行内 markup 只保存在 `runtime_annotation.annotation_markup`，评测和检索以 `spans` 为准。
