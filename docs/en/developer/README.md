# Developer Overview

Last updated: 2026-05-08

New implementation work should follow the current architecture boundaries:

1. `app/core`: stable domain models.
2. `app/workflows`: user-executable workflows.
3. `app/agents`: agent kernel, tools, and context.
4. `app/data`: annotation formats and adapters.
5. `app/runtime`: SQLite store, paths, runs, artifacts, and traces.
6. `app/infrastructure`: LLM providers, embeddings, config, and debug tooling.

Legacy `app/research` and `app/corpusgen` remain for compatibility and migration reference.

Canonical Chinese reference: [Developer Overview](../../developer/README.md).
