# 📚 Gerador de Questões BNCC - 4º Ano

Sistema inteligente para geração automática de questões educacionais baseadas nos códigos de habilidade da BNCC (Base Nacional Comum Curricular) para o 4º ano do ensino fundamental.

## 🎯 Funcionalidades

- **🤖 Geração automática** de questões múltipla escolha e verdadeiro/falso
- **🎯 Validação inteligente** de alinhamento com códigos BNCC
- **📊 Distribuição por dificuldade** (fácil, médio, difícil)
- **💾 Sistema de cache** para evitar questões duplicadas
- **🔄 Interface web** intuitiva com Streamlit
- **📤 Exportação para JSON** das questões geradas

## 📋 Matérias Suportadas

- **📐 Matemática** - 28 códigos de habilidade
- **🔬 Ciências** - 11 códigos de habilidade
- **📖 Português** - 21 códigos de habilidade

## 🚀 Como Usar

### 1. Instalação

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar chave OpenAI no .env
OPENAI_API_KEY=sua_chave_aqui
```

### 2. Interface Web (Streamlit)

```bash
streamlit run app.py
```

Acesse: http://localhost:8501

### 3. Uso Programático

```python
from pipeline import generate_questions

# Gerar questões para códigos específicos
batches = generate_questions(
    codes=["EF04MA01", "EF04CI01"],
    easy_count=2,
    medium_count=1,
    hard_count=1,
    multiple_choice_ratio=0.7
)

# Exportar resultados
for batch in batches:
    print(batch.to_export_format())
```

## 🏗️ Arquitetura

```
question_generator/
├── 📁 chains/           # Chains especializadas por matéria
│   ├── matematica.py    # Professor especialista em matemática
│   ├── portugues.py     # Professor especialista em português
│   ├── ciencias.py      # Professor especialista em ciências
│   └── validator.py     # Validador de questões
├── 📁 models/           # Modelos de dados Pydantic
│   └── schemas.py       # Estruturas de dados
├── 📁 data/             # Dados da BNCC
│   └── BNCC_4ano_Mapeamento.json
├── 📁 db/               # Cache SQLite
├── pipeline.py          # Pipeline principal
├── cache_manager.py     # Sistema de cache
├── app.py              # Interface Streamlit
└── test_pipeline.py    # Testes
```

## 🧪 Testes

```bash
# Executar testes da pipeline
python test_pipeline.py
```

## 📊 Exemplo de Questão Gerada

```
[EF04MA01] QUESTÃO: Qual é o maior número entre os seguintes: 125, 213, 145 e 321?
A) 125
B) 213
C) 145
D) 321

Gabarito: D
```

**Validação:**

- ✅ Alinhada com código BNCC
- 🎯 Confiança: 0.90
- 📝 Adequada para 4º ano

## ⚙️ Configurações Avançadas

### Cache

- **Localização:** `db/questions_cache.db`
- **Chave:** código + dificuldade + tipo + hash do conteúdo
- **Limpeza:** Automática após 30 dias

### Validação

- **Critérios:** Alinhamento BNCC + adequação cognitiva + qualidade pedagógica
- **Confiança mínima:** 0.6 para aprovação
- **Feedback:** Detalhado para cada questão

### Prompts Especializados

Cada matéria possui prompts específicos:

- **Matemática:** Foco em operações, geometria, medidas
- **Ciências:** Investigação científica, fenômenos naturais
- **Português:** Análise linguística, interpretação textual

## 🔧 Solução de Problemas

### Erro: Arquivo BNCC não encontrado

```bash
# Certificar que existe: data/BNCC_4ano_Mapeamento.json
python scripts/extract_from_mapping.py
```

### Erro: Chave OpenAI não encontrada

```bash
# Verificar .env
echo $OPENAI_API_KEY
```

### Cache corrompido

```bash
# Limpar cache via interface ou diretamente
rm db/questions_cache.db
```

## 📈 Estatísticas de Teste

- ✅ **100% dos testes** passando
- 🎯 **Taxa de aprovação:** ~90% nas validações
- ⚡ **Performance:** ~2-3s por questão
- 💾 **Cache hit rate:** ~60% após uso inicial

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature
3. Implemente com testes
4. Submeta um Pull Request

## 📄 Licença

Projeto educacional - uso livre para fins pedagógicos.

---

## 🎓 Códigos BNCC Suportados

### Matemática (28 códigos)

- **Números:** EF04MA01 a EF04MA13
- **Álgebra:** EF04MA14 a EF04MA16
- **Geometria:** EF04MA17 a EF04MA20
- **Grandezas e medidas:** EF04MA21 a EF04MA23
- **Estatística:** EF04MA24 a EF04MA28

### Ciências (11 códigos)

- **Matéria e energia:** EF04CI01 a EF04CI03
- **Vida e evolução:** EF04CI04 a EF04CI08
- **Terra e universo:** EF04CI09 a EF04CI11

### Português (21 códigos)

- **Análise linguística:** EF04LP01 a EF04LP12
- **Leitura/escuta:** EF04LP13 a EF04LP18
- **Produção textual:** EF04LP19 a EF04LP21

---

**🚀 Desenvolvido com LangChain, OpenAI GPT e Streamlit**
