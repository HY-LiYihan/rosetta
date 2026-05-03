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

Rosetta 也是一套可验证的研究工程：它要证明 LLM agent 在低资源、概念可描述、任务边界会变化或任务不够常规的场景中，能比传统 PLM-first 标注流程更快形成可审计的数据生产闭环。它不声称在完整高质量训练集条件下无条件超过 PLM，而是强调样本效率、概念迭代速度、人类审核收益和过程可追溯性。

从 `v4.2.0` 开始，Rosetta 的主线是 **concept bootstrap loop**：系统会用 15 条金样例反复校准概念阐释，再把失败模式、相似样例、边界远例和专家审核结果反哺到后续批量标注中。

`v4.2.1` 起，概念修订会严格区分“干净提示词”和“诊断日志”：失败摘要、样例编号、模型原始解释只保存在运行日志与 `metadata`，不会再被拼进最终概念阐释。

`v4.2.2` 起，概念自举不再单路径贪心改写。系统会为当前概念和候选概念计算 gold loss，只接受让 15 条金样例表现变好的候选，避免坏提示词越滚越差。

`v4.2.3` 起，文档架构重排为面向两类人群：用户文档强调“照着填就能跑完整标注”，开发文档强调“代码文件架构、运行结构、数据流和实验产物”，研究主张单独说明 Rosetta 如何比较 LLM agent 与 PLM。

`v4.2.4` 起，Rosetta 将 **Prompt-as-Parameter** 写成核心创新：概念 prompt 被视为可训练文本参数，系统通过 Mask 遮挡、对比替换、消融链路和 LLM 自诊断估算 Text Gradient，再用 `LLM-AdamW` 式优化器生成候选，并用 gold loss 验证是否接受。

`v4.3.0` 起，Prompt-as-Parameter 进入最小可用实现：概念自举会切分 prompt 语义片段，生成启发式 Mask 文本梯度，将梯度方向注入候选改写，并把候选 loss、长度惩罚、loss delta 和接受/拒绝结果写入 `ConceptVersion.metadata.prompt_optimization_trace`。

`v4.4.0` 起，概念实验室新增 **提示词优化训练**：系统可以在同一批 15 条金样例上公平比较 `只要求优化`、`失败反思` 和 `文本梯度 AdamW` 三种方法。每种方法独立运行最多 5 轮，每轮生成候选提示词、回到金样例上计算 loss，只接受损失下降的干净版本；最终只把胜出的可用提示词写入 `ConceptVersion.description`，方法对比、loss 曲线、候选日志和原始响应进入 metadata / artifact。

`v4.4.1` 起，提示词优化训练增加 **防背答案检查**：训练反馈可以包含原文、标准答案和模型错误回答，就像学生看批改作业；但学习出来的 operational prompt 不能复制语料词、gold span、模型 span 或可识别答案片段。Rosetta 会用 `MemorizationGuard` 拦截泄露候选，并只在报告中展示 hash / count。当前结论只限于“15 条 gold 内未直接背答案且能通过”，不声称跨样本泛化。

## 快速入口

