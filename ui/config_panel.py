import streamlit as st
from pipeline import get_subjects, get_codes_for_subject

def config_panel():
    subjects = get_subjects()
    if not subjects:
        st.error("❌ Dados da BNCC não encontrados! Verifique se o arquivo BNCC_4ano_Mapeamento.json existe.")
        return None, None, None

    selected_subject = st.selectbox(
        "📖 Selecione a Matéria:",
        subjects,
        key="subject_select"
    )

    selected_codes = []
    codes_data = None
    if selected_subject:
        codes_data = get_codes_for_subject(selected_subject)
        if codes_data:
            st.subheader(f"📋 Códigos - {selected_subject}")
            select_all = st.checkbox("Selecionar todos os códigos")
            if select_all:
                selected_codes = [code["codigo"] for code in codes_data]
            else:
                selected_codes = st.multiselect(
                    "Códigos de Habilidade:",
                    options=[code["codigo"] for code in codes_data],
                    format_func=lambda x: f"{x} - {next(c['objeto_conhecimento'][:50] + '...' if len(c['objeto_conhecimento']) > 50 else c['objeto_conhecimento'] for c in codes_data if c['codigo'] == x)}",
                    key="codes_select"
                )
    return selected_subject, selected_codes, codes_data
