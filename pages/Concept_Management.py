import streamlit as st
import json
from app.state.session_state import ensure_core_state
from app.services.concept_service import (
    build_export_filename,
    build_import_preview,
    build_export_json,
    create_concept,
    merge_concepts,
    parse_import_json,
    replace_concepts,
    validate_import_payload,
)

# 页面标题
st.title("📚 概念管理")

st.markdown("""
<p style='color: var(--color-text); line-height: 1.6; margin-bottom: 1.5rem;'>
    在此页面管理您的语义概念。您可以添加新概念、编辑现有概念、导入导出概念数据。
    概念是标注的基础，每个概念包含名称、提示词、分类和标注样例。
</p>
""", unsafe_allow_html=True)

# 初始化共享 session state
ensure_core_state()

# 数据管理部分
st.subheader("📁 数据管理")

col1, col2 = st.columns(2)

with col1:
    # 导出功能
    st.markdown("**导出概念**")
    st.markdown("将当前所有概念导出为JSON文件")
    
    # 创建一个容器来模拟文件上传器的高度
    with st.container():
        # 显示当前概念数量
        st.markdown(f":blue[当前共有 {len(st.session_state.concepts)} 个概念]")
        st.caption(f"当前数据版本: v{st.session_state.get('concepts_data_version', '1.0')}")
        
        # 准备导出的数据
        export_json = build_export_json(st.session_state.concepts)
        export_file_name = build_export_filename(st.session_state.get("concepts_data_version", "1.0"))
        
        # 创建下载按钮
        st.download_button(
            label="📥 下载概念文件",
            data=export_json,
            file_name=export_file_name,
            mime="application/json",
            help="下载当前所有概念为JSON文件",
            use_container_width=True,
            type="primary"
        )
        
        # 添加一些提示信息
        st.caption("导出的文件可以在其他设备或会话中导入使用")

with col2:
    # 导入功能
    st.markdown("**导入概念**")
    st.markdown("从JSON文件导入概念")
    
    uploaded_file = st.file_uploader(
        "选择概念文件",
        type=["json"],
        help="选择包含概念的JSON文件",
        key="concept_import"
    )
    
    if uploaded_file is not None:
        try:
            # 读取上传的文件
            file_content = uploaded_file.getvalue().decode("utf-8")
            imported_data = parse_import_json(file_content)

            is_valid, error_details = validate_import_payload(imported_data)
            if not is_valid:
                st.error("导入校验失败")
                if error_details:
                    st.markdown(f"**字段**: `{error_details['field']}`")
                    st.markdown(f"**原因**: {error_details['reason']}")
                    st.markdown(f"**建议**: {error_details['hint']}")
            else:
                ok, preview_error, preview = build_import_preview(imported_data, st.session_state.concepts)
                if not ok:
                    st.error("导入预检失败")
                    if preview_error:
                        st.markdown(f"**字段**: `{preview_error['field']}`")
                        st.markdown(f"**原因**: {preview_error['reason']}")
                        st.markdown(f"**建议**: {preview_error['hint']}")
                else:
                    st.info(f"检测到 {preview['concept_count']} 个概念（version: {preview['version']}）")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("重复概念数", preview["duplicate_count"])
                    with c2:
                        st.metric("自动修复字段数", preview["auto_fix_count"])
                    with c3:
                        st.metric("可导入概念数", preview["concept_count"] - preview["duplicate_count"])

                    # 显示导入选项
                    import_option = st.radio(
                        "导入选项",
                        ["替换现有概念", "添加到当前所有概念的后面"],
                        index=0,
                        help="选择如何导入概念"
                    )

                    if st.button("确认导入", type="primary", use_container_width=True):
                        normalized_imported_concepts = preview["normalized_concepts"]
                        if import_option == "替换现有概念":
                            st.session_state.concepts, import_message = replace_concepts(normalized_imported_concepts)
                        else:
                            st.session_state.concepts, import_message = merge_concepts(
                                st.session_state.concepts,
                                normalized_imported_concepts,
                            )

                        st.session_state.concepts_data_version = preview["version"]
                        st.success(import_message)
                        st.rerun()
        except json.JSONDecodeError:
            st.error("文件格式错误：不是有效的JSON文件")
        except Exception as e:
            st.error(f"导入失败：{str(e)}")

st.divider()

# 概念列表和编辑
st.subheader("📋 概念列表")

if not st.session_state.concepts:
    st.info("暂无概念，请先添加概念")
