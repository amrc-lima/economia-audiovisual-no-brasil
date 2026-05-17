import os
import requests
import re
import logging
from duckduckgo_search import DDGS
from dotenv import load_dotenv

# ==========================================
# 0. CONFIGURAÇÕES E CHAVES
# ==========================================
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
TMDB_READ_TOKEN = os.getenv('TMDB_READ_TOKEN')
OMDB_API_KEY = os.getenv('OMDB_API_KEY')

class LimiteDiarioExcedido(Exception):
    pass

logger = logging.getLogger('API_Logger')

# ==========================================
# 1. REQUISIÇÃO TRANSPARENTE E SEGURA
# ==========================================
def fazer_requisicao(url, headers=None, tag=""):
    logger.debug(f"Req: {url} {tag}")
    resp = requests.get(url, headers=headers, timeout=10)
    
    if resp.status_code == 429:
        logger.error(f"Rate Limit (429) atingido na API. {tag}")
        raise LimiteDiarioExcedido("Erro 429: Rate Limit")
        
    if resp.status_code == 401 and 'omdbapi' in url:
        try:
            if 'limit' in resp.json().get('Error', '').lower():
                logger.error(f"Limite OMDb atingido detectado no Erro 401! {tag}")
                raise LimiteDiarioExcedido("Limite OMDb atingido!")
        except LimiteDiarioExcedido as e: raise e
        except: pass 

    resp.raise_for_status()
    json_resp = resp.json()
    logger.debug(f"Resp JSON: {str(json_resp)[:150]}... {tag}") 
    return json_resp

# ==========================================
# 2. ENGENHARIA DE TEXTO (NLP BÁSICO)
# ==========================================
def normalizar_titulo(titulo):
    """Resolve apenas problemas estruturais léxicos comuns."""
    t = titulo.upper()
    t = t.replace('&', 'AND')
    t = t.replace("'", "")
    t = re.sub(r'\bIII\b', '3', t)
    t = re.sub(r'\bII\b', '2', t)
    t = re.sub(r'\bIV\b', '4', t)
    return t.strip()

# ==========================================
# 3. O AVALIADOR DE CANDIDATOS (O CÉREBRO)
# ==========================================
def avaliar_candidatos(resultados, ano_ancine, nome_pesquisa):
    """Filtra o lixo e garante que o filme pertence ao ano certo."""
    if not resultados: 
        return None
    
    candidatos_ordenados = sorted(resultados, key=lambda x: x.get('vote_count', 0), reverse=True)
    nome_pesquisa_limpo = re.sub(r'[^A-Z0-9]', '', nome_pesquisa.upper())
    
    for cand in candidatos_ordenados:
        data_tmdb = cand.get('release_date', '')
        ano_tmdb = int(data_tmdb[:4]) if data_tmdb else 0
        votos = cand.get('vote_count', 0)
        titulo_tmdb = re.sub(r'[^A-Z0-9]', '', cand.get('original_title', '').upper())
        
        # REGRA 1 (Relançamentos como Titanic/Avatar): 
        # Só ignora o ano SE o título for EXATAMENTE IGUAL e tiver mais de 1000 votos (Mundialmente Famoso)
        if titulo_tmdb == nome_pesquisa_limpo and votos > 1000:
            return cand
            
        # REGRA 2 (A TOLERÂNCIA DE 1 ANO): 
        # Pega a diferença do Fuso Horário de estreia (ex: Saiu nos EUA final de 2019 e no BR início de 2020)
        if ano_tmdb and abs(ano_tmdb - ano_ancine) <= 1:
            if votos >= 5 or titulo_tmdb == nome_pesquisa_limpo:
                return cand
                
    return None

# ==========================================
# 4. ORÁCULO DE BUSCA SEMÂNTICA (DUCKDUCKGO)
# ==========================================
def buscar_imdb_no_ddg(nome_sujo, ano, tag):
    logger.info(f"[Oráculo DDG] Buscando Semântica de: '{nome_sujo}' ({ano}) {tag}")
    query = f"site:imdb.com/title {nome_sujo} {ano} movie"
    
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, max_results=3))
            for res in resultados:
                url = res.get('href', '')
                match = re.search(r'(tt\d+)', url)
                if match:
                    imdb_id = match.group(1)
                    logger.info(f"   ↳ [Oráculo] Achou o ID: {imdb_id} {tag}")
                    return imdb_id
    except Exception as e:
        logger.warning(f"   ↳ [Oráculo] Falhou: {e} {tag}")
    return None

# ==========================================
# 5. MOTOR PRINCIPAL DE EXTRAÇÃO
# ==========================================
def extrair_todas_as_infos(nome_filme, ano):
    headers_tmdb = {"accept": "application/json", "Authorization": f"Bearer {TMDB_READ_TOKEN}"}
    dados_completos = {}
    
    nome_pesquisa = normalizar_titulo(nome_filme)
    tag = f"@@{nome_filme}@@" 
    
    try:
        filme_valido = None
        imdb_id_oraculo = None
        
        # 🟢 CAMADA 1: Busca Única no TMDB (O Avaliador resolve a tolerância de 1 ano)
        logger.info(f"[Busca TMDB] Procurando: {nome_pesquisa} {tag}")
        url_busca = f"https://api.themoviedb.org/3/search/movie?query={nome_pesquisa}&language=pt-BR"
        resp_busca = fazer_requisicao(url_busca, headers=headers_tmdb, tag=tag)
        
        filme_valido = avaliar_candidatos(resp_busca.get('results', []), ano, nome_pesquisa)
        if filme_valido:
            logger.info(f"[TMDB] Aprovado na Régua de 1 Ano: {filme_valido.get('title')} | Votos: {filme_valido.get('vote_count')} {tag}")

        # 🟣 CAMADA 2: Oráculo (DuckDuckGo)
        if not filme_valido:
            imdb_id_oraculo = buscar_imdb_no_ddg(nome_pesquisa, ano, tag)
            if not imdb_id_oraculo:
                logger.error(f"[FALHA TOTAL] O filme não pôde ser encontrado. {tag}")
                return {}

        # -----------------------------
        # CAPTURA DE DETALHES GERAIS
        # -----------------------------
        imdb_id_final = None
        
        if filme_valido:
            filme_id = filme_valido['id']
            url_detalhes = f"https://api.themoviedb.org/3/movie/{filme_id}?language=pt-BR"
            detalhes = fazer_requisicao(url_detalhes, headers=headers_tmdb, tag=tag)
            
            for chave, valor in detalhes.items():
                if isinstance(valor, (dict, list)): valor = str(valor)
                dados_completos[f"TMDB_{chave}"] = valor
                
            imdb_id_final = detalhes.get('imdb_id')
            
        elif imdb_id_oraculo:
            imdb_id_final = imdb_id_oraculo
        
        # BATE NO OMDB!
        if imdb_id_final:
            logger.info(f"[OMDB] Buscando dados para IMDb ID: {imdb_id_final} {tag}")
            url_omdb = f"http://www.omdbapi.com/?i={imdb_id_final}&apikey={OMDB_API_KEY}"
            resp_omdb = fazer_requisicao(url_omdb, tag=tag)
            
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
        logger.error(f"Erro Crítico: {e} {tag}")
        return dados_completos