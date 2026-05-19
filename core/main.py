import os
import sys
import logging
import ctypes
import pandas as pd
import time
from datetime import datetime, timedelta

from modulo_ancine import limpar_dados_ancine
from modulo_api import extrair_todas_as_infos, LimiteDiarioExcedido

# ==========================================
# 0. POPUPS CRÍTICOS NATIVOS DO WINDOWS
# ==========================================
def solicitar_acao_usuario(titulo_filme):
    """
    Se tiver terminal, pede no teclado.
    Se estiver invisível (pythonw), abre um Popup nativo do Windows!
    """
    if hasattr(sys, 'stdin') and sys.stdin and sys.stdin.isatty():
        return input(f"\n🚨 [C] Tentar Novamente, [P] Pular filme ou [S] Salvar e Sair? ").strip().upper()
    else:
        texto = f"Atenção, Mestre!\n\nO filme '{titulo_filme}' falhou 3 vezes consecutivas no TMDB/OMDb.\nO que o robô deve fazer?\n\n[Repetir] = Tentar novamente\n[Ignorar] = Pular filme e ir pro próximo\n[Anular] = Salvar progresso e Desligar robô"
        resposta = ctypes.windll.user32.MessageBoxW(0, texto, "🚨 Robô de Dados: Alerta Crítico", 0x02 | 0x30 | 0x40000)
        
        if resposta == 4: return 'C'
        elif resposta == 5: return 'P'
        else: return 'S'

# ==========================================
# 1. AJUSTE DOS CAMINHOS E LOGS
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQUIVO_ANCINE = os.path.join(BASE_DIR, 'data', 'lancamentos-comerciais-por-distribuidoras.csv')
ARQUIVO_SAIDA = os.path.join(BASE_DIR, 'data', 'master_filmes_db.csv')
ARQUIVO_COOLDOWN = os.path.join(BASE_DIR, 'data', 'api_cooldown.txt')
PASTA_LOGS = os.path.join(BASE_DIR, 'logs')

os.makedirs(PASTA_LOGS, exist_ok=True)
arquivo_log = os.path.join(PASTA_LOGS, f"pipeline_historico_{datetime.now().strftime('%Y-%m-%d')}.log")

class LoggerDuplo:
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open(arquivo_log, "a", encoding="utf-8")

    def write(self, message):
        if self.terminal: self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        if self.terminal: self.terminal.flush()
        self.log.flush()

if sys.stdout:
    sys.stdout = LoggerDuplo()
    sys.stderr = sys.stdout

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.FileHandler(arquivo_log, encoding='utf-8')]
)
logger = logging.getLogger(__name__)

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ==========================================
# 2. O SISTEMA DE COOLDOWN DE 24 HORAS
# ==========================================
def verificar_cooldown():
    """Lê a trava de segurança e faz o Python dormir se necessário"""
    if os.path.exists(ARQUIVO_COOLDOWN):
        with open(ARQUIVO_COOLDOWN, 'r') as f:
            cooldown_str = f.read().strip()
            
        if cooldown_str:
            cooldown_end = datetime.fromisoformat(cooldown_str)
            agora = datetime.now()
            
            if agora < cooldown_end:
                restante = cooldown_end - agora
                horas, resto = divmod(restante.seconds, 3600)
                minutos, _ = divmod(resto, 60)
                
                msg_log = f"Pausando robô até {cooldown_end.strftime('%d/%m %H:%M:%S')}"
                
                print(f"\n[{agora.strftime('%H:%M:%S')}] ⏳ COOLDOWN ATIVO: {msg_log}")
                logger.warning(f"COOLDOWN ATIVO. {msg_log}")
                
                # O processador congela aqui
                time.sleep(restante.total_seconds())
                
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⏰ Cooldown finalizado! Acordando...")
                logger.info("Cooldown finalizado. Retomando extrações.")
            
            os.remove(ARQUIVO_COOLDOWN)