else:
    # 显示所有概念
    for i, concept in enumerate(st.session_state.concepts):
        with st.expander(f"{concept['name']} - {concept.get('category', '未分类')}", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**概念ID**: {i}")
                st.markdown(f"**分类**: {concept.get('category', '未分类')}")
                st.markdown(f"**提示词**: {concept['prompt'][:200]}..." if len(concept['prompt']) > 200 else f"**提示词**: {concept['prompt']}")
                st.markdown(f"**样例数量**: {len(concept.get('examples', []))}")
                
                if concept.get('is_default', False):
                    st.info("🔒 这是默认概念")
            
            with col2:
                # 编辑按钮
                edit_key = f"edit_{i}"
                if st.button("✏️ 编辑", key=edit_key, use_container_width=True):
                    st.session_state.editing_concept_index = i
                    st.rerun()
                
                # 删除按钮（不能删除默认概念）
                if not concept.get('is_default', False):
                    delete_key = f"delete_{i}"
                    if st.button("🗑️ 删除", key=delete_key, use_container_width=True):
                        st.session_state.concepts.pop(i)
                        st.success(f"概念 '{concept['name']}' 已删除")
                        st.rerun()

# 编辑概念功能
if "editing_concept_index" in st.session_state:
    st.divider()
    st.subheader("✏️ 编辑概念")
    
    index = st.session_state.editing_concept_index
    concept = st.session_state.concepts[index]
    
    with st.form(key=f"edit_form_{index}"):
        new_name = st.text_input("概念名称", value=concept["name"])
        new_prompt = st.text_area("提示词", value=concept["prompt"], height=150)
        new_category = st.text_input("分类", value=concept.get("category", ""))
        
        st.subheader("标注样例")
        examples = concept.get("examples", [])
        
        for i, example in enumerate(examples):
            col1, col2 = st.columns(2)
            with col1:
                new_text = st.text_area(f"样例{i+1}文本", value=example["text"], 
                                       key=f"edit_text_{index}_{i}")
            with col2:
                new_annotation = st.text_area(f"样例{i+1}标注", value=example["annotation"],
                                            key=f"edit_ann_{index}_{i}")
            
            if new_text != example["text"] or new_annotation != example["annotation"]:
                example["text"] = new_text
                example["annotation"] = new_annotation
        
        # 添加新样例按钮
        add_example = st.form_submit_button("添加样例")
        if add_example:
            examples.append({"text": "", "annotation": ""})
            st.rerun()
        
        # 删除最后一个样例按钮
        delete_example = False
        if len(examples) > 0:
            delete_example = st.form_submit_button("删除最后一个样例")
            if delete_example:
                examples.pop()
                st.rerun()
        
        # 保存和取消按钮
        col1, col2 = st.columns(2)
        with col1:
            save_clicked = st.form_submit_button("💾 保存修改", type="primary", use_container_width=True)
        with col2:
            cancel_clicked = st.form_submit_button("❌ 取消", use_container_width=True)
        
        if save_clicked:
            concept["name"] = new_name
            concept["prompt"] = new_prompt
            concept["category"] = new_category
            concept["examples"] = examples
            
            # 清除编辑状态
            del st.session_state.editing_concept_index
            st.success("概念已更新！")
            st.rerun()
        
        if cancel_clicked:
            # 清除编辑状态
            del st.session_state.editing_concept_index
            st.rerun()

# 添加新概念
st.divider()
st.subheader("➕ 添加新概念")

with st.form(key="add_concept_form"):
    new_concept_name = st.text_input("新概念名称*", placeholder="请输入概念名称（必填）")
    new_concept_prompt = st.text_area("新概念提示词*", height=150, 
                                     placeholder="请输入概念提示词，描述这个概念的定义和标注要求（必填）")
    new_concept_category = st.text_input("新概念分类*", placeholder="请输入分类（必填）")
    
    # 提示信息
    st.caption("注：带 * 的字段为必填项")
    
    col1, col2 = st.columns(2)
    with col1:
        submit_clicked = st.form_submit_button("✅ 添加概念", type="primary", use_container_width=True)
    with col2:
        reset_clicked = st.form_submit_button("🔄 重置", use_container_width=True)
    
    if submit_clicked:
        if new_concept_name and new_concept_prompt and new_concept_category:
            # 检查是否已存在同名概念
            existing_names = {c["name"] for c in st.session_state.concepts}
            if new_concept_name in existing_names:
                st.error(f"概念名称 '{new_concept_name}' 已存在，请使用其他名称")
            else:
                new_concept = create_concept(new_concept_name, new_concept_prompt, new_concept_category)
                st.session_state.concepts.append(new_concept)
                st.success(f"概念 '{new_concept_name}' 已添加！")
                st.rerun()
        else:
            st.warning("请填写所有必填字段：概念名称、提示词和分类")

# 导航按钮
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🏠 返回首页", use_container_width=True):
        st.switch_page("pages/Home.py")

with col2:
    if st.button("✏️ 前往标注", use_container_width=True):
        st.switch_page("pages/Annotation.py")

with col3:
    if st.button("🔄 刷新页面", use_container_width=True):
        st.rerun()

# 页脚
st.divider()
st.markdown("""
<div style='text-align: center; color: var(--color-text); font-size: 0.9rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid rgba(255, 255, 255, 0.2);'>
    <p><strong>概念管理页面</strong> | 当前概念数量: {}</p>
    <p>提示: 概念数据保存在 session state 中，重启应用后会从 concepts.json 重新加载</p>
</div>
""".format(len(st.session_state.concepts)), unsafe_allow_html=True)
