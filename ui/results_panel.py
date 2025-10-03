import streamlit as st


def _confidence_icon(score: float) -> str:
    if score >= 0.8:
        return "🟢"
    if score >= 0.6:
        return "🟡"
    return "🔴"


def _is_approved_local(qwv) -> bool:
    try:
        return bool(qwv.validation.is_aligned) and float(qwv.validation.confidence_score) >= 0.7
    except Exception:
        return False


def _render_rejected_panel(batches):
    rejected_exists = any(any(not _is_approved_local(q) for q in batch.questions) for batch in batches)
    if not rejected_exists:
        return
    with st.expander("⚠️ Questões Rejeitadas na Validação", expanded=True):
        st.markdown("**🔄 Estas questões não foram aprovadas e podem ser regeneradas:**")
        for batch in batches:
            rejected_pairs = [(idx, q) for idx, q in enumerate(batch.questions) if not _is_approved_local(q)]
            if not rejected_pairs:
                continue
            st.markdown(f"### 📖 {batch.request.codigo} - {batch.request.objeto_conhecimento[:60]}...")
            for orig_idx, qwv in rejected_pairs:
                question = qwv.question
                validation = qwv.validation
                st.markdown(f"**❌ Questão Rejeitada {orig_idx+1}** - {question.question_type.value.replace('_', ' ').title()}")
                st.code(question.format_question(), language="text")
                st.markdown(f"**Motivo da Rejeição:** {_confidence_icon(validation.confidence_score)} Confiança: {validation.confidence_score:.2f}")
                st.markdown(f"**📝 Feedback:** {validation.feedback}")
                regen_key = f"regen_btn_{batch.request.codigo}_{orig_idx}"
                if st.button("🔄 Regenerar", key=regen_key, type="secondary"):
                    st.session_state['regenerate_request'] = {
                        'codigo': batch.request.codigo,
                        'index': orig_idx,
                        'request': batch.request
                    }
                    st.rerun()


def _render_approved_panel(batches):
    with st.expander("🔍 Análise Detalhada das Questões Aprovadas", expanded=False):
        for batch in batches:
            approved_questions = [q for q in batch.questions if _is_approved_local(q)]
            st.markdown(f"## 📖 {batch.request.codigo} - {batch.request.objeto_conhecimento[:80]}...")
            st.info(f"**Unidade Temática:** {batch.request.unidade_tematica}")
            if not approved_questions:
                st.warning("⚠️ Nenhuma questão foi aprovada na validação para este código.")
                st.markdown("---")
                continue
            for j, qwv in enumerate(approved_questions):
                question = qwv.question
                validation = qwv.validation
                st.markdown(f"### ✅ Questão Aprovada {j+1} - {question.question_type.value.replace('_', ' ').title()}")
                st.markdown("**Questão:**")
                st.code(question.format_question(), language="text")
                st.markdown(f"**Validação:** {_confidence_icon(validation.confidence_score)} Confiança: {validation.confidence_score:.2f}")
                st.markdown(f"**Feedback:** {validation.feedback}")
                st.divider()


def results_panel(batches, display_questions_table):
    st.header("📊 Resultados da Geração Atual")
    total_generated = sum(batch.total_generated for batch in batches)
    total_approved = sum(sum(1 for q in batch.questions if _is_approved_local(q)) for batch in batches)
    approval_rate = (total_approved / total_generated * 100) if total_generated > 0 else 0
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Gerado", total_generated)
    with col2:
        st.metric("Aprovadas", total_approved)
    with col3:
        st.metric("Taxa de Aprovação", f"{approval_rate:.1f}%")
    with col4:
        st.metric("Códigos Processados", len(batches))

    _render_rejected_panel(batches)
    _render_approved_panel(batches)

    # Tabela de questões
    st.subheader("📋 Tabela de Todas as Questões")
    display_questions_table(batches)

    # Exportação (mantenho funcionalidade existente)
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            from utils.export import export_questions_list_json, export_question_json
            import json
            export_list = []
            for batch in batches:
                for idx, qwv in enumerate(batch.questions):
                    q = qwv.question
                    disciplina = getattr(q, 'materia', getattr(q, 'subject', None))
                    alternativas = q.opcoes if hasattr(q, 'opcoes') else {}
                    gabarito = q.gabarito if q.gabarito in ['A', 'B', 'C', 'D'] else str(q.gabarito)
                    json_data_individual, _ = export_question_json(disciplina, batch.request.codigo, q.enunciado, alternativas, gabarito, f"_atual_{idx+1}")
                    export_list.append(json.loads(json_data_individual))
            json_data, file_name = export_questions_list_json(export_list, filename_prefix="questoes_bncc_4ano")
            st.download_button(
                label="💾 Exportar Geração Atual (JSON)",
                data=json_data,
                file_name=file_name,
                mime="application/json",
                type="primary",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"❌ Erro na preparação da exportação: {e}")
