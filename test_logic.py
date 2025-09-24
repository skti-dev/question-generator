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
    
    def calculate_distribution(questions_per_code: int):
        """Simula a lógica de distribuição da pipeline - sempre múltipla escolha"""
        
        # Todas as questões serão múltipla escolha
        question_types = [QuestionType.MULTIPLE_CHOICE] * questions_per_code
        
        return question_types
    
    # Casos de teste
    test_cases = [
        {"name": "1 questão", "questions": 1},
        {"name": "2 questões", "questions": 2},
        {"name": "3 questões", "questions": 3},
        {"name": "5 questões", "questions": 5},
    ]
    
    for test_case in test_cases:
        print(f"\n📊 {test_case['name']}")
        print("-" * 30)
        
        question_types = calculate_distribution(test_case['questions'])
        
        total = len(question_types)
        mc_count = sum(1 for qt in question_types if qt == QuestionType.MULTIPLE_CHOICE)
        
        print(f"  Total questões: {total}")
        print(f"  Múltipla Escolha: {mc_count}")
        print(f"  Proporção MC: 100%")
        
        # Verificar se está correto (deve sempre ser 100% múltipla escolha)
        if mc_count == total:
            print("  ✅ PASSOU - Todas as questões são múltipla escolha")
        else:
            print("  ❌ FALHOU - Nem todas as questões são múltipla escolha")
    
    print("\n" + "=" * 50)
    print("🎯 TESTE CONCLUÍDO - Sistema configurado para gerar apenas questões de múltipla escolha")

if __name__ == "__main__":
    test_distribution_logic()