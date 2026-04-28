# 用户教程（网站使用版）

更新时间: 2026-04-29

Rosetta 是一个基于 Streamlit 的本地优先标注工具。默认界面为中文，主流程只保留 5 个页面。

## 1. 使用流程总览

推荐路径：

```text
工作台 -> 概念实验室 -> 批量标注 -> 审核队列 -> 导出与可视化
```

这条路径对应一次完整标注实验：

1. 在“概念实验室”输入一句话概念描述，并维护约 15 条金样例。
2. 在“批量标注”上传 TXT、JSONL 或 CSV，系统自动生成标注任务。
3. 批量任务按多次采样、自洽性和模型自评置信度路由。
4. 低置信、低自洽和抽检样本进入“审核队列”。
5. 在“导出与可视化”下载 Prodigy-compatible JSONL 和报告。

## 2. 工作台

“工作台”只展示最必要的信息：

1. 当前任务总数、候选标注数、待审核数和批量任务数。
2. 一个“继续下一步”入口，根据当前状态跳转到概念实验室、批量标注、审核队列或导出与可视化。
3. 最近批量任务和最近审核状态。
4. 折叠区中的完整流程说明和本地运行目录。

## 3. 概念实验室

“概念实验室”负责产出稳定概念阐释和金样例库。

需要填写：

1. 标注项目名称和说明。
2. 概念名称。
3. 一句话概念描述。
4. 标签集合。
5. 边界说明。
6. 负例规则。
7. 模型运行时标注格式，默认是 `[原文]{标签}`。

金样例支持三种输入：

1. 手动新增一条原文和行内标注。
2. 粘贴 JSONL。
3. 上传 JSONL 或 CSV。

保存后会写入本地 SQLite，并可导出：

1. `concept_guideline.md`
2. `gold_examples.jsonl`
3. `concept_versions.jsonl`

“验证概念”可以先用本地结构验证跑通流程，也可以选择已配置的大模型对金样例试标。验证结果会分成通过、失败、边界不稳定三类，失败样例可用于生成修订草案。

## 4. 批量标注

“批量标注”负责把原始语料变成任务队列。

输入支持：

1. TXT：默认按段落和中英文句末标点分句，并做轻量 tokenize。
2. JSONL：优先按 Prodigy-compatible task 读取。
3. CSV：选择文本列，其余列进入 `meta`。

提交任务时可以设置：

1. 每条采样次数：1、3 或 5。
2. 并发数：默认 4。
3. 人工审核阈值：默认 0.75。
4. 高置信抽检比例：默认 5%。

执行方式：

1. 只提交队列：创建任务后不立刻调用模型。
2. 本地模拟：用于本机 smoke test，不消耗 API。
3. 调用大模型：使用已配置平台后台执行。

批量任务写入本地 SQLite 队列。提交后可以离开页面，之后到“审核队列”查看低置信样本。

## 5. 审核队列

“审核队列”不是表格后台，而是逐条弹出的专家审核台。

顶部可以设置：

1. 低于多少置信度需要审核。
2. 是否包含高置信抽检样本。
3. 批次过滤。

每条审核卡片展示：

1. 原文。
2. 当前概念阐释。
3. 少量金样例参考。
4. 候选 A/B/C/D/E。
5. 综合置信度、自洽性、模型自评和路由原因。

可执行操作：

1. 保存选择。
2. 编辑 span 后保存手动修正。
3. 标记全部不对。
4. 跳过。
5. 标记为疑难样例。

保存后会更新对应任务，并把审核结果写入本地 SQLite。

## 6. 导出与可视化

“导出与可视化”用于最终检查和下载数据。

支持查看：

1. 任务总数。
2. 自动通过率。
3. 人工审核率。
4. 待审核数量。
5. 标签分布。
6. 片段长度和候选一致性概况。

支持导出：

1. 全部样本。
2. 全部已确认样本。
3. 自动通过样本。
4. 人工审核样本。
5. 疑难样例。
6. 低置信样本。

主导出格式是 Prodigy-compatible JSONL。页面还可下载 `report.md` 和 `manifest.json`。

## 7. 语言切换

侧栏顶部提供 `中文 / English` 全局切换。

切换语言只影响固定界面文案，例如导航、页面标题、按钮、表单标签和提示信息。用户输入、数据库内容、任务文本、模型输出、标签值和导出文件名不会被自动翻译。

## 8. 完整使用案例：硬科学英文科普术语标注

这个案例可以直接照填。更快的方式是在“概念实验室”点击“填入硬科学术语示例”，页面会自动填入以下内容，但不会自动保存。

### 8.1 概念实验室

在“标注项目”中选择“创建新项目”，填入：

| 字段 | 内容 |
| --- | --- |
| 项目名称 | 硬科学科普术语标注 |
| 项目说明 | 用于从英文硬科学科普新闻中抽取科学概念、技术名词、实验对象和物理过程术语。 |

在“概念阐释”中填入：

| 字段 | 内容 |
| --- | --- |
| 概念名称 | 硬科学术语 |
| 一句话概念描述 | 标出英文科普新闻中与物理、化学、天文、生物医学、材料科学或工程技术直接相关的专业术语。 |
| 标签集合 | Term |
| 模型运行时标注格式 | `[原文]{标签}` |

