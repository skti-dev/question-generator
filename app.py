import streamlit as st
import json
import sys
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.export import export_question_json, export_questions_list_json
from pipeline import get_subjects, get_codes_for_subject, generate_questions

# Configuração da página
st.set_page_config(
  page_title="Gerador de Questões BNCC",
  page_icon="📚",
  layout="wide"
)

def check_authentication():
  """Verifica se o usuário está autenticado"""
  # Obter senha do .env
  app_password = os.getenv('APP_PASSWORD')
  
  if not app_password:
    st.error("❌ Senha não configurada no sistema!")
    st.stop()
  
  # Verificar se já está autenticado
  if st.session_state.get('authenticated', False):
    return True
  
  # Interface de login
  st.title("🔐 Acesso ao Sistema")
  st.markdown("**Digite a senha para acessar o Gerador de Questões BNCC**")
  
  with st.form("login_form"):
    password = st.text_input("Senha:", type="password", placeholder="Digite a senha...")
    submit_button = st.form_submit_button("🔓 Entrar", type="primary", use_container_width=True)
    
    if submit_button:
      if password == app_password:
        st.session_state['authenticated'] = True
        st.success("✅ Acesso autorizado! Redirecionando...")
        st.rerun()
      else:
        st.error("❌ Senha incorreta! Tente novamente.")
        return False
  
  # Mostrar informações do sistema na parte inferior
  st.markdown("---")
  st.markdown("**ℹ️ Sistema de Geração de Questões BNCC - 4º Ano**")
  st.markdown("Sistema inteligente para geração de questões educacionais baseadas na Base Nacional Comum Curricular.")
  
  return False

def main():
  st.title("📚 Gerador de Questões BNCC - 4º Ano")
  st.markdown("Gerador inteligente de questões baseado nos códigos de habilidade da BNCC")
  
  _cleanup_regenerate_keys()
  _process_regenerate_request_if_any()
  _render_config_section()
  _render_advanced_section()
  _render_results_and_history()


def _cleanup_regenerate_keys():
  # Limpar estados problemáticos de regeneração antigos
  keys_to_remove = [key for key in st.session_state.keys() if key.startswith('regenerate_') and key != 'regenerate_request']
  for key in keys_to_remove:
    del st.session_state[key]


def _normalize_disciplina(disciplina):
  """Normaliza o nome da disciplina para o formato curto (LP/MA/CI)"""
  subject_map = {
    'Português': 'LP',
    'Matemática': 'MA',
    'Ciências': 'CI',
    'LP': 'LP',
    'MA': 'MA',
    'CI': 'CI'
  }
  return subject_map.get(str(disciplina), disciplina)


def _confidence_icon(score: float) -> str:
  if score >= 0.8:
    return "🟢"
  if score >= 0.6:
    return "🟡"
  return "🔴"


def _alternativas_from_opcoes(opcoes):
  """Converte opcoes (lista/tuple/dict) para dict {'A':..., 'B':...} ou {}."""
  if not opcoes:
    return {}
  if isinstance(opcoes, dict):
    return opcoes
  if isinstance(opcoes, (list, tuple)):
    letras = ['A', 'B', 'C', 'D']
    return dict(zip(letras, opcoes))
  return {}


def _is_approved(qwv) -> bool:
  """Retorna True se a questão for considerada aprovada (alinhada e confiança >= 0.7)."""
  try:
    return bool(qwv.validation.is_aligned) and float(qwv.validation.confidence_score) >= 0.7
  except Exception:
    return False


def _regen_find_old_question_text(regenerate_request):
  """Retorna o enunciado da questão antiga para evitar duplicação, ou None."""
  if 'current_batches' not in st.session_state:
    return None
  for batch in st.session_state.current_batches:
    if batch.request.codigo == regenerate_request['codigo']:
      if regenerate_request['index'] < len(batch.questions):
        return batch.questions[regenerate_request['index']].question.enunciado
  return None

def _regen_generate_new_question(regenerate_request, avoid_text):
  """Invoca pipeline para regenerar a questão."""
  from pipeline import pipeline
  return pipeline.regenerate_question_with_variety(regenerate_request['request'], avoid_text=avoid_text)

