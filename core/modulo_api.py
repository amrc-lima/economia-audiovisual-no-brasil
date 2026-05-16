import os
import requests
import re
import logging
from googlesearch import search
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

TMDB_READ_TOKEN = os.getenv('TMDB_READ_TOKEN')
OMDB_API_KEY = os.getenv('OMDB_API_KEY')

class LimiteDiarioExcedido(Exception):
    pass

# Configuração do Logger local do módulo
logger = logging.getLogger('API_Logger')

def fazer_requisicao(url, headers=None):
    logger.debug(f"Req: {url}")
    resp = requests.get(url, headers=headers, timeout=10)
    
    if resp.status_code == 429:
        logger.error("Rate Limit (429) atingido na API.")
        raise LimiteDiarioExcedido("Erro 429: Rate Limit")
        
    # 💡 O NOVO DRIBLE: Se o OMDb der 401, a gente lê o erro antes de o Python surtar
    if resp.status_code == 401 and 'omdbapi' in url:
        try:
            erro_json = resp.json()
            if 'limit' in erro_json.get('Error', '').lower():
                logger.error("Limite OMDb atingido detectado no Erro 401!")
                raise LimiteDiarioExcedido("Limite de 1000 requisições do OMDb atingido!")
        except LimiteDiarioExcedido as e:
            raise e
        except:
            pass # Se for outro erro, deixa o raise_for_status pegar normalmente

    resp.raise_for_status() # O Leão de chácara volta a atuar aqui
    json_resp = resp.json()
    logger.debug(f"Resp JSON: {str(json_resp)[:500]}...") 
    return json_resp

def buscar_imdb_no_google(nome_sujo, ano):
    logger.info(f"[Oráculo] Perguntando ao Google sobre: '{nome_sujo}' ({ano})")
    query = f'site:imdb.com/title/ "{nome_sujo}" {ano} movie'
    try:
        for url in search(query, num_results=3):
            match = re.search(r'(tt\d+)', url)
            if match:
                imdb_id = match.group(1)
                logger.info(f"   ↳ [Oráculo] Achou o ID: {imdb_id}")
                return imdb_id
    except Exception as e:
        logger.warning(f"   ↳ [Oráculo] Falhou: {e}")
    return None

def extrair_todas_as_infos(nome_filme, ano):
    headers_tmdb = {"accept": "application/json", "Authorization": f"Bearer {TMDB_READ_TOKEN}"}
    dados_completos = {}
    nome_pesquisa = nome_filme.strip()
    
    try:
        filme_valido = None
        imdb_id_oraculo = None
        
        # 🟢 CAMADA 1: Busca Exata
        logger.info(f"[T1] Tentativa de busca exata no TMDB: {nome_pesquisa}")
        url_t1 = f"https://api.themoviedb.org/3/search/movie?query={nome_pesquisa}&primary_release_year={ano}&language=pt-BR"
        resp_t1 = fazer_requisicao(url_t1, headers=headers_tmdb)
        
        # Só aceita se o filme for 'famoso' (Mais de 50 votos) para evitar curtas-metragens obscuros com o mesmo nome
        if resp_t1.get('results'):
            for candidato in resp_t1['results']:
                if candidato.get('vote_count', 0) > 50:
                    filme_valido = candidato
                    logger.info(f"[T1] Sucesso: {filme_valido.get('title')} (ID: {filme_valido['id']})")
                    break
            
        # 🟡 CAMADA 2: Sem Ano
        if not filme_valido:
            logger.info(f"[T2] Tentativa sem ano: {nome_pesquisa}")
            url_t2 = f"https://api.themoviedb.org/3/search/movie?query={nome_pesquisa}&language=pt-BR"
            resp_t2 = fazer_requisicao(url_t2, headers=headers_tmdb)
            if resp_t2.get('results'):
                for candidato in resp_t2['results'][:5]:
                    data_tmdb = candidato.get('release_date', '')
                    if data_tmdb and abs(int(data_tmdb[:4]) - ano) <= 1 and candidato.get('vote_count', 0) > 50:
                        filme_valido = candidato
                        logger.info(f"[T2] Sucesso (Aprovado na janela de 1 ano): {filme_valido.get('title')}")
                        break

        # 🟠 CAMADA 3: Machado (Franquia)
        if not filme_valido and (":" in nome_pesquisa or "-" in nome_pesquisa):
            nome_curto = nome_pesquisa.replace("-", ":").split(":")[0].strip()
            logger.info(f"[T3] Tentativa cortando subtítulo: {nome_curto}")
            url_t3 = f"https://api.themoviedb.org/3/search/movie?query={nome_curto}&language=pt-BR"
            resp_t3 = fazer_requisicao(url_t3, headers=headers_tmdb)
            if resp_t3.get('results'):
                for candidato in resp_t3['results'][:10]:
                    data_tmdb = candidato.get('release_date', '')
                    if data_tmdb and abs(int(data_tmdb[:4]) - ano) <= 1 and candidato.get('vote_count', 0) > 50:
                        filme_valido = candidato
                        logger.info(f"[T3] Sucesso com nome curto: {filme_valido.get('title')}")
                        break

        # 🟣 CAMADA 4: Oráculo
        if not filme_valido:
            imdb_id_oraculo = buscar_imdb_no_google(nome_pesquisa, ano)
            if not imdb_id_oraculo:
                logger.error(f"[FALHA] Nenhuma camada encontrou o filme {nome_pesquisa}.")
                return {}

        # -----------------------------
        # CAPTURA DE DETALHES GERAIS
        # -----------------------------
        imdb_id_final = None
        
        if filme_valido:
            filme_id = filme_valido['id']
            url_detalhes = f"https://api.themoviedb.org/3/movie/{filme_id}?language=pt-BR"
            detalhes = fazer_requisicao(url_detalhes, headers=headers_tmdb)
            
            for chave, valor in detalhes.items():
                if isinstance(valor, (dict, list)): valor = str(valor)
                dados_completos[f"TMDB_{chave}"] = valor
                
            imdb_id_final = detalhes.get('imdb_id')
            
        elif imdb_id_oraculo:
            imdb_id_final = imdb_id_oraculo
        
        # BATE NO OMDB COM O ID DO IMDB ACHADO!
        if imdb_id_final:
            logger.info(f"[OMDB] Buscando dados para IMDb ID: {imdb_id_final}")
            url_omdb = f"http://www.omdbapi.com/?i={imdb_id_final}&apikey={OMDB_API_KEY}"
            resp_omdb = fazer_requisicao(url_omdb)
            
            if resp_omdb.get('Response') == 'False' and 'limit' in resp_omdb.get('Error', '').lower():
                raise LimiteDiarioExcedido("Limite de 1000 requisições do OMDb atingido!")
            
            if resp_omdb.get('Response') == 'True':
                for chave, valor in resp_omdb.items():
                    if chave == 'Ratings' and isinstance(valor, list):
                        for avaliacao in valor:
                            if avaliacao.get('Source') == 'Rotten Tomatoes':
                                dados_completos["OMDB_RottenTomatoes"] = avaliacao.get('Value', '').replace('%', '')
                    if isinstance(valor, (dict, list)): valor = str(valor)
                    dados_completos[f"OMDB_{chave}"] = valor

        return dados_completos
        
    except LimiteDiarioExcedido as e:
        raise e
    except Exception as e:
        logger.error(f"Erro Crítico ao processar '{nome_pesquisa}': {e}")
        return dados_completos