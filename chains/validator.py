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
  """Estrutura simplificada para validação"""
  is_aligned: bool = Field(description="Se questão alinha com BNCC")
  confidence_score: float = Field(ge=0, le=1, description="Confiança 0-1")
  feedback: str = Field(description="Feedback conciso")

# Template para validação
validation_prompt = ChatPromptTemplate.from_messages([
  ("system", """Valide questão BNCC 4º ano.

AVALIE:
1. Alinha com código BNCC?
2. Adequada para 9-10 anos?
3. Questão clara, gabarito correto?

CONFIANÇA:
- 0.8-1.0: Excelente
- 0.6-0.7: Boa
- 0-0.5: Problemas"""),
  
  ("human", """Código: {codigo}
Habilidade: {objeto_conhecimento}

{enunciado}
{opcoes}
Gabarito: {gabarito}""")
])

# Chain estruturada para validação
validation_chain = validation_prompt | chat.with_structured_output(ValidationOutput)

def validate_question(question: Question, request: QuestionRequest) -> ValidationResult:
  """Valida se uma questão está alinhada com o código de habilidade"""
  
  # Preparar dados para validação
  validation_data = {
    "codigo": request.codigo,
    "objeto_conhecimento": request.objeto_conhecimento,
    "enunciado": question.enunciado,
    "opcoes": question.opcoes,
    "gabarito": question.gabarito
  }
  
  # Executar validação
  validation_output = validation_chain.invoke(validation_data)
  
  # Calcular alinhamento geral
  overall_alignment = validation_output.is_aligned and validation_output.confidence_score >= 0.6
  
  # Criar resultado da validação
  result = ValidationResult(
    is_aligned=overall_alignment,
    confidence_score=validation_output.confidence_score,
    feedback=validation_output.feedback
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
        feedback="Erro na validação"
      ))
  
  return results

# Chain principal para validação
def validator_chain(input_data: dict) -> ValidationResult:
  """Chain principal para validar questões"""
  question = Question(**input_data['question'])
  request = QuestionRequest(**input_data['request'])
  return validate_question(question, request)