def _regen_replace_question_in_batches(regenerate_request, new_question):
  """Substitui a questão nos batches atuais e atualiza contadores."""
  if 'current_batches' not in st.session_state:
    return
  for batch in st.session_state.current_batches:
    if batch.request.codigo == regenerate_request['codigo']:
      if regenerate_request['index'] < len(batch.questions):
        batch.questions[regenerate_request['index']] = new_question
        batch.total_approved = sum(1 for q in batch.questions if _is_approved(q))
        batch.total_generated = len(batch.questions)
      break

def _regen_show_generation_result(regenerate_request, new_question):
  """Mostra feedback para o usuário conforme a validação da nova questão."""
  if new_question.validation.is_aligned:
    st.success(f"✅ Nova questão aprovada gerada para {regenerate_request['codigo']}!")
  elif new_question.validation.confidence_score > 0.0:
    st.warning(
      f"⚠️ Nova questão gerada para {regenerate_request['codigo']}, mas ainda precisa de revisão. "
      f"Confiança: {new_question.validation.confidence_score:.2f}"
    )
  else:
    st.error(f"❌ Houve problemas na regeneração. Motivo: {new_question.validation.feedback}")

def _process_regenerate_request_if_any():
  # Processar solicitação de regeneração se houver
  if 'regenerate_request' not in st.session_state:
    return

  regenerate_request = st.session_state['regenerate_request']

  try:
    with st.spinner(f"Regenerando questão para {regenerate_request['codigo']}..."):
      old_question_text = _regen_find_old_question_text(regenerate_request)
      new_question = _regen_generate_new_question(regenerate_request, old_question_text)
      _regen_replace_question_in_batches(regenerate_request, new_question)
      _regen_show_generation_result(regenerate_request, new_question)
  except Exception as e:
    st.error(f"❌ Erro ao regenerar questão: {e}")
  finally:
    # Limpar a solicitação
    if 'regenerate_request' in st.session_state:
      del st.session_state['regenerate_request']


def _render_config_section():
  # Configurações como accordion
  from ui.config_panel import config_panel
  with st.expander("⚙️ Configurações", expanded=True):
    selected_subject, selected_codes, _codes_data = config_panel()
    questions_per_code = st.number_input("Questões por Código", min_value=1, max_value=20, value=1)
    total_questions = len(selected_codes) * questions_per_code
    if st.button(
      f"🚀 Gerar {total_questions} questões",
      disabled=len(selected_codes) == 0 or total_questions == 0,
      type="primary"
    ):
      st.session_state.generation_config = {
        'codes': selected_codes,
        'questions_per_code': questions_per_code,
        'subject': selected_subject
      }
      generate_questions_ui()


def _render_advanced_section():
  # Configurações avançadas (fora do expander principal)
  with st.expander("🔧 Configurações Avançadas"):
    st.info("🔧 Configurações de sistema e manutenção")
    
    if st.button("🗑️ Limpar Cache"):
      try:
        from pipeline import pipeline
        deleted = pipeline.cache_manager.clear_cache(older_than_days=0)
        st.success(f"✅ {deleted} entradas removidas do cache")
      except Exception as e:
        st.error(f"❌ Erro ao limpar cache: {e}")


def _render_results_and_history():
  # Mostrar resultados se existirem no session state
  from ui.results_panel import results_panel
  from ui.questions_table import questions_table_panel
  from ui.cache_panel import cache_panel

  if 'current_batches' in st.session_state and st.session_state.current_batches:
    results_panel(st.session_state.current_batches, lambda batches: questions_table_panel(batches, handle_question_actions))
  # Seção do histórico do cache em accordion
  with st.expander("🗄️ Histórico Completo de Questões", expanded=False):
      cache_panel()

