# 用户教程（网站使用版）

更新时间: 2026-05-07

Rosetta 是一个基于 Streamlit 的本地优先标注工具。默认界面为中文，主流程只保留 5 个页面。

这份教程优先面向第一次接触数据标注工具的用户。你不需要先理解模型训练、PLM 或 agent 架构，只需要按页面顺序完成：定义任务与标注规范、给出 15 条标准答案、验证并优化定义、批量处理文本、审核不确定样本、导出数据。

## 0. 最少要知道的 5 个词

1. **概念阐释**：你用自然语言告诉系统“什么应该被标出来，什么不应该”。它不是论文定义，而是模型执行标注时要看的操作说明。
2. **金样例**：你亲自确认正确的标准样例。定义优化建议准备 15 条，因为系统要用它们反复测试概念阐释是否稳定。
3. **提示词验证**：系统用格式检查、无样例标注验证或 top-k 参考样例验证，检查当前定义能否稳定标出金样例。
4. **定义优化**：页面入口叫“提示词优化”，实际优化对象是可优化定义。系统会生成候选定义、计算 loss、只接受变好版本；达到 15/15 或连续 5 轮无下降时停止。
5. **审核与修正**：系统把自己不确定的样本优先交给人类专家。你通常先选候选答案，必要时再轻量修改。

## 1. 使用流程总览

推荐路径：

```text
项目总览 -> 定义与规范 -> 批量标注 -> 审核与修正 -> 结果与导出
```

这条路径对应一次完整标注实验，也对应后续论文或项目报告中的一条证据链：

1. 在“定义与规范”输入一句话概念描述，并维护 15 条金样例。
2. 在“提示词验证”中运行格式验证、无样例标注验证或 top-k 参考样例验证，再进入用于定义优化的“提示词优化”，选择人工优化、无样例自监督优化或类训练优化。
3. 在“批量标注”上传 TXT、JSONL 或 CSV，系统自动生成标注任务，并用相似样例、边界远例和失败记忆增强提示词。
4. 批量任务按多次采样、自洽性、模型自评和规则风险路由。
5. 低置信、低自洽和抽检样本进入“审核与修正”，专家选择候选并记录错误类型。
6. 在“结果与导出”下载 Prodigy-compatible JSONL 和实验报告。

### 1.1 5 分钟跑通官方样例

如果你只是想确认网站和本机流程能跑通，可以先不用创建新项目：

1. 打开“定义与规范”，使用默认官方项目“专业命名实体标注”。
2. 在“提示词验证”中先运行“格式验证”，确认 15 条金样例的结构是合法的。
3. 打开“批量标注”，粘贴 2-3 句英文科技文本，执行方式选择“本地模拟”。
4. 打开“审核与修正”，如果出现待审核样本，就选择候选或跳过。
5. 打开“结果与导出”，下载 `annotations.jsonl` 和 `report.md`。

“本地模拟”只用于检查页面、队列、审核和导出链路，不代表真实模型效果；正式实验应选择“调用大模型”，并记录所用 provider、model、并发和 token。

## 2. 项目总览

“项目总览”只展示最必要的信息：

1. 当前任务总数、候选标注数、待审核数和批量任务数。
2. 一个“继续下一步”入口，根据当前状态跳转到定义与规范、批量标注、审核与修正或结果与导出。
3. 最近批量任务和最近审核状态。
4. 折叠区中的完整流程说明和本地运行目录。

## 3. 定义与规范

“定义与规范”负责产出稳定概念阐释和金样例库。它是 Rosetta 最重要的页面：如果定义没有验证和优化好，后面的批量标注会放大错误。

页面顶部的“提示词验证 / 提示词优化”现在是两张更大的子页入口按钮，而不是小 radio。选中项会更醒目，也更不容易点错。

这个页面先做四件事：选择或新建标注项目；在“当前定义与金样例”里选择已有定义或新建定义；填写当前定义名称和当前概念阐释；选择金样例格式并上传/粘贴 15 条金样例；运行提示词验证或定义优化。定义优化的页面入口显示为“提示词优化”。

需要填写：

