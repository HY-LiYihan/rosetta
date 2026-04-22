from __future__ import annotations

import json

import streamlit as st

from app.infrastructure.llm.api_utils import probe_available_platforms
from app.services.corpus_studio_flow_service import (
    generate_corpus_collection,
    generate_corpus_plan,
    generate_sample_articles,
    judge_corpus_collection,
)
from app.services.corpus_studio_service import (
    apply_plan_overrides,
    build_corpus_studio_export_filename,
    build_corpus_studio_export_json,
    recommended_batch_size,
)
from app.state.keys import (
    AVAILABLE_CONFIG,
    CORPUS_MODEL_SELECTOR,
    CORPUS_PLATFORM_SELECTOR,
    CORPUS_STUDIO_WORKFLOW,
    SELECTED_MODEL,
    SELECTED_PLATFORM,
)
from app.state.session_state import (
    ensure_available_config,
    ensure_core_state,
    ensure_corpus_studio_state,
    ensure_platform_selection,
)


def _seed_plan_editor(plan: dict) -> None:
    st.session_state["corpus_plan_refined_brief"] = plan["refined_brief"]
    st.session_state["corpus_plan_strategy_summary"] = plan["strategy_summary"]
    st.session_state["corpus_plan_generation_rules"] = "\n".join(plan["generation_rules"])
    st.session_state["corpus_plan_title_candidates"] = "\n".join(plan["title_candidates"])
    st.session_state["corpus_plan_style_profile"] = "\n".join(plan["style_profile"])
    st.session_state["corpus_plan_judge_focus"] = "\n".join(plan["judge_focus"])
    st.session_state["corpus_plan_risk_notes"] = "\n".join(plan["risk_notes"])
    st.session_state["corpus_sample_title_selector"] = [
        item["title"] for item in plan.get("sample_angles", [])[:2]
    ] or plan["title_candidates"][:2]
    st.session_state["corpus_batch_title_selector"] = plan["title_candidates"][:]


def _read_plan_from_editor(plan: dict) -> dict:
    return apply_plan_overrides(
        plan=plan,
        refined_brief=st.session_state.get("corpus_plan_refined_brief", plan["refined_brief"]),
        strategy_summary=st.session_state.get("corpus_plan_strategy_summary", plan["strategy_summary"]),
        generation_rules_text=st.session_state.get("corpus_plan_generation_rules", ""),
        title_candidates_text=st.session_state.get("corpus_plan_title_candidates", ""),
        style_profile_text=st.session_state.get("corpus_plan_style_profile", ""),
        judge_focus_text=st.session_state.get("corpus_plan_judge_focus", ""),
        risk_notes_text=st.session_state.get("corpus_plan_risk_notes", ""),
    )


def _render_article(article: dict, prefix: str) -> None:
    with st.expander(f"{article['title']} ({article['word_count_estimate']})", expanded=False):
        st.markdown(f"**摘要**: {article['summary']}")
        if article.get("angle"):
            st.markdown(f"**角度**: {article['angle']}")
        if article.get("keywords"):
            st.markdown(f"**关键词**: {', '.join(article['keywords'])}")
        st.markdown("**正文**")
        st.write(article["body"])
        if article.get("quality_notes"):
            st.markdown(f"**模型自检**: {'；'.join(article['quality_notes'])}")
        st.caption(f"{prefix} | id={article['id']}")


def _render_judge_table(judge: dict) -> None:
    rows = []
    for item in judge.get("items", []):
        rows.append(
            {
                "title": item["title"],
                "verdict": item["verdict"],
                "brief_alignment": item["scores"]["brief_alignment"],
                "style_fit": item["scores"]["style_fit"],
                "clarity": item["scores"]["clarity"],
                "scientific_tone": item["scores"]["scientific_tone"],
                "usefulness": item["scores"]["usefulness"],
                "issues": " | ".join(item["issues"]),
                "revision_hint": item["revision_hint"],
            }
        )
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)