def generate_questions_ui():
  """Interface para geração de questões"""
  
  # Verificar se há configurações no session state
  if 'generation_config' not in st.session_state:
    st.error("❌ Configurações de geração não encontradas!")
    return
  
  config = st.session_state.generation_config
  
  with st.container():
    st.header("🔄 Gerando Questões...")
    
    # Barra de progresso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
      # Gerar questões
      with st.spinner("Processando..."):
        batches = generate_questions(
          codes=config['codes'],
          questions_per_code=config['questions_per_code']
        )
      # Salvar todas as questões aprovadas no cache
      try:
        from pipeline import pipeline
        for batch in batches:
          for qwv in batch.questions:
            if qwv.validation.is_aligned:
              pipeline.cache_manager.cache_question(batch.request, qwv.question, qwv.validation)
      except Exception as cache_error:
        st.warning(f"⚠️ Erro ao salvar questões no cache: {cache_error}")
      progress_bar.progress(100)
      status_text.text("✅ Questões geradas com sucesso!")
      # Salvar no session state
      st.session_state.current_batches = batches
      st.rerun()  # Rerun para mostrar os resultados na main
      
    except Exception as e:
      st.error(f"❌ Erro na geração: {str(e)}")
      st.exception(e)

def display_results(batches):
  """Exibe os resultados das questões geradas (orquestração simplificada)."""
  # Persistir batches e delegar responsabilidades a helpers
  st.session_state.current_batches = batches

  _render_results_header(batches)
  _render_rejected_questions_section(batches)
  _render_approved_analysis_section(batches)
  st.subheader("📋 Tabela de Todas as Questões")
  display_questions_table(batches)
  _render_export_current_generation(batches)


def _render_results_header(batches):
  """Renderiza cabeçalho e métricas principais."""
  st.header("📊 Resultados da Geração Atual")

  total_generated = sum(batch.total_generated for batch in batches)
  total_approved = sum(
    sum(1 for q in batch.questions if _is_approved(q))
    for batch in batches
  )
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


def _render_single_rejected_question(batch, index_in_list, question_with_validation):
  """Renderiza uma única questão rejeitada com seus controles (helper para reduzir complexidade)."""
  question = question_with_validation.question
  validation = question_with_validation.validation

  with st.container():
    col1, col2 = st.columns([3, 1])
    with col1:
      st.markdown(f"**❌ Questão Rejeitada {index_in_list+1}** - {question.question_type.value.replace('_', ' ').title()}")

      show_question_key = f"show_rejected_{batch.request.codigo}_{index_in_list}"
      if st.button("👁️ Ver questão completa", key=f"toggle_{show_question_key}", type="secondary"):
        st.session_state[show_question_key] = not st.session_state.get(show_question_key, False)

      if st.session_state.get(show_question_key, False):
        st.code(question.format_question(), language="text")
      confidence_color = _confidence_icon(validation.confidence_score)
      st.markdown(f"**Motivo da Rejeição:** {confidence_color} Confiança: {validation.confidence_score:.2f}")
      st.markdown(f"**📝 Feedback:** {validation.feedback}")
      if validation.suggestions:
        st.markdown(f"**💡 Sugestões:** {validation.suggestions}")

    with col2:
      regenerate_key = f"regen_btn_{batch.request.codigo}_{index_in_list}"
      if st.button("🔄 Regenerar", key=regenerate_key, type="secondary"):
        st.session_state['regenerate_request'] = {
          'codigo': batch.request.codigo,
          'index': index_in_list,
          'request': batch.request
        }
        st.rerun()

  st.divider()


def _render_rejected_questions_section(batches):
  """Renderiza a seção de questões rejeitadas com ações de regeneração."""
  rejected_exists = any(
    any(not _is_approved(q) for q in batch.questions)
    for batch in batches
  )
  if not rejected_exists:
    return

  with st.expander("⚠️ Questões Rejeitadas na Validação", expanded=True):
    st.markdown("**🔄 Estas questões não foram aprovadas e podem ser regeneradas:**")

    for batch in batches:
      # manter índices originais para regeneração correta
      rejected_pairs = [(idx, q) for idx, q in enumerate(batch.questions) if not _is_approved(q)]
      if not rejected_pairs:
        continue

      st.markdown(f"### 📖 {batch.request.codigo} - {batch.request.objeto_conhecimento[:60]}...")
      for orig_idx, qwv in rejected_pairs:
        _render_single_rejected_question(batch, orig_idx, qwv)