1. 标注项目。已有项目直接选择，需要新项目时点击“新建项目”。
2. 当前定义。已有定义可以直接编辑，需要新定义时选择“新建定义”。
3. 当前定义名称。
4. 当前概念阐释。
5. 金样例格式，默认“自动识别”。
6. 金样例文件或 JSONL 粘贴。
7. 标注输出协议，一般保持默认。

金样例推荐使用 JSONL。最小格式如下，每行一条样例：

```jsonl
{"text":"Quantum dots can emit precise colors when excited by light.","annotation":"[Quantum dots]{Term} can emit precise colors when excited by light."}
{"text":"The telescope detected faint gravitational waves from a distant merger.","annotation":"The telescope detected faint [gravitational waves]{Term} from a distant merger."}
```

其中 `text` 是原句，`annotation` 是把目标片段用 `[片段]{标签}` 标出来后的答案。CSV 更适合先导入待标注原文，不适合作为完整金样例；如果要做正式定义优化，建议准备带 `annotation` 的 JSONL。

从 `v4.5.13` 开始，定义面板不再把边界说明、负例规则、单条样例原文/标注拆成多个输入框。边界、排除和特殊情况都写进“当前概念阐释”正文里；Rosetta 后续的提示词优化也只改这一段可优化定义。标签会从金样例里的 span label 自动推断；如果推断不到，系统默认使用 `Term`。标注输出协议保持选项：

| 选项 | 适用场景 |
| --- | --- |
| Span 标注：JSON + `[span]{Term}` | 当前默认路径，适合普通 span 标注任务；模型运行时可以返回简单 markup，Rosetta 会解析成统一 AnnotationDoc / Prodigy-compatible 存储格式 |
| 全量 JSON：AnnotationDoc | 适合 relation、attributes 或多层标注任务；模型运行时直接返回完整 AnnotationDoc JSON，最终仍进入统一存储结构 |

页面会直接把当前规范分成两栏：

1. **可优化定义**：你需要认真写的是当前概念阐释，包括任务定义、概念定义、边界和排除说明。提示词优化训练只会改这一栏。
2. **冻结输出协议**：Rosetta 负责固定标签、JSON 字段、`[span]{Term}` 或完整 AnnotationDoc JSON、格式校验和格式修复。这一栏会被锁定注入给模型，不交给优化器改写。

也就是说，提示词优化训练不会去“训练”标签、JSON schema 或输出格式。它只尝试把概念规则写得更清楚；模型每次实际标注时，Rosetta 会把冻结的输出协议注入进去，并检查返回结果是否合格。如果模型在候选提示词里又写回标签或输出格式，系统会把这些冻结字段剥离并记录 warning。

注意这里有两层格式：**模型运行时格式**可以是简单的 `[span]{Term}`，便于 LLM 稳定输出；**最终存储格式**仍是 Rosetta 统一的结构化标注格式，保留 spans、relations、meta 和导出所需字段。

模型真实标注时，Rosetta 会把 prompt 固定拼成五段：

```text
概念定义
-> 相似参考样例
-> 标注格式
-> 通用格式示例
-> 待标注文本
-> 任务强调
```

其中“相似参考样例”是可选槽位，只在 top-k 验证或批量标注明确检索到参考样例时填充。通用格式示例只讲 JSON 和 `[span]{Term}` 或 AnnotationDoc 应该长什么样，不使用你的 gold 句子、gold 答案或当前待标注文本。这样可以让模型知道怎么返回结果，又不会把标准答案混进 operational prompt。

金样例输入面板现在只保留必要字段：

1. 当前定义名称。
2. 当前概念阐释。
3. 金样例格式，默认选择“自动识别”。
4. 上传金样例文件，或粘贴 JSONL。

自动识别会根据文件扩展名和首条记录判断格式：`text + annotation` JSONL、Prodigy/Rosetta spans JSONL 或 CSV。正式 gold 推荐使用 JSONL，并包含可定位的 span 标注；CSV 只适合先导入原文列，不适合作为完整金样例。

保存后会写入本地 SQLite，并可导出：

1. `concept_guideline.md`
2. `gold_examples.jsonl`
3. `concept_versions.jsonl`

