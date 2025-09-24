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
  opcoes: Optional[List[str]] = Field(description="4 opções para múltipla escolha (apenas se aplicável)")
  gabarito: str = Field(description="Resposta correta (A/B/C/D para múltipla escolha, Verdadeiro/Falso para V/F)")
  explicacao: str = Field(description="Breve explicação da resposta para contexto")

# Template para questões de múltipla escolha
multiple_choice_prompt = ChatPromptTemplate.from_messages([
  ("system", """Você é um professor especialista em MATEMÁTICA do 4º ano do ensino fundamental.
  
  Sua missão é criar questões de MÚLTIPLA ESCOLHA alinhadas com a BNCC (Base Nacional Comum Curricular).
  
  INSTRUÇÕES IMPORTANTES:
  - Use linguagem adequada para crianças de 9-10 anos
  - A questão deve estar DIRETAMENTE relacionada ao código de habilidade fornecido
  - Crie 4 alternativas (A, B, C, D) sendo apenas 1 correta
  - As alternativas incorretas devem ser plausíveis mas claramente erradas
  - Use contextos do cotidiano da criança (escola, casa, brincadeiras)
  - Evite cálculos muito complexos
  
  IMPORTANTE: Como estamos trabalhando com 4º ano do ensino fundamental (crianças de 9-10 anos),
  a questão deve ser adequada para essa faixa etária em termos de:
  - Vocabulário acessível e contextualizado
  - Conceitos apropriados para o desenvolvimento cognitivo
  - Situações do cotidiano das crianças (escola, casa, brincadeiras)
  - Operações e números adequados ao nível de aprendizagem
  
  IMPORTANTE: Retorne APENAS UMA questão por vez, bem elaborada e revisada."""),
  
  ("human", """Crie uma questão de múltipla escolha de matemática:

  CÓDIGO DA HABILIDADE: {codigo}
  OBJETO DE CONHECIMENTO: {objeto_conhecimento}
  UNIDADE TEMÁTICA: {unidade_tematica}
  
  A questão deve ser adequada para alunos do 4º ano e seguir exatamente o código de habilidade especificado.""")
])

# Template para questões verdadeiro/falso
true_false_prompt = ChatPromptTemplate.from_messages([
  ("system", """Você é um professor especialista em MATEMÁTICA do 4º ano do ensino fundamental.
  
  Sua missão é criar questões de VERDADEIRO ou FALSO alinhadas com a BNCC.
  
  INSTRUÇÕES IMPORTANTES:
  - Use linguagem adequada para crianças de 9-10 anos
  - A afirmação deve estar DIRETAMENTE relacionada ao código de habilidade
  - Crie afirmações claras que permitam resposta definitiva (V ou F)
  - Evite afirmações ambíguas ou que dependam de interpretação
  - Use contextos familiares às crianças
  
  IMPORTANTE: Como estamos trabalhando com 4º ano do ensino fundamental (crianças de 9-10 anos),
  a questão deve ser adequada para essa faixa etária em termos de:
  - Vocabulário acessível e contextualizado
  - Afirmações claras que permitam resposta definitiva (V ou F)
  - Situações familiares às crianças
  - Conceitos apropriados para o desenvolvimento cognitivo
  
  IMPORTANTE: O gabarito deve ser EXATAMENTE "Verdadeiro" ou "Falso"."""),
  
  ("human", """Crie uma questão de verdadeiro/falso de matemática:

  CÓDIGO DA HABILIDADE: {codigo}
  OBJETO DE CONHECIMENTO: {objeto_conhecimento}
  UNIDADE TEMÁTICA: {unidade_tematica}
  
  A questão deve ser adequada para alunos do 4º ano e seguir exatamente o código de habilidade especificado.""")
])

# Chains estruturadas
multiple_choice_chain = multiple_choice_prompt | chat.with_structured_output(MathQuestionOutput)
true_false_chain = true_false_prompt | chat.with_structured_output(MathQuestionOutput)

def create_math_question(request: QuestionRequest) -> Question:
  """Cria uma questão de matemática baseada na solicitação"""
  
  # Preparar dados para o prompt
  prompt_data = {
    "codigo": request.codigo,
    "objeto_conhecimento": request.objeto_conhecimento,
    "unidade_tematica": request.unidade_tematica
  }
  
  # Escolher chain baseado no tipo de questão
  if request.question_type == QuestionType.MULTIPLE_CHOICE:
    chain_output = multiple_choice_chain.invoke(prompt_data)
    opcoes = chain_output.opcoes
  else:  # TRUE_FALSE
    chain_output = true_false_chain.invoke(prompt_data)
    opcoes = None
  
  # Criar objeto Question
  question = Question(
    codigo=request.codigo,
    enunciado=chain_output.enunciado,
    opcoes=opcoes,
    gabarito=chain_output.gabarito,
    question_type=request.question_type
  )
  
  return question

# Chain principal para matemática
def math_chain(input_data: dict) -> Question:
  """Chain principal para gerar questões de matemática"""
  request = QuestionRequest(**input_data)
  return create_math_question(request)