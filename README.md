<div align="center">

# Rosetta

基于 Streamlit 的本地优先智能体式标注工具。

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

## 对外入口

| 入口 | 地址 | 说明 |
| --- | --- | --- |
| 官方文档站 | [hy-liyihan.github.io/rosetta](https://hy-liyihan.github.io/rosetta/) | 面向使用者和开发者的公开文档首页 |
| Demo 页面 | [rosetta-stone.xyz](https://rosetta-stone.xyz/) | 在线体验入口 |
| GitHub 项目 | [github.com/HY-LiYihan/rosetta](https://github.com/HY-LiYihan/rosetta) | 源码、issue、提交记录和部署材料 |

## Rosetta 是什么

Rosetta 是一个 **本地优先的智能体式标注工具**。它面向需要快速建立标注任务的研究者、语言学家、数字人文团队和领域专家，把“一句话概念描述 + 15 条金样例”转成可运行、可复核、可导出的标注流水线。这里的 15 条金样例用于启动、校准和演示，不等于充分训练集，也不保证外部语料泛化。

Rosetta 围绕真实标注路径组织能力，而不是只提供单次模型调用：

```text
项目总览 -> 定义与规范 -> 批量标注 -> 审核与修正 -> 结果与导出
```

核心目标是让使用者先写清楚“什么应该被标出来”，再用 15 条金样例校准概念阐释，随后通过批量模型标注、低置信复核、自洽性路由和可回放运行记录，逐步得到可用的数据集。

Rosetta 也是一套可验证的研究工程：它要检验大模型智能体在低资源、概念可描述、任务边界会变化或任务不够常规的场景中，是否能比传统 PLM-first 标注流程更快形成可审计的数据生产闭环。它不声称在完整高质量训练集条件下无条件超过 PLM，而是强调样本效率、概念迭代速度、人类审核收益和过程可追溯性。

“本地优先”指项目数据、运行记录、导出文件和调试产物优先落在本机或你部署的运行目录中；它不等于默认离线，也不等于不会调用云端大模型。选择真实 provider 时，文本和 prompt 会按对应平台配置发送给模型服务。

核心能力集中在四件事：

1. **定义优化**：用 15 条金样例验证概念阐释，比较候选定义，只保存表现更好的版本。
2. **稳定输出格式**：用户负责写清概念边界，Rosetta 固定标签、JSON 字段和 `[span]{Term}` 标注格式。
3. **上下文增强标注**：批量标注时结合相似参考样例、边界远例、失败模式和人工审核反馈。
4. **可回放产物**：导出 Prodigy-compatible JSONL、运行报告、prompt 版本和实验 trace。

提示词优化训练包含三种方法：`sgd_candidate_search / critic_adamw_optimizer / mask_guided_optimization`。训练结果只说明当前 gold 集合内的表现；如果要证明泛化，需要额外 held-out 数据或外部数据集。

## 快速入口

| 入口 | 地址 | 用途 |
| --- | --- | --- |
| 官方文档站 | [hy-liyihan.github.io/rosetta](https://hy-liyihan.github.io/rosetta/) | 所有文档的主入口 |
| Demo 页面 | [rosetta-stone.xyz](https://rosetta-stone.xyz/) | 在线体验入口 |
| GitHub 项目 | [github.com/HY-LiYihan/rosetta](https://github.com/HY-LiYihan/rosetta) | 源码、issue、部署与提交记录 |
| 研究主张 | [docs/ideas/RESEARCH_CLAIMS.md](./docs/ideas/RESEARCH_CLAIMS.md) | LLM agent vs PLM 的创新点、边界和实验方案 |
| Prompt-as-Parameter | [docs/ideas/PROMPT_AS_PARAMETER.md](./docs/ideas/PROMPT_AS_PARAMETER.md) | 文本梯度估算、prompt 优化器和 `LLM-AdamW` |
| 提示词构成 | [docs/user/PROMPT_COMPOSITION.md](./docs/user/PROMPT_COMPOSITION.md) | 标注运行时 prompt 的中英文模板和输出格式 |
| 架构总览 | [docs/developer/ARCHITECTURE.md](./docs/developer/ARCHITECTURE.md) | 新 `core/workflows/agents/data/runtime` 分层 |
| Embedding 检索 | [docs/developer/EMBEDDING_RETRIEVAL.md](./docs/developer/EMBEDDING_RETRIEVAL.md) | 本地轻量 embedding、top-k 参考样例与后续可插拔后端 |
| 用户教程 | [docs/user/TUTORIAL.md](./docs/user/TUTORIAL.md) | 页面使用方式 |
| 标注存储格式 | [docs/developer/ANNOTATION_JSONL_FORMAT.md](./docs/developer/ANNOTATION_JSONL_FORMAT.md) | Prodigy-compatible JSONL profile |
| 运行时标注格式 | [docs/developer/ANNOTATION_FORMAT.md](./docs/developer/ANNOTATION_FORMAT.md) | JSON+markup、`[原文]{标签}` / `[!隐含义]{标签}` 与格式修复契约 |
| 统一 CLI | [scripts/tool/rosetta_tool.py](./scripts/tool/rosetta_tool.py) | workflow 命令入口 |
| 变更记录 | [docs/CHANGELOG.md](./docs/CHANGELOG.md) | 版本与阶段记录 |

## 核心能力

| 能力 | 说明 |
| --- | --- |
| Streamlit 本地界面 | 默认 5 个中文主页面：项目总览、定义与规范、批量标注、审核与修正、结果与导出 |
| 中英文切换按钮 | 应用侧栏提供 `中文 / English` 两个切换按钮；主导航和主要固定界面文案随按钮切换，用户输入、日志和模型输出不自动翻译 |
| 文档站语言切换 | 文档站支持中文和 English 两种语言 |
| 提示词构成对照 | 标注提示词提供中英文同构模板，默认使用中文模板 |
| 内置案例 | 程序启动即内置“专业命名实体标注”官方样例，包含 15 条金样例和基础提示词 |
| 运行中防重复提交 | 长耗时按钮点击后会切换为运行中状态并禁用，避免重复触发验证、批量提交和审核保存 |
| 调试追踪页 | debug 模式下可通过 `http://localhost:8501/debug` 查看大模型请求和回复，日志落盘到 `.runtime/logs/debug/` |
| 定义优化闭环 | 15 条金样例正式校准，用 loss 比较当前版本和候选版本，只接受变好的干净概念 |
| 提示词优化训练 | 在同一批 15 条金样例上比较“候选搜索优化”“批判器 AdamW 优化”“遮挡梯度优化”，达到 15/15 即成功，否则按连续无下降轮数或最大轮数停止 |
| 大模型服务运行时 | 提示词验证和定义优化会记录进度、token、耗时和重试信息 |
| 本地相似样例检索 | top-k 参考样例和批量上下文默认使用 `rosetta-local-hash-384`，零 API、零 token 成本，后续可插拔替换为在线或本地语义 embedding |
| 实时进度与事件日志 | 提示词优化训练后台执行，SQLite 轮询展示阶段、ETA、调用数、token、修复和可下载 `run_events.jsonl` |
| 概念验证进度 | “验证概念”并发检查 15 条 gold，页面显示进度条、运行中数量、ETA、token 和耗时 |
| 三层提示词验证 | 在“定义与规范”中可分别运行格式验证、无样例大模型标注验证、带 top-k 相似参考样例的标注验证 |
| 冻结输出协议 | “定义与规范”页面分栏展示可优化定义与冻结协议；定义优化只改概念语义，JSON 字段、标签、标注格式、解析和格式修复由 Rosetta 固定注入；标注格式通过选项选择，不再手写 |
| 统一标注 prompt 框架 | 概念验证、批量标注和候选回测统一使用“概念定义 -> 相似参考样例 -> 标注格式 -> 通用格式示例 -> 待标注文本 -> 任务强调”；相似参考样例只有显式检索后才填充 |
| 统一标注助手身份 | 概念验证、候选回测、单条标注和批量标注共享同一个 system prompt，差异只放在 user prompt 的任务内容中 |
| 防背答案与去语料化修复 | 训练反馈允许看批改对照；候选提示词若复制语料或答案片段，会先修复为抽象规则，修复失败才拒绝 |
| 提示词版本历史 | 每次人工或训练式优化都会保存 prompt 版本，训练 run 记录 v0、v1 ... vn 以及对应 loss / pass count / accepted candidate |
| 三方法真实对比实验 | `sgd_candidate_search / critic_adamw_optimizer / mask_guided_optimization` 从同一简单提示词出发，连续 5 轮 loss 无下降才停止，并输出 Markdown/JSON/JSONL 结果 |
| 文本梯度估算与 prompt 优化器 | 将 prompt 切成可训练语义参数，结合 Mask 启发式梯度、LLM-AdamW trace、长度惩罚和 gold loss 验证 |
| LLM / PLM 研究对比 | 文档中明确 low-budget PLM、full-data PLM、zero-shot、ICL、retrieval 和 Rosetta full loop 的比较方式 |
| 上下文增强标注 | 批量标注 prompt 自动加入相似样例、边界远例、高置信样例和失败模式记忆 |
| 主动审核反馈 | 审核结果沉淀错误类型、疑难样例和 gold-like 样例，用于后续检索与修订 |
| 智能体执行内核 | 统一执行目标、上下文、工具和策略，并记录 `WorkflowRun` 与 `AgentStep` |
| 工具注册表 | 将检索、标注、judge、JSON repair、导出等能力做成可组合工具 |
| 上下文引擎 | 支持最新片段、摘要、检索片段和字符预算控制 |
| Prodigy-compatible JSONL | 长期存储沿用 `text / tokens / spans / relations / label / options / accept / answer / meta` |
| Runtime Store | 本地 SQLite 存储项目、任务、候选、审核、批量任务、运行记录和产物 |
| Docker 部署 | 构建期安装依赖，运行期挂载 `/opt/rosetta/runtime` |

## 系统结构

| 层级 | 主要目录 | 职责 |
| --- | --- | --- |
| UI | `app/ui/` | Streamlit 页面、组件、viewmodel |
| Core | `app/core/` | Project、AnnotationTask、Prediction、ReviewTask、WorkflowRun、AgentStep |
| Workflows | `app/workflows/` | 用户可执行流程：annotation、bootstrap、corpus、evaluation |
| Agents | `app/agents/` | AgentKernel、ToolRegistry、ContextEngine、Skill |
| Data | `app/data/` | Prodigy JSONL、Label Studio edge adapter、导入导出 |
| Runtime | `app/runtime/` | 本地路径、SQLite store、run/artifact/trace 持久化 |
| Infrastructure | `app/infrastructure/` | LLM provider、embedding、config、debug |

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

### Conda 运行

```bash
git clone https://github.com/HY-LiYihan/rosetta.git
cd rosetta

conda env create -f environment.yml
conda activate rosetta-dev

streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
```

本机排障时可以开启 debug 模式：

```bash
streamlit run streamlit_app.py -- --debug
```

然后直接打开 `http://localhost:8501/debug` 查看完整 LLM prompt / response。Debug 页面会记录提示词、语料片段和模型回复，请只在本机排障时开启。

## 页面入口

| 页面 | 用途 |
| --- | --- |
| 项目总览 | 4 个核心指标、最近批量任务、最近审核状态和一个继续下一步入口 |
| 定义与规范 | 创建项目，维护 15 条金样例，分清可优化定义和冻结输出协议，运行提示词验证或提示词优化 |
| 批量标注 | 上传 TXT / JSONL / CSV，自动分句和 tokenize，用增强上下文提交本地批量任务 |
| 审核与修正 | 按置信度阈值逐条展示待审核样本，记录候选选择、错误类型、疑难样例和 gold-like 反馈 |
| 结果与导出 | 查看统计、标签分布、自洽性分布，并导出 JSONL、实验报告和运行清单 |
| 调试追踪 | debug 模式下通过 `/debug` 查看 LLM prompt / response 子对话和 debug 事件 |

`Corpus Builder` 是高级语料生成能力，可按需使用。

## 完整使用案例

第一次使用可以直接打开“定义与规范”。程序启动时会自动把主运行库刷新为官方样例“专业命名实体标注”，页面中已经有项目、概念阐释、15 条金样例和初始概念版本。

完整逐步说明见 [用户教程](./docs/user/TUTORIAL.md#8-完整使用案例专业命名实体标注)。

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

推荐使用统一 CLI。

## 数据格式

Rosetta 区分两层格式：

| 格式 | 用途 |
| --- | --- |
| LLM runtime markup | 给模型输出和人工快速阅读，形如 `[heart failure]{Term}` |
| Prodigy-compatible JSONL | 长期存储、评测、导入导出和人工复核 |

存储格式见 [ANNOTATION_JSONL_FORMAT.md](./docs/developer/ANNOTATION_JSONL_FORMAT.md)。

如果数据用于 PLM / LLM 对比实验，建议保留 `concept_version_id / source_pool / route / score / agreement / reviewed / human_edit_type / model / run_id` 等 metadata，方便后续复现实验和统计人工审核收益。

## 开发者文档

架构、工作流、部署和检查命令见 [Developer Overview](./docs/developer/README.md) 与 [Workflow](./docs/developer/WORKFLOW.md)。

## License

本项目采用 MIT 许可证，详见 [LICENSE](./LICENSE)。

---

最后更新：2026-05-08