def _reset_downstream(workflow: dict, keep_plan: bool = True) -> None:
    if not keep_plan:
        workflow["plan"] = None
        workflow["confirmed_plan"] = None
    workflow["samples"] = None
    workflow["corpus"] = None
    workflow["judge"] = None


st.title("🧪 Corpus Studio")
st.markdown(
    """
<p style='color: var(--color-text); line-height: 1.7;'>
    这是一个面向语料生成的分步式工作台。你先用一句话描述想要的语料，再让系统给出标题候选和样稿，
    经过一到多轮确认后，再批量生成完整语料库，最后用独立的 judge 阶段做质量评审。
</p>
""",
    unsafe_allow_html=True,
)

ensure_core_state()
ensure_corpus_studio_state()

if AVAILABLE_CONFIG not in st.session_state:
    with st.spinner("正在探测可用 AI 平台..."):
        ensure_available_config(probe_available_platforms)

ensure_platform_selection(preferred_platform="zhipuai")
workflow = st.session_state[CORPUS_STUDIO_WORKFLOW]

with st.sidebar:
    st.title("⚙️ Corpus 设置")
    st.subheader("模型配置")

    if not st.session_state[AVAILABLE_CONFIG]:
        st.warning("⚠️ 未探测到可用平台，请在 `secrets.toml` 中配置 API Key")
        selected_platform = None
        selected_model = None
    else:
        platform_options = list(st.session_state[AVAILABLE_CONFIG].keys())
        if st.session_state[SELECTED_PLATFORM] not in platform_options:
            preferred_index = platform_options.index("zhipuai") if "zhipuai" in platform_options else 0
            st.session_state[SELECTED_PLATFORM] = platform_options[preferred_index]

        def on_corpus_platform_change():
            new_platform = st.session_state[CORPUS_PLATFORM_SELECTOR]
            st.session_state[SELECTED_PLATFORM] = new_platform
            st.session_state[SELECTED_MODEL] = st.session_state[AVAILABLE_CONFIG][new_platform]["default_model"]

        selected_platform = st.selectbox(
            "选择 AI 平台",
            platform_options,
            index=platform_options.index(st.session_state[SELECTED_PLATFORM]),
            format_func=lambda x: st.session_state[AVAILABLE_CONFIG][x]["name"],
            key=CORPUS_PLATFORM_SELECTOR,
            on_change=on_corpus_platform_change,
        )
        st.session_state[SELECTED_PLATFORM] = selected_platform

        config = st.session_state[AVAILABLE_CONFIG][selected_platform]
        model_options = config["models"]
        if st.session_state[SELECTED_MODEL] not in model_options:
            st.session_state[SELECTED_MODEL] = config["default_model"]

        selected_model = st.selectbox(
            "选择模型",
            model_options,
            index=model_options.index(st.session_state[SELECTED_MODEL]),
            key=CORPUS_MODEL_SELECTOR,
        )
        st.session_state[SELECTED_MODEL] = selected_model

    st.subheader("阶段温度")
    plan_temperature = st.slider("策略规划温度", 0.0, 1.0, 0.6, 0.1, key="corpus_plan_temperature")
    sample_temperature = st.slider("样稿/生成温度", 0.0, 1.0, 0.7, 0.1, key="corpus_sample_temperature")
    judge_temperature = st.slider("Judge 温度", 0.0, 1.0, 0.2, 0.1, key="corpus_judge_temperature")

status_cols = st.columns(4)
status_cols[0].metric("策略", "已确认" if workflow.get("confirmed_plan") else ("草案中" if workflow.get("plan") else "未开始"))
status_cols[1].metric("样稿", len(workflow.get("samples", {}).get("articles", [])) if workflow.get("samples") else 0)
status_cols[2].metric("语料", len(workflow.get("corpus", {}).get("articles", [])) if workflow.get("corpus") else 0)
status_cols[3].metric("Judge", len(workflow.get("judge", {}).get("items", [])) if workflow.get("judge") else 0)

