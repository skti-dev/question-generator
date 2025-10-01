import streamlit as st
from utils.export import export_question_json, export_questions_list_json
from pipeline import pipeline
from ui.actions import prepare_export_list_from_selected

_MIME_JSON = "application/json"


def _render_actions_bar(cache_entries):
    if 'selected_questions_cache' not in st.session_state:
        st.session_state['selected_questions_cache'] = []

    st.markdown("#### 🔧 Ações Disponíveis")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _handle_select_all(cache_entries)
    with col2:
        _handle_delete_selected()
    with col3:
        if st.button("💾 Exportar Selecionadas", key="export_selected_cache", disabled=len(st.session_state['selected_questions_cache']) == 0):
            if len(st.session_state['selected_questions_cache']) > 0:
                # Preparar lista de exportação usando helper central (evita import circular)
                export_list = prepare_export_list_from_selected(st.session_state['selected_questions_cache'])
                if export_list:
                    json_data, filename = export_questions_list_json(export_list, filename_prefix="questoes_selecionadas")
                    if json_data and filename:
                        st.download_button(
                            label=f"📥 Download {len(st.session_state['selected_questions_cache'])} Questões",
                            data=json_data,
                            file_name=filename,
                            mime=_MIME_JSON,
                            key="download_selected_cache"
                        )
    with col4:
        selected_count = len(st.session_state['selected_questions_cache'])
        st.metric("Selecionadas", selected_count)


def _handle_select_all(cache_entries):
    if st.button("📋 Selecionar Todas", key="select_all_cache"):
        st.session_state['selected_questions_cache'] = []
        for i, entry in enumerate(cache_entries):
            st.session_state['selected_questions_cache'].append({
                'source': 'cache',
                'cache_key': entry.cache_key,
                'codigo': entry.question.codigo,
                'index': i
            })
        st.rerun()


def _handle_delete_selected():
    if st.button("🗑️ Excluir Selecionadas", key="delete_selected_cache", disabled=len(st.session_state['selected_questions_cache']) == 0):
        if len(st.session_state['selected_questions_cache']) > 0:
            st.session_state['delete_selected_questions'] = st.session_state['selected_questions_cache']
            st.rerun()


def _format_date(created_at):
    from datetime import datetime
    try:
        if isinstance(created_at, str):
            try:
                return datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                try:
                    return datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    return datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        return created_at
    except Exception:
        return None


def _render_stats(cache_entries):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total no Cache", len(cache_entries))
    with col2:
        high_confidence = sum(1 for entry in cache_entries if entry.validation.confidence_score >= 0.8)
        st.metric("Alta Confiança", high_confidence)
    with col3:
        unique_codes = len({entry.question.codigo for entry in cache_entries})
        st.metric("Códigos Únicos", unique_codes)
    with col4:
        latest_dates = [d for d in (_format_date(entry.created_at) for entry in cache_entries) if d is not None]
        if latest_dates:
            latest_date = max(latest_dates)
            st.metric("Última Atualização", latest_date.strftime("%d/%m/%Y"))
        else:
            st.metric("Última Atualização", "N/A")


def _confidence_icon(score: float) -> str:
    if score >= 0.8:
        return "🟢"
    if score >= 0.6:
        return "🟡"
    return "🔴"


def _render_cache_item(i, entry):
    question = entry.question
    validation = entry.validation
    confidence_score = validation.confidence_score
    confidence_icon = _confidence_icon(confidence_score)
    status_icon = "✅" if validation.is_aligned else "❌"

    created_at = _format_date(entry.created_at)
    date_str = created_at.strftime("%d/%m/%Y %H:%M") if created_at else "Data inválida"

    with st.container():
        col1, col2 = st.columns([4, 1])
        _render_cache_item_selection(col1, entry, i, date_str, question, confidence_icon, confidence_score, status_icon)
        _render_cache_item_actions(col2, entry, i, question)
    st.divider()


