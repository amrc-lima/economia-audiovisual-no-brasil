import os
import logging
import pandas as pd
import time
from datetime import datetime, timedelta
from modulo_ancine import limpar_dados_ancine
from modulo_api import extrair_todas_as_infos, LimiteDiarioExcedido
try:
    from win10toast import ToastNotifier
    toaster = ToastNotifier()
except ImportError:
    toaster = None

def notificar_windows(titulo, mensagem):
    """Gera o balão de notificação no Windows 11"""
    if toaster:
        # threaded=True permite que o balão suma sem travar o código
        toaster.show_toast(titulo, mensagem, duration=5, threaded=True)


# --- CAMINHOS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQUIVO_ANCINE = os.path.join(BASE_DIR, 'data', 'lancamentos-comerciais-por-distribuidoras.csv')
ARQUIVO_SAIDA = os.path.join(BASE_DIR, 'data', 'master_filmes_db.csv')
ARQUIVO_COOLDOWN = os.path.join(BASE_DIR, 'data', 'api_cooldown.txt')
PASTA_LOGS = os.path.join(BASE_DIR, 'logs')

# ==========================================
# CONFIGURAÇÃO DE LOGS (FILE + TERMINAL)
# ==========================================
os.makedirs(PASTA_LOGS, exist_ok=True)
arquivo_log = os.path.join(PASTA_LOGS, "pipeline_historico.log")

# Tudo que for logging.info/debug vai pro Arquivo. Terminal fica limpo.
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(arquivo_log, encoding='utf-8'), 
        logging.StreamHandler() # Se quiser tirar o lixo do terminal, delete essa linha
    ]
)
logger = logging.getLogger(__name__)

# ==========================================
# 1. O SISTEMA DE COOLDOWN DE 24 HORAS
# ==========================================
def verificar_cooldown():
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
                msg_balao = f"Limite da API atingido. Retorno em {restante.days}d {horas}h {minutos}m."
                
                logger.warning(f"COOLDOWN ATIVO. {msg_log}")
                
                # 🎈 Notificação: Fui dormir!
                notificar_windows("Robô em Cooldown ⏳", msg_balao)
                
                # O processador congela aqui
                time.sleep(restante.total_seconds())
                
                logger.info("Cooldown finalizado. Retomando extrações.")
                # 🎈 Notificação: Acordei!
                notificar_windows("Robô Acordou! 🚀", "Cooldown finalizado. Retomando a extração de dados da Ancine.")
            
            # Deleta o caderninho
            os.remove(ARQUIVO_COOLDOWN)

def orquestrar_pipeline():
    logger.info("=== INICIANDO PIPELINE DE DADOS ===")
    verificar_cooldown()
    df_ancine = limpar_dados_ancine(ARQUIVO_ANCINE)
    
    filmes_processados = set()
    if os.path.exists(ARQUIVO_SAIDA):
        df_mestre = pd.read_csv(ARQUIVO_SAIDA, sep=';', dtype=str)
        for _, row in df_mestre.iterrows():
            try:
                ano_lido = int(float(row.get('ANCINE_Ano', 0)))
            except:
                ano_lido = 0
            chave = f"{str(row.get('ANCINE_TITULO_ORIGINAL', '')).strip()}_{ano_lido}"
            filmes_processados.add(chave)
        logger.info(f"{len(filmes_processados)} filmes já processados. Pulando...")
    else:
        df_mestre = pd.DataFrame()

    try:
        for index, row in df_ancine.iterrows():
            titulo = str(row['TITULO_ORIGINAL']).strip()
            ano = int(row['Ano'])
            chave_atual = f"{titulo}_{ano}"
            
            if chave_atual in filmes_processados:
                continue
                
            sucesso = False
            tentativas = 0
            while not sucesso and tentativas < 3:
                try:
                    # Print simples para você ver o progresso no terminal
                    print(f"Extraindo: {titulo} ({ano})") 
                    dados_api = extrair_todas_as_infos(titulo, ano)
                    
                    linha_final = {}
                    for coluna in df_ancine.columns:
                        linha_final[f"ANCINE_{coluna}"] = row[coluna]
                    
                    if dados_api:
                        linha_final.update(dados_api)
                    
                    nova_linha_df = pd.DataFrame([linha_final])
                    df_mestre = pd.concat([df_mestre, nova_linha_df], ignore_index=True)
                    df_mestre.to_csv(ARQUIVO_SAIDA, sep=';', index=False, encoding='utf-8-sig')
                    
                    filmes_processados.add(chave_atual)
                    sucesso = True
                    time.sleep(0.5)

                except LimiteDiarioExcedido:
                    agora = datetime.now()
                    liberacao = agora + timedelta(hours=24)
                    with open(ARQUIVO_COOLDOWN, 'w') as f:
                        f.write(liberacao.isoformat())
                    logger.error("LIMITE DA API OMDB ATINGIDO. Ativando Cooldown.")
                    verificar_cooldown() 
                except Exception as e:
                    tentativas += 1
                    logger.error(f"Erro ao extrair {titulo}. Tentativa {tentativas}. Erro: {e}")
                    if tentativas < 3:
                        time.sleep(60)
                    else:
                        raise SystemExit("Falha em 3 tentativas consecutivas.")

    except KeyboardInterrupt:
        logger.warning("Pipeline abortado pelo usuário (Ctrl+C).")
    except Exception as e:
        logger.critical(f"Falha Crítica no Pipeline: {e}")

if __name__ == "__main__":
    orquestrar_pipeline()