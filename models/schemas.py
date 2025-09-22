from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum

class DifficultyLevel(str, Enum):
  EASY = "facil"
  MEDIUM = "medio"
  HARD = "dificil"

class QuestionType(str, Enum):
  MULTIPLE_CHOICE = "multipla_escolha"
  TRUE_FALSE = "verdadeiro_falso"

class Subject(str, Enum):
  MATEMATICA = "Matemática"
  PORTUGUES = "Português"
  CIENCIAS = "Ciências"

class QuestionRequest(BaseModel):
  codigo: str = Field(description="Código da habilidade (ex: EF04MA01)")
  objeto_conhecimento: str = Field(description="Descrição do objeto de conhecimento")
  unidade_tematica: str = Field(description="Unidade temática/campo")
  subject: Subject = Field(description="Matéria da questão")
  difficulty: DifficultyLevel = Field(description="Nível de dificuldade")
  question_type: QuestionType = Field(description="Tipo de questão")
  quantity: int = Field(default=1, ge=1, le=20, description="Quantidade de questões")

class Question(BaseModel):
  codigo: str = Field(description="Código da habilidade")
  enunciado: str = Field(description="Enunciado da questão")
  opcoes: Optional[List[str]] = Field(default=None, description="Opções para múltipla escolha")
  gabarito: str = Field(description="Resposta correta")
  difficulty: DifficultyLevel = Field(description="Nível de dificuldade")
  question_type: QuestionType = Field(description="Tipo de questão")
  
  def format_question(self) -> str:
    """Formata a questão no padrão solicitado"""
    if self.question_type == QuestionType.MULTIPLE_CHOICE:
      opcoes_text = "\n".join([f"{chr(65+i)}) {opcao}" for i, opcao in enumerate(self.opcoes)])
      return f"[{self.codigo}] QUESTÃO: {self.enunciado}\n{opcoes_text}\n\nGabarito: {self.gabarito}"
    else:  # TRUE_FALSE
      return f"[{self.codigo}] QUESTÃO: {self.enunciado}\n( ) Verdadeiro\n( ) Falso\n\nGabarito: {self.gabarito}"

class ValidationResult(BaseModel):
  is_aligned: bool = Field(description="Se a questão está alinhada com o código de habilidade")
  confidence_score: float = Field(ge=0, le=1, description="Confiança da validação (0-1)")
  feedback: str = Field(description="Feedback sobre a validação")
  suggestions: Optional[str] = Field(default=None, description="Sugestões de melhoria")

class QuestionWithValidation(BaseModel):
  question: Question = Field(description="Questão gerada")
  validation: ValidationResult = Field(description="Resultado da validação")

class QuestionBatch(BaseModel):
  request: QuestionRequest = Field(description="Solicitação original")
  questions: List[QuestionWithValidation] = Field(description="Lista de questões validadas")
  total_generated: int = Field(description="Total de questões geradas")
  total_approved: int = Field(description="Total de questões aprovadas na validação")
  
  def to_export_format(self) -> dict:
    """Converte para formato de exportação JSON"""
    return {
      "codigo_habilidade": self.request.codigo,
      "objeto_conhecimento": self.request.objeto_conhecimento,
      "unidade_tematica": self.request.unidade_tematica,
      "materia": self.request.subject.value,
      "total_questoes": self.total_approved,
      "questoes": [
        {
          "enunciado": q.question.enunciado,
          "opcoes": q.question.opcoes,
          "gabarito": q.question.gabarito,
          "dificuldade": q.question.difficulty.value,
          "tipo": q.question.question_type.value,
          "validacao": {
            "alinhada": q.validation.is_aligned,
            "confianca": q.validation.confidence_score,
            "feedback": q.validation.feedback
          }
        }
        for q in self.questions if q.validation.is_aligned
      ]
    }

class CacheEntry(BaseModel):
  cache_key: str = Field(description="Chave única do cache")
  question: Question = Field(description="Questão em cache")
  validation: ValidationResult = Field(description="Validação em cache")
  created_at: str = Field(description="Timestamp de criação")