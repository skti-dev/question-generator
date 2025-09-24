import streamlit as st
import json
import sys
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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
  
  # Limpar estados problemáticos de regeneração antigos
  keys_to_remove = [key for key in st.session_state.keys() if key.startswith('regenerate_') and key != 'regenerate_request']
  for key in keys_to_remove:
    del st.session_state[key]
  
  # Processar solicitação de regeneração se houver
  if 'regenerate_request' in st.session_state:
    regenerate_request = st.session_state['regenerate_request']
    try:
      # Regenerar a questão específica
      with st.spinner(f"Regenerando questão para {regenerate_request['codigo']}..."):
        # Importar a função necessária
        from pipeline import pipeline
        
        # Obter a questão antiga para evitar duplicatas
        old_question_text = None
        if 'current_batches' in st.session_state:
          for batch in st.session_state.current_batches:
            if batch.request.codigo == regenerate_request['codigo']:
              if regenerate_request['index'] < len(batch.questions):
                old_question_text = batch.questions[regenerate_request['index']].question.enunciado
                break
        
        # Gerar nova questão usando método específico de regeneração
        new_question = pipeline.regenerate_question_with_variety(
          regenerate_request['request'], 
          avoid_text=old_question_text
        )
        
        # Sempre haverá uma questão (mesmo que seja de erro)
        # Substituir na lista de batches se existir
        if 'current_batches' in st.session_state:
          for batch in st.session_state.current_batches:
            if batch.request.codigo == regenerate_request['codigo']:
              if regenerate_request['index'] < len(batch.questions):
                batch.questions[regenerate_request['index']] = new_question
                # Atualizar contadores
                batch.total_approved = sum(1 for q in batch.questions if q.validation.is_aligned)
                batch.total_generated = len(batch.questions)
                break
        
        # Mostrar resultado baseado na qualidade da questão
        if new_question.validation.is_aligned:
          st.success(f"✅ Nova questão aprovada gerada para {regenerate_request['codigo']}!")
        elif new_question.validation.confidence_score > 0.0:
          st.warning(f"⚠️ Nova questão gerada para {regenerate_request['codigo']}, mas ainda precisa de revisão. Confiança: {new_question.validation.confidence_score:.2f}")
        else:
          st.error(f"❌ Houve problemas na regeneração. Motivo: {new_question.validation.feedback}")
        
    except Exception as e:
      st.error(f"❌ Erro ao regenerar questão: {e}")
    
    # Limpar a solicitação
    del st.session_state['regenerate_request']
  
  # Configurações como accordion
  with st.expander("⚙️ Configurações", expanded=True):
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
        
        # Configurações de quantidade
        st.subheader("📊 Configurações de Geração")
        
        col1, col2 = st.columns(2)
        with col1:
          questions_per_code = st.number_input("Questões por Código", min_value=1, max_value=3, value=1)
        with col2:
          pass  # Coluna vazia para espaçamento
        
        # Botão de geração
        total_questions = len(selected_codes) * questions_per_code
        
        if st.button(
          f"🚀 Gerar {total_questions} questões",
          disabled=len(selected_codes) == 0 or total_questions == 0,
          type="primary"
        ):
          # Salvar configurações no session state
          st.session_state.generation_config = {
            'codes': selected_codes,
            'questions_per_code': questions_per_code
          }
          generate_questions_ui()
  
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
  
  # Mostrar resultados se existirem no session state
  if 'current_batches' in st.session_state and st.session_state.current_batches:
    display_results(st.session_state.current_batches)
  
  # Seção do histórico do cache em accordion
  with st.expander("🗄️ Histórico Completo de Questões", expanded=False):
    display_cache_history()

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
  
  st.header("📊 Resultados da Geração Atual")
  
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
  
  # Seção 1: Questões Rejeitadas (se houver)
  rejected_questions_exist = any(
    any(not q.validation.is_aligned for q in batch.questions)
    for batch in batches
  )
  
  if rejected_questions_exist:
    with st.expander("⚠️ Questões Rejeitadas na Validação", expanded=True):
      st.markdown("**🔄 Estas questões não foram aprovadas e podem ser regeneradas:**")
      
      for i, batch in enumerate(batches):
        rejected_questions = [q for q in batch.questions if not q.validation.is_aligned]
        
        if rejected_questions:
          st.markdown(f"### 📖 {batch.request.codigo} - {batch.request.objeto_conhecimento[:60]}...")
          
          for j, question_with_validation in enumerate(rejected_questions):
            question = question_with_validation.question
            validation = question_with_validation.validation
            
            # Card para questão rejeitada
            with st.container():
              col1, col2 = st.columns([3, 1])
              
              with col1:
                st.markdown(f"**❌ Questão Rejeitada {j+1}** - {question.question_type.value.replace('_', ' ').title()}")
                
                # Botão para mostrar/ocultar questão completa
                show_question_key = f"show_rejected_{batch.request.codigo}_{j}"
                if st.button("👁️ Ver questão completa", key=f"toggle_{show_question_key}", type="secondary"):
                  st.session_state[show_question_key] = not st.session_state.get(show_question_key, False)
                
                # Mostrar questão se solicitado
                if st.session_state.get(show_question_key, False):
                  st.code(question.format_question(), language="text")
                
                # Motivo da rejeição
                confidence_color = "🔴" if validation.confidence_score < 0.6 else "🟡"
                st.markdown(f"**Motivo da Rejeição:** {confidence_color} Confiança: {validation.confidence_score:.2f}")
                st.markdown(f"**📝 Feedback:** {validation.feedback}")
                
                if validation.suggestions:
                  st.markdown(f"**💡 Sugestões:** {validation.suggestions}")
              
              with col2:
                regenerate_key = f"regen_btn_{batch.request.codigo}_{j}"
                if st.button(f"🔄 Regenerar", key=regenerate_key, type="secondary"):
                  # Usar callback approach - marcar para processamento
                  st.session_state['regenerate_request'] = {
                    'codigo': batch.request.codigo,
                    'index': j,
                    'request': batch.request
                  }
                  st.rerun()
            
            st.divider()
  
  # Seção 2: Análise Detalhada das Questões Aprovadas (Accordion)
  with st.expander("🔍 Análise Detalhada das Questões Aprovadas", expanded=False):
    for i, batch in enumerate(batches):
      # Usar container ao invés de expander aninhado
      with st.container():
        st.markdown(f"## 📖 {batch.request.codigo} - {batch.request.objeto_conhecimento[:80]}...")
        
        # Info do código
        st.info(f"**Unidade Temática:** {batch.request.unidade_tematica}")
        
        # Questões aprovadas
        approved_questions = [q for q in batch.questions if q.validation.is_aligned]
        
        if approved_questions:
          for j, question_with_validation in enumerate(approved_questions):
            question = question_with_validation.question
            validation = question_with_validation.validation
            
            st.markdown(f"### ✅ Questão Aprovada {j+1} - {question.question_type.value.replace('_', ' ').title()}")
            
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
        
        st.markdown("---")  # Separador entre códigos
  
  # Seção 3: Tabela de Questões Geradas
  st.subheader("📋 Tabela de Todas as Questões")
  display_questions_table(batches)
  
  # Sistema de exportação
  st.markdown("---")
  col1, col2, col3 = st.columns([1, 2, 1])
  
  with col2:
    # Preparar dados JSON
    try:
      from pipeline import pipeline
      output_path = pipeline.export_to_json(batches, "questoes_exportadas.json")
      with open(output_path, 'r', encoding='utf-8') as f:
        json_data = f.read()
      
      # Gerar nome do arquivo com códigos
      codes_list = [batch.request.codigo for batch in batches]
      codes_str = "_".join(codes_list)
      file_name = f"{codes_str}_questoes_bncc_4ano.json"
      
      # Botão de download direto
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
    try:
      from pipeline import pipeline
      
      if delete_data['source'] == 'current':
        # Remover da geração atual e do cache
        if 'current_batches' in st.session_state:
          for batch in st.session_state.current_batches:
            if batch.request.codigo == delete_data['codigo']:
              # Encontrar e remover a questão específica
              if delete_data['index'] < len(batch.questions):
                question_content = batch.questions[delete_data['index']].question.enunciado
                # Remover do cache usando o enunciado como identificador
                pipeline.cache_manager.remove_question_by_content(question_content)
                # Remover da lista local
                del batch.questions[delete_data['index']]
                batch.total_generated = len(batch.questions)
                batch.total_approved = sum(1 for q in batch.questions if q.validation.is_aligned)
              break
        st.success("✅ Questão removida com sucesso!")
      
      elif delete_data['source'] == 'cache':
        # Remover apenas do cache
        cache_key = delete_data['cache_key']
        pipeline.cache_manager.remove_by_key(cache_key)
        st.success("✅ Questão removida do cache!")
        
    except Exception as e:
      st.error(f"❌ Erro ao remover questão: {e}")
    
    # Limpar ação
    del st.session_state['delete_question']
    st.rerun()
  
  # Processar exclusão múltipla
  if 'delete_selected_questions' in st.session_state:
    selected_items = st.session_state['delete_selected_questions']
    try:
      from pipeline import pipeline
      deleted_count = 0
      
      for item in selected_items:
        if item['source'] == 'current':
          # Remover da geração atual e do cache
          if 'current_batches' in st.session_state:
            for batch in st.session_state.current_batches:
              if batch.request.codigo == item['codigo']:
                if item['index'] < len(batch.questions):
                  question_content = batch.questions[item['index']].question.enunciado
                  pipeline.cache_manager.remove_question_by_content(question_content)
                  del batch.questions[item['index']]
                  batch.total_generated = len(batch.questions)
                  batch.total_approved = sum(1 for q in batch.questions if q.validation.is_aligned)
                  deleted_count += 1
                break
        elif item['source'] == 'cache':
          pipeline.cache_manager.remove_by_key(item['cache_key'])
          deleted_count += 1
      
      st.success(f"✅ {deleted_count} questões removidas com sucesso!")
      
    except Exception as e:
      st.error(f"❌ Erro ao remover questões: {e}")
    
    # Limpar ação e seleção apropriada
    del st.session_state['delete_selected_questions']
    
    # Limpar as listas de seleção baseado na fonte das questões removidas
    sources_removed = {item['source'] for item in selected_items}
    if 'current' in sources_removed and 'selected_questions_current' in st.session_state:
      st.session_state['selected_questions_current'] = []
    if 'cache' in sources_removed and 'selected_questions_cache' in st.session_state:
      st.session_state['selected_questions_cache'] = []
    
    st.rerun()