# ==========================================
# 3. O MAESTRO (PIPELINE PRINCIPAL)
# ==========================================
def orquestrar_pipeline():
    print(f"\n{'='*50}")
    print(f"🚀 INÍCIO DO PIPELINE: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*50}\n")
    logger.info("=== INICIANDO PIPELINE DE DADOS ===")
    
    verificar_cooldown()
    df_ancine = limpar_dados_ancine(ARQUIVO_ANCINE)
    filmes_processados = set()
    
    if os.path.exists(ARQUIVO_SAIDA):
        print(f"📁 Banco de dados 'master_filmes_db.csv' encontrado. Lendo histórico...")
        df_mestre = pd.read_csv(ARQUIVO_SAIDA, sep=';', dtype=str)
        for _, row in df_mestre.iterrows():
            try: ano_lido = int(float(row.get('ANCINE_Ano', 0)))
            except: ano_lido = 0
            chave = f"{str(row.get('ANCINE_TITULO_ORIGINAL', '')).strip()}_{ano_lido}"
            filmes_processados.add(chave)
        print(f"✅ {len(filmes_processados)} filmes já processados. Pulando...\n")
    else:
        print("📁 Criando Master Database do zero em /data...\n")

    print(f"🔍 Baixando TUDO das APIs para os filmes restantes...")
    
    try:
        for index, row in df_ancine.iterrows():
            titulo = str(row['TITULO_ORIGINAL']).strip()
            ano = int(row['Ano'])
            chave_atual = f"{titulo}_{ano}"
            tag = f"@@{titulo}@@"
            
            if chave_atual in filmes_processados:
                continue
                
            sucesso = False
            tentativas = 0
            
            while not sucesso and tentativas < 3:
                try:
                    hora_atual = datetime.now().strftime('%H:%M:%S')
                    print(f"[{hora_atual}] Extraindo: {titulo} ({ano})")
                    logger.info(f"Iniciando extração para: {titulo} ({ano}) {tag}")
                    
                    dados_api = extrair_todas_as_infos(titulo, ano)
                    
                    linha_final = {}
                    for coluna in df_ancine.columns:
                        linha_final[f"ANCINE_{coluna}"] = row[coluna]
                    
                    if dados_api:
                        linha_final.update(dados_api)
                    
                    nova_linha_df = pd.DataFrame([linha_final])
                    cabecalho = not os.path.exists(ARQUIVO_SAIDA)
                    
                    nova_linha_df.to_csv(ARQUIVO_SAIDA, sep=';', mode='a', header=cabecalho, index=False, encoding='utf-8-sig')
                    
                    filmes_processados.add(chave_atual)
                    sucesso = True
                    logger.info(f"Salvo no banco com sucesso. {tag}")
                    time.sleep(0.5) 

                except LimiteDiarioExcedido:
                    agora = datetime.now()
                    liberacao = agora + timedelta(hours=24)
                    
                    with open(ARQUIVO_COOLDOWN, 'w') as f:
                        f.write(liberacao.isoformat())
                    
                    print(f"\n🚨 [{agora.strftime('%H:%M:%S')}] LIMITE DA API OMDb ATINGIDO!")
                    print(f"   Salvando checkpoint. O script entrará em hibernação automática.")
                    logger.error(f"Limite da API atingido. Entrando em Cooldown. {tag}")
                    
                    verificar_cooldown() 
                    
                except Exception as e:
                    tentativas += 1
                    print(f"   ❌ ERRO na Tentativa {tentativas}/3: {e}")
                    logger.error(f"Erro na extração de {titulo}: {e} {tag}")
                    
                    if tentativas < 3:
                        time.sleep(60) 
                    else:
                        comando = solicitar_acao_usuario(titulo)
                        if comando == 'C': 
                            tentativas = 0
                            logger.info(f"Usuário escolheu REPETIR para {titulo}.")
                            print("🔄 Resetando as tentativas e forçando novamente...")
                        elif comando == 'P': 
                            sucesso = True
                            logger.info(f"Usuário escolheu IGNORAR {titulo}.")
                            print("⏭️ Pulando o filme e indo para o próximo...")
                        else: 
                            logger.info(f"Usuário escolheu ABORTAR no filme {titulo}.")
                            print("🛑 Abortando execução! O robô será desligado.")
                            raise SystemExit("Desligado pelo usuário via Popup.")

    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🛑 Interrompido manualmente (Ctrl+C).")
        logger.warning("Pipeline abortado pelo usuário (Ctrl+C).")
    except Exception as e:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ❌ Erro crítico inesperado: {e}")
        logger.critical(f"Falha Crítica no Pipeline: {e}")
        
    print(f"\n{'='*50}")
    print(f"🏁 FIM DA EXECUÇÃO: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    orquestrar_pipeline()