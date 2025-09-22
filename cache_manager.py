import sqlite3
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from models.schemas import Question, ValidationResult, CacheEntry, QuestionRequest

class CacheManager:
  def __init__(self, db_path: str = "db/questions_cache.db"):
    self.db_path = Path(db_path)
    self.db_path.parent.mkdir(exist_ok=True)
    self._init_db()
  
  def _init_db(self):
    """Inicializa o banco de dados SQLite"""
    with sqlite3.connect(self.db_path) as conn:
      conn.execute("""
        CREATE TABLE IF NOT EXISTS question_cache (
          cache_key TEXT PRIMARY KEY,
          question_data TEXT NOT NULL,
          validation_data TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
      """)
      conn.commit()
  
  def _generate_cache_key(self, request: QuestionRequest, question_content: str = "") -> str:
    """Gera chave única para cache baseada nos parâmetros da solicitação"""
    key_data = {
      "codigo": request.codigo,
      "difficulty": request.difficulty.value,
      "question_type": request.question_type.value,
      "subject": request.subject.value,
      "content_hash": hashlib.md5(question_content.encode()).hexdigest()[:8]
    }
    key_string = json.dumps(key_data, sort_keys=True)
    return hashlib.sha256(key_string.encode()).hexdigest()[:16]
  
  def get_cached_questions(self, request: QuestionRequest, limit: int = 10) -> List[CacheEntry]:
    """Busca questões em cache para a solicitação"""
    # Busca por questões similares (mesmo código, dificuldade, tipo)
    base_key_data = {
      "codigo": request.codigo,
      "difficulty": request.difficulty.value,
      "question_type": request.question_type.value,
      "subject": request.subject.value
    }
    
    with sqlite3.connect(self.db_path) as conn:
      cursor = conn.execute("""
        SELECT cache_key, question_data, validation_data, created_at 
        FROM question_cache 
        WHERE cache_key LIKE ? 
        ORDER BY created_at DESC 
        LIMIT ?
      """, (f"{json.dumps(base_key_data, sort_keys=True)[:20]}%", limit))
      
      entries = []
      for row in cursor.fetchall():
        try:
          question_data = json.loads(row[1])
          validation_data = json.loads(row[2])
          
          question = Question(**question_data)
          validation = ValidationResult(**validation_data)
          
          entry = CacheEntry(
            cache_key=row[0],
            question=question,
            validation=validation,
            created_at=row[3]
          )
          entries.append(entry)
        except Exception as e:
          # Se houver erro ao deserializar, ignora entrada
          continue
      
      return entries
  
  def cache_question(self, request: QuestionRequest, question: Question, validation: ValidationResult) -> str:
    """Armazena questão no cache"""
    cache_key = self._generate_cache_key(request, question.enunciado)
    
    question_data = question.model_dump_json()
    validation_data = validation.model_dump_json()
    created_at = datetime.now().isoformat()
    
    with sqlite3.connect(self.db_path) as conn:
      conn.execute("""
        INSERT OR REPLACE INTO question_cache 
        (cache_key, question_data, validation_data, created_at)
        VALUES (?, ?, ?, ?)
      """, (cache_key, question_data, validation_data, created_at))
      conn.commit()
    
    return cache_key
  
  def is_duplicate(self, request: QuestionRequest, new_question: Question, similarity_threshold: float = 0.8) -> bool:
    """Verifica se uma questão é muito similar a questões existentes"""
    cached_questions = self.get_cached_questions(request, limit=50)
    
    new_question_text = new_question.enunciado.lower()
    
    for cached_entry in cached_questions:
      cached_text = cached_entry.question.enunciado.lower()
      
      # Simples verificação de similaridade baseada em palavras comuns
      new_words = set(new_question_text.split())
      cached_words = set(cached_text.split())
      
      if len(new_words) == 0 or len(cached_words) == 0:
        continue
      
      intersection = len(new_words.intersection(cached_words))
      union = len(new_words.union(cached_words))
      
      similarity = intersection / union if union > 0 else 0
      
      if similarity >= similarity_threshold:
        return True
    
    return False
  
  def clear_cache(self, older_than_days: int = 30):
    """Remove entradas antigas do cache"""
    cutoff_date = datetime.now().replace(day=datetime.now().day - older_than_days).isoformat()
    
    with sqlite3.connect(self.db_path) as conn:
      cursor = conn.execute("DELETE FROM question_cache WHERE created_at < ?", (cutoff_date,))
      deleted_count = cursor.rowcount
      conn.commit()
    
    return deleted_count
  
  def get_cache_stats(self) -> dict:
    """Retorna estatísticas do cache"""
    with sqlite3.connect(self.db_path) as conn:
      cursor = conn.execute("SELECT COUNT(*) FROM question_cache")
      total_entries = cursor.fetchone()[0]
      
      cursor = conn.execute("""
        SELECT 
          COUNT(*) as count,
          substr(cache_key, 1, 10) as key_prefix
        FROM question_cache 
        GROUP BY substr(cache_key, 1, 10)
        ORDER BY count DESC
        LIMIT 10
      """)
      top_keys = cursor.fetchall()
    
    return {
      "total_entries": total_entries,
      "top_cached_patterns": [{"pattern": row[1], "count": row[0]} for row in top_keys]
    }
  
  def get_all_cache_entries(self) -> List[CacheEntry]:
    """Retorna todas as entradas do cache"""
    with sqlite3.connect(self.db_path) as conn:
      cursor = conn.execute("""
        SELECT cache_key, question_data, validation_data, created_at 
        FROM question_cache 
        ORDER BY created_at DESC
      """)
      
      entries = []
      for row in cursor.fetchall():
        try:
          question_data = json.loads(row[1])
          validation_data = json.loads(row[2])
          
          question = Question(**question_data)
          validation = ValidationResult(**validation_data)
          
          entry = CacheEntry(
            cache_key=row[0],
            question=question,
            validation=validation,
            created_at=row[3]
          )
          entries.append(entry)
        except Exception as e:
          # Se houver erro ao deserializar, ignora entrada
          continue
      
      return entries