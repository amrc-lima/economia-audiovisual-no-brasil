import os
import pandas as pd

def limpar_dados_ancine(caminho_arquivo):
    print("📂 [Módulo Ancine] Lendo arquivo oficial...")
    
    try:
        # Tenta ler no padrão moderno
        df = pd.read_csv(caminho_arquivo, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        # Fallback caso a Ancine tenha salvo o Excel em formato antigo do Windows
        df = pd.read_csv(caminho_arquivo, sep=';', encoding='latin1')
        
    # 1. Tratamento da coluna Ano (Extrai apenas os 4 últimos caracteres da data)
    df['Ano'] = df['DATA_LANCAMENTO_OBRA'].astype(str).str[-4:]
    df['Ano'] = pd.to_numeric(df['Ano'], errors='coerce')
    
    # 2. Tratamento Financeiro (Arruma a bagunça do dinheiro)
    # Ex: "R$ 18.220.407,82" vira 18220407.82
    df['RENDA_TOTAL'] = df['RENDA_TOTAL'].astype(str).str.replace('R$ ', '', regex=False)
    df['RENDA_TOTAL'] = df['RENDA_TOTAL'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df['RENDA_TOTAL'] = pd.to_numeric(df['RENDA_TOTAL'], errors='coerce')
    
    # 3. Higienização
    # Remove as linhas sem renda ou sem ano, porque sem isso o filme é inútil para a nossa análise
    df = df.dropna(subset=['Ano', 'RENDA_TOTAL'])
    
    # 4. Ordenação
    # Ordenamos pela maior bilheteria de todas. Assim, o robô raspa os mais importantes (Monopólio) primeiro!
    df_ordenado = df.sort_values(by='RENDA_TOTAL', ascending=False)
    
    print(f"✅ [Módulo Ancine] Base pronta com {len(df_ordenado)} filmes válidos para processamento.")
    return df_ordenado

# ==========================================
# ÁREA DE TESTE INDIVIDUAL
# ==========================================
# Esse bloco só roda se você executar este arquivo sozinho no terminal (python modulo_ancine.py)
if __name__ == "__main__":
    # Sobe uma pasta para achar o arquivo na /data
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    caminho_teste = os.path.join(BASE_DIR, 'data', 'lancamentos-comerciais-por-distribuidoras.csv')
    
    if os.path.exists(caminho_teste):
        df_teste = limpar_dados_ancine(caminho_teste)
        print("\n--- TOP 5 MAIORES BILHETERIAS ---")
        print(df_teste[['TITULO_ORIGINAL', 'Ano', 'RENDA_TOTAL']].head())
    else:
        print(f"❌ Arquivo não encontrado para teste em: {caminho_teste}")