# Embedding Retrieval

Last updated: 2026-05-08

Rosetta’s default reference retrieval backend is:

```text
rosetta-local-hash-384
```

It uses local word/character n-gram feature hashing and cosine similarity. It does not call DeepSeek, Zhipu, or other embedding APIs and does not consume tokens.

Retrieved examples may still increase downstream LLM annotation prompt tokens when they are injected as context.

Canonical Chinese reference: [Embedding Retrieval](../../developer/EMBEDDING_RETRIEVAL.md).
