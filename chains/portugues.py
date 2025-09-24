from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
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

class PortugueseQuestionOutput(BaseModel):
  """Estrutura para questão de português gerada pelo LLM"""
  enunciado: str = Field(description="Enunciado claro e adequado para o 4º ano")
  opcoes: List[str] = Field(description="4 opções para múltipla escolha")
  gabarito: str = Field(description="Resposta correta (A/B/C/D)")
  explicacao: str = Field(description="Breve explicação da resposta")

# Template para questões de múltipla escolha
multiple_choice_prompt = ChatPromptTemplate.from_messages([
  ("system", """Você é um professor especialista em LÍNGUA PORTUGUESA do 4º ano do ensino fundamental.
  
  Sua missão é criar questões de MÚLTIPLA ESCOLHA alinhadas com a BNCC (Base Nacional Comum Curricular).
  
  INSTRUÇÕES IMPORTANTES:
  - Use linguagem adequada para crianças de 9-10 anos
  - A questão deve estar DIRETAMENTE relacionada ao código de habilidade fornecido
  - Crie 4 alternativas (A, B, C, D) sendo apenas 1 correta
  - As alternativas incorretas devem ser plausíveis mas claramente erradas
  - Use textos apropriados para a idade (histórias, músicas, quadrinhos simples)
  - Foque em análise linguística, leitura e produção textual adequada ao nível
  
  IMPORTANTE: Como estamos trabalhando com 4º ano do ensino fundamental (crianças de 9-10 anos),
  a questão deve ser adequada para essa faixa etária em termos de:
  - Vocabulário apropriado para a idade
  - Textos adequados (histórias, músicas, quadrinhos simples)
  - Conceitos linguísticos acessíveis ao desenvolvimento cognitivo
  - Contextualização familiar às crianças
  
  CAMPOS DE ATUAÇÃO (conforme BNCC):
  - Todos os campos de atuação
  - Campo da vida cotidiana
  - Campo artístico-literário
  - Campo das práticas de estudo e pesquisa
  
  IMPORTANTE: Retorne APENAS UMA questão por vez, bem elaborada e revisada."""),
  
  ("human", """Crie uma questão de múltipla escolha de português:

  CÓDIGO DA HABILIDADE: {codigo}
  OBJETO DE CONHECIMENTO: {objeto_conhecimento}
  UNIDADE TEMÁTICA: {unidade_tematica}
  
  A questão deve ser adequada para alunos do 4º ano e seguir exatamente o código de habilidade especificado.""")
])

# Chain estruturada - sempre múltipla escolha
multiple_choice_chain = multiple_choice_prompt | chat.with_structured_output(PortugueseQuestionOutput)

def create_portuguese_question(request: QuestionRequest) -> Question:
  """Cria uma questão de português baseada na solicitação"""
  
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

# Chain principal para português
def portuguese_chain(input_data: dict) -> Question:
  """Chain principal para gerar questões de português"""
  request = QuestionRequest(**input_data)
  return create_portuguese_question(request)