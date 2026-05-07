# Rosetta Docs

Last updated: 2026-05-08

## Official Entrypoints

| Entry | URL | Purpose |
| --- | --- | --- |
| Documentation site | [https://hy-liyihan.github.io/rosetta/](https://hy-liyihan.github.io/rosetta/) | Public documentation for users and maintainers |
| Demo page | [https://rosetta-stone.xyz/](https://rosetta-stone.xyz/) | Demo page, not the documentation site |
| GitHub repository | [https://github.com/HY-LiYihan/rosetta](https://github.com/HY-LiYihan/rosetta) | Source code, issues, deployment files, and project history |

## What Rosetta Is

Rosetta is a local-first, Streamlit-based agentic annotation tool. It helps researchers, linguists, digital humanities teams, and domain experts turn a concept description plus a small gold set into a traceable annotation workflow.

The main user path is:

```text
Project Overview -> Definition & Guideline -> Batch Run -> Review & Fix -> Results & Export
```

The 15 gold examples used in the default workflow are for startup, calibration, and demonstration. They are not a sufficient training set and do not prove generalization to external corpora.

“Local-first” means project data, runtime records, exports, and debug artifacts are written to the local runtime directory or your own deployment directory first. It does not mean Rosetta is offline by default. If you choose a real LLM provider, prompts and task text are sent according to that provider configuration.

## First Pages To Read

1. [Quickstart](./user/TUTORIAL.md): run the official sample and understand the main UI flow.
2. [Prompt Composition](./user/PROMPT_COMPOSITION.md): see what the LLM receives in Chinese and English prompt templates.
3. [Chinese home](../README.md): the canonical full documentation index.

## Language Boundary

The documentation site now has a top language switcher. The English pages are a concise entry layer; the Chinese documentation remains the canonical full reference for now.

The Streamlit app also has `中文 / English` buttons in the sidebar. Those buttons switch the main navigation and primary fixed UI labels. They do not automatically translate user input, task text, model output, labels, logs, database content, or export filenames.
