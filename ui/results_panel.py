import streamlit as st

def results_panel(batches, display_questions_table):
    st.header("📊 Resultados da Geração Atual")
    total_generated = sum(batch.total_generated for batch in batches)
    total_approved = sum(batch.total_approved for batch in batches)
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

    # Tabela de questões
    st.subheader("📋 Tabela de Todas as Questões")
    display_questions_table(batches)

    # Exportação
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            from utils.export import export_questions_list_json
            from utils.export import export_question_json
            import json
            
            export_list = []
            for batch in batches:
                for idx, qwv in enumerate(batch.questions):
                    q = qwv.question
                    disciplina = getattr(q, 'materia', getattr(q, 'subject', None))
                    alternativas = q.opcoes if hasattr(q, 'opcoes') else {}
                    gabarito = q.gabarito if q.gabarito in ['A', 'B', 'C', 'D'] else str(q.gabarito)
                    # Usa função utilitária para garantir formato
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
