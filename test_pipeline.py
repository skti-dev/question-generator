import os
import sys
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Adicionar path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
  from pipeline import pipeline, get_subjects, get_codes_for_subject
  from models.schemas import DifficultyLevel, QuestionType
  
  def test_basic_functionality():
    """Testa funcionalidades básicas da pipeline"""
    print("🧪 INICIANDO TESTES DA PIPELINE")
    print("=" * 50)
    
    # Teste 1: Verificar carregamento de dados
    print("\n1. 📊 Testando carregamento de dados BNCC...")
    subjects = get_subjects()
    print(f"   ✅ Matérias encontradas: {subjects}")
    
    if not subjects:
      print("   ❌ ERRO: Nenhuma matéria encontrada!")
      return False
    
    # Teste 2: Verificar códigos por matéria
    print("\n2. 📋 Testando códigos por matéria...")
    for subject in subjects:
      codes = get_codes_for_subject(subject)
      print(f"   📖 {subject}: {len(codes)} códigos")
      if codes:
        print(f"      Exemplo: {codes[0]['codigo']} - {codes[0]['objeto_conhecimento'][:50]}...")
    
    # Teste 3: Gerar uma questão simples
    print("\n3. 🎯 Testando geração de questão...")
    
    # Pegar primeiro código de matemática
    math_codes = get_codes_for_subject("Matemática")
    if not math_codes:
      print("   ❌ ERRO: Nenhum código de matemática encontrado!")
      return False
    
    test_code = math_codes[0]["codigo"]
    print(f"   🧮 Testando com código: {test_code}")
    
    try:
      # Gerar uma questão de múltipla escolha fácil
      from pipeline import generate_questions
      
      batches = generate_questions(
        codes=[test_code],
        easy_count=1,
        medium_count=0,
        hard_count=0,
        multiple_choice_ratio=1.0
      )
      
      if batches and len(batches) > 0:
        batch = batches[0]
        print(f"   ✅ Questões geradas: {batch.total_generated}")
        print(f"   ✅ Questões aprovadas: {batch.total_approved}")
        
        if batch.questions:
          question = batch.questions[0].question
          validation = batch.questions[0].validation
          
          print(f"\n   📝 EXEMPLO DE QUESTÃO GERADA:")
          print(f"   {'-' * 40}")
          print(f"   {question.format_question()}")
          print(f"   {'-' * 40}")
          print(f"   🔍 Validação - Alinhada: {validation.is_aligned}")
          print(f"   🔍 Confiança: {validation.confidence_score:.2f}")
          print(f"   🔍 Feedback: {validation.feedback}")
        
        return True
      else:
        print("   ❌ ERRO: Nenhuma questão foi gerada!")
        return False
        
    except Exception as e:
      print(f"   ❌ ERRO na geração: {str(e)}")
      import traceback
      traceback.print_exc()
      return False
  
  def test_cache_functionality():
    """Testa funcionalidade do cache"""
    print("\n4. 💾 Testando sistema de cache...")
    
    try:
      stats = pipeline.get_cache_stats()
      print(f"   ✅ Cache inicializado: {stats['total_entries']} entradas")
      return True
    except Exception as e:
      print(f"   ❌ ERRO no cache: {str(e)}")
      return False
  
  def run_all_tests():
    """Executa todos os testes"""
    print("🚀 INICIANDO BATERIA DE TESTES COMPLETA")
    print("=" * 60)
    
    tests = [
      ("Funcionalidade Básica", test_basic_functionality),
      ("Sistema de Cache", test_cache_functionality)
    ]
    
    results = []
    for test_name, test_func in tests:
      try:
        result = test_func()
        results.append((test_name, result))
      except Exception as e:
        print(f"\n❌ ERRO CRÍTICO em {test_name}: {e}")
        results.append((test_name, False))
    
    # Resumo dos resultados
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
      status = "✅ PASSOU" if result else "❌ FALHOU"
      print(f"   {test_name}: {status}")
      if result:
        passed += 1
    
    print(f"\n🎯 RESULTADO FINAL: {passed}/{len(tests)} testes passaram")
    
    if passed == len(tests):
      print("🎉 TODOS OS TESTES PASSARAM! Pipeline está funcionando corretamente.")
    else:
      print("⚠️  Alguns testes falharam. Verifique os erros acima.")
    
    return passed == len(tests)

  if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

except ImportError as e:
  print(f"❌ ERRO DE IMPORTAÇÃO: {e}")
  print("Verifique se todos os arquivos foram criados corretamente.")
  sys.exit(1)
except Exception as e:
  print(f"❌ ERRO GERAL: {e}")
  import traceback
  traceback.print_exc()
  sys.exit(1)