def export_individual_question(question, validation, codigo, filename_suffix=""):
  """Exporta uma questão individual"""
  try:
    from datetime import datetime
    
    export_data = {
      "codigo": codigo,
      "data_exportacao": datetime.now().isoformat(),
      "questao": {
        "enunciado": question.enunciado,
        "opcoes": question.opcoes,
        "gabarito": question.gabarito,
        "tipo": question.question_type.value,
        "questao_formatada": question.format_question()
      },
      "validacao": {
        "alinhada": validation.is_aligned,
        "confianca": validation.confidence_score,
        "feedback": validation.feedback
      }
    }
    
    json_data = json.dumps(export_data, ensure_ascii=False, indent=2)
    filename = f"{codigo}{filename_suffix}_questao_individual.json"
    
    return json_data, filename
    
  except Exception as e:
    st.error(f"❌ Erro ao preparar exportação individual: {e}")
    return None, None


def export_selected_questions(selected_items):
  """Exporta questões selecionadas"""
  try:
    from datetime import datetime
    from pipeline import pipeline
    
    export_data = {
      "data_exportacao": datetime.now().isoformat(),
      "total_questoes": len(selected_items),
      "questoes": []
    }
    
    # Coletar dados das questões selecionadas
    for item in selected_items:
      if item['source'] == 'current':
        # Buscar na geração atual
        if 'current_batches' in st.session_state:
          for batch in st.session_state.current_batches:
            if batch.request.codigo == item['codigo']:
              if item['index'] < len(batch.questions):
                q = batch.questions[item['index']]
                export_data["questoes"].append({
                  "codigo": item['codigo'],
                  "questao": {
                    "enunciado": q.question.enunciado,
                    "opcoes": q.question.opcoes,
                    "gabarito": q.question.gabarito,
                    "tipo": q.question.question_type.value,
                    "questao_formatada": q.question.format_question()
                  },
                  "validacao": {
                    "alinhada": q.validation.is_aligned,
                    "confianca": q.validation.confidence_score,
                    "feedback": q.validation.feedback
                  }
                })
              break
      
      elif item['source'] == 'cache':
        # Buscar no cache
        cache_entries = pipeline.cache_manager.get_all_cache_entries()
        for entry in cache_entries:
          if entry.cache_key == item['cache_key']:
            export_data["questoes"].append({
              "codigo": entry.question.codigo,
              "questao": {
                "enunciado": entry.question.enunciado,
                "opcoes": entry.question.opcoes,
                "gabarito": entry.question.gabarito,
                "tipo": entry.question.question_type.value,
                "questao_formatada": entry.question.format_question()
              },
              "validacao": {
                "alinhada": entry.validation.is_aligned,
                "confianca": entry.validation.confidence_score,
                "feedback": entry.validation.feedback
              }
            })
            break
    
    json_data = json.dumps(export_data, ensure_ascii=False, indent=2)
    
    # Gerar nome do arquivo baseado nos códigos
    codes = list(set([item['codigo'] for item in selected_items]))
    codes_str = "_".join(sorted(codes))
    filename = f"{codes_str}_questoes_selecionadas.json"
    
    return json_data, filename
    
  except Exception as e:
    st.error(f"❌ Erro ao preparar exportação de questões selecionadas: {e}")
    return None, None