| 入口 | 地址 | 用途 |
| --- | --- | --- |
| 文档站首页 | [hy-liyihan.github.io/rosetta](https://hy-liyihan.github.io/rosetta/) | 所有文档的主入口 |
| 研究主张 | [docs/ideas/RESEARCH_CLAIMS.md](./docs/ideas/RESEARCH_CLAIMS.md) | LLM agent vs PLM 的创新点、边界和实验方案 |
| Prompt-as-Parameter | [docs/ideas/PROMPT_AS_PARAMETER.md](./docs/ideas/PROMPT_AS_PARAMETER.md) | 文本梯度估算、prompt 优化器和 `LLM-AdamW` |
| 架构总览 | [docs/developer/ARCHITECTURE.md](./docs/developer/ARCHITECTURE.md) | 新 `core/workflows/agents/data/runtime` 分层 |
| 用户教程 | [docs/user/TUTORIAL.md](./docs/user/TUTORIAL.md) | 页面使用方式 |
| 文档评审记录 | [docs/developer/DOCS_REVIEW_ITERATIONS.md](./docs/developer/DOCS_REVIEW_ITERATIONS.md) | 传统语言学家、PLM 研究者、开发者 6 轮评审 |
| 标注存储格式 | [docs/developer/ANNOTATION_JSONL_FORMAT.md](./docs/developer/ANNOTATION_JSONL_FORMAT.md) | Prodigy-compatible JSONL profile |
| 运行时标注格式 | [docs/developer/ANNOTATION_FORMAT.md](./docs/developer/ANNOTATION_FORMAT.md) | `[原文]{标签}` / `[!隐含义]{标签}` |
| 统一 CLI | [scripts/tool/rosetta_tool.py](./scripts/tool/rosetta_tool.py) | workflow 命令入口 |
| 变更记录 | [docs/CHANGELOG.md](./docs/CHANGELOG.md) | 版本与阶段记录 |

## 核心能力

| 能力 | 说明 |
| --- | --- |
| Streamlit tool UI | 默认 5 个中文主页面：工作台、概念实验室、批量标注、审核队列、导出与可视化 |
| 中英文界面 | 侧栏顶部提供 `中文 / English` 全局切换，5 个主页面正文同步切换 |
| 内置案例 | 概念实验室可一键填入“硬科学科普术语标注”完整示例，用户教程提供逐项填写说明 |
| 运行中防重复提交 | 长耗时按钮点击后会切换为运行中状态并禁用，避免重复触发验证、批量提交和审核保存 |
| 概念自举闭环 | 15 条金样例正式校准，用 loss 比较当前版本和候选版本，只接受变好的干净概念 |
| 提示词优化训练 | 在同一批 15 条金样例上比较“只要求优化”“失败反思”“文本梯度 AdamW”，最多 5 轮内以 15/15 通过为成功标准 |
| 防背答案检查 | 训练反馈允许看批改对照，但候选提示词和最终提示词必须通过 `MemorizationGuard`，不能复制语料或答案片段 |
| 文本梯度估算与 prompt 优化器 | 将 prompt 切成可训练语义参数，当前实现 Mask 启发式梯度、LLM-AdamW trace、长度惩罚和 gold loss 验证；对比替换、消融和完整 optimizer state 是下一阶段扩展 |
| LLM / PLM 研究对比 | 文档中明确 low-budget PLM、full-data PLM、zero-shot、ICL、retrieval 和 Rosetta full loop 的比较方式 |
| 上下文增强标注 | 批量标注 prompt 自动加入相似样例、边界远例、高置信样例和失败模式记忆 |
| 主动审核反馈 | 审核结果沉淀错误类型、疑难样例和 gold-like 样例，用于后续检索与修订 |
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

开发约束：

1. 新功能优先进入 `app/workflows`，再调用 `agents / data / runtime`。
2. Streamlit 页面只负责收集输入、展示状态和调用 workflow。
3. 旧 `app/research` 与 `app/corpusgen` 只作为兼容层和算法来源，不再作为产品边界。
4. 实验可复现字段必须进入 SQLite runtime store、artifacts、JSONL 或 report。

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
| 工作台 | 4 个核心指标、最近批量任务、最近审核状态和一个继续下一步入口 |
| 概念实验室 | 创建项目，维护 15 条金样例，运行概念自举校准或提示词优化训练，生成干净概念版本和可追溯失败日志 |
| 批量标注 | 上传 TXT / JSONL / CSV，自动分句和 tokenize，用增强上下文提交本地批量任务 |
| 审核队列 | 按置信度阈值逐条展示待审核样本，记录候选选择、错误类型、疑难样例和 gold-like 反馈 |
| 导出与可视化 | 查看统计、标签分布、自洽性分布，并导出 JSONL、实验报告和运行清单 |

`Corpus Builder` 继续保留为高级语料生成能力，但不再进入默认主导航。

## 完整使用案例

第一次使用可以直接打开“概念实验室”，点击“填入硬科学术语示例”。页面会自动填入项目说明、概念阐释、边界规则、负例规则和 15 条金样例草稿，但不会自动保存。

完整逐步说明见 [用户教程](./docs/user/TUTORIAL.md#8-完整使用案例硬科学英文科普术语标注)。

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

如果数据用于 PLM / LLM 对比实验，建议保留 `concept_version_id / source_pool / route / score / agreement / reviewed / human_edit_type / model / run_id` 等 metadata，方便后续复现实验和统计人工审核收益。

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

最后更新：2026-05-03