边界说明：

```text
优先标注最小完整术语。
包含必要修饰词，例如 quantum dots、gravitational waves。
不要把整句话、普通动词或泛泛描述标成术语。
多词术语应整体标注，不拆成单个普通词。
```

负例规则：

```text
不标注 science、researchers、study 这类过泛词。
不标注没有明确科学概念含义的修辞表达。
不标注机构名、新闻来源名或人物名，除非任务明确要求。
不标注只表达程度或时间的普通短语。
```

将以下内容粘贴到“批量粘贴 JSONL”：

```jsonl
{"text":"Quantum dots can emit precise colors when excited by light.","annotation":"[Quantum dots]{Term} can emit precise colors when excited by light."}
{"text":"The telescope detected faint gravitational waves from a distant merger.","annotation":"The telescope detected faint [gravitational waves]{Term} from a distant merger."}
{"text":"Researchers used CRISPR gene editing to repair a mutation in the cells.","annotation":"Researchers used [CRISPR gene editing]{Term} to repair a mutation in the cells."}
{"text":"Perovskite solar cells may improve the efficiency of next-generation panels.","annotation":"[Perovskite solar cells]{Term} may improve the efficiency of next-generation panels."}
{"text":"The experiment measured superconductivity at extremely low temperatures.","annotation":"The experiment measured [superconductivity]{Term} at extremely low temperatures."}
{"text":"A new catalyst accelerated hydrogen production during electrolysis.","annotation":"A new [catalyst]{Term} accelerated [hydrogen production]{Term} during [electrolysis]{Term}."}
{"text":"The spacecraft mapped methane plumes in the planet's atmosphere.","annotation":"The spacecraft mapped [methane plumes]{Term} in the planet's [atmosphere]{Term}."}
{"text":"The vaccine candidate uses messenger RNA to train immune cells.","annotation":"The vaccine candidate uses [messenger RNA]{Term} to train [immune cells]{Term}."}
{"text":"Scientists observed protein folding with high-resolution microscopy.","annotation":"Scientists observed [protein folding]{Term} with [high-resolution microscopy]{Term}."}
{"text":"The battery prototype uses a solid-state electrolyte.","annotation":"The battery prototype uses a [solid-state electrolyte]{Term}."}
{"text":"Neutrino oscillation reveals that neutrinos have mass.","annotation":"[Neutrino oscillation]{Term} reveals that [neutrinos]{Term} have mass."}
{"text":"The reactor design improves plasma confinement in fusion experiments.","annotation":"The reactor design improves [plasma confinement]{Term} in [fusion experiments]{Term}."}
{"text":"Carbon capture systems remove carbon dioxide from industrial exhaust.","annotation":"[Carbon capture systems]{Term} remove [carbon dioxide]{Term} from industrial exhaust."}
{"text":"The sensor detects biomarkers associated with early-stage disease.","annotation":"The sensor detects [biomarkers]{Term} associated with early-stage disease."}
{"text":"Nanoporous membranes can filter salts from seawater.","annotation":"[Nanoporous membranes]{Term} can filter salts from seawater."}
```

然后点击“保存概念与金样例”。保存后可以先选择“本地结构验证”，点击“验证概念”，确认 15 条金样例能通过本地结构检查。

### 8.2 批量标注

进入“批量标注”，选择刚创建的项目和概念。可以先粘贴一小段 TXT 测试：

```text
Astronomers used adaptive optics to sharpen images of distant exoplanets.
The new polymer membrane improved desalination efficiency in laboratory tests.
Researchers monitored neural activity with calcium imaging during the experiment.
```

推荐首次测试参数：

| 参数 | 值 |
| --- | --- |
| 每条采样次数 | 1 |
| 并发数 | 1 |
| 人工审核阈值 | 0.75 |
| 高置信抽检比例 | 0.05 |
| 执行方式 | 本地模拟 |

点击“提交批量任务”。如果只想创建队列、不立刻执行，选择“只提交队列”。

### 8.3 审核队列

进入“审核队列”，保持默认阈值 `0.75`。如果有待审核样本，逐条查看原文、当前概念阐释、金样例参考和候选 A/B/C/D/E。

推荐操作顺序：

1. 候选正确时，选择候选并点击“保存选择”。
2. 候选边界不准时，编辑 span 列表后点击“保存手动修正”。
3. 所有候选都不对时，点击“全部不对”，必要时勾选“标记为疑难样例”。

### 8.4 导出与可视化

进入“导出与可视化”，先查看任务总数、自动通过率、人工审核率和标签分布。

常用导出范围：

1. “全部已确认样本”：用于训练或评测。
2. “人工审核样本”：用于分析模型错误。
3. “疑难样例”：用于下一轮修订概念阐释。

下载 `annotations.jsonl` 和 `report.md` 后，即可进入后续实验记录或论文对比。

## 9. 标注格式

LLM 运行时仍使用易读 markup：

1. 显性标注：`[原文片段]{概念标签}`
2. 隐含义标注：`[!隐含义]{概念标签}`

长期存储格式见 [Annotation JSONL Format](../developer/ANNOTATION_JSONL_FORMAT.md)。