def display_questions_table(batches):
  """Exibe tabela com todas as questões geradas (aprovadas e rejeitadas) com ações"""
  import pandas as pd
  
  # Processar ações pendentes
  handle_question_actions()
  
  # Inicializar seleção se não existir
  if 'selected_questions_current' not in st.session_state:
    st.session_state['selected_questions_current'] = []
  
  st.markdown("#### 🔧 Ações Disponíveis")
  
  # Barra de ações
  col1, col2, col3, col4 = st.columns(4)
  
  with col1:
    if st.button("📋 Selecionar Todas", key="select_all_current"):
      # Selecionar todas as questões da geração atual
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
    if st.button("🗑️ Excluir Selecionadas", key="delete_selected_current", 
                 disabled=len(st.session_state['selected_questions_current']) == 0):
      if len(st.session_state['selected_questions_current']) > 0:
        st.session_state['delete_selected_questions'] = st.session_state['selected_questions_current']
        st.rerun()
  
  with col3:
    if st.button("💾 Exportar Selecionadas", key="export_selected_current",
                 disabled=len(st.session_state['selected_questions_current']) == 0):
      if len(st.session_state['selected_questions_current']) > 0:
        json_data, filename = export_selected_questions(st.session_state['selected_questions_current'])
        if json_data and filename:
          st.download_button(
            label=f"📥 Download {len(st.session_state['selected_questions_current'])} Questões",
            data=json_data,
            file_name=filename,
            mime="application/json",
            key="download_selected_current"
          )
  
  with col4:
    selected_count = len(st.session_state['selected_questions_current'])
    st.metric("Selecionadas", selected_count)
  
  st.markdown("---")
  
  # Tabela com questões e ações individuais
  for i, batch in enumerate(batches):
    st.markdown(f"### 📖 {batch.request.codigo} - {batch.request.objeto_conhecimento[:60]}...")
    
    for j, question_with_validation in enumerate(batch.questions):
      question = question_with_validation.question
      validation = question_with_validation.validation
      
      # Status da questão
      if validation.is_aligned:
        status_icon = "✅"
        status_text = "Aprovada"
      else:
        status_icon = "❌"
        status_text = "Rejeitada"
      
      # Ícone de confiança
      if validation.confidence_score >= 0.8:
        confidence_icon = "🟢"
      elif validation.confidence_score >= 0.6:
        confidence_icon = "🟡"
      else:
        confidence_icon = "🔴"
      
      # Container para cada questão
      with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
          # Checkbox para seleção
          item_selected = {
            'source': 'current',
            'codigo': batch.request.codigo,
            'batch_index': i,
            'index': j
          }
          
          is_selected = any(
            item['batch_index'] == i and item['index'] == j 
            for item in st.session_state['selected_questions_current']
          )
          
          checkbox_changed = False
          
          if st.checkbox(
            f"{status_icon} **{batch.request.codigo}** - {question.enunciado[:80]}{'...' if len(question.enunciado) > 80 else ''}",
            key=f"select_current_{i}_{j}",
            value=is_selected
          ):
            if item_selected not in st.session_state['selected_questions_current']:
              st.session_state['selected_questions_current'].append(item_selected)
              checkbox_changed = True
          else:
            if any(item['batch_index'] == i and item['index'] == j for item in st.session_state['selected_questions_current']):
              st.session_state['selected_questions_current'] = [
                item for item in st.session_state['selected_questions_current']
                if not (item['batch_index'] == i and item['index'] == j)
              ]
              checkbox_changed = True
          
          # Forçar atualização se houve mudança
          if checkbox_changed:
            st.rerun()
          
          # Informações da questão
          col_info1, col_info2, col_info3 = st.columns(3)
          with col_info1:
            st.write(f"**Tipo:** {question.question_type.value.replace('_', ' ').title()}")
          with col_info2:
            st.write(f"**Gabarito:** {question.gabarito}")
          with col_info3:
            st.write(f"**Confiança:** {confidence_icon} {validation.confidence_score:.2f}")
        
        with col2:
          # Ações individuais
          st.markdown("**Ações:**")
          
          # Botão ver questão completa (toggle)
          show_question_key = f"show_current_{i}_{j}"
          button_text = "🙈 Ocultar questão" if st.session_state.get(show_question_key, False) else "👁️ Ver questão completa"
          
          if st.button(button_text, help="Alternar visualização da questão", key=f"view_current_{i}_{j}"):
            st.session_state[show_question_key] = not st.session_state.get(show_question_key, False)
            st.rerun()
          
          # Mostrar questão se solicitado
          if st.session_state.get(show_question_key, False):
            st.code(question.format_question(), language="text")
          
          # Botão exportar individual
          json_data, filename = export_individual_question(
            question, validation, batch.request.codigo, f"_atual_{j+1}"
          )
          if json_data and filename:
            st.download_button(
              label="💾",
              data=json_data,
              file_name=filename,
              mime="application/json",
              help="Exportar questão individual",
              key=f"export_current_{i}_{j}"
            )
          
          # Botão excluir individual
          if st.button("🗑️", help="Excluir questão", key=f"delete_current_{i}_{j}"):
            st.session_state['delete_question'] = {
              'source': 'current',
              'codigo': batch.request.codigo,
              'index': j
            }
            st.rerun()
      
      st.divider()
  
  # Estatísticas finais
  total_questions = sum(len(batch.questions) for batch in batches)
  total_approved = sum(sum(1 for q in batch.questions if q.validation.is_aligned) for batch in batches)
  total_rejected = total_questions - total_approved
  
  col1, col2, col3 = st.columns(3)
  with col1:
    st.metric("✅ Aprovadas", total_approved)
  with col2:
    st.metric("❌ Rejeitadas", total_rejected)
  with col3:
    st.metric("📊 Total", total_questions)


