<div align="center">

# Rosetta

基于 Streamlit 的本地优先 Agentic Annotation Tool。

<p>
  <a href="https://hy-liyihan.github.io/rosetta/">
    <img src="https://img.shields.io/badge/Docs-%E6%96%87%E6%A1%A3%E7%AB%99-c2410c?style=flat-square" alt="Docs">
  </a>
  <a href="https://github.com/HY-LiYihan/rosetta">
    <img src="https://img.shields.io/badge/GitHub-HY--LiYihan%2Frosetta-111111?style=flat-square&logo=github" alt="GitHub">
  </a>
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="MIT License">
  </a>
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11">
  <img src="https://img.shields.io/badge/Streamlit-UI-FF4B4B?style=flat-square&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Docker-%E6%94%AF%E6%8C%81-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
</p>

</div>

## 项目定位

Rosetta 现在定位为一个 **本地优先标注工具**，不是 `research` 与 `corpusgen` 两条科研流水线的集合。它围绕真实标注路径组织能力：

```text
工作台 -> 概念实验室 -> 批量标注 -> 审核队列 -> 导出与可视化
```

核心目标是让使用者用一句话概念描述和 15 条金样例启动项目，通过批量模型标注、低置信复核、自洽性路由和可回放运行记录，逐步得到可用的数据集。

## 快速入口

| 入口 | 地址 | 用途 |
| --- | --- | --- |
| 文档站首页 | [hy-liyihan.github.io/rosetta](https://hy-liyihan.github.io/rosetta/) | 所有文档的主入口 |
| 架构总览 | [docs/developer/ARCHITECTURE.md](./docs/developer/ARCHITECTURE.md) | 新 `core/workflows/agents/data/runtime` 分层 |
| 用户教程 | [docs/user/TUTORIAL.md](./docs/user/TUTORIAL.md) | 页面使用方式 |
| 标注存储格式 | [docs/developer/ANNOTATION_JSONL_FORMAT.md](./docs/developer/ANNOTATION_JSONL_FORMAT.md) | Prodigy-compatible JSONL profile |
| 运行时标注格式 | [docs/developer/ANNOTATION_FORMAT.md](./docs/developer/ANNOTATION_FORMAT.md) | `[原文]{标签}` / `[!隐含义]{标签}` |
| 统一 CLI | [scripts/tool/rosetta_tool.py](./scripts/tool/rosetta_tool.py) | workflow 命令入口 |
| 变更记录 | [docs/CHANGELOG.md](./docs/CHANGELOG.md) | 版本与阶段记录 |

## 核心能力

| 能力 | 说明 |
| --- | --- |
| Streamlit tool UI | 默认 5 个中文主页面：工作台、概念实验室、批量标注、审核队列、导出与可视化 |
| Agent Kernel | 统一执行 goal、context、tool registry、policy，并记录 `WorkflowRun` 与 `AgentStep` |
| Tool Registry | 将检索、标注、judge、JSON repair、导出等能力做成可组合 tool |
| Context Engine | 支持 fresh tail、summary、retrieval chunks 和字符预算控制 |
| Prodigy-compatible JSONL | 长期存储沿用 `text / tokens / spans / relations / label / options / accept / answer / meta` |
| Runtime Store | 本地 SQLite 存储项目、任务、候选、审核、批量任务、运行记录和产物 |
| 兼容旧能力 | 原 bootstrap、corpus generation 保留为 compatibility wrapper |
| Docker 部署 | 构建期安装依赖，运行期挂载 `/opt/rosetta/runtime` |

## 新系统结构

| 层级 | 主要目录 | 职责 |
| --- | --- | --- |
| UI | `app/ui/` | Streamlit 页面、组件、viewmodel |
| Core | `app/core/` | Project、AnnotationTask、Prediction、ReviewTask、WorkflowRun、AgentStep |
| Workflows | `app/workflows/` | 用户可执行流程：annotation、bootstrap、corpus、evaluation |
| Agents | `app/agents/` | AgentKernel、ToolRegistry、ContextEngine、Skill |
| Data | `app/data/` | Prodigy JSONL、Label Studio edge adapter、导入导出 |
| Runtime | `app/runtime/` | 本地路径、SQLite store、run/artifact/trace 持久化 |
| Infrastructure | `app/infrastructure/` | LLM provider、embedding、config、debug |
| Legacy | `app/research/`, `app/corpusgen/` | 暂时保留，供 wrappers 和旧脚本兼容 |

## 快速开始

### Docker 部署

```bash
sudo mkdir -p /opt/streamlit /opt/rosetta/runtime
cd /opt/streamlit

if [ ! -d rosetta ]; then
  git clone https://github.com/HY-LiYihan/rosetta.git
else
  git -C rosetta fetch --all --prune
  git -C rosetta pull --ff-only origin main
fi

cd /opt/streamlit/rosetta
cp -n .env.example .env
./scripts/deploy/deploy.sh
./scripts/ops/healthcheck.sh
```

访问地址：`http://localhost:8501`

### Conda 开发

```bash
git clone https://github.com/HY-LiYihan/rosetta.git
cd rosetta

conda env create -f environment.yml
conda activate rosetta-dev

python -m compileall app streamlit_app.py
python -m unittest discover -s tests -p 'test_*.py'
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
```

## 页面入口

| 页面 | 用途 |
| --- | --- |
| 工作台 | 系统概览、最近任务、待审核数量和主流程快捷入口 |
| 概念实验室 | 创建标注项目，编辑概念阐释，维护 15 条金样例，验证并修订概念 |
| 批量标注 | 上传 TXT / JSONL / CSV，自动分句和 tokenize，提交本地批量任务 |
| 审核队列 | 按置信度阈值逐条展示待审核样本，支持候选选择、人工修正和疑难样例标记 |
| 导出与可视化 | 查看统计、标签分布、自洽性分布，并导出 JSONL、报告和运行清单 |

`Corpus Builder` 继续保留为高级语料生成能力，但不再进入默认主导航。

## CLI

新的统一入口：

```bash
python scripts/tool/rosetta_tool.py bootstrap-analyze \
  --samples configs/research/bootstrap/acter_heart_failure.samples.example.jsonl \
  --candidates configs/research/bootstrap/acter_heart_failure.candidates.example.jsonl \
  --record

python scripts/tool/rosetta_tool.py corpus-prepare \
  --config configs/corpusgen/domain/linguistics_zh_qa.json \
  --dataset configs/corpusgen/domain/linguistics_zh_seed.example.jsonl \
  --record

python scripts/tool/rosetta_tool.py runs
```

旧 `scripts/research/*` 和 `scripts/corpusgen/*` 仍可用，但会提示迁移到统一 CLI。

## 数据格式

Rosetta 区分两层格式：

| 格式 | 用途 |
| --- | --- |
| LLM runtime markup | 给模型输出和人工快速阅读，形如 `[heart failure]{Term}` |
| Prodigy-compatible JSONL | 长期存储、评测、导入导出和人工复核 |

存储格式见 [ANNOTATION_JSONL_FORMAT.md](./docs/developer/ANNOTATION_JSONL_FORMAT.md)。

## 开发检查

```bash
python -m compileall app streamlit_app.py
python -m unittest discover -s tests -p 'test_*.py'
for f in $(find scripts -type f -name '*.sh'); do bash -n "$f"; done
mkdocs build --strict --clean
```

## License

本项目采用 MIT 许可证，详见 [LICENSE](./LICENSE)。

---

最后更新：2026-04-29
