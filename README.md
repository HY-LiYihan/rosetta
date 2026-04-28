<div align="center">

# Rosetta

面向语言学与术语研究的 LLM 辅助概念标注、语料生成与可复核实验流水线。

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

Rosetta 不是单一标注脚本，而是一个面向科研实验的轻量系统。它把“概念描述、少量金样例、LLM 多轮标注、人工复核、语义检索、语料生成、实验报告”拆成可确认、可回放、可评测的步骤。

当前重点支持两条彼此隔离的 pipeline：

| Pipeline | 目标 | 入口 |
| --- | --- | --- |
| Concept Bootstrap / Research | 用一句话概念描述和少量金样例，迭代出可用于大规模标注的概念定义与标注流程 | [Concept Bootstrap](./docs/developer/BOOTSTRAP_PIPELINE.md) |
| Corpus Generation / Corpus Studio | 从一句话需求开始，分步生成指定领域、题材、语言的语料库，并用 judge 做质量检查 | [Corpus Pipeline](./docs/developer/CORPUS_PIPELINE.md) |

## 快速入口

| 入口 | 地址 | 用途 |
| --- | --- | --- |
| 文档站首页 | [hy-liyihan.github.io/rosetta](https://hy-liyihan.github.io/rosetta/) | 所有文档的主入口，适合从这里开始 |
| 本地文档索引 | [docs/README.md](./docs/README.md) | 在仓库内查看文档层级 |
| 用户教程 | [docs/user/TUTORIAL.md](./docs/user/TUTORIAL.md) | 页面功能、概念管理、标注与 Corpus Studio 使用说明 |
| 标注存储格式 | [docs/developer/ANNOTATION_JSONL_FORMAT.md](./docs/developer/ANNOTATION_JSONL_FORMAT.md) | Prodigy-compatible JSONL profile，长期数据格式 |
| LLM 运行时标注格式 | [docs/developer/ANNOTATION_FORMAT.md](./docs/developer/ANNOTATION_FORMAT.md) | `[原文]{标签}` 与 `[!隐含义]{标签}`，用于 prompt 和解析 |
| 开发者入口 | [docs/developer/README.md](./docs/developer/README.md) | 架构、工作流、脚本、部署、路线图 |
| 变更记录 | [docs/CHANGELOG.md](./docs/CHANGELOG.md) | 每个阶段的功能、文档与版本变化 |

## 核心能力

| 能力 | 说明 |
| --- | --- |
| 多平台模型调用 | 支持 Kimi、DeepSeek、Qwen、Zhipu AI / BigModel 等 OpenAI-compatible API |
| GLM-5 标注与生成 | 默认支持 `glm-5`，并关闭 thinking 以提升结构化输出稳定性 |
| Embedding-3 CPU 检索 | 使用 `embedding-3` 生成向量，配合 numpy CPU index 做相似样例检索 |
| Concept Bootstrap | 以 15 个左右金样例为起点，结合自洽性、低置信复核和对比式检索改写概念定义 |
| Corpus Studio | Streamlit 页面中按 brief、标题、样稿、批量生成、judge 逐步确认 |
| Prodigy-compatible JSONL | 长期标注存储沿用 `text / tokens / spans / relations / label / options / accept / answer / meta` |
| Docker 与 Conda 双环境 | 生产环境优先 Docker，本地开发优先 Conda |

## 系统结构

| 层级 | 主要目录 | 职责 |
| --- | --- | --- |
| UI 层 | `app/ui/`, `streamlit_app.py` | Streamlit 页面、组件、viewmodel，不承载复杂业务规则 |
| Service 层 | `app/services/` | 页面流程编排、LLM 调用、导入导出、Corpus Studio 工作流 |
| Domain 层 | `app/domain/` | 数据 schema、标注格式解析、校验与迁移 |
| Research 层 | `app/research/` | Concept Bootstrap、动态 few-shot、CPU index、复核队列、报告 |
| Corpusgen 层 | `app/corpusgen/` | 独立语料生成 pipeline、memory 压缩、规划、生成、judge |
| Infrastructure 层 | `app/infrastructure/` | 平台配置、凭据读取、OpenAI-compatible provider、运行开关 |
| Scripts 层 | `scripts/` | 部署、运维、数据备份、research / corpusgen CLI |

关键边界：`app/research/*` 与 `app/corpusgen/*` 平行隔离，不互相 import；二者只共享底层 LLM provider、配置和通用基础设施。

## 快速开始

### 方式 A：服务器部署（Docker，推荐生产）

环境要求：

- Python 3.11 镜像环境由 Docker 构建提供
- Docker + Docker Compose
- 2GB+ 可用内存

```bash
sudo mkdir -p /opt/streamlit
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
curl -f http://localhost:8501/_stcore/health
```

访问地址：

- 本机访问：`http://localhost:8501`
- 服务器访问：`http://<server-ip>:8501`

常用运维命令：

```bash
cd /opt/streamlit/rosetta
./scripts/deploy/update.sh
./scripts/data/backup.sh
./scripts/ops/logs.sh
docker compose ps
ls -la /opt/rosetta/runtime
```

### 方式 B：本地开发（Conda，推荐开发）

```bash
git clone https://github.com/HY-LiYihan/rosetta.git
cd rosetta

conda env create -f environment.yml
conda activate rosetta-dev

python -m compileall app streamlit_app.py
python -m unittest discover -s tests -p 'test_*.py'

streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
```

如果本机已经有 `rosetta-dev` 环境，直接执行：

```bash
conda activate rosetta-dev
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
```

### Debug 模式

Debug 模式用于短期留存操作轨迹和中间结果，便于排查模型输出、JSON repair、导入文件和页面流程问题。

```bash
streamlit run streamlit_app.py -- --debug
```

也可以用环境变量启动：

```bash
ROSETTA_DEBUG_MODE=1 streamlit run streamlit_app.py
```

开启后会写入：

- `.runtime/logs/debug/*.jsonl`
- `.runtime/data/debug_uploads/`

## 页面入口

| 页面 | 用途 |
| --- | --- |
| 首页 | 查看系统状态、快速入口和项目概览 |
| 概念管理 | 导入、创建、合并、替换概念与示例 |
| 智能标注 | 选择概念和模型，对输入文本进行 LLM 辅助标注 |
| Corpus Studio | 从一句话 brief 开始，分步确认并生成语料库 |

## 科研脚本入口

### Concept Bootstrap / Research

面向标注实验、pilot audit、自洽性分析、低置信人工复核和报告输出。

```bash
conda activate rosetta-dev
python scripts/research/run_bootstrap.py analyze \
  --experiment configs/research/bootstrap/acter_heart_failure.experiment.json
```

继续阅读：

- [Concept Bootstrap Pipeline](./docs/developer/BOOTSTRAP_PIPELINE.md)
- [Bootstrap Experiments](./docs/developer/BOOTSTRAP_EXPERIMENTS.md)
- [Research Pipeline](./docs/developer/RESEARCH_PIPELINE.md)

### Corpus Generation / Corpusgen

面向指定领域、题材、语言的语料生成，脚本 pipeline 与 `research` runner 分离。

```bash
conda activate rosetta-dev
python scripts/corpusgen/prepare_seeds.py \
  --config configs/corpusgen/domain/linguistics_zh_qa.json \
  --dataset configs/corpusgen/domain/linguistics_zh_seed.example.jsonl
```

完整流程见：

- [Corpus Pipeline](./docs/developer/CORPUS_PIPELINE.md)

## 数据与标注格式

Rosetta 区分“LLM 运行时格式”和“长期存储格式”：

| 格式 | 用途 | 文档 |
| --- | --- | --- |
| Inline markup | 给大模型输出和人工快速阅读，形如 `[heart failure]{Specific_Term}` | [ANNOTATION_FORMAT.md](./docs/developer/ANNOTATION_FORMAT.md) |
| Prodigy-compatible JSONL | 长期存储、评测、导入导出和人工复核，支持 span、relation、分类与选择题 | [ANNOTATION_JSONL_FORMAT.md](./docs/developer/ANNOTATION_JSONL_FORMAT.md) |

## 仓库结构

```text
rosetta/
├── streamlit_app.py
├── app/
│   ├── ui/                 # Streamlit 页面、组件、viewmodel
│   ├── services/           # 页面流程和业务编排
│   ├── domain/             # 数据结构、校验与标注格式
│   ├── research/           # 标注科研 pipeline
│   ├── corpusgen/          # 语料生成 pipeline
│   └── infrastructure/     # LLM provider、凭据、运行配置
├── configs/
│   ├── research/           # research / bootstrap 配置模板
│   └── corpusgen/          # corpusgen 配置模板
├── scripts/
│   ├── research/           # 标注实验 CLI
│   ├── corpusgen/          # 语料生成 CLI
│   ├── deploy/             # Docker 部署脚本
│   ├── ops/                # 运维检查脚本
│   └── data/               # 备份与恢复脚本
├── docs/                   # MkDocs 文档站源文件
├── tests/                  # 单元测试与集成测试
├── Dockerfile
├── docker-compose.yml
├── environment.yml
└── mkdocs.yml
```

## 文档导航

| 文档 | 说明 |
| --- | --- |
| [文档站首页](https://hy-liyihan.github.io/rosetta/) | 在线文档入口 |
| [用户教程](./docs/user/TUTORIAL.md) | 页面使用、概念管理、标注和 Corpus Studio |
| [Concept Bootstrap](./docs/developer/BOOTSTRAP_PIPELINE.md) | 核心研究流程 |
| [标注 JSONL 格式](./docs/developer/ANNOTATION_JSONL_FORMAT.md) | 长期存储格式来源、字段和示例 |
| [架构总览](./docs/developer/ARCHITECTURE.md) | 分层边界与代码职责 |
| [部署与运维](./docs/developer/DEPLOYMENT.md) | Docker 部署、更新、回滚、备份 |
| [变更记录](./docs/CHANGELOG.md) | 版本演进与每阶段改动 |

## 开发协作

默认协作流程：

```text
branch -> small commit -> local validation -> review -> push / PR
```

提交前至少执行：

```bash
python -m compileall app streamlit_app.py
python -m unittest discover -s tests -p 'test_*.py'
for f in $(find scripts -type f -name '*.sh'); do bash -n "$f"; done
```

开发约束见：

- [docs/developer/WORKFLOW.md](./docs/developer/WORKFLOW.md)
- [docs/developer/ARCHITECTURE.md](./docs/developer/ARCHITECTURE.md)

## License

本项目采用 MIT 许可证，详见 [LICENSE](./LICENSE)。

---

最后更新：2026-04-28
