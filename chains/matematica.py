from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from models.schemas import Question, QuestionRequest, QuestionType

# Configuração do modelo
chat = ChatOpenAI(
  model='gpt-4o-mini', 
  temperature=0.7,
  api_key=os.getenv('OPENAI_API_KEY')
)

class MathQuestionOutput(BaseModel):
  """Estrutura para questão de matemática gerada pelo LLM"""
  enunciado: str = Field(description="Enunciado claro e objetivo da questão")
  opcoes: List[str] = Field(description="4 opções para múltipla escolha")
  gabarito: str = Field(description="Resposta correta (A/B/C/D)")
  explicacao: str = Field(description="Breve explicação da resposta para contexto")

# Template para questões de múltipla escolha
multiple_choice_prompt = ChatPromptTemplate.from_messages([
  ("system", """Crie questão matemática múltipla escolha para 4º ano BNCC.

REGRAS:
- Linguagem simples (9-10 anos)
- 4 alternativas (A,B,C,D), só 1 correta
- Contexto cotidiano infantil
- Siga exatamente o código BNCC"""),
  
  ("human", """Código: {codigo}
Objeto: {objeto_conhecimento}
Unidade: {unidade_tematica}""")
])

# Chain estruturada - sempre múltipla escolha
multiple_choice_chain = multiple_choice_prompt | chat.with_structured_output(MathQuestionOutput)

def create_math_question(request: QuestionRequest) -> Question:
  """Cria uma questão de matemática baseada na solicitação"""
  
  # Preparar dados para o prompt
  prompt_data = {
    "codigo": request.codigo,
    "objeto_conhecimento": request.objeto_conhecimento,
    "unidade_tematica": request.unidade_tematica
  }
  
  # Sempre gerar questão de múltipla escolha
  chain_output = multiple_choice_chain.invoke(prompt_data)
  
  # Criar objeto Question
  question = Question(
    codigo=request.codigo,
    enunciado=chain_output.enunciado,
    opcoes=chain_output.opcoes,
    gabarito=chain_output.gabarito,
    question_type=QuestionType.MULTIPLE_CHOICE
  )
  
  return question

# Chain principal para matemática
def math_chain(input_data: dict) -> Question:
  """Chain principal para gerar questões de matemática"""
  request = QuestionRequest(**input_data)
  return create_math_question(request)