st.divider()
st.subheader("1. 一句话 Brief")
with st.form("corpus_brief_form"):
    st.text_input(
        "你想生成什么语料？",
        key="corpus_brief_input",
        value=st.session_state.get("corpus_brief_input", "英文硬科学科普新闻"),
        placeholder="例如：英文的硬科学科普新闻，面向大学新生",
    )
    brief_col1, brief_col2, brief_col3 = st.columns(3)
    with brief_col1:
        st.selectbox("语言", ["zh", "en", "ja", "fr", "de"], key="corpus_language_input", index=1)
        st.text_input("领域", key="corpus_domain_input", value=st.session_state.get("corpus_domain_input", "hard science"))
        st.number_input("目标文章数", min_value=2, max_value=200, value=st.session_state.get("corpus_total_articles_input", 12), step=2, key="corpus_total_articles_input")
    with brief_col2:
        st.text_input("体裁", key="corpus_genre_input", value=st.session_state.get("corpus_genre_input", "science news"))
        st.text_input("受众", key="corpus_audience_input", value=st.session_state.get("corpus_audience_input", "general readers with curiosity about science"))
        st.number_input("每篇目标词数", min_value=150, max_value=4000, value=st.session_state.get("corpus_target_words_input", 700), step=50, key="corpus_target_words_input")
    with brief_col3:
        st.text_input("语气 / 风格", key="corpus_tone_input", value=st.session_state.get("corpus_tone_input", "clear, factual, engaging"))
        st.text_area("硬约束", key="corpus_constraints_input", value=st.session_state.get("corpus_constraints_input", "避免夸张标题；避免虚构实验数据；保持可读但不过度娱乐化"), height=100)
        st.text_area("补充说明", key="corpus_notes_input", value=st.session_state.get("corpus_notes_input", "优先覆盖天体物理、材料科学、气候科学等方向"), height=100)

    generate_plan_clicked = st.form_submit_button("生成策略与标题候选", type="primary")

if generate_plan_clicked:
    with st.spinner("正在生成语料策略与标题候选..."):
        result = generate_corpus_plan(
            brief=st.session_state["corpus_brief_input"],
            language=st.session_state["corpus_language_input"],
            genre=st.session_state["corpus_genre_input"],
            domain=st.session_state["corpus_domain_input"],
            audience=st.session_state["corpus_audience_input"],
            tone=st.session_state["corpus_tone_input"],
            total_articles=st.session_state["corpus_total_articles_input"],
            target_words=st.session_state["corpus_target_words_input"],
            hard_constraints=st.session_state["corpus_constraints_input"],
            extra_notes=st.session_state["corpus_notes_input"],
            available_config=st.session_state[AVAILABLE_CONFIG],
            selected_platform=selected_platform,
            selected_model=selected_model,
            temperature=plan_temperature,
        )
    if result["ok"]:
        workflow["plan"] = result["plan"]
        workflow["confirmed_plan"] = None
        workflow["plan_round"] = workflow.get("plan_round", 0) + 1
        _reset_downstream(workflow)
        _seed_plan_editor(result["plan"])
        st.success("策略草案已生成。先看标题和样稿方向，再决定是否确认。")
    else:
        st.error(result["error"])