def _render_cache_item_selection(col, entry, i, date_str, question, confidence_icon, confidence_score, status_icon):
    with col:
        item_selected = {
            'source': 'cache',
            'cache_key': entry.cache_key,
            'codigo': question.codigo,
            'index': i
        }
        if 'selected_questions_cache' not in st.session_state:
            st.session_state['selected_questions_cache'] = []
        is_selected = any(item['cache_key'] == entry.cache_key for item in st.session_state['selected_questions_cache'])
        checkbox_changed = False
        if st.checkbox(
            f"{status_icon} **{question.codigo}** - {question.enunciado[:80]}{'...' if len(question.enunciado) > 80 else ''}",
            key=f"select_cache_{i}",
            value=is_selected
        ):
            if item_selected not in st.session_state['selected_questions_cache']:
                st.session_state['selected_questions_cache'].append(item_selected)
                checkbox_changed = True
        else:
            if any(item['cache_key'] == entry.cache_key for item in st.session_state['selected_questions_cache']):
                st.session_state['selected_questions_cache'] = [
                    item for item in st.session_state['selected_questions_cache']
                    if item['cache_key'] != entry.cache_key
                ]
                checkbox_changed = True
        if checkbox_changed:
            st.rerun()
        col_info1, col_info2, col_info3, col_info4 = st.columns(4)
        with col_info1:
            st.write(f"**Data:** {date_str}")
        with col_info2:
            st.write(f"**Tipo:** {question.question_type.value.replace('_', ' ').title()}")
        with col_info3:
            st.write(f"**Gabarito:** {question.gabarito}")
        with col_info4:
            st.write(f"**Confiança:** {confidence_icon} {confidence_score:.2f}")


def _render_cache_item_actions(col, entry, i, question):
    with col:
        st.markdown("**Ações:**")
        show_question_key = f"show_cache_{i}"
        button_text = "🙈 Ocultar questão" if st.session_state.get(show_question_key, False) else "👁️ Ver questão completa"
        if st.button(button_text, help="Alternar visualização da questão", key=f"view_cache_{i}"):
            st.session_state[show_question_key] = not st.session_state.get(show_question_key, False)
            st.rerun()
        if st.session_state.get(show_question_key, False):
            st.code(question.format_question(), language="text")
        json_data, filename = export_question_json(
            getattr(question, 'materia', getattr(question, 'subject', None)),
            question.codigo,
            question.enunciado,
            dict(zip(['A', 'B', 'C', 'D'], question.opcoes)) if question.opcoes else {},
            question.gabarito,
            f"_cache_{i+1}"
        )
        if json_data and filename:
            st.download_button(
                label="💾",
                data=json_data,
                file_name=filename,
                mime=_MIME_JSON,
                help="Exportar questão individual",
                key=f"export_cache_{i}"
            )
        if st.button("🗑️", help="Excluir do cache", key=f"delete_cache_{i}"):
            st.session_state['delete_question'] = {
                'source': 'cache',
                'cache_key': entry.cache_key
            }
            st.rerun()


def cache_panel():
    cache_entries = pipeline.cache_manager.get_all_cache_entries()
    if not cache_entries:
        st.info("📭 Nenhuma questão encontrada no cache.")
        return

    _render_actions_bar(cache_entries)
    _render_stats(cache_entries)
    st.markdown("---")

    for i, entry in enumerate(cache_entries):
        _render_cache_item(i, entry)

    # Exportação do histórico completo
    st.markdown("---")
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        export_list = []
        for entry in cache_entries:
            q = entry.question
            disciplina = getattr(q, 'materia', getattr(q, 'subject', None))
            alternativas = dict(zip(['A', 'B', 'C', 'D'], q.opcoes)) if q.opcoes else {}
            gabarito = q.gabarito if q.gabarito in ['A', 'B', 'C', 'D'] else str(q.gabarito)
            # Use central exporter to normalize each item
            json_ind, _ = export_question_json(disciplina, q.codigo, q.enunciado, alternativas, gabarito)
            export_list.append(__import__('json').loads(json_ind))
        if export_list:
            json_export, file_name = export_questions_list_json(export_list, filename_prefix="historico_completo_questoes")
            st.download_button(
                label="📥 Exportar Histórico Completo (JSON)",
                data=json_export,
                file_name=file_name,
                mime=_MIME_JSON,
                type="secondary",
                use_container_width=True
            )
        else:
            st.warning("⚠️ Nenhum dado válido para exportação")