“定义与规范”页面现在主要只有两个 tab：`提示词验证` 和 `提示词优化`。

提示词验证分三种。页面上的“格式验证”就是本地结构检查；它不调用大模型，适合作为第一步：

| 验证 | 作用 |
| --- | --- |
| 格式验证 | 本地检查 ConceptPromptSpec、冻结输出协议、标签和 gold span 是否合法，不消耗模型 |
| 无样例标注验证 | 调用大模型直接标 15 条 gold，不给参考样例 |
| 标注验证（top-k 参考） | 每条待标注句子会先用本地轻量 embedding 检索 top-k 相似 gold 作为参考，再调用大模型标注 |

top-k 参考检索默认使用 `rosetta-local-hash-384` 本地 embedding，不调用智谱或 DeepSeek embedding API，不消耗 token。检索出的参考样例会进入标注 prompt 的“相似参考样例”专门槽位，位置在概念定义和冻结输出协议之间；它只用于理解边界，不是当前句子的答案。真实 LLM 验证默认并发上限为 `50`；页面会显示进度条、运行中数量、已用时、预计剩余时间、调用数、token 和模型耗时。验证时使用的模型身份和批量标注一致，都是“严谨的标注助手，只输出 JSON”。验证结果会分成通过、失败、边界不稳定三类；最终保存的概念阐释只保留可直接用于标注的提示词正文。

定义优化分三种，页面入口显示为“提示词优化”：

| 方法 | 你可以怎么理解 |
| --- | --- |
| 人工优化 | 给一个编辑框，专家直接修改当前可优化提示词并保存为新版本 |
| 无样例自监督优化 | 只告诉大模型“请优化当前提示词”，不给它看失败细节、gold answer、loss 或历史 |
| 类训练优化 | 当前第一版使用失败对照，让大模型每轮生成候选提示词，再用 15 条 gold 选择 loss 最小且下降的版本 |

推荐首次测试参数：

| 参数 | 值 |
| --- | --- |
| 优化方式 | 先选“类训练优化” |
| 最大训练轮数 | 30 |
| 每轮候选数 | 5 |
| 最小损失下降 | 0.01 |
| 连续无下降轮数 | 5 |
| 成功后自动应用最佳提示词 | 第一次先不勾选 |

点击“开始优化训练”后，任务会进入后台运行，按钮会变成不可重复点击的运行状态。页面会出现“当前训练任务”卡片，并每 2 秒自动刷新一次；你可以看到当前阶段、预计剩余时间、已完成模型调用、运行中调用、token、修复次数、当前最佳方法、最佳通过数和当前最佳 loss。你可以离开页面，稍后回来继续查看同一个 run。

类训练优化的核心循环是：

```text
当前 prompt
  -> 让 LLM 生成 5 个优化候选
  -> 逐个跑 15 条 gold 计算 loss
  -> 选出最优候选
  -> 如果 loss 下降，就接受
  -> 把“旧 prompt -> 新 prompt -> loss 变化”记入历史
  -> 下一轮生成候选时，把这段历史摘要告诉 LLM
  -> 持续到 15/15 或连续多轮无提升
```

训练完成后，页面会展示最佳方法、通过数、loss、最佳干净提示词、v0 到 vn 的提示词版本历史和折叠训练日志。如果达到 15/15，可以检查最佳提示词后再决定是否应用；如果没有达到，系统会继续探索，直到连续 5 轮 loss 没有下降或达到最大轮数，状态会显示“仍需修订”。最佳提示词按历史最优接受版本统计，不等同于最后一轮的临时结果。

从 `v4.5.0` 开始，提示词优化训练会区分“批改参考”“去语料化修复”和“最终提示词”：

