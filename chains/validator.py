from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
import os
from models.schemas import Question, ValidationResult, QuestionRequest

# Configuração do modelo
chat = ChatOpenAI(
  model='gpt-4o-mini', 
  temperature=0.3,  # Menor temperatura para validação mais consistente
  api_key=os.getenv('OPENAI_API_KEY')
)

class ValidationOutput(BaseModel):
  """Estrutura para resultado da validação pelo LLM"""
  is_aligned: bool = Field(description="Se a questão está alinhada com o código de habilidade")
  confidence_score: float = Field(ge=0, le=1, description="Confiança da avaliação de 0 a 1")
  feedback: str = Field(description="Feedback detalhado sobre o alinhamento")
  suggestions: str = Field(description="Sugestões de melhoria se necessário")
  cognitive_level_appropriate: bool = Field(description="Se está adequada para o 4º ano")
  bncc_compliance: bool = Field(description="Se segue as diretrizes da BNCC")

# Template para validação
validation_prompt = ChatPromptTemplate.from_messages([
  ("system", """Você é um especialista em avaliação educacional e BNCC (Base Nacional Comum Curricular).
  
  Sua missão é VALIDAR se uma questão está adequadamente alinhada com um código de habilidade específico.
  
  CRITÉRIOS DE AVALIAÇÃO:
  
  1. ALINHAMENTO COM CÓDIGO DE HABILIDADE:
     - A questão aborda EXATAMENTE o que o código de habilidade especifica?
     - O objeto de conhecimento está sendo avaliado corretamente?
     - A unidade temática está respeitada?
  
  2. ADEQUAÇÃO COGNITIVA (4º ANO - 9/10 ANOS):
     - Linguagem apropriada para a idade
     - Complexidade adequada ao nível de desenvolvimento
     - Conceitos acessíveis para a faixa etária
     - Contextos familiares às crianças
  
  3. QUALIDADE PEDAGÓGICA:
     - Questão clara e objetiva
     - Alternativas bem formuladas (para múltipla escolha)
     - Gabarito correto e justificável
     - Promove aprendizagem significativa
  
  4. CONFORMIDADE BNCC:
     - Segue as competências e habilidades da BNCC
     - Respeita os campos de atuação (para português)
     - Alinhada com as unidades temáticas
  
  INSTRUÇÕES:
  - Seja rigoroso na avaliação
  - Dê feedback construtivo e específico
  - Confiança alta (0.8-1.0) apenas para questões excelentes
  - Confiança média (0.5-0.7) para questões adequadas mas com pequenos problemas
  - Confiança baixa (0-0.4) para questões com problemas significativos
  - Sempre forneça sugestões de melhoria, mesmo para questões aprovadas"""),
  
  ("human", """Avalie a seguinte questão:

  === CÓDIGO DE HABILIDADE ===
  Código: {codigo}
  Objeto de Conhecimento: {objeto_conhecimento}
  Unidade Temática: {unidade_tematica}
  Matéria: {subject}
  
  === QUESTÃO GERADA ===
  Enunciado: {enunciado}
  Opções: {opcoes}
  Gabarito: {gabarito}
  Tipo: {question_type}
  
  Analise se esta questão está adequadamente alinhada com o código de habilidade especificado e apropriada para alunos do 4º ano.""")
])

# Chain estruturada para validação
validation_chain = validation_prompt | chat.with_structured_output(ValidationOutput)

def validate_question(question: Question, request: QuestionRequest) -> ValidationResult:
  """Valida se uma questão está alinhada com o código de habilidade"""
  
  # Preparar dados para validação
  validation_data = {
    "codigo": request.codigo,
    "objeto_conhecimento": request.objeto_conhecimento,
    "unidade_tematica": request.unidade_tematica,
    "subject": request.subject.value,
    "enunciado": question.enunciado,
    "opcoes": question.opcoes if question.opcoes else "N/A (Verdadeiro/Falso)",
    "gabarito": question.gabarito,
    "question_type": question.question_type.value
  }
  
  # Executar validação
  validation_output = validation_chain.invoke(validation_data)
  
  # Calcular alinhamento geral baseado nos critérios
  overall_alignment = (
    validation_output.is_aligned and 
    validation_output.cognitive_level_appropriate and 
    validation_output.bncc_compliance and
    validation_output.confidence_score >= 0.6
  )
  
  # Criar resultado da validação
  result = ValidationResult(
    is_aligned=overall_alignment,
    confidence_score=validation_output.confidence_score,
    feedback=validation_output.feedback,
    suggestions=validation_output.suggestions if not overall_alignment else None
  )
  
  return result

def validate_question_batch(questions: list[Question], request: QuestionRequest) -> list[ValidationResult]:
  """Valida um lote de questões"""
  results = []
  
  for question in questions:
    try:
      validation_result = validate_question(question, request)
      results.append(validation_result)
    except Exception:
      # Se falhar na validação, marca como não alinhada
      results.append(ValidationResult(
        is_aligned=False,
        confidence_score=0.0,
        feedback="Erro durante o processo de validação",
        suggestions="Revisar a questão manualmente"
      ))
  
  return results

# Chain principal para validação
def validator_chain(input_data: dict) -> ValidationResult:
  """Chain principal para validar questões"""
  question = Question(**input_data['question'])
  request = QuestionRequest(**input_data['request'])
  return validate_question(question, request)