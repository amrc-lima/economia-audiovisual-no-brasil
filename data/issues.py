import os
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQUIVO_MESTRE = os.path.join(BASE_DIR, 'data', 'master_filmes_db.csv')
ARQUIVO_ISSUES = os.path.join(BASE_DIR, 'data', 'issues.csv')
ARQUIVO_LOGS = os.path.join(BASE_DIR, 'logs', f"pipeline_historico_{datetime.now().strftime('%Y-%m-%d')}.log")
ARQUIVO_SAIDA_LOGS = os.path.join(BASE_DIR, 'data', 'issues_logs_filtrados.txt')

def extrair_e_limpar_issues():
    print("🕵️ Iniciando Auditoria de Data Quality com Pandas...")
    
    if not os.path.exists(ARQUIVO_MESTRE):
        print("⚠️ O banco de dados mestre não foi encontrado.")
        return
        
    df = pd.read_csv(ARQUIVO_MESTRE, sep=';', dtype=str)
    
    # 1. Quarentena: Isola quem não achou o TMDB_id
    filtro_ruins = df['TMDB_id'].isna() | (df['TMDB_id'] == '')
    df_ruins = df[filtro_ruins]
    df_bons = df[~filtro_ruins]
    
    if df_ruins.empty:
        print("🎉 Nenhum erro encontrado! Seu banco de dados está perfeito.")
        return

    titulos_corrompidos = set(df_ruins['ANCINE_TITULO_ORIGINAL'].str.strip())
    
    # 2. Salva e Limpa o Banco
    df_ruins.to_csv(ARQUIVO_ISSUES, sep=';', index=False, encoding='utf-8-sig')
    df_bons.to_csv(ARQUIVO_MESTRE, sep=';', index=False, encoding='utf-8-sig')
            
    print(f"✅ Higienização concluída!")
    print(f"   ➔ {len(df_ruins)} filme(s) corrompidos movidos para a quarentena.")
    print(f"   ➔ {len(df_bons)} filme(s) mantidos no banco oficial.")

    # 3. Busca histórica de falhas
    print("\n📜 Vasculhando histórico de logs atrás dos culpados...")
    logs_encontrados = []
    try:
        with open(ARQUIVO_LOGS, 'r', encoding='utf-8') as f_log:
            for linha_log in f_log:
                for titulo in titulos_corrompidos:
                    if f"@@{titulo}@@" in linha_log:
                        logs_encontrados.append(linha_log)
                        break
                        
        if logs_encontrados:
            with open(ARQUIVO_SAIDA_LOGS, 'w', encoding='utf-8') as f_out_log:
                f_out_log.write(f"=== LOGS DOS {len(titulos_corrompidos)} FILMES FALHOS ===\n\n")
                f_out_log.writelines(logs_encontrados)
            print(f"✅ Histórico de falhas salvo em 'data/issues_logs_filtrados.txt'")
    except:
        print(f"⚠️ O arquivo de log de hoje ({ARQUIVO_LOGS}) não foi encontrado para auditoria.")

if __name__ == "__main__":
    extrair_e_limpar_issues()