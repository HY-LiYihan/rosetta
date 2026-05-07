# LLM Service Runtime

Last updated: 2026-05-08

Rosetta treats each LLM call as a service call:

```text
workflow
  -> LLMCall
  -> provider profile
  -> bounded scheduler
  -> progress events
  -> token/cost accounting
  -> response artifact
```

The runtime should record provider, model, concurrency, retry, timing, token/cost metadata, and progress events. Provider-specific limits should be enforced through provider profiles rather than scattered page code.

Canonical Chinese reference: [LLM Service Runtime](../../developer/LLM_SERVICE_RUNTIME.md).
