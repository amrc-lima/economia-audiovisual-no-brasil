import os

# ==========================================
# CONFIGURAÇÃO DE CAMINHOS
# ==========================================
# Sobe uma pasta (..) para a raiz do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ARQUIVO_MESTRE = os.path.join(BASE_DIR, 'data', 'master_filmes_db.csv')
ARQUIVO_ISSUES = os.path.join(BASE_DIR, 'data', 'issues.csv')

# Para pegar o log com a data de hoje (se quiser auditar dias anteriores, mude o nome aqui)
from datetime import datetime
ARQUIVO_LOGS = os.path.join(BASE_DIR, 'logs', f"pipeline_historico_{datetime.now().strftime('%Y-%m-%d')}.log")
ARQUIVO_SAIDA_LOGS = os.path.join(BASE_DIR, 'data', 'issues_logs_filtrados.txt')

def extrair_e_limpar_issues():
    print(f"\n{'='*60}")
    print("🕵️ INICIANDO AUDITORIA DE DATA QUALITY E AUTO-CURA")
    print(f"{'='*60}\n")
    
    linhas_corrompidas = []
    linhas_boas = []
    titulos_corrompidos = set()
    
    # ==========================================
    # 1. VARREDURA E QUARENTENA NO BANCO DE DADOS
    # ==========================================
    try:
        with open(ARQUIVO_MESTRE, 'r', encoding='utf-8-sig') as f:
            linhas = f.readlines()
            
        if not linhas:
            print("⚠️ O banco de dados está vazio.")
            return
            
        cabecalho = linhas[0]
        linhas_boas.append(cabecalho)
        
        for linha in linhas[1:]:
            # Identifica a anomalia: se tiver múltiplos pontos e vírgulas vazios na string
            if ';;;;;;' in linha or 'False;;;0' in linha:
                linhas_corrompidas.append(linha)
                
                # Extrai o título do filme (A coluna 2 do nosso CSV oficial da Ancine)
                colunas = linha.split(';')
                if len(colunas) > 1:
                    titulo = colunas[1].strip()
                    titulos_corrompidos.add(titulo)
            else:
                linhas_boas.append(linha)
                
        # Exporta o lixo para a Quarentena
        if linhas_corrompidas:
            with open(ARQUIVO_ISSUES, 'w', encoding='utf-8-sig') as f_out:
                f_out.write(cabecalho)
                f_out.writelines(linhas_corrompidas)
                
        # Sobrescreve o Master Database apenas com os dados saudáveis
        with open(ARQUIVO_MESTRE, 'w', encoding='utf-8-sig') as f_master:
            f_master.writelines(linhas_boas)
            
        print("✅ [ETAPA 1] Higienização do Master Database concluída!")
        print(f"   ➔ Filmes corrompidos movidos para a quarentena: {len(linhas_corrompidas)}")
        print(f"   ➔ Filmes saudáveis mantidos no banco oficial: {len(linhas_boas) - 1}")
        
    except FileNotFoundError:
        print(f"❌ Erro: O arquivo '{ARQUIVO_MESTRE}' não foi encontrado.")
        return

    # ==========================================
    # 2. CAÇA AOS LOGS (RASTREAMENTO DE ERROS)
    # ==========================================
    if not titulos_corrompidos:
        print("\n🎉 Nenhum erro encontrado! Seu banco de dados está perfeito.")
        return
        
    print("\n📜 [ETAPA 2] Vasculhando histórico de logs atrás dos culpados...")
    logs_encontrados = []
    
    try:
        with open(ARQUIVO_LOGS, 'r', encoding='utf-8') as f_log:
            for linha_log in f_log:
                # Checa se a tag mágica de algum filme corrompido está na linha do log
                for titulo in titulos_corrompidos:
                    tag = f"@@{titulo}@@"
                    if tag in linha_log:
                        logs_encontrados.append(linha_log)
                        break
                        
        if logs_encontrados:
            with open(ARQUIVO_SAIDA_LOGS, 'w', encoding='utf-8') as f_out_log:
                f_out_log.write(f"=== HISTÓRICO DE LOGS DOS {len(titulos_corrompidos)} FILMES COM FALHA ===\n\n")
                f_out_log.writelines(logs_encontrados)
            print(f"✅ Histórico de falhas salvo em 'data/issues_logs_filtrados.txt'")
        else:
            print("   ⚠️ As tags não foram encontradas no log de hoje.")
            
    except FileNotFoundError:
        print(f"❌ Arquivo de log não encontrado ({ARQUIVO_LOGS}). Pulo a etapa de logs.")
        
    print(f"\n{'='*60}")
    print("🎯 AUDITORIA FINALIZADA. O ROBÔ PODE SER REINICIADO!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    extrair_e_limpar_issues()