def _render_approved_analysis_section(batches):
  """Renderiza seção de análise detalhada para questões aprovadas."""
  with st.expander("🔍 Análise Detalhada das Questões Aprovadas", expanded=False):
    for batch in batches:
      with st.container():
        st.markdown(f"## 📖 {batch.request.codigo} - {batch.request.objeto_conhecimento[:80]}...")
        st.info(f"**Unidade Temática:** {batch.request.unidade_tematica}")

        approved_questions = [q for q in batch.questions if _is_approved(q)]
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

          confidence_color = _confidence_icon(validation.confidence_score)
          st.markdown(f"**Validação:** {confidence_color} Confiança: {validation.confidence_score:.2f}")
          st.markdown(f"**Feedback:** {validation.feedback}")
          st.divider()

        st.markdown("---")


def _render_export_current_generation(batches):
  """Prepara e exibe botão de exportação para a geração atual."""
  st.markdown("---")
  _, col2, _ = st.columns([1, 2, 1])
  with col2:
    try:
      from utils.export import export_questions_list_json, export_question_json
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


def handle_question_actions():
  """Processa ações pendentes nas questões"""
  # Processar exclusão individual
  if 'delete_question' in st.session_state:
    delete_data = st.session_state['delete_question']
    from ui.actions import process_delete_question
    process_delete_question(delete_data)
    del st.session_state['delete_question']
    st.rerun()
  
  # Processar exclusão múltipla
  if 'delete_selected_questions' in st.session_state:
    selected_items = st.session_state['delete_selected_questions']
    from ui.actions import process_delete_selected
    process_delete_selected(selected_items)
    # Limpar ação e seleção apropriada
    del st.session_state['delete_selected_questions']
    sources_removed = {item['source'] for item in selected_items}
    if 'current' in sources_removed and 'selected_questions_current' in st.session_state:
      st.session_state['selected_questions_current'] = []
    if 'cache' in sources_removed and 'selected_questions_cache' in st.session_state:
      st.session_state['selected_questions_cache'] = []
    st.rerun()


def export_individual_question(question, codigo, filename_suffix=""):
  """Exporta uma questão individual"""
  try:
    disciplina = _normalize_disciplina(getattr(question, 'materia', getattr(question, 'subject', None)))
    alternativas = _alternativas_from_opcoes(getattr(question, 'opcoes', None))
    gabarito = question.gabarito if question.gabarito in ['A', 'B', 'C', 'D'] else str(question.gabarito)
    return export_question_json(disciplina, codigo, question.enunciado, alternativas, gabarito, filename_suffix)
  except Exception as exc:
    st.error(f"❌ Erro ao preparar exportação individual: {exc}")
    return None, None


def export_selected_questions(selected_items):
  """Exporta questões selecionadas utilizando o helper centralizado."""
  from ui.actions import prepare_export_list_from_selected
  export_list = prepare_export_list_from_selected(selected_items)
  return export_questions_list_json(export_list)


def display_questions_table(batches):
  """Wrapper: delega renderização da tabela ao módulo UI."""
  from ui.questions_table import questions_table_panel
  questions_table_panel(batches, handle_question_actions)


def display_cache_history():
  """Exibe histórico completo de questões do cache com ações"""
  
  # Processar ações pendentes
  handle_question_actions()
  
  try:
    """Wrapper: delega renderização do histórico do cache ao módulo UI."""
    from ui.cache_panel import cache_panel
    cache_panel(export_selected_questions)
  
  except Exception as export_error:
    st.error(f"❌ Erro na preparação da exportação: {export_error}")  


# Função para mostrar informações do sistema
def show_system_info():
  """Mostra informações do sistema na sidebar"""
  with st.sidebar:
    # Botão de logout
    st.markdown("---")
    if st.button("🚪 Sair do Sistema", type="secondary", use_container_width=True):
      st.session_state['authenticated'] = False
      st.rerun()
    
    st.header("ℹ️ Informações do Sistema")
    try:
      from pipeline import pipeline
      cache_stats = pipeline.get_cache_stats()
      st.write(f"**Cache:** {cache_stats['total_entries']} entradas")
      
      subjects = get_subjects()
      st.write(f"**Matérias:** {len(subjects)}")
      
      total_codes = sum(len(get_codes_for_subject(subject)) for subject in subjects)
      st.write(f"**Códigos BNCC:** {total_codes}")
      
    except Exception as e:
      st.write(f"Erro ao carregar stats: {e}")

if __name__ == "__main__":
  # Verificar autenticação primeiro
  if not check_authentication():
    st.stop()
  
  # Se autenticado, mostrar aplicação principal
  show_system_info()
  main()