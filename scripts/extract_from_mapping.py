import pandas as pd
import json
from pathlib import Path

def excel_to_json(excel_path):
  data = pd.read_excel(excel_path, sheet_name=None)
  result = {}
  
  for sheet_name, df in data.items():
    df_clean = df.dropna(how='all')
    sheet_data = []
    
    for _, row in df_clean.iterrows():
      row_data = {
        'codigo': row.get('Código', ''),
        'objeto_conhecimento': row.get('Objeto de Conhecimento', ''),
        'unidade_tematica': row.get('Unidade Temática / Campo', '')
      }
      
      row_data = {k: v for k, v in row_data.items() if pd.notna(v) and str(v).strip() != ''}
      
      if row_data.get('codigo') or row_data.get('objeto_conhecimento'):
        sheet_data.append(row_data)
    
    if sheet_data:
      result[sheet_name] = sheet_data
  
  excel_name = Path(excel_path).stem
  output_path = Path(excel_path).parent / f"{excel_name}.json"
  
  with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
  
  return output_path

def test():
  import os
  
  possible_paths = [
    '../data/BNCC_4ano_Mapeamento.xlsx',  # Se executado da pasta scripts
    'data/BNCC_4ano_Mapeamento.xlsx',     # Se executado da raiz do projeto
  ]
  
  excel_path = None
  for path in possible_paths:
    if os.path.exists(path):
      excel_path = path
      break
  
  if not excel_path:
    print("Arquivo Excel não encontrado nos caminhos:")
    for path in possible_paths:
      print(f"  - {os.path.abspath(path)}")
    return
  
  output_path = excel_to_json(excel_path)
  print(f"Arquivo criado em: {output_path}")
  
if __name__ == "__main__":
  test()