1. 批改参考可以包含原文、标准答案和模型自己的错误回答。你可以把它理解成学生看老师批改过的作业。
2. 最终提示词不能复制这些作业里的具体词、原句、gold span 或模型 span。它只能把错误抽象成边界规则、排除规则和输出要求。
3. 如果候选提示词复制了语料或答案片段，系统不会立刻丢弃，而是先调用“去语料化修复”，要求模型删除具体词和答案片段，只保留抽象规则。
4. 修复后仍然复制语料时，系统才会把它标记为“修复失败”，不会拿它继续训练。
5. 页面会显示“最终提示词干净”“拦截候选数”“真实模型”“实际并发”“总调用”“总 token”“模型耗时秒”和“修复尝试”。DeepSeek 默认模型为 `deepseek-v4-pro`，默认并发上限为 `50`。
6. 折叠日志里只显示安全摘要、hash 和数量，不在主报告里展开被复制的具体词、raw prompt、raw response 或 gold 原文。
7. 日志区可以按事件类型和阶段筛选，也可以下载 `run_events.jsonl`。这个文件记录训练过程中的阶段、候选状态、模型调用、token、ETA 和错误摘要，方便你复现实验过程。
8. 这一轮只测试 15 条 gold，因此结果只能说明“没有直接背答案，并且能通过这 15 条 gold”。如果要写论文或证明泛化，后续还需要 held-out 数据。

从 `v4.5.5` 的文档契约开始，提示词优化训练还会区分“概念优化”和“格式修复”：

1. `只要求优化` 方法只让大模型优化概念语义，不给它看原文、标准答案、错误回答、loss、失败摘要或文本梯度。
2. `失败反思` 会先给当前可优化提示词，再把每个失败 detail 按“原文 -> 标准答案 annotation -> 模型回答 JSON -> 错误摘要”放在同一个小块里，方便模型看懂同一句哪里错了。
3. `失败反思` 和 `文本梯度 AdamW` 可以利用批改参考或文本梯度，但生成的候选仍只能改概念定义、边界规则和排除规则。
4. 输出协议被冻结为 JSON+markup：`text / annotation / explanation` 三个核心字段，`annotation` 使用 `[span]{Term}`。
5. 如果模型返回了非法 JSON、漏字段、字段外多余解释、span 找不到或 label 不合法，系统应先尝试最多 2 次格式修复。
6. 格式修复只修 JSON 和 markup，不改概念语义；修复成功后才计算漏标、多标和边界错误。
7. 后续实验报告会把“格式错误率”“格式修复成功率”和“语义 loss”分开显示，这样你能知道问题到底是模型不会按格式输出，还是概念规则本身不够好。

ACTER `en/corp` 100 正例实验会使用 `deepseek-v4-flash` 和“ACTER 反腐败术语抽取”任务做更大测试。这个测试只用正例句子，因此可以观察术语召回、边界稳定性和格式稳定性，但不能证明模型不会在负例上过度标注。

如果要运行完整三方法真实对比实验，可以使用统一 CLI：

