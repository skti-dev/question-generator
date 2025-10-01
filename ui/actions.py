import streamlit as st
from pipeline import pipeline
from utils.export import export_question_json, export_questions_list_json


def process_delete_question(delete_data):
    try:
        if delete_data['source'] == 'current':
            _delete_current_item(delete_data)
            st.success("✅ Questão removida com sucesso!")
        elif delete_data['source'] == 'cache':
            _delete_cache_item(delete_data['cache_key'])
            st.success("✅ Questão removida do cache!")
    except Exception as e:
        st.error(f"❌ Erro ao remover questão: {e}")


def process_delete_selected(selected_items):
    try:
        deleted_count = 0
        for item in selected_items:
            if item['source'] == 'current':
                deleted_count += _delete_current_item(item, count=True)
            elif item['source'] == 'cache':
                if _delete_cache_item(item['cache_key']):
                    deleted_count += 1
        st.success(f"✅ {deleted_count} questões removidas com sucesso!")
    except Exception as e:
        st.error(f"❌ Erro ao remover questões: {e}")


def _delete_current_item(item_or_delete_data, count: bool = False):
    """Remove um item da geração atual; pode receber tanto delete_data quanto item."""
    delete_data = item_or_delete_data
    removed = 0
    if 'current_batches' in st.session_state:
        for batch in st.session_state.current_batches:
            if batch.request.codigo == delete_data['codigo']:
                if delete_data.get('index', 0) < len(batch.questions):
                    question_content = batch.questions[delete_data['index']].question.enunciado
                    pipeline.cache_manager.remove_question_by_content(question_content)
                    del batch.questions[delete_data['index']]
                    batch.total_generated = len(batch.questions)
                    batch.total_approved = sum(1 for q in batch.questions if q.validation.is_aligned)
                    removed = 1
                break
    return removed if count else True


def _delete_cache_item(cache_key: str) -> bool:
    try:
        return pipeline.cache_manager.remove_by_key(cache_key)
    except Exception:
        return False


def prepare_export_list_from_batches(batches):
    export_list = []
    for batch in batches:
        for qwv in batch.questions:
            q = qwv.question
            disciplina = getattr(q, 'materia', getattr(q, 'subject', None))
            alternativas = q.opcoes if hasattr(q, 'opcoes') else {}
            gabarito = q.gabarito if q.gabarito in ['A', 'B', 'C', 'D'] else str(q.gabarito)
            json_data_individual, _ = export_question_json(disciplina, batch.request.codigo, q.enunciado, alternativas, gabarito)
            export_list.append(__import__('json').loads(json_data_individual))
    return export_list


def prepare_export_list_from_selected(selected_items):
    """Cria uma lista pronta para exportação a partir de itens selecionados (current/cache)."""
    export_list = []
    for item in selected_items:
        if item['source'] == 'current':
            _append_current_item_export(export_list, item)
        elif item['source'] == 'cache':
            _append_cache_item_export(export_list, item)
    return export_list


def _append_current_item_export(export_list, item):
    if 'current_batches' not in st.session_state:
        return
    for batch in st.session_state.current_batches:
        if batch.request.codigo == item['codigo']:
            if item['index'] < len(batch.questions):
                q = batch.questions[item['index']].question
                disciplina = getattr(q, 'materia', getattr(q, 'subject', None))
                alternativas = q.opcoes if hasattr(q, 'opcoes') else {}
                gabarito = q.gabarito if q.gabarito in ['A', 'B', 'C', 'D'] else str(q.gabarito)
                json_data_individual, _ = export_question_json(disciplina, item['codigo'], q.enunciado, alternativas, gabarito)
                export_list.append(__import__('json').loads(json_data_individual))
            break


def _append_cache_item_export(export_list, item):
    cache_entries = pipeline.cache_manager.get_all_cache_entries()
    for entry in cache_entries:
        if entry.cache_key == item['cache_key']:
            q = entry.question
            disciplina = getattr(q, 'materia', getattr(q, 'subject', None))
            alternativas = q.opcoes if hasattr(q, 'opcoes') else {}
            gabarito = q.gabarito if q.gabarito in ['A', 'B', 'C', 'D'] else str(q.gabarito)
            json_data_individual, _ = export_question_json(disciplina, entry.question.codigo, q.enunciado, alternativas, gabarito)
            export_list.append(__import__('json').loads(json_data_individual))
            break
