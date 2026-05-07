# Rosetta Docs

Last updated: 2026-05-08

## Official Entrypoints

| Entry | URL | Purpose |
| --- | --- | --- |
| Documentation site | [https://hy-liyihan.github.io/rosetta/](https://hy-liyihan.github.io/rosetta/) | Public documentation for users and maintainers |
| Demo page | [https://rosetta-stone.xyz/](https://rosetta-stone.xyz/) | Interactive demo for trying Rosetta in the browser |
| GitHub repository | [https://github.com/HY-LiYihan/rosetta](https://github.com/HY-LiYihan/rosetta) | Source code, issues, deployment files, and project history |

## What Rosetta Is

Rosetta is a local-first, Streamlit-based agentic annotation tool. It helps researchers, linguists, digital humanities teams, and domain experts turn a concept description plus a small gold set into a traceable annotation workflow.

The main user path is:

```text
Project Overview -> Definition & Guideline -> Batch Run -> Review & Fix -> Results & Export
```

The 15 gold examples used in the default workflow are for startup, calibration, and demonstration. They are not a sufficient training set and do not prove generalization to external corpora.

“Local-first” means project data, runtime records, exports, and debug artifacts are written to the local runtime directory or your own deployment directory first. It does not mean Rosetta is offline by default. If you choose a real LLM provider, prompts and task text are sent according to that provider configuration.

## Documentation Map

Use the pages below to find user guides, research notes, developer references, deployment guidance, and release history.

| Need | English page |
| --- | --- |
| First run | [Quickstart](./user/TUTORIAL.md) |
| Prompt structure | [Prompt Composition](./user/PROMPT_COMPOSITION.md) |
| Research claim | [LLM Agent vs PLM](./ideas/RESEARCH_CLAIMS.md) |
| Prompt-as-Parameter | [Prompt-as-Parameter](./ideas/PROMPT_AS_PARAMETER.md) |
| Core idea | [Core Annotation Bootstrap](./ideas/CORE_ANNOTATION_BOOTSTRAP.md) |
| Guideline bootstrap workflow | [Guideline Bootstrap](./developer/BOOTSTRAP_PIPELINE.md) |
| Bootstrap experiments | [Bootstrap Experiments](./developer/BOOTSTRAP_EXPERIMENTS.md) |
| Corpus builder | [Corpus Builder](./developer/CORPUS_PIPELINE.md) |
| Runtime annotation format | [Annotation Format](./developer/ANNOTATION_FORMAT.md) |
| JSONL storage format | [Annotation JSONL Format](./developer/ANNOTATION_JSONL_FORMAT.md) |
| Developer overview | [Developer Overview](./developer/README.md) |
| Architecture | [Architecture](./developer/ARCHITECTURE.md) |
| LLM runtime | [LLM Service Runtime](./developer/LLM_SERVICE_RUNTIME.md) |
| Embedding retrieval | [Embedding Retrieval](./developer/EMBEDDING_RETRIEVAL.md) |
| Workflow | [Workflow](./developer/WORKFLOW.md) |
| Scripts | [Scripts](./developer/SCRIPTS.md) |
| Roadmap | [Roadmap](./developer/ROADMAP.md) |
| Deployment | [Deployment](./developer/DEPLOYMENT.md) |
| Changelog | [Changelog](./CHANGELOG.md) |

## Language

Use the language switcher to open the same topic in English or Chinese when both versions are available.

In the Streamlit app, the language buttons change interface labels only. Project content, task text, labels, model outputs, logs, and exports remain in the language you entered or selected for the task.
