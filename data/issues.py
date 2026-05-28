import os
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQUIVO_PARQUET = os.path.join(BASE_DIR, 'data', 'master_filmes_db.parquet')
ARQUIVO_ISSUES = os.path.join(BASE_DIR, 'data', 'issues.csv') 
PASTA_LOGS = os.path.join(BASE_DIR, 'logs')
ARQUIVO_SAIDA_LOGS = os.path.join(BASE_DIR, 'data', 'issues_logs_filtrados.txt')

def extrair_e_limpar_issues():
    print("🕵️ Iniciando Auditoria Profunda de Data Quality...")
    
    # --- PARTE 1: HIGIENIZAÇÃO DO PARQUET ---
    if not os.path.exists(ARQUIVO_PARQUET):
        print("⚠️ Banco mestre não encontrado. Criando DataFrame vazio para auditoria.")
        df_bons = pd.DataFrame()
        titulos_no_parquet = set()
    else:
        df = pd.read_parquet(ARQUIVO_PARQUET, engine='pyarrow')
        ids_numericos = pd.to_numeric(df['TMDB_id'], errors='coerce')
        filtro_ruins = ids_numericos.isna()
        
        df_ruins_existentes = df[filtro_ruins]
        df_bons = df[~filtro_ruins]
        titulos_no_parquet = set(df_bons['ANCINE_TITULO_ORIGINAL'].str.strip().unique())

        # Salva o banco limpo (Escrita Atômica)
        arquivo_temp = ARQUIVO_PARQUET + ".temp"
        df_bons.to_parquet(arquivo_temp, engine='pyarrow', index=False)
        os.replace(arquivo_temp, ARQUIVO_PARQUET)
        print(f"✅ Higienização concluída: {len(df_ruins_existentes)} removidos, {len(df_bons)} mantidos.")

    # --- PARTE 2: AUDITORIA REVERSA VIA LOGS ---
    print("📜 Escaneando logs para identificar 'Filmes Fantasmas' (erros que não entraram no banco)...")
    
    # Dicionário para mapear Titulo -> Última linha de log de erro
    falhas_detectadas = {} 
    
    if os.path.exists(PASTA_LOGS):
        arquivos_de_log = sorted([f for f in os.listdir(PASTA_LOGS) if f.endswith('.log')])
        for arquivo in arquivos_de_log:
            with open(os.path.join(PASTA_LOGS, arquivo), 'r', encoding='utf-8') as f:
                for linha in f:
                    if "@@" in linha:
                        # Extrai o título entre as tags @@
                        partes = linha.split("@@")
                        if len(partes) >= 3:
                            titulo = partes[1].strip()
                            # Se o log indica erro ou falha e o filme NÃO está no parquet
                            if titulo not in titulos_no_parquet:
                                falhas_detectadas[titulo] = linha.strip()

    # --- PARTE 3: GERAÇÃO DE RELATÓRIO DE QUARENTENA ---
    if falhas_detectadas:
        print(f"🚩 Detectados {len(falhas_detectadas)} filmes que falharam e estão fora do banco.")
        
        # Criamos um relatório de issues com o título e o motivo (log)
        report_data = []
        for titulo, log_inteiro in falhas_detectadas.items():
            report_data.append({
                "DATA_AUDITORIA": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ANCINE_TITULO_ORIGINAL": titulo,
                "MOTIVO_FALHA_LOG": log_inteiro
            })
        
        df_issues = pd.DataFrame(report_data)
        
        # Se já existir um issues.csv, concatena, senão cria novo
        if os.path.exists(ARQUIVO_ISSUES):
            df_antigo = pd.read_csv(ARQUIVO_ISSUES, sep=';', encoding='utf-8-sig')
            df_issues = pd.concat([df_antigo, df_issues]).drop_duplicates(subset=['ANCINE_TITULO_ORIGINAL'], keep='last')
        
        df_issues.to_csv(ARQUIVO_ISSUES, sep=';', index=False, encoding='utf-8-sig')
        
        # Também salva o log detalhado para debug rápido
        with open(ARQUIVO_SAIDA_LOGS, 'w', encoding='utf-8') as f_out:
            f_out.write("=== RELATÓRIO DE INVESTIGAÇÃO DE FALHAS ===\n\n")
            for t, l in falhas_detectadas.items():
                f_out.write(f"FILME: {t}\nSTATUS: {l}\n{'-'*50}\n")
                
        print(f"✅ Quarentena atualizada em '{ARQUIVO_ISSUES}'")
        print(f"✅ Detalhes técnicos salvos em '{ARQUIVO_SAIDA_LOGS}'")
    else:
        print("🎉 Tudo limpo! Nenhum filme fantasma detectado nos logs.")

if __name__ == "__main__":
    extrair_e_limpar_issues()