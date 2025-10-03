import streamlit as st
from utils.export import export_question_json


def _ensure_selected_state():
    if 'selected_questions_current' not in st.session_state:
        st.session_state['selected_questions_current'] = []


def _actions_bar(batches):
    st.markdown("#### 🔧 Ações Disponíveis")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📋 Selecionar Todas", key="select_all_current"):
            st.session_state['selected_questions_current'] = []
            for i, batch in enumerate(batches):
                for j, _ in enumerate(batch.questions):
                    st.session_state['selected_questions_current'].append({
                        'source': 'current',
                        'codigo': batch.request.codigo,
                        'batch_index': i,
                        'index': j
                    })
            st.rerun()
    with col2:
        if st.button("🗑️ Excluir Selecionadas", key="delete_selected_current", disabled=len(st.session_state['selected_questions_current']) == 0):
            if len(st.session_state['selected_questions_current']) > 0:
                st.session_state['delete_selected_questions'] = st.session_state['selected_questions_current']
                st.rerun()
    with col3:
        _export_selected_current(batches)
    with col4:
        selected_count = len(st.session_state['selected_questions_current'])
        st.metric("Selecionadas", selected_count)


def _render_question_block(batch_idx, q_idx, batch, qwv):
    question = qwv.question
    validation = qwv.validation
    # Considera aprovada apenas se alinhada e confiança >= 0.7
    def _is_approved_local(q):
        try:
            return bool(q.validation.is_aligned) and float(q.validation.confidence_score) >= 0.7
        except Exception:
            return False

    status_icon = "✅" if _is_approved_local(qwv) else "❌"
    confidence_icon = _confidence_icon(validation.confidence_score)

    with st.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            item_selected = {
                'source': 'current',
                'codigo': batch.request.codigo,
                'batch_index': batch_idx,
                'index': q_idx
            }
            label = f"{status_icon} **{batch.request.codigo}** - {question.enunciado[:80]}" + ("..." if len(question.enunciado) > 80 else "")
            _toggle_selection_for_item(item_selected, label, batch_idx, q_idx)
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.write(f"**Tipo:** {question.question_type.value.replace('_', ' ').title()}")
            with col_info2:
                st.write(f"**Gabarito:** {question.gabarito}")
            with col_info3:
                st.write(f"**Confiança:** {confidence_icon} {validation.confidence_score:.2f}")
        with col2:
            st.markdown("**Ações:**")
            show_question_key = f"show_current_{batch_idx}_{q_idx}"
            button_text = "🙈 Ocultar questão" if st.session_state.get(show_question_key, False) else "👁️ Ver questão completa"
            if st.button(button_text, help="Alternar visualização da questão", key=f"view_current_{batch_idx}_{q_idx}"):
                st.session_state[show_question_key] = not st.session_state.get(show_question_key, False)
                st.rerun()
            if st.session_state.get(show_question_key, False):
                st.code(question.format_question(), language="text")
            alternativas = dict(zip(['A', 'B', 'C', 'D'], question.opcoes)) if question.opcoes else {}
            json_data, filename = export_question_json(
                getattr(question, 'materia', getattr(question, 'subject', None)),
                batch.request.codigo,
                question.enunciado,
                alternativas,
                question.gabarito,
                f"_atual_{q_idx+1}"
            )
            if json_data and filename:
                st.download_button(
                    label="💾",
                    data=json_data,
                    file_name=filename,
                    mime="application/json",
                    help="Exportar questão individual",
                    key=f"export_current_{batch_idx}_{q_idx}"
                )
            if st.button("🗑️", help="Excluir questão", key=f"delete_current_{batch_idx}_{q_idx}"):
                st.session_state['delete_question'] = {
                    'source': 'current',
                    'codigo': batch.request.codigo,
                    'index': q_idx
                }
                st.rerun()
    st.divider()


def _confidence_icon(score: float) -> str:
    if score >= 0.8:
        return "🟢"
    if score >= 0.6:
        return "🟡"
    return "🔴"


def _export_selected_current(batches):
    if st.button("💾 Exportar Selecionadas", key="export_selected_current", disabled=len(st.session_state['selected_questions_current']) == 0):
        if len(st.session_state['selected_questions_current']) > 0:
            # Import local to avoid circular imports
            from ui.actions import prepare_export_list_from_selected
            export_list = prepare_export_list_from_selected(st.session_state['selected_questions_current'], current_batches=batches)
            if export_list:
                from utils.export import export_questions_list_json
                json_data, filename = export_questions_list_json(export_list, filename_prefix="questoes_selecionadas")
                if json_data and filename:
                    st.download_button(
                        label=f"📥 Download {len(st.session_state['selected_questions_current'])} Questões",
                        data=json_data,
                        file_name=filename,
                        mime="application/json",
                        key="download_selected_current"
                    )


def _toggle_selection_for_item(item_selected, label, batch_idx, q_idx):
    # handle checkbox selection state for a question item
    if 'selected_questions_current' not in st.session_state:
        st.session_state['selected_questions_current'] = []
    is_selected = any(item['batch_index'] == batch_idx and item['index'] == q_idx for item in st.session_state['selected_questions_current'])
    checkbox_changed = False
    if st.checkbox(label, key=f"select_current_{batch_idx}_{q_idx}", value=is_selected):
        if item_selected not in st.session_state['selected_questions_current']:
            st.session_state['selected_questions_current'].append(item_selected)
            checkbox_changed = True
    else:
        if any(item['batch_index'] == batch_idx and item['index'] == q_idx for item in st.session_state['selected_questions_current']):
            st.session_state['selected_questions_current'] = [
                item for item in st.session_state['selected_questions_current']
                if not (item['batch_index'] == batch_idx and item['index'] == q_idx)
            ]
            checkbox_changed = True
    if checkbox_changed:
        st.rerun()


def questions_table_panel(batches, handle_question_actions):
    handle_question_actions()
    _ensure_selected_state()
    _actions_bar(batches)
    st.markdown("---")

    for i, batch in enumerate(batches):
        st.markdown(f"### 📖 {batch.request.codigo} - {batch.request.objeto_conhecimento[:60]}...")
        for j, qwv in enumerate(batch.questions):
            _render_question_block(i, j, batch, qwv)
    total_questions = sum(len(batch.questions) for batch in batches)
    total_approved = sum(sum(1 for q in batch.questions if (bool(q.validation.is_aligned) and float(q.validation.confidence_score) >= 0.7)) for batch in batches)
    total_rejected = total_questions - total_approved
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Aprovadas", total_approved)
    with col2:
        st.metric("❌ Rejeitadas", total_rejected)
    with col3:
        st.metric("📊 Total", total_questions)
