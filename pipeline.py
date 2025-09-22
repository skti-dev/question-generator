from typing import List, Dict, Any
import json
from pathlib import Path
from datetime import datetime
import os
import sys

# Adicionar o diretório atual ao path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.schemas import (
  QuestionRequest, Question, QuestionBatch, 
  QuestionWithValidation, Subject, DifficultyLevel, QuestionType, ValidationResult
)
from chains.matematica import math_chain
from chains.portugues import portuguese_chain
from chains.ciencias import science_chain
from chains.validator import validate_question
from cache_manager import CacheManager

class QuestionGeneratorPipeline:
  """Pipeline principal para geração de questões"""
  
  def __init__(self):
    self.cache_manager = CacheManager()
    self.data_path = Path("data/BNCC_4ano_Mapeamento.json")
    self.bncc_data = self._load_bncc_data()
  
  def _load_bncc_data(self) -> Dict[str, List[Dict]]:
    """Carrega dados da BNCC do arquivo JSON"""
    try:
      if not self.data_path.exists():
        # Tentar caminho alternativo
        alt_path = Path("../data/BNCC_4ano_Mapeamento.json")
        if alt_path.exists():
          self.data_path = alt_path
        else:
          raise FileNotFoundError(f"Arquivo BNCC não encontrado em {self.data_path}")
      
      with open(self.data_path, 'r', encoding='utf-8') as f:
        return json.load(f)
    except Exception as e:
      print(f"Erro ao carregar dados BNCC: {e}")
      return {}
  
  def get_available_subjects(self) -> List[str]:
    """Retorna lista de matérias disponíveis"""
    return list(self.bncc_data.keys())
  
  def get_skill_codes_by_subject(self, subject: str) -> List[Dict[str, str]]:
    """Retorna códigos de habilidade para uma matéria específica"""
    if subject not in self.bncc_data:
      return []
    
    return [
      {
        "codigo": item["codigo"],
        "objeto_conhecimento": item["objeto_conhecimento"],
        "unidade_tematica": item["unidade_tematica"]
      }
      for item in self.bncc_data[subject]
    ]
  
  def find_skill_by_code(self, code: str) -> Dict[str, Any]:
    """Encontra uma habilidade pelo código"""
    for subject, skills in self.bncc_data.items():
      for skill in skills:
        if skill["codigo"] == code:
          return {
            **skill,
            "subject": subject
          }
    return {}
  
  def _route_to_subject_chain(self, request: QuestionRequest) -> Question:
    """Roteia a solicitação para a chain da matéria apropriada"""
    input_data = request.model_dump()
    
    if request.subject == Subject.MATEMATICA:
      return math_chain(input_data)
    elif request.subject == Subject.PORTUGUES:
      return portuguese_chain(input_data)
    elif request.subject == Subject.CIENCIAS:
      return science_chain(input_data)
    else:
      raise ValueError(f"Matéria não suportada: {request.subject}")
  
  def generate_single_question(self, request: QuestionRequest, use_cache: bool = True) -> QuestionWithValidation:
    """Gera uma única questão com validação"""
    
    # Verificar cache primeiro se habilitado
    if use_cache:
      cached_questions = self.cache_manager.get_cached_questions(request, limit=5)
      if cached_questions:
        cached_entry = cached_questions[0]  # Pegar a mais recente
        return QuestionWithValidation(
          question=cached_entry.question,
          validation=cached_entry.validation
        )
    
    # Gerar nova questão
    max_attempts = 3
    for attempt in range(max_attempts):
      try:
        # Gerar questão usando a chain apropriada
        question = self._route_to_subject_chain(request)
        
        # Verificar se é duplicata apenas se usar cache
        if use_cache and self.cache_manager.is_duplicate(request, question):
          continue  # Tentar novamente
        
        # Validar questão
        validation = validate_question(question, request)
        
        # Salvar no cache apenas se válida e usar cache
        if use_cache and validation.is_aligned:
          self.cache_manager.cache_question(request, question, validation)
        
        return QuestionWithValidation(
          question=question,
          validation=validation
        )
        
      except Exception as e:
        if attempt == max_attempts - 1:
          # Última tentativa falhou, criar validação de erro
          validation = ValidationResult(
            is_aligned=False,
            confidence_score=0.0,
            feedback=f"Erro na geração: {str(e)}",
            suggestions="Tentar novamente ou revisar parâmetros"
          )
          
          # Criar questão de fallback
          question = Question(
            codigo=request.codigo,
            enunciado="Erro na geração da questão",
            opcoes=None,
            gabarito="N/A",
            difficulty=request.difficulty,
            question_type=request.question_type
          )
          
          return QuestionWithValidation(question=question, validation=validation)
        
        continue
  
  def regenerate_question_with_variety(self, request: QuestionRequest, avoid_text: str = None) -> QuestionWithValidation:
    """Gera uma nova questão garantindo variedade e evitando texto específico"""
    
    max_attempts = 8  # Mais tentativas para regeneração
    best_question = None
    best_score = 0.0
    
    for attempt in range(max_attempts):
      try:
        # Gerar questão SEM usar cache
        question = self._route_to_subject_chain(request)
        
        # Se deve evitar texto específico, verificar diferença
        if avoid_text and avoid_text.strip():
          if question.enunciado.strip() == avoid_text.strip():
            continue  # Pular questões idênticas
        
        # Validar questão
        validation = validate_question(question, request)
        
        # Manter a melhor questão encontrada
        if validation.confidence_score > best_score:
          best_question = QuestionWithValidation(question=question, validation=validation)
          best_score = validation.confidence_score
          
          # Se encontrou uma boa questão, usar ela
          if validation.is_aligned and validation.confidence_score >= 0.7:
            break
            
      except Exception as e:
        continue  # Tentar próxima iteração
    
    # Retornar a melhor questão encontrada ou criar uma de erro
    if best_question:
      return best_question
    else:
      # Criar questão de erro como fallback
      validation = ValidationResult(
        is_aligned=False,
        confidence_score=0.0,
        feedback="Não foi possível gerar uma questão válida após várias tentativas",
        suggestions="Tentar novamente com parâmetros diferentes"
      )
      
      question = Question(
        codigo=request.codigo,
        enunciado="Erro na regeneração da questão",
        opcoes=None,
        gabarito="N/A",
        difficulty=request.difficulty,
        question_type=request.question_type
      )
      
      return QuestionWithValidation(question=question, validation=validation)
  
  def generate_questions_batch(
    self, 
    code: str, 
    difficulties: List[DifficultyLevel],
    question_types: List[QuestionType],
    use_cache: bool = True
  ) -> QuestionBatch:
    """Gera um lote de questões para um código de habilidade"""
    
    # Encontrar informações da habilidade
    skill_info = self.find_skill_by_code(code)
    if not skill_info:
      raise ValueError(f"Código de habilidade não encontrado: {code}")
    
    # Determinar matéria
    subject = Subject(skill_info["subject"])
    
    # Gerar questões para cada combinação de dificuldade e tipo
    questions_with_validation = []
    total_generated = 0
    
    for difficulty in difficulties:
      for question_type in question_types:
        request = QuestionRequest(
          codigo=code,
          objeto_conhecimento=skill_info["objeto_conhecimento"],
          unidade_tematica=skill_info["unidade_tematica"],
          subject=subject,
          difficulty=difficulty,
          question_type=question_type,
          quantity=1
        )
        
        question_with_validation = self.generate_single_question(request, use_cache)
        questions_with_validation.append(question_with_validation)
        total_generated += 1
    
    # Contar questões aprovadas
    total_approved = sum(
      1 for qv in questions_with_validation 
      if qv.validation.is_aligned
    )
    
    # Criar batch
    batch = QuestionBatch(
      request=QuestionRequest(
        codigo=code,
        objeto_conhecimento=skill_info["objeto_conhecimento"],
        unidade_tematica=skill_info["unidade_tematica"],
        subject=subject,
        difficulty=difficulties[0] if difficulties else DifficultyLevel.MEDIUM,
        question_type=question_types[0] if question_types else QuestionType.MULTIPLE_CHOICE,
        quantity=total_generated
      ),
      questions=questions_with_validation,
      total_generated=total_generated,
      total_approved=total_approved
    )
    
    return batch
  
  def generate_custom_distribution(
    self,
    codes: List[str],
    easy_count: int = 1,
    medium_count: int = 1,
    hard_count: int = 1,
    multiple_choice_ratio: float = 0.7,
    use_cache: bool = True
  ) -> List[QuestionBatch]:
    """Gera questões com distribuição customizada"""
    
    results = []
    
    for code in codes:
      # Calcular distribuição de tipos
      total_per_code = easy_count + medium_count + hard_count
      mc_count = int(total_per_code * multiple_choice_ratio)
      tf_count = total_per_code - mc_count
      
      # Criar listas de dificuldades na ordem desejada
      difficulties_ordered = []
      for _ in range(easy_count):
        difficulties_ordered.append(DifficultyLevel.EASY)
      for _ in range(medium_count):
        difficulties_ordered.append(DifficultyLevel.MEDIUM)
      for _ in range(hard_count):
        difficulties_ordered.append(DifficultyLevel.HARD)
      
      # Embaralhar para distribuição aleatória
      import random
      random.shuffle(difficulties_ordered)
      
      # Criar lista de tipos: primeiro múltipla escolha, depois verdadeiro/falso
      question_types_ordered = []
      for _ in range(mc_count):
        question_types_ordered.append(QuestionType.MULTIPLE_CHOICE)
      for _ in range(tf_count):
        question_types_ordered.append(QuestionType.TRUE_FALSE)
      
      # Embaralhar os tipos também
      random.shuffle(question_types_ordered)
      
      # Combinar dificuldades e tipos
      difficulties = difficulties_ordered
      question_types = question_types_ordered
      
      
      # Gerar batch para este código
      batch = self.generate_questions_batch(
        code=code,
        difficulties=difficulties,
        question_types=question_types,
        use_cache=use_cache
      )
      
      results.append(batch)
    
    return results
  
  def export_to_json(self, batches: List[QuestionBatch], output_path: str = "questoes_geradas.json") -> str:
    """Exporta questões para arquivo JSON"""
    export_data = {
      "metadata": {
        "total_batches": len(batches),
        "total_questions": sum(batch.total_approved for batch in batches),
        "generated_at": datetime.now().isoformat()
      },
      "questoes_por_codigo": [batch.to_export_format() for batch in batches]
    }
    
    output_file = Path(output_path)
    with open(output_file, 'w', encoding='utf-8') as f:
      json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    return str(output_file.absolute())
  
  def get_cache_stats(self) -> dict:
    """Retorna estatísticas do cache"""
    return self.cache_manager.get_cache_stats()

# Instância global do pipeline
pipeline = QuestionGeneratorPipeline()

# Funções de conveniência para uso externo
def get_subjects() -> List[str]:
  """Retorna matérias disponíveis"""
  return pipeline.get_available_subjects()

def get_codes_for_subject(subject: str) -> List[Dict[str, str]]:
  """Retorna códigos para uma matéria"""
  return pipeline.get_skill_codes_by_subject(subject)

def generate_questions(
  codes: List[str],
  easy_count: int = 1,
  medium_count: int = 1, 
  hard_count: int = 1,
  multiple_choice_ratio: float = 0.7
) -> List[QuestionBatch]:
  """Função principal para gerar questões"""
  return pipeline.generate_custom_distribution(
    codes=codes,
    easy_count=easy_count,
    medium_count=medium_count,
    hard_count=hard_count,
    multiple_choice_ratio=multiple_choice_ratio
  )