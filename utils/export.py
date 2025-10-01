import json


_SUBJECT_MAP = {
    'Português': 'LP',
    'Matemática': 'MA',
    'Ciências': 'CI',
    'LP': 'LP',
    'MA': 'MA',
    'CI': 'CI'
}


def _normalize_disciplina_for_export(disciplina, codigo=None):
    """Normalize disciplina input (enum/string/None) to LP/MA/CI or None."""
    try:
        raw = disciplina.value if hasattr(disciplina, 'value') else disciplina
    except Exception:
        raw = disciplina

    corrected = _SUBJECT_MAP.get(str(raw), raw)
    if corrected:
        return corrected

    # Infer from codigo if possible
    code_upper = (codigo or '').upper()
    if 'MA' in code_upper:
        return 'MA'
    if 'CI' in code_upper:
        return 'CI'
    if 'PT' in code_upper or 'PORT' in code_upper or 'LP' in code_upper:
        return 'LP'
    return None


def _clean_alternativa(alt):
    if isinstance(alt, str):
        if alt.startswith(('A) ', 'B) ', 'C) ', 'D) ')):
            return alt[3:].strip()
        return alt.strip()
    return alt


def export_question_json(disciplina, codigo, enunciado, alternativas, gabarito, filename_suffix="", ano=4, url=None):
    disciplina_corrigida = _normalize_disciplina_for_export(disciplina, codigo)

    alternativas_corrigidas = {}
    if isinstance(alternativas, dict):
        for letra, alt in alternativas.items():
            alternativas_corrigidas[letra] = _clean_alternativa(alt)
    elif isinstance(alternativas, (list, tuple)):
        letras = ['A', 'B', 'C', 'D']
        for idx, alt in enumerate(alternativas):
            if idx < 4:
                alternativas_corrigidas[letras[idx]] = _clean_alternativa(alt)

    export_data = {
        "disciplina": disciplina_corrigida,
        "ano": ano,
        "codigo": codigo,
        "questao": {
            "enunciado": enunciado,
            "alternativas": alternativas_corrigidas,
            "gabarito": gabarito,
            "url": url
        }
    }
    json_data = json.dumps(export_data, ensure_ascii=False, indent=2)
    filename = f"{codigo}{filename_suffix}_questao_individual.json"
    return json_data, filename


def export_questions_list_json(export_list, filename_prefix="questoes_selecionadas"):
    export_objects = []
    for item in export_list:
        disciplina = item.get("disciplina")
        codigo = item.get("codigo")
        enunciado = item["questao"]["enunciado"]
        alternativas = item["questao"].get("alternativas")
        gabarito = item["questao"].get("gabarito")
        url = item["questao"].get("url")
        ano = item.get("ano", 4)
        obj_json, _ = export_question_json(disciplina, codigo, enunciado, alternativas, gabarito, ano=ano, url=url)
        export_objects.append(json.loads(obj_json))
    codes = {item["codigo"] for item in export_list}
    codes_str = "_".join(sorted(codes)) if codes else "export"
    filename = f"{codes_str}_{filename_prefix}.json"
    json_data = json.dumps(export_objects, ensure_ascii=False, indent=2)
    return json_data, filename