```bash
conda run -n rosetta-dev python scripts/tool/rosetta_tool.py prompt-training-experiment \
  --case professional-ner \
  --provider deepseek \
  --model deepseek-v4-pro \
  --concurrency 50 \
  --candidate-count 5 \
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
2. 并发数：默认 50。批量页当前按这个数启动本地线程调用 provider；如果平台限流，建议先手动降到 1-5 做真实 API 小样本测试。
3. 人工审核阈值：默认 0.75。
4. 高置信抽检比例：默认 5%。

执行方式：

| 执行方式 | 适合什么时候用 | 结果能否代表真实模型 |
| --- | --- | --- |
| 只提交队列 | 只想确认导入、分句和任务创建是否正常 | 不能，尚未生成模型标注 |
| 本地模拟 | 首次检查页面、队列、审核和导出链路 | 不能，只是 smoke test，不消耗 API |
| 调用大模型 | 正式标注或真实实验 | 可以，需要记录 provider、model、并发、token 和运行报告 |

批量任务写入本地 SQLite 队列。提交后可以离开页面，之后到“审核与修正”查看低置信样本。

长耗时动作运行时，按钮会切换为“正在处理…”并变成不可点击状态。此时重复点击不会提交第二个批量任务；等待页面恢复或跳转到审核与修正即可。

## 5. 审核与修正

“审核与修正”不是表格后台，而是逐条弹出的专家审核台。

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

## 6. 结果与导出

“结果与导出”用于最终检查和下载数据。

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

主导出格式是 Prodigy-compatible JSONL。`annotations.jsonl` 用于后续训练、统计、人工复核或迁移到其他标注工具；`report.md` 用于记录本次运行的方法、概念版本、模型设置、人工审核量和自动通过比例；`manifest.json` 用于让脚本复现或检查导出批次。后续要比较 LLM agent 和 PLM 时，优先保存 `report.md`。

## 7. 界面语言

当前公开教程按中文界面维护，页面名称、按钮和示例都以中文为准。文档中的英文主要保留在文件格式、命令、模型名、字段名和代码标识符中，例如 `JSONL`、`report.md`、`deepseek-v4-pro` 和 `[span]{Term}`。

用户输入、数据库内容、任务文本、模型输出、标签值和导出文件名不会被自动翻译。

## 8. 完整使用案例：专业命名实体标注

这个案例是 Rosetta 的官方样例。程序重启时，主运行库会自动恢复为这个项目，并内置 15 条金样例和基础提示词；不需要再点击“一键填入”。

### 8.1 定义与规范

打开“定义与规范”后，默认选择官方项目：

| 字段 | 内容 |
| --- | --- |
| 项目名称 | 专业命名实体标注 |
| 项目说明 | 用于从英文科学与技术科普文本中抽取可命名、可边界化的专业实体，包括研究对象、方法、材料、设备、过程和领域专门概念。 |

官方概念阐释已经写入：

| 字段 | 内容 |
| --- | --- |
| 概念名称 | 专业命名实体 |
| 当前概念阐释 | 标出英文科学与技术文本中具有明确领域含义、可命名且边界清楚的专业实体。优先标注最小完整实体名称；包含形成实体名称所必需的修饰成分，但不要扩展到整句或普通描述；多词实体应整体标注。 |
| 标注输出协议 | Span 标注：JSON + `[span]{Term}` |

标签 `Term` 来自官方 gold 标注并作为冻结输出协议注入，不需要在表单里手填。官方样例没有把负例规则作为主输入项暴露；如果后续任务确实需要复杂排除条件，应直接写进当前概念阐释里的“不包括……”规则。

下面 15 条金样例已自动内置在官方项目中。这里列出它们是为了让你知道系统正在用什么验证和优化定义；这些具体实体不会被写进 operational prompt：

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

如果要测试完整的提示词优化训练，进入“提示词优化”tab，先选择“类训练优化”，保持最大训练轮数 `30`、每轮候选数 `5`、连续无下降轮数 `5`，点击“开始优化训练”。建议第一次不要勾选自动应用，先查看 v0 到 vn 的版本历史、loss 变化和折叠日志；确认结果后再手动或自动应用最佳提示词。

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
| 并发数 | 50；如果只是首次真实 API 小样本 smoke，可手动降为 1 |
| 人工审核阈值 | 0.75 |
| 高置信抽检比例 | 0.05 |
| 执行方式 | 本地模拟 |

点击“提交批量任务”。如果只想创建队列、不立刻执行，选择“只提交队列”。

### 8.3 审核与修正

进入“审核与修正”，保持默认阈值 `0.75`。如果有待审核样本，逐条查看原文、当前概念阐释、金样例参考和候选 A/B/C/D/E。

推荐操作顺序：

1. 候选正确时，选择候选并点击“保存选择”。
2. 候选边界不准时，编辑 span 列表后点击“保存手动修正”。
3. 所有候选都不对时，点击“全部不对”，必要时勾选“标记为疑难样例”。

### 8.4 结果与导出

进入“结果与导出”，先查看任务总数、自动通过率、人工审核率和标签分布。

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

## 10. 用户术语小抄

| 文档术语 | 普通理解 |
| --- | --- |
| loss | 错误分数，越低越好 |
| top-k 参考样例 | 当前句子最相似的几个参考例 |
| embedding 检索 | 本地相似度检索，不调用在线 embedding API |
| Prodigy-compatible JSONL | 方便后续训练、评测和迁移的结构化标注文件 |
| JSON+markup | 模型运行时返回的简单格式，例如 `[Quantum dots]{Term}` |
| 冻结输出协议 | 标签、JSON 字段和格式校验由 Rosetta 固定，不交给优化器改写 |