plan = workflow.get("plan")
if plan:
    st.divider()
    st.subheader("2. 标题与策略确认")
    st.caption(f"当前策略轮次：{workflow.get('plan_round', 1)}")
    st.markdown(f"**系统精炼 Brief**: {plan['refined_brief']}")
    st.markdown(f"**策略摘要**: {plan['strategy_summary']}")

    angle_cols = st.columns(min(2, len(plan["sample_angles"])) or 1)
    for index, angle in enumerate(plan["sample_angles"][:2]):
        with angle_cols[index]:
            st.markdown(f"**样稿方向 {index + 1}**")
            st.markdown(f"**标题**: {angle['title']}")
            st.markdown(f"**角度**: {angle['angle']}")
            st.caption(angle["why_it_works"])

    st.text_area("精炼 Brief（可改）", key="corpus_plan_refined_brief", height=80)
    st.text_area("策略摘要（可改）", key="corpus_plan_strategy_summary", height=100)
    editor_col1, editor_col2 = st.columns(2)
    with editor_col1:
        st.text_area("生成规则（每行一条）", key="corpus_plan_generation_rules", height=160)
        st.text_area("标题候选（每行一个）", key="corpus_plan_title_candidates", height=220)
    with editor_col2:
        st.text_area("风格要求（每行一条）", key="corpus_plan_style_profile", height=160)
        st.text_area("Judge 重点（每行一条）", key="corpus_plan_judge_focus", height=160)
        st.text_area("风险提示（每行一条）", key="corpus_plan_risk_notes", height=120)

    st.text_area(
        "微调反馈",
        key="corpus_plan_feedback",
        height=100,
        placeholder="例如：标题不要太像媒体标题党；希望增加材料科学和气候科学的比例；样稿更像 Nature News 一点",
    )
    action_col1, action_col2 = st.columns(2)
    with action_col1:
        replan_clicked = st.button("根据反馈重规划", use_container_width=True)
    with action_col2:
        confirm_plan_clicked = st.button("确认策略并进入样稿", type="primary", use_container_width=True)

    if replan_clicked:
        current_plan = _read_plan_from_editor(plan)
        with st.spinner("正在根据反馈重新规划标题与策略..."):
            result = generate_corpus_plan(
                brief=st.session_state["corpus_brief_input"],
                language=st.session_state["corpus_language_input"],
                genre=st.session_state["corpus_genre_input"],
                domain=st.session_state["corpus_domain_input"],
                audience=st.session_state["corpus_audience_input"],
                tone=st.session_state["corpus_tone_input"],
                total_articles=st.session_state["corpus_total_articles_input"],
                target_words=st.session_state["corpus_target_words_input"],
                hard_constraints=st.session_state["corpus_constraints_input"],
                extra_notes=st.session_state["corpus_notes_input"],
                available_config=st.session_state[AVAILABLE_CONFIG],
                selected_platform=selected_platform,
                selected_model=selected_model,
                temperature=plan_temperature,
                current_plan=current_plan,
                feedback=st.session_state.get("corpus_plan_feedback", ""),
            )
        if result["ok"]:
            workflow["plan"] = result["plan"]
            workflow["plan_round"] = workflow.get("plan_round", 1) + 1
            _reset_downstream(workflow)
            _seed_plan_editor(result["plan"])
            st.success("策略已更新。")
            st.rerun()
        else:
            st.error(result["error"])

    if confirm_plan_clicked:
        confirmed_plan = _read_plan_from_editor(plan)
        workflow["plan"] = confirmed_plan
        workflow["confirmed_plan"] = confirmed_plan
        _reset_downstream(workflow, keep_plan=True)
        st.success("策略已确认，进入样稿阶段。")