def display_cache_history():
  """Exibe histórico completo de questões do cache com ações"""
  
  # Processar ações pendentes
  handle_question_actions()
  
  try:
    # Buscar todas as questões do cache
    from pipeline import pipeline
    cache_entries = pipeline.cache_manager.get_all_cache_entries()
    
    if not cache_entries:
      st.info("📭 Nenhuma questão encontrada no cache.")
      return
    
    # Inicializar seleção se não existir
    if 'selected_questions_cache' not in st.session_state:
      st.session_state['selected_questions_cache'] = []
    
    st.markdown("#### 🔧 Ações Disponíveis")
    
    # Barra de ações
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
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
    
    with col2:
      if st.button("🗑️ Excluir Selecionadas", key="delete_selected_cache", 
                   disabled=len(st.session_state['selected_questions_cache']) == 0):
        if len(st.session_state['selected_questions_cache']) > 0:
          st.session_state['delete_selected_questions'] = st.session_state['selected_questions_cache']
          st.rerun()
    
    with col3:
      if st.button("💾 Exportar Selecionadas", key="export_selected_cache",
                   disabled=len(st.session_state['selected_questions_cache']) == 0):
        if len(st.session_state['selected_questions_cache']) > 0:
          json_data, filename = export_selected_questions(st.session_state['selected_questions_cache'])
          if json_data and filename:
            st.download_button(
              label=f"📥 Download {len(st.session_state['selected_questions_cache'])} Questões",
              data=json_data,
              file_name=filename,
              mime="application/json",
              key="download_selected_cache"
            )
    
    with col4:
      selected_count = len(st.session_state['selected_questions_cache'])
      st.metric("Selecionadas", selected_count)
    
    # Mostrar estatísticas do cache
    try:
      col1, col2, col3, col4 = st.columns(4)
      with col1:
        st.metric("Total no Cache", len(cache_entries))
      with col2:
        try:
          high_confidence = sum(1 for entry in cache_entries if entry.validation.confidence_score >= 0.8)
          st.metric("Alta Confiança", high_confidence)
        except Exception as e:
          st.metric("Alta Confiança", "Erro")
      with col3:
        try:
          unique_codes = len({entry.question.codigo for entry in cache_entries})
          st.metric("Códigos Únicos", unique_codes)
        except Exception as e:
          st.metric("Códigos Únicos", "Erro")
      with col4:
        try:
          from datetime import datetime
          latest_dates = []
          for entry in cache_entries:
            try:
              if isinstance(entry.created_at, str):
                try:
                  date_obj = datetime.fromisoformat(entry.created_at.replace('Z', '+00:00'))
                except ValueError:
                  try:
                    date_obj = datetime.strptime(entry.created_at, "%Y-%m-%d %H:%M:%S.%f")
                  except ValueError:
                    date_obj = datetime.strptime(entry.created_at, "%Y-%m-%d %H:%M:%S")
                latest_dates.append(date_obj)
              else:
                latest_dates.append(entry.created_at)
            except (ValueError, TypeError):
              continue
          
          if latest_dates:
            latest_date = max(latest_dates)
            st.metric("Última Atualização", latest_date.strftime("%d/%m/%Y"))
          else:
            st.metric("Última Atualização", "N/A")
        except Exception as e:
          st.metric("Última Atualização", "Erro")
    except Exception as stats_error:
      st.error(f"Erro geral nas estatísticas: {stats_error}")
    
    st.markdown("---")
    
    # Lista de questões com ações individuais
    for i, entry in enumerate(cache_entries):
      try:
        question = entry.question
        validation = entry.validation
        
        # Ícone de confiança
        confidence_score = validation.confidence_score
        confidence_icon = "🟢" if confidence_score >= 0.8 else "🟡" if confidence_score >= 0.6 else "🔴"
        
        # Status da questão
        status_icon = "✅" if validation.is_aligned else "❌"
        
        # Converter created_at para string
        from datetime import datetime
        try:
          if isinstance(entry.created_at, str):
            try:
              created_at = datetime.fromisoformat(entry.created_at.replace('Z', '+00:00'))
            except ValueError:
              try:
                created_at = datetime.strptime(entry.created_at, "%Y-%m-%d %H:%M:%S.%f")
              except ValueError:
                created_at = datetime.strptime(entry.created_at, "%Y-%m-%d %H:%M:%S")
          else:
            created_at = entry.created_at
          date_str = created_at.strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
          date_str = "Data inválida"
        
        # Container para cada questão
        with st.container():
          col1, col2 = st.columns([4, 1])
          
          with col1:
            # Checkbox para seleção
            item_selected = {
              'source': 'cache',
              'cache_key': entry.cache_key,
              'codigo': question.codigo,
              'index': i
            }
            
            is_selected = any(
              item['cache_key'] == entry.cache_key 
              for item in st.session_state['selected_questions_cache']
            )
            
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
            
            # Forçar atualização se houve mudança
            if checkbox_changed:
              st.rerun()
            
            # Informações da questão
            col_info1, col_info2, col_info3, col_info4 = st.columns(4)
            with col_info1:
              st.write(f"**Data:** {date_str}")
            with col_info2:
              st.write(f"**Tipo:** {question.question_type.value.replace('_', ' ').title()}")
            with col_info3:
              st.write(f"**Gabarito:** {question.gabarito}")
            with col_info4:
              st.write(f"**Confiança:** {confidence_icon} {confidence_score:.2f}")
          
          with col2:
            # Ações individuais
            st.markdown("**Ações:**")
            
            # Botão ver questão completa (toggle)
            show_question_key = f"show_cache_{i}"
            button_text = "🙈 Ocultar questão" if st.session_state.get(show_question_key, False) else "👁️ Ver questão completa"
            
            if st.button(button_text, help="Alternar visualização da questão", key=f"view_cache_{i}"):
              st.session_state[show_question_key] = not st.session_state.get(show_question_key, False)
              st.rerun()
            
            # Mostrar questão se solicitado
            if st.session_state.get(show_question_key, False):
              st.code(question.format_question(), language="text")
            
            # Botão exportar individual
            json_data, filename = export_individual_question(
              question, validation, question.codigo, f"_cache_{i+1}"
            )
            if json_data and filename:
              st.download_button(
                label="💾",
                data=json_data,
                file_name=filename,
                mime="application/json",
                help="Exportar questão individual",
                key=f"export_cache_{i}"
              )
            
            # Botão excluir individual
            if st.button("🗑️", help="Excluir do cache", key=f"delete_cache_{i}"):
              st.session_state['delete_question'] = {
                'source': 'cache',
                'cache_key': entry.cache_key
              }
              st.rerun()
        
        st.divider()
        
      except Exception as e:
        st.warning(f"⚠️ Erro ao processar entrada do cache: {e}")
        continue
    
    # Botão de exportação do histórico completo (mantido como estava)
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
      try:
        # Preparar dados completos para exportação
        export_data = []
        for entry in cache_entries:
          try:
            if isinstance(entry.created_at, str):
              created_at_str = entry.created_at
            else:
              try:
                created_at_str = entry.created_at.isoformat()
              except AttributeError:
                created_at_str = str(entry.created_at)
            
            export_data.append({
              "codigo": entry.question.codigo,
              "tipo": entry.question.question_type.value,
              "data_criacao": created_at_str,
              "questao": {
                "enunciado": entry.question.enunciado,
                "opcoes": entry.question.opcoes,
                "gabarito": entry.question.gabarito,
                "questao_formatada": entry.question.format_question()
              },
              "validacao": {
                "alinhada": entry.validation.is_aligned,
                "confianca": entry.validation.confidence_score,
                "feedback": entry.validation.feedback
              }
            })
          except Exception as entry_error:
            st.warning(f"⚠️ Erro ao preparar exportação para entrada {entry.cache_key}: {entry_error}")
            continue
        
        if export_data:
          json_export = json.dumps(export_data, ensure_ascii=False, indent=2)
          
          st.download_button(
            label="📥 Exportar Histórico Completo (JSON)",
            data=json_export,
            file_name="historico_completo_questoes.json",
            mime="application/json",
            type="secondary",
            use_container_width=True
          )
        else:
          st.warning("⚠️ Nenhum dado válido para exportação")
      except Exception as export_error:
        st.error(f"❌ Erro na preparação da exportação: {export_error}")
  
  except Exception as e:
    st.error(f"❌ Erro ao carregar histórico do cache: {e}")


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