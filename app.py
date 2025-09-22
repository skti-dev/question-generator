import streamlit as st
import json
from pathlib import Path
import sys
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipeline import pipeline, get_subjects, get_codes_for_subject, generate_questions
from models.schemas import DifficultyLevel, QuestionType

# Configuração da página
st.set_page_config(
  page_title="Gerador de Questões BNCC",
  page_icon="📚",
  layout="wide"
)

def main():
  st.title("📚 Gerador de Questões BNCC - 4º Ano")
  st.markdown("Gerador inteligente de questões baseado nos códigos de habilidade da BNCC")
  
  # Configurações centralizadas
  st.header("⚙️ Configurações")
  
  # Seleção de matéria
  subjects = get_subjects()
  if not subjects:
    st.error("❌ Dados da BNCC não encontrados! Verifique se o arquivo BNCC_4ano_Mapeamento.json existe.")
    return
  
  selected_subject = st.selectbox(
    "📖 Selecione a Matéria:",
    subjects,
    key="subject_select"
  )
  
  # Códigos disponíveis para a matéria selecionada
  if selected_subject:
    codes_data = get_codes_for_subject(selected_subject)
    
    if codes_data:
      st.subheader(f"📋 Códigos - {selected_subject}")
      
      # Opção de selecionar todos
      select_all = st.checkbox("Selecionar todos os códigos")
      
      if select_all:
        selected_codes = [code["codigo"] for code in codes_data]
      else:
        # Seleção individual de códigos
        selected_codes = st.multiselect(
          "Códigos de Habilidade:",
          options=[code["codigo"] for code in codes_data],
          format_func=lambda x: f"{x} - {next(c['objeto_conhecimento'][:50] + '...' if len(c['objeto_conhecimento']) > 50 else c['objeto_conhecimento'] for c in codes_data if c['codigo'] == x)}",
          key="codes_select"
        )
      
      # Configurações de dificuldade
      st.subheader("🎯 Distribuição de Dificuldade")
      
      col1, col2, col3 = st.columns(3)
      with col1:
        easy_count = st.number_input("Fácil", min_value=0, max_value=10, value=1)
      with col2:
        medium_count = st.number_input("Médio", min_value=0, max_value=10, value=1)
      with col3:
        hard_count = st.number_input("Difícil", min_value=0, max_value=10, value=1)
      
      # Proporção de tipos de questão
      st.subheader("📝 Tipos de Questão")
      multiple_choice_ratio = st.slider(
        "% Múltipla Escolha",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="Restante será Verdadeiro/Falso"
      )
      
      # Configurações avançadas
      with st.expander("🔧 Configurações Avançadas"):
        use_cache = st.checkbox("Usar cache", value=True, help="Reutilizar questões já geradas")
        
        if st.button("🗑️ Limpar Cache"):
          try:
            deleted = pipeline.cache_manager.clear_cache(older_than_days=0)
            st.success(f"✅ {deleted} entradas removidas do cache")
          except Exception as e:
            st.error(f"❌ Erro ao limpar cache: {e}")
      
      # Botão de geração
      total_questions = len(selected_codes) * (easy_count + medium_count + hard_count)
      
      if st.button(
        f"🚀 Gerar {total_questions} Questões",
        disabled=len(selected_codes) == 0 or total_questions == 0,
        type="primary"
      ):
        generate_questions_ui(selected_codes, easy_count, medium_count, hard_count, multiple_choice_ratio, use_cache)
  
  # Mostrar resultados se existirem no session state
  if 'current_batches' in st.session_state and st.session_state.current_batches:
    display_results(st.session_state.current_batches)

def generate_questions_ui(codes, easy_count, medium_count, hard_count, multiple_choice_ratio, use_cache):
  """Interface para geração de questões"""
  
  with st.container():
    st.header("🔄 Gerando Questões...")
    
    # Barra de progresso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
      # Gerar questões
      with st.spinner("Processando..."):
        batches = generate_questions(
          codes=codes,
          easy_count=easy_count,
          medium_count=medium_count,
          hard_count=hard_count,
          multiple_choice_ratio=multiple_choice_ratio
        )
      
      progress_bar.progress(100)
      status_text.text("✅ Questões geradas com sucesso!")
      
      # Salvar no session state
      st.session_state.current_batches = batches
      st.rerun()  # Rerun para mostrar os resultados na main
      
    except Exception as e:
      st.error(f"❌ Erro na geração: {str(e)}")
      st.exception(e)

def display_results(batches):
  """Exibe os resultados das questões geradas"""
  
  # Salvar batches no session state para persistir entre reruns
  st.session_state.current_batches = batches
  
  st.header("📊 Resultados")
  
  # Estatísticas gerais
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
  
  # Exibir questões por código
  for i, batch in enumerate(batches):
    with st.expander(f"📖 {batch.request.codigo} - {batch.request.objeto_conhecimento[:80]}..."):
      
      # Info do código
      st.info(f"**Unidade Temática:** {batch.request.unidade_tematica}")
      
      # Questões aprovadas
      approved_questions = [q for q in batch.questions if q.validation.is_aligned]
      
      if approved_questions:
        for j, question_with_validation in enumerate(approved_questions):
          question = question_with_validation.question
          validation = question_with_validation.validation
          
          st.markdown(f"### Questão {j+1} - {question.difficulty.value.title()} - {question.question_type.value.replace('_', ' ').title()}")
          
          # Mostrar questão formatada
          st.markdown("**Questão:**")
          st.code(question.format_question(), language="text")
          
          # Mostrar validação
          confidence_color = "🟢" if validation.confidence_score >= 0.8 else "🟡" if validation.confidence_score >= 0.6 else "🔴"
          st.markdown(f"**Validação:** {confidence_color} Confiança: {validation.confidence_score:.2f}")
          st.markdown(f"**Feedback:** {validation.feedback}")
          
          st.divider()
      else:
        st.warning("⚠️ Nenhuma questão foi aprovada na validação para este código.")
  
  # Sistema de exportação simplificado
  st.markdown("---")
  col1, col2, col3 = st.columns([1, 2, 1])
  
  with col2:
    # Preparar dados JSON
    try:
      output_path = pipeline.export_to_json(batches, "questoes_exportadas.json")
      with open(output_path, 'r', encoding='utf-8') as f:
        json_data = f.read()
      
      # Botão de download direto
      st.download_button(
        label="💾 Exportar e Baixar JSON",
        data=json_data,
        file_name="questoes_bncc_4ano.json",
        mime="application/json",
        type="primary",
        use_container_width=True
      )
      
    except Exception as e:
      st.error(f"❌ Erro na preparação da exportação: {e}")

# Função para mostrar informações do sistema
def show_system_info():
  """Mostra informações do sistema na sidebar"""
  with st.sidebar:
    st.header("ℹ️ Informações do Sistema")
    try:
      cache_stats = pipeline.get_cache_stats()
      st.write(f"**Cache:** {cache_stats['total_entries']} entradas")
      
      subjects = get_subjects()
      st.write(f"**Matérias:** {len(subjects)}")
      
      total_codes = sum(len(get_codes_for_subject(subject)) for subject in subjects)
      st.write(f"**Códigos BNCC:** {total_codes}")
      
    except Exception as e:
      st.write(f"Erro ao carregar stats: {e}")

if __name__ == "__main__":
  show_system_info()
  main()