confirmed_plan = workflow.get("confirmed_plan")
if confirmed_plan:
    st.divider()
    st.subheader("3. 样稿确认")
    st.multiselect(
        "选择 1-2 个标题先生成样稿",
        options=confirmed_plan["title_candidates"],
        default=st.session_state.get("corpus_sample_title_selector", confirmed_plan["title_candidates"][:2]),
        key="corpus_sample_title_selector",
    )
    st.text_area(
        "样稿补充要求",
        key="corpus_sample_feedback",
        height=100,
        placeholder="例如：开头更像新闻导语；减少解释腔；更突出研究发现的社会影响",
    )
    sample_col1, sample_col2 = st.columns(2)
    with sample_col1:
        generate_samples_clicked = st.button("生成样稿", type="primary", use_container_width=True)
    with sample_col2:
        sample_replan_clicked = st.button("把样稿反馈打回策略层", use_container_width=True)

    if generate_samples_clicked:
        with st.spinner("正在生成样稿..."):
            result = generate_sample_articles(
                plan=confirmed_plan,
                selected_titles=st.session_state.get("corpus_sample_title_selector", []),
                target_words=st.session_state["corpus_target_words_input"],
                available_config=st.session_state[AVAILABLE_CONFIG],
                selected_platform=selected_platform,
                selected_model=selected_model,
                temperature=sample_temperature,
                feedback=st.session_state.get("corpus_sample_feedback", ""),
            )
        if result["ok"]:
            workflow["samples"] = result
            workflow["corpus"] = None
            workflow["judge"] = None
            st.success("样稿已生成。确认风格后再进入批量生成。")
        else:
            st.error(result["error"])

    if sample_replan_clicked:
        current_plan = _read_plan_from_editor(confirmed_plan)
        feedback = st.session_state.get("corpus_sample_feedback", "").strip()
        if not feedback:
            st.warning("请先写一点样稿反馈，再回到策略层。")
        else:
            with st.spinner("正在根据样稿反馈回调策略..."):
                result = generate_corpus_plan(
                    brief=st.session_state["corpus_brief_input"],
                    language=st.session_state["corpus_language_input"],
                    genre=st.session_state["corpus_genre_input"],
                    domain=st.session_state["corpus_domain_input"],
                    audience=st.session_state["corpus_audience_input"],
                    tone=st.session_state["corpus_tone_input"],
                    total_articles=st.session_state["corpus_total_articles_input"],
                    target_words=st.session_state["corpus_target_words_input"],
                    hard_constraints=st.session_state["corpus_constraints_input"],
                    extra_notes=st.session_state["corpus_notes_input"],
                    available_config=st.session_state[AVAILABLE_CONFIG],
                    selected_platform=selected_platform,
                    selected_model=selected_model,
                    temperature=plan_temperature,
                    current_plan=current_plan,
                    feedback=feedback,
                )
            if result["ok"]:
                workflow["plan"] = result["plan"]
                workflow["confirmed_plan"] = None
                workflow["plan_round"] = workflow.get("plan_round", 1) + 1
                _reset_downstream(workflow)
                _seed_plan_editor(result["plan"])
                st.success("策略草案已按样稿反馈回调，请重新确认。")
                st.rerun()
            else:
                st.error(result["error"])

samples = workflow.get("samples")
if samples:
    st.markdown("**样稿预览**")
    for article in samples["articles"]:
        _render_article(article, prefix="sample")

