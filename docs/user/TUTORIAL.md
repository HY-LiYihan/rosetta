# 用户教程（网站使用版）

更新时间: 2026-05-04

Rosetta 是一个基于 Streamlit 的本地优先标注工具。默认界面为中文，主流程只保留 5 个页面。

这份教程优先面向第一次接触数据标注工具的用户。你不需要先理解模型训练、PLM 或 agent 架构，只需要按页面顺序完成：定义概念、给出 15 条标准答案、让系统校准、批量处理文本、审核不确定样本、导出数据。

## 0. 最少要知道的 4 个词

1. **概念阐释**：你用自然语言告诉系统“什么应该被标出来，什么不应该”。它不是论文定义，而是模型执行标注时要看的操作说明。
2. **金样例**：你亲自确认正确的标准样例。正式自举需要 15 条，因为系统要用它们反复测试概念阐释是否稳定。
3. **自举校准**：系统像考试一样用 15 条金样例测试当前概念阐释，失败后生成候选修订，并只接受让 loss 下降的版本。
4. **提示词优化训练**：系统把概念阐释当作可训练参数，在同一批金样例上比较多种优化方法，目标是在最多 5 轮内达到 15/15 全部通过。
5. **审核队列**：系统把自己不确定的样本优先交给人类专家。你通常先选候选答案，必要时再轻量修改。

## 1. 使用流程总览

推荐路径：

```text
工作台 -> 概念实验室 -> 批量标注 -> 审核队列 -> 导出与可视化
```

这条路径对应一次完整标注实验，也对应后续论文或项目报告中的一条证据链：

1. 在“概念实验室”输入一句话概念描述，并维护 15 条金样例。
2. 运行“概念自举校准”或“提示词优化训练”，让系统逐轮验证金样例、生成失败日志和干净概念版本。
3. 在“批量标注”上传 TXT、JSONL 或 CSV，系统自动生成标注任务，并用相似样例、边界远例和失败记忆增强提示词。
4. 批量任务按多次采样、自洽性、模型自评和规则风险路由。
5. 低置信、低自洽和抽检样本进入“审核队列”，专家选择候选并记录错误类型。
6. 在“导出与可视化”下载 Prodigy-compatible JSONL 和实验报告。

## 2. 工作台

“工作台”只展示最必要的信息：

1. 当前任务总数、候选标注数、待审核数和批量任务数。
2. 一个“继续下一步”入口，根据当前状态跳转到概念实验室、批量标注、审核队列或导出与可视化。
3. 最近批量任务和最近审核状态。
4. 折叠区中的完整流程说明和本地运行目录。

## 3. 概念实验室

“概念实验室”负责产出稳定概念阐释和金样例库。它是 Rosetta 最重要的页面：如果概念没有校准好，后面的批量标注会放大错误。

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

“验证概念”可以先用本地结构验证跑通流程，也可以选择已配置的大模型对金样例试标。真实 LLM 模式会并发验证 15 条 gold，默认并发上限为 `20`；页面会显示进度条、运行中数量、已用时、预计剩余时间、调用数、token 和模型耗时。验证结果会分成通过、失败、边界不稳定三类，失败样例会进入修订日志；最终保存的概念阐释只保留可直接用于标注的提示词正文。

正式自举校准需要 15 条金样例。少于 15 条可以保存草稿，但不能启动正式自举。点击“开始自举校准”后，系统会反复执行：

```text
当前概念阐释 -> 试标 15 条金样例 -> 计算当前 loss -> 生成多个候选概念 -> 候选逐个试标 -> 只接受 loss 下降的干净概念版本
```

默认最多 5 轮。默认不会自动覆盖稳定概念，除非勾选“自动应用最终版本”。

概念自举中，大模型的修订任务被刻意简化：它只需要返回优化后的概念阐释正文。样例编号、失败摘要、漏标/多标诊断和模型原始响应会保留在“失败详情与修订日志”和 `concept_versions.jsonl`，不会进入最终提示词。

如果某一轮候选概念都没有让金样例 loss 下降，系统会保留当前最优概念并停止搜索，而不是把更差的提示词继续带入下一轮。这一点是为了避免“越优化越烂”。

“提示词优化训练”适合用来测试你的核心想法：只给一个简单任务描述和 15 条金样例，系统是否能像训练一样把提示词优化到 15/15 全部通过。第一版会比较三种方法：

| 方法 | 你可以怎么理解 |
| --- | --- |
| 只要求优化 | 只告诉大模型“请优化当前提示词”，不给它看失败细节，作为最简单基线 |
| 失败反思 | 告诉大模型哪里出了问题，让它自己改写整体概念阐释 |
| 文本梯度 AdamW | 把提示词切成可优化片段，结合文本梯度方向、长度惩罚和 gold loss 验证 |

