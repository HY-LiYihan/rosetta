# Embedding Retrieval

更新时间: 2026-05-05

Rosetta 的主流程现在默认使用本地轻量文本向量检索，用于“定义与规范”的 top-k 参考样例验证，以及批量标注上下文中的相似样例 / 边界远例选择。

## 1. 当前默认

默认模型标识：

```text
rosetta-local-hash-384
```

它不是 DeepSeek、智谱或其他远端 embedding API，而是本地 feature hashing embedding：

1. 不调用外部 API。
2. 不消耗 token。
3. 不需要下载 transformer 权重。
4. 只依赖 `numpy`。
5. 对 word n-gram 和 char n-gram 做稳定 hash，再做 L2 normalization，用 cosine 排序。

这类方法借鉴 OpenWebUI / RAG 工具常见的“embedding backend 可插拔 + 本地 fallback”设计，但 Rosetta 第一版先选择更轻的本地 hashing backend，避免在 annotation UI 中强制安装 `torch`、`sentence-transformers`、FAISS 或 Chroma。

## 2. 为什么不继续用 token overlap

旧的 top-k 参考样例主要依赖词面 overlap：

```text
query/doc -> tokenize -> token count cosine 或 Jaccard
```

这个方案稳定、可解释，但问题明显：

1. 只要换词、派生词或拼写形态变化，分数会掉得很快。
2. 它更像关键词匹配，不像统一的 retrieval backend。
3. 后续要接 sentence-transformers、智谱 `embedding-3` 或本地 ONNX 模型时，接口不够自然。

新的本地 embedding 仍然是轻量近似方法，不应被宣传为 transformer 级语义模型；它的价值是把 Rosetta 主流程先迁移到“向量化 -> cosine top-k -> trace model id”的检索契约上。

## 3. 使用位置

### 定义与规范

`标注验证（top-k 参考）` 会为每条待验证 gold 检索相似 gold：

```text
当前待标注文本
  -> rosetta-local-hash-384 embed
  -> gold pool embed
  -> cosine top-k
  -> 注入为参考样例
```

参考样例只用于理解边界，不是当前文本答案。

从 `v4.5.18` 起，检索结果不再拼进可优化概念定义，而是作为 `reference_examples` 进入运行时 prompt 的专门槽位：

```text
概念定义
  -> 相似参考样例
  -> 冻结标注格式
```

普通 `examples` 仍可用于标签推断，但不会自动作为 few-shot 答案注入 prompt。

### 批量标注

`build_annotation_context()` 使用同一个本地 embedding 排序：

```text
待标注文本
  -> 相似样例 top-k
  -> 剩余样例中低相似度边界远例
  -> failure memory
  -> 批量标注上下文
```

这样“定义与规范”和“批量标注”不会各自维护不同的相似度逻辑。

## 4. 后续可替换后端

后续可以在 `app/infrastructure/embedding` 下增加 provider：

| 后端 | 适用场景 | 代价 |
| --- | --- | --- |
| `rosetta-local-hash-384` | 默认本地 demo、小样本验证、无 API 环境 | 语义能力有限 |
| `sentence-transformers` | 离线语义检索、英文/多语种任务 | 依赖较重，需要模型下载 |
| `embedding-3` | 智谱在线 embedding、研究实验对齐 | 需要 API key，有调用成本 |
| ONNX / GGUF embedding | 本地轻量模型部署 | 需要模型管理和运行时适配 |

OpenWebUI 的主要启发不是绑定某个模型，而是把 embedding 当作可配置服务：模型、维度、缓存、检索参数和 chunk 策略都应显式记录。Rosetta 后续也应在 run metadata 中记录 `retrieval_model / dimensions / top_k / score`。

## 5. 当前边界

1. 当前本地 hashing embedding 不计算 token/cost，usage report 中不应把它记为 LLM token。
2. 当前没有引入 FAISS/Chroma；15 gold 和小批量上下文直接用 `numpy` matrix cosine 足够。
3. 当前没有持久化 embedding cache；小样例每次重算成本很低，后续批量数据再考虑 SQLite 或 `.runtime/indexes/` cache。
4. 当前不声明语义泛化能力，只声明主 workflow 已从 token overlap 切换到本地向量检索契约。