if samples:
    st.divider()
    st.subheader("4. 批量生成语料库")
    default_total = st.session_state.get("corpus_total_articles_input", len(confirmed_plan["title_candidates"]))
    default_batch = recommended_batch_size(default_total)
    batch_col1, batch_col2, batch_col3 = st.columns(3)
    with batch_col1:
        st.number_input("最终文章数", min_value=2, max_value=200, value=default_total, step=2, key="corpus_batch_total_articles")
    with batch_col2:
        st.number_input("最终每篇目标词数", min_value=150, max_value=4000, value=st.session_state.get("corpus_target_words_input", 700), step=50, key="corpus_batch_target_words")
    with batch_col3:
        st.slider("每批生成标题数", 1, 3, value=default_batch, key="corpus_batch_size")
    st.multiselect(
        "优先标题池（不足时系统会自动扩展）",
        options=confirmed_plan["title_candidates"],
        default=st.session_state.get("corpus_batch_title_selector", confirmed_plan["title_candidates"]),
        key="corpus_batch_title_selector",
    )
    st.text_area(
        "批量生成补充要求",
        key="corpus_batch_feedback",
        height=110,
        placeholder="例如：后半批次增加气候科学与材料科学；标题不要太接近前面的样稿；保持新闻感",
    )
    with st.expander("断点续跑（可选）", expanded=False):
        st.text_input(
            "会话目录路径",
            key="corpus_session_dir",
            placeholder="例如：.runtime/corpus_sessions/my_run（留空则不持久化）",
            help="指定后，每批生成结果会写入该目录的 batches.jsonl，重新运行时自动跳过已完成批次。",
        )
    generate_corpus_clicked = st.button("开始批量生成语料库", type="primary", use_container_width=True)

    if generate_corpus_clicked:
        with st.spinner("正在批量生成语料库..."):
            session_dir_val = st.session_state.get("corpus_session_dir", "").strip() or None
            result = generate_corpus_collection(
                plan=confirmed_plan,
                selected_titles=st.session_state.get("corpus_batch_title_selector", []),
                total_articles=st.session_state["corpus_batch_total_articles"],
                target_words=st.session_state["corpus_batch_target_words"],
                batch_size=st.session_state["corpus_batch_size"],
                available_config=st.session_state[AVAILABLE_CONFIG],
                selected_platform=selected_platform,
                selected_model=selected_model,
                temperature=sample_temperature,
                feedback=st.session_state.get("corpus_batch_feedback", ""),
                session_dir=session_dir_val,
            )
        if result["ok"]:
            workflow["corpus"] = result
            workflow["judge"] = None
            st.success(f"已生成 {len(result['articles'])} 篇文章。下一步运行 judge。")
        else:
            st.error(result["error"])

corpus = workflow.get("corpus")
if corpus:
    corpus_cols = st.columns(3)
    corpus_cols[0].metric("文章数", len(corpus["articles"]))
    corpus_cols[1].metric("标题池", len(corpus["titles"]))
    corpus_cols[2].metric("批次数", len(corpus["batch_runs"]))
    st.download_button(
        "下载当前语料 JSON",
        data=json.dumps(corpus, ensure_ascii=False, indent=2),
        file_name="corpus_articles.json",
        mime="application/json",
        use_container_width=True,
        key="download_corpus_articles",
    )
    for article in corpus["articles"]:
        _render_article(article, prefix="batch")

if corpus:
    st.divider()
    st.subheader("5. Judge 评估")
    judge_clicked = st.button("运行 Judge", type="primary", use_container_width=True)
    if judge_clicked:
        with st.spinner("正在进行 judge 评估..."):
            result = judge_corpus_collection(
                plan=confirmed_plan,
                articles=corpus["articles"],
                available_config=st.session_state[AVAILABLE_CONFIG],
                selected_platform=selected_platform,
                selected_model=selected_model,
                temperature=judge_temperature,
            )
        if result["ok"]:
            workflow["judge"] = result
            st.success("Judge 已完成。")
        else:
            st.error(result["error"])

judge = workflow.get("judge")
if judge:
    st.markdown(f"**Judge 总结**: {judge['summary']}")
    if judge["averages"]:
        judge_cols = st.columns(5)
        metrics = [
            ("贴合 brief", "brief_alignment"),
            ("风格贴合", "style_fit"),
            ("清晰度", "clarity"),
            ("科学语气", "scientific_tone"),
            ("实用性", "usefulness"),
        ]
        for col, (label, key) in zip(judge_cols, metrics, strict=True):
            col.metric(label, judge["averages"][key])
    if judge["global_issues"]:
        st.markdown("**全局问题**")
        for issue in judge["global_issues"]:
            st.markdown(f"- {issue}")
    _render_judge_table(judge)

    st.download_button(
        "下载完整工作流 JSON",
        data=build_corpus_studio_export_json(
            plan=workflow.get("confirmed_plan") or workflow.get("plan"),
            samples=workflow.get("samples"),
            corpus=workflow.get("corpus"),
            judge=workflow.get("judge"),
        ),
        file_name=build_corpus_studio_export_filename(),
        mime="application/json",
        use_container_width=True,
        key="download_corpus_studio_bundle",
    )
