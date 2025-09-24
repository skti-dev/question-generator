#!/usr/bin/env python3
"""
Teste da lógica de distribuição sem usar API OpenAI
"""

from typing import List
from models.schemas import QuestionType
import random

def test_distribution_logic():
    """Testa apenas a lógica de distribuição sem usar API"""
    
    print("🧪 TESTANDO LÓGICA DE DISTRIBUIÇÃO")
    print("=" * 50)
    
    def calculate_distribution(questions_per_code: int, multiple_choice_ratio: float):
        """Simula a lógica de distribuição da pipeline"""
        
        mc_count = int(questions_per_code * multiple_choice_ratio)
        tf_count = questions_per_code - mc_count
        
        # Construir listas finais
        question_types = []
        
        # Adicionar questões de múltipla escolha
        for _ in range(mc_count):
            question_types.append(QuestionType.MULTIPLE_CHOICE)
        
        # Adicionar questões verdadeiro/falso
        for _ in range(tf_count):
            question_types.append(QuestionType.TRUE_FALSE)
        
        return question_types
    
    # Casos de teste
    test_cases = [
        {"ratio": 0.0, "name": "0% MC (100% TF)", "questions": 6},
        {"ratio": 0.3, "name": "30% MC", "questions": 6},
        {"ratio": 0.5, "name": "50% MC", "questions": 6},
        {"ratio": 0.7, "name": "70% MC", "questions": 6},
        {"ratio": 1.0, "name": "100% MC (0% TF)", "questions": 6},
        {"ratio": 0.5, "name": "50% MC (caso ímpar)", "questions": 5},
    ]
    
    for test_case in test_cases:
        print(f"\n📊 {test_case['name']} (ratio={test_case['ratio']})")
        print("-" * 30)
        
        question_types = calculate_distribution(
            test_case['questions'], 
            test_case['ratio']
        )
        
        total = len(question_types)
        mc_count = sum(1 for qt in question_types if qt == QuestionType.MULTIPLE_CHOICE)
        tf_count = sum(1 for qt in question_types if qt == QuestionType.TRUE_FALSE)
        actual_ratio = mc_count / total if total > 0 else 0
        
        print(f"  Total questões: {total}")
        print(f"  Múltipla Escolha: {mc_count}")
        print(f"  Verdadeiro/Falso: {tf_count}")
        print(f"  Proporção MC real: {actual_ratio:.2f}")
        print(f"  Proporção MC esperada: {test_case['ratio']:.2f}")
        
        # Verificar se está correto
        tolerance = 0.2
        if abs(actual_ratio - test_case['ratio']) <= tolerance:
            print("  ✅ PASSOU - Distribuição correta")
        else:
            print("  ❌ FALHOU - Distribuição incorreta")
    
    print("\n" + "=" * 50)
    print("🎯 TESTE CONCLUÍDO")

if __name__ == "__main__":
    test_distribution_logic()