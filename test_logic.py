#!/usr/bin/env python3
"""
Teste da lógica de distribuição sem usar API OpenAI
"""

from typing import List
from models.schemas import DifficultyLevel, QuestionType
import random

def test_distribution_logic():
    """Testa apenas a lógica de distribuição sem usar API"""
    
    print("🧪 TESTANDO LÓGICA DE DISTRIBUIÇÃO")
    print("=" * 50)
    
    def calculate_distribution(easy_count: int, medium_count: int, hard_count: int, multiple_choice_ratio: float):
        """Simula a lógica de distribuição da pipeline"""
        
        total_per_code = easy_count + medium_count + hard_count
        mc_count = int(total_per_code * multiple_choice_ratio)
        tf_count = total_per_code - mc_count
        
        # Calcular quantos de cada tipo por dificuldade
        easy_mc = int(easy_count * multiple_choice_ratio) if easy_count > 0 else 0
        easy_tf = easy_count - easy_mc
        
        medium_mc = int(medium_count * multiple_choice_ratio) if medium_count > 0 else 0
        medium_tf = medium_count - medium_mc
        
        hard_mc = int(hard_count * multiple_choice_ratio) if hard_count > 0 else 0
        hard_tf = hard_count - hard_mc
        
        # Ajustar para garantir que o total bate
        total_mc_calculated = easy_mc + medium_mc + hard_mc
        total_tf_calculated = easy_tf + medium_tf + hard_tf
        
        # Se houver diferença devido ao arredondamento, ajustar
        if total_mc_calculated < mc_count:
            # Adicionar múltipla escolha onde for possível
            if hard_count > 0 and hard_tf > 0:
                hard_mc += 1
                hard_tf -= 1
            elif medium_count > 0 and medium_tf > 0:
                medium_mc += 1
                medium_tf -= 1
            elif easy_count > 0 and easy_tf > 0:
                easy_mc += 1
                easy_tf -= 1
        
        # Construir listas finais
        difficulties = []
        question_types = []
        
        # Adicionar questões fáceis
        for _ in range(easy_mc):
            difficulties.append(DifficultyLevel.EASY)
            question_types.append(QuestionType.MULTIPLE_CHOICE)
        for _ in range(easy_tf):
            difficulties.append(DifficultyLevel.EASY)
            question_types.append(QuestionType.TRUE_FALSE)
        
        # Adicionar questões médias
        for _ in range(medium_mc):
            difficulties.append(DifficultyLevel.MEDIUM)
            question_types.append(QuestionType.MULTIPLE_CHOICE)
        for _ in range(medium_tf):
            difficulties.append(DifficultyLevel.MEDIUM)
            question_types.append(QuestionType.TRUE_FALSE)
        
        # Adicionar questões difíceis
        for _ in range(hard_mc):
            difficulties.append(DifficultyLevel.HARD)
            question_types.append(QuestionType.MULTIPLE_CHOICE)
        for _ in range(hard_tf):
            difficulties.append(DifficultyLevel.HARD)
            question_types.append(QuestionType.TRUE_FALSE)
        
        return difficulties, question_types
    
    # Casos de teste
    test_cases = [
        {"ratio": 0.0, "name": "0% MC (100% TF)", "easy": 2, "medium": 2, "hard": 2},
        {"ratio": 0.3, "name": "30% MC", "easy": 2, "medium": 2, "hard": 2},
        {"ratio": 0.5, "name": "50% MC", "easy": 2, "medium": 2, "hard": 2},
        {"ratio": 0.7, "name": "70% MC", "easy": 2, "medium": 2, "hard": 2},
        {"ratio": 1.0, "name": "100% MC (0% TF)", "easy": 2, "medium": 2, "hard": 2},
        {"ratio": 0.5, "name": "50% MC (caso ímpar)", "easy": 1, "medium": 2, "hard": 2},
    ]
    
    for test_case in test_cases:
        print(f"\n📊 {test_case['name']} (ratio={test_case['ratio']})")
        print("-" * 30)
        
        difficulties, question_types = calculate_distribution(
            test_case['easy'], 
            test_case['medium'], 
            test_case['hard'], 
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
        
        # Verificar distribuição por dificuldade
        easy_mc = sum(1 for d, qt in zip(difficulties, question_types) 
                     if d == DifficultyLevel.EASY and qt == QuestionType.MULTIPLE_CHOICE)
        easy_tf = sum(1 for d, qt in zip(difficulties, question_types) 
                     if d == DifficultyLevel.EASY and qt == QuestionType.TRUE_FALSE)
        
        print(f"  Distribuição - Fácil: {easy_mc} MC, {easy_tf} TF")
        
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