推荐首次测试参数：

| 参数 | 值 |
| --- | --- |
| 训练方法 | 三个都选 |
| 最大训练轮数 | 30 |
| 每轮候选数 | 3 |
| 最小损失下降 | 0.01 |
| 连续无下降轮数 | 5 |
| 成功后自动应用最佳提示词 | 第一次先不勾选 |

点击“开始优化训练”后，任务会进入后台运行，按钮会变成不可重复点击的运行状态。页面会出现“当前训练任务”卡片，并每 2 秒自动刷新一次；你可以看到当前阶段、预计剩余时间、已完成模型调用、运行中调用、token、修复次数、当前最佳方法、最佳通过数和当前最佳 loss。你可以离开页面，稍后回来继续查看同一个 run。

训练完成后，页面会展示最佳方法、通过数、loss、最佳干净提示词和折叠训练日志。如果达到 15/15，可以检查最佳提示词后再决定是否应用；如果没有达到，系统会继续探索，直到某个方法连续 5 轮 loss 没有下降或达到最大轮数，状态会显示“仍需修订”。最佳方法和最佳提示词按历史最优接受版本统计，不等同于最后一轮的临时结果。

从 `v4.5.0` 开始，提示词优化训练会区分“批改参考”“去语料化修复”和“最终提示词”：

1. 批改参考可以包含原文、标准答案和模型自己的错误回答。你可以把它理解成学生看老师批改过的作业。
2. 最终提示词不能复制这些作业里的具体词、原句、gold span 或模型 span。它只能把错误抽象成边界规则、排除规则和输出要求。
3. 如果候选提示词复制了语料或答案片段，系统不会立刻丢弃，而是先调用“去语料化修复”，要求模型删除具体词和答案片段，只保留抽象规则。
4. 修复后仍然复制语料时，系统才会把它标记为“修复失败”，不会拿它继续训练。
5. 页面会显示“最终提示词干净”“拦截候选数”“真实模型”“实际并发”“总调用”“总 token”“模型耗时秒”和“修复尝试”。DeepSeek 默认模型为 `deepseek-v4-pro`，默认并发上限为 `20`。
6. 折叠日志里只显示安全摘要、hash 和数量，不在主报告里展开被复制的具体词、raw prompt、raw response 或 gold 原文。
7. 日志区可以按事件类型和阶段筛选，也可以下载 `run_events.jsonl`。这个文件记录训练过程中的阶段、候选状态、模型调用、token、ETA 和错误摘要，方便你复现实验过程。
8. 这一轮只测试 15 条 gold，因此结果只能说明“没有直接背答案，并且能通过这 15 条 gold”。如果要写论文或证明泛化，后续还需要 held-out 数据。

如果要运行完整三方法真实对比实验，可以使用统一 CLI：

```bash
conda run -n rosetta-dev python scripts/tool/rosetta_tool.py prompt-training-experiment \
  --case professional-ner \
  --provider deepseek \
  --model deepseek-v4-pro \
  --concurrency 20 \
  --candidate-count 3 \
  --patience-rounds 5 \
  --max-rounds 30 \
  --output-dir .runtime/experiments/prompt_training_professional_ner \
  --record
```

CLI 和页面产物保持一致：`comparison_report.md`、`comparison_result.json`、`prompt_evolution.jsonl` 和 `run_events.jsonl`。

完成后重点查看 `comparison_report.md`、`comparison_result.json` 和 `prompt_evolution.jsonl`。

## 4. 批量标注

“批量标注”负责把原始语料变成任务队列。运行时不再只使用概念描述，而会自动构建标注上下文：

1. 当前稳定概念版本。
2. 相似金样例或高置信样例。
3. 少量边界远例，提醒模型不要过度泛化。
4. 最近失败模式摘要。

输入支持：

1. TXT：默认按段落和中英文句末标点分句，并做轻量 tokenize。
2. JSONL：优先按 Prodigy-compatible task 读取。
3. CSV：选择文本列，其余列进入 `meta`。

提交任务时可以设置：

1. 每条采样次数：1、3 或 5。
2. 并发数：默认 20。这个值是 Rosetta 的 provider 级默认上限；如果平台限流，系统会按 provider profile 和重试策略等待。
3. 人工审核阈值：默认 0.75。
4. 高置信抽检比例：默认 5%。

执行方式：

1. 只提交队列：创建任务后不立刻调用模型。
2. 本地模拟：用于本机 smoke test，不消耗 API。
3. 调用大模型：使用已配置平台后台执行。

批量任务写入本地 SQLite 队列。提交后可以离开页面，之后到“审核队列”查看低置信样本。

长耗时动作运行时，按钮会切换为“正在处理…”并变成不可点击状态。此时重复点击不会提交第二个批量任务；等待页面恢复或跳转到审核队列即可。

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
6. 选择错误类型。
7. 将高质量人工确认结果标记为 gold-like 样例，参与后续检索。

保存后会更新对应任务，并把审核结果写入本地 SQLite。高质量人工确认样本可以被标记为 gold-like，用作下一轮检索和概念修订参考；明显暴露边界问题的样本可以标记为疑难样例。

审核保存过程中，当前动作按钮会进入“正在处理…”状态，其余审核按钮也会暂时不可点击，避免同一条样本被重复保存。

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

主导出格式是 Prodigy-compatible JSONL。页面还可下载 `report.md` 和 `manifest.json`。如果你后续要比较 LLM agent 和 PLM，优先保存 `report.md`，里面会记录概念版本、loss、人工审核量和自动通过比例。

## 7. 语言切换

侧栏顶部提供 `中文 / English` 全局切换。

切换语言只影响固定界面文案，例如导航、页面标题、按钮、表单标签和提示信息。用户输入、数据库内容、任务文本、模型输出、标签值和导出文件名不会被自动翻译。

## 8. 完整使用案例：专业命名实体标注

这个案例是 Rosetta 的官方样例。程序重启时，主运行库会自动恢复为这个项目，并内置 15 条金样例和基础提示词；不需要再点击“一键填入”。

### 8.1 概念实验室

打开“概念实验室”后，默认选择官方项目：

| 字段 | 内容 |
| --- | --- |
| 项目名称 | 专业命名实体标注 |
| 项目说明 | 用于从英文科学与技术科普文本中抽取可命名、可边界化的专业实体，包括研究对象、方法、材料、设备、过程和领域专门概念。 |

官方概念阐释已经写入：

| 字段 | 内容 |
| --- | --- |
| 概念名称 | 专业命名实体 |
| 一句话概念描述 | 标出英文科学与技术文本中具有明确领域含义、可命名且边界清楚的专业实体。 |
| 标签集合 | Term |
| 模型运行时标注格式 | `[原文]{标签}` |

边界说明：

```text
优先标注最小完整实体名称。
包含形成实体名称所必需的修饰成分，但不要扩展到整句或普通描述。
多词实体应整体标注，不拆成单个普通词。
同一句中出现多个相互独立的专业实体时，应分别标注。
```

负例规则：

```text
不标注过泛、无明确领域实体含义的普通词。
不标注没有专业概念指向的修辞表达。
不标注机构名、新闻来源名或人物名，除非任务明确要求。
不标注只表达程度或时间的普通短语。
```

下面 15 条金样例已自动内置在官方项目中。这里列出它们是为了让你知道系统正在用什么校准概念；这些具体实体不会被写进 operational prompt：

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

可以先选择“本地结构验证”，点击“验证概念”，确认 15 条金样例能通过本地结构检查。

如果要测试完整的提示词优化训练，在“提示词优化训练”区域保持默认选择三个方法，最大训练轮数填 `5`，每轮候选数填 `3`，点击“开始优化训练”。本地结构验证模式可以先跑通页面和存储逻辑；配置好真实 API 后，再切换到“调用大模型”进行真实训练。

### 8.2 批量标注

进入“批量标注”，选择官方项目和概念。可以先粘贴一小段 TXT 测试：

```text
Astronomers used adaptive optics to sharpen images of distant exoplanets.
The new polymer membrane improved desalination efficiency in laboratory tests.
Researchers monitored neural activity with calcium imaging during the experiment.
```

推荐首次测试参数：

| 参数 | 值 |
| --- | --- |
| 每条采样次数 | 1 |
| 并发数 | 20；如果只是首次真实 API 小样本 smoke，可手动降为 1 |
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

下载 `annotations.jsonl` 和 `report.md` 后，即可进入后续实验记录或论文对比。报告会包含概念版本变化、疑难样例、人工修改量和主动审核反馈。

如果要和 PLM 做对比，建议额外记录：

1. 当前只用了多少条人工 gold。
2. PLM baseline 使用同样数量 gold 时的表现。
3. Rosetta 自动通过了多少样本，人工审核了多少样本。
4. 人类专家是直接选择候选、轻量编辑，还是完全重写。

## 9. 标注格式

LLM 运行时仍使用易读 markup：

1. 显性标注：`[原文片段]{概念标签}`
2. 隐含义标注：`[!隐含义]{概念标签}`

长期存储格式见 [Annotation JSONL Format](../developer/ANNOTATION_JSONL_FORMAT.md)。
