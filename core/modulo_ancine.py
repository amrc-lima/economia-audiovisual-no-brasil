import os
import pandas as pd

def limpar_dados_ancine(caminho_arquivo):
    print("📂 [Módulo Ancine] Lendo arquivo oficial...")
    try:
        df = pd.read_csv(caminho_arquivo, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(caminho_arquivo, sep=';', encoding='latin1')
        
    df['Ano'] = df['DATA_LANCAMENTO_OBRA'].astype(str).str[-4:]
    df['Ano'] = pd.to_numeric(df['Ano'], errors='coerce')
    
    df['RENDA_TOTAL'] = df['RENDA_TOTAL'].astype(str).str.replace('R$ ', '', regex=False)
    df['RENDA_TOTAL'] = df['RENDA_TOTAL'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df['RENDA_TOTAL'] = pd.to_numeric(df['RENDA_TOTAL'], errors='coerce')
    
    df = df.dropna(subset=['Ano', 'RENDA_TOTAL'])
    df_ordenado = df.sort_values(by='RENDA_TOTAL', ascending=False)
    
    print(f"✅ [Módulo Ancine] Base pronta com {len(df_ordenado)} filmes válidos para processamento.")
    return df_ordenado