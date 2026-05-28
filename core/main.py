import os
import sys
import logging
import ctypes
import pandas as pd
import time
from datetime import datetime, timedelta

from modulo_ancine import limpar_dados_ancine
from modulo_api import extrair_todas_as_infos, LimiteDiarioExcedido

def solicitar_acao_usuario(titulo_filme):
    if hasattr(sys, 'stdin') and sys.stdin and sys.stdin.isatty():
        return input(f"\n🚨 [C] Tentar Novamente, [P] Pular filme ou [S] Salvar e Sair? ").strip().upper()
    else:
        texto = f"Atenção, Mestre!\n\nO filme '{titulo_filme}' falhou 3 vezes.\n\n[Repetir] = Tentar novamente\n[Ignorar] = Pular filme\n[Anular] = Desligar robô"
        resposta = ctypes.windll.user32.MessageBoxW(0, texto, "🚨 Alerta", 0x02 | 0x30 | 0x40000)
        if resposta == 4: return 'C'
        elif resposta == 5: return 'P'
        else: return 'S'

# --- CAMINHOS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQUIVO_ANCINE = os.path.join(BASE_DIR, 'data', 'lancamentos-comerciais-por-distribuidoras.csv')
ARQUIVO_PARQUET = os.path.join(BASE_DIR, 'data', 'master_filmes_db.parquet') # AGORA É PARQUET
ARQUIVO_COOLDOWN = os.path.join(BASE_DIR, 'data', 'api_cooldown.txt')
PASTA_LOGS = os.path.join(BASE_DIR, 'logs')

ESQUEMA_OFICIAL = [
    "ANCINE_DATA_LANCAMENTO_OBRA", "ANCINE_TITULO_ORIGINAL", "ANCINE_CPB_ROE", "ANCINE_TIPO_OBRA", 
    "ANCINE_PAIS_OBRA", "ANCINE_PUBLICO_TOTAL", "ANCINE_RENDA_TOTAL", "ANCINE_RAZAO_SOCIAL_DISTRIBUIDORA", 
    "ANCINE_REGISTRO_DISTRIBUIDORA", "ANCINE_CNPJ_DISTRIBUIDORA", "ANCINE_Ano", "TMDB_adult", 
    "TMDB_alternative_titles", "TMDB_backdrop_path", "TMDB_belongs_to_collection", "TMDB_budget", 
    "TMDB_credits", "TMDB_external_ids", "TMDB_genres", "TMDB_homepage", "TMDB_id", "TMDB_images", 
    "TMDB_imdb_id", "TMDB_keywords", "TMDB_origin_country", "TMDB_original_language", "TMDB_original_title", 
    "TMDB_overview", "TMDB_popularity", "TMDB_poster_path", "TMDB_production_companies", 
    "TMDB_production_countries", "TMDB_release_date", "TMDB_release_dates", "TMDB_revenue", "TMDB_runtime", 
    "TMDB_similar", "TMDB_softcore", "TMDB_spoken_languages", "TMDB_status", "TMDB_tagline", "TMDB_title", 
    "TMDB_translations", "TMDB_video", "TMDB_videos", "TMDB_vote_average", "TMDB_vote_count", "OMDB_Actors", 
    "OMDB_Awards", "OMDB_BoxOffice", "OMDB_Country", "OMDB_DVD", "OMDB_Director", "OMDB_Episode", 
    "OMDB_Error", "OMDB_Genre", "OMDB_Language", "OMDB_Metascore", "OMDB_Plot", "OMDB_Poster", 
    "OMDB_Production", "OMDB_Rated", "OMDB_Ratings", "OMDB_Released", "OMDB_Response", "OMDB_RottenTomatoes", 
    "OMDB_Runtime", "OMDB_Season", "OMDB_Title", "OMDB_Type", "OMDB_Website", "OMDB_Writer", "OMDB_Year", 
    "OMDB_imdbID", "OMDB_imdbRating", "OMDB_imdbVotes", "OMDB_seriesID"
]

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s', handlers=[logging.FileHandler(arquivo_log, encoding='utf-8')])
logger = logging.getLogger(__name__)

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

def verificar_cooldown():
    if os.path.exists(ARQUIVO_COOLDOWN):
        with open(ARQUIVO_COOLDOWN, 'r') as f: cooldown_str = f.read().strip()
        if cooldown_str:
            cooldown_end = datetime.fromisoformat(cooldown_str)
            agora = datetime.now()
            if agora < cooldown_end:
                restante = cooldown_end - agora
                print(f"\n[{agora.strftime('%H:%M:%S')}] ⏳ COOLDOWN ATIVO")
                logger.warning(f"COOLDOWN ATIVO. Pausando robô até {cooldown_end.strftime('%d/%m %H:%M:%S')}")
                time.sleep(restante.total_seconds())
                logger.info("Cooldown finalizado. Retomando extrações.")
            os.remove(ARQUIVO_COOLDOWN)

def orquestrar_pipeline():
    print(f"\n{'='*50}\n🚀 INÍCIO DO PIPELINE\n{'='*50}\n")
    logger.info("=== INICIANDO PIPELINE DE DADOS (PARQUET) ===")
    
    verificar_cooldown()
    df_ancine = limpar_dados_ancine(ARQUIVO_ANCINE)
    filmes_processados = set()
    
    # 🗄️ CHECAGEM NO PARQUET
    if os.path.exists(ARQUIVO_PARQUET):
        print(f"📁 Banco de dados Parquet encontrado. Lendo histórico...")
        df_mestre = pd.read_parquet(ARQUIVO_PARQUET, engine='pyarrow')
        for _, row in df_mestre.iterrows():
            try: ano_lido = int(float(row.get('ANCINE_Ano', 0)))
            except: ano_lido = 0
            chave = f"{str(row.get('ANCINE_TITULO_ORIGINAL', '')).strip()}_{ano_lido}"
            filmes_processados.add(chave)
        print(f"✅ {len(filmes_processados)} filmes já processados. Pulando...\n")
    else:
        print("📁 Criando Master Database (.parquet) do zero em /data...\n")
        df_mestre = pd.DataFrame(columns=ESQUEMA_OFICIAL)

    print(f"🔍 Baixando TUDO das APIs para os filmes restantes...")
    
    try:
        for index, row in df_ancine.iterrows():
            titulo = str(row['TITULO_ORIGINAL']).strip()
            ano = int(row['Ano'])
            chave_atual = f"{titulo}_{ano}"
            tag = f"@@{titulo}@@"
            
            if chave_atual in filmes_processados: continue
                
            sucesso = False
            tentativas = 0
            
            while not sucesso and tentativas < 3:
                try:
                    hora_atual = datetime.now().strftime('%H:%M:%S')
                    print(f"[{hora_atual}] Extraindo: {titulo} ({ano})")
                    logger.info(f"Iniciando extração para: {titulo} ({ano}) {tag}")
                    
                    dados_api = extrair_todas_as_infos(titulo, ano)
                    
                    # 💡 A SUA REGRA: Se a API retornou vazio ou sem TMDB_id, não fazemos NADA!
                    if not dados_api or not dados_api.get("TMDB_id"):
                        logger.warning(f"Filme rejeitado ou não encontrado. Ignorando salvamento para tentar na próxima execução. {tag}")
                        sucesso = True # Quebra o loop de retentativas (pois a API já exauriu)
                        break # Pula fora do While e NÃO adiciona no `filmes_processados`
                    
                    linha_final = {}
                    for coluna in df_ancine.columns:
                        linha_final[f"ANCINE_{coluna}"] = row[coluna]
                    
                    linha_final.update(dados_api)
                    
                    # 💡 EVOLUÇÃO PARQUET: Mantém tipos nativos (listas/dicts) e limpa apenas strings
                    linha_padronizada = {}
                    for col in ESQUEMA_OFICIAL:
                        valor = linha_final.get(col, "")
                        if isinstance(valor, str):
                            valor = valor.strip()
                        linha_padronizada[col] = valor

                    nova_linha_df = pd.DataFrame([linha_padronizada])
                    
                    # 🗄️ ESCRITA ATÔMICA NO PARQUET (Só chega aqui se o filme for um SUCESSO)
                    df_mestre = pd.concat([df_mestre, nova_linha_df], ignore_index=True)
                    arquivo_temp = ARQUIVO_PARQUET + ".temp"
                    df_mestre.to_parquet(arquivo_temp, engine='pyarrow', index=False)
                    os.replace(arquivo_temp, ARQUIVO_PARQUET)
                    
                    # Como teve sucesso, anotamos que ele tá pronto!
                    filmes_processados.add(chave_atual)
                    sucesso = True
                    logger.info(f"Salvo no banco Parquet com sucesso. {tag}")
                    time.sleep(0.5)

                except LimiteDiarioExcedido:
                    agora = datetime.now()
                    with open(ARQUIVO_COOLDOWN, 'w') as f: f.write((agora + timedelta(hours=24)).isoformat())
                    print(f"\n🚨 [{agora.strftime('%H:%M:%S')}] LIMITE DA API OMDb ATINGIDO!")
                    logger.error(f"Limite da API atingido. Entrando em Cooldown. {tag}")
                    verificar_cooldown() 
                    
                except Exception as e:
                    tentativas += 1
                    logger.error(f"Erro na extração de {titulo}: {e} {tag}")
                    if tentativas < 3:
                        time.sleep(60) 
                    else:
                        comando = solicitar_acao_usuario(titulo)
                        if comando == 'C': tentativas = 0
                        elif comando == 'P': sucesso = True
                        else: raise SystemExit("Desligado pelo usuário via Popup.")

    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🛑 Interrompido manualmente (Ctrl+C).")
        logger.warning("Pipeline abortado pelo usuário (Ctrl+C).")
    except Exception as e:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ❌ Erro crítico inesperado: {e}")
        logger.critical(f"Falha Crítica no Pipeline: {e}")

if __name__ == "__main__":
    orquestrar_pipeline()