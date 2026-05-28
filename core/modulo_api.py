import os
import requests
import re
import time
import logging
from google import genai
from dotenv import load_dotenv

# ==========================================
# 0. CONFIGURAÇÕES E CHAVES
# ==========================================
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

TMDB_READ_TOKEN = os.getenv('TMDB_READ_TOKEN')
OMDB_API_KEY = os.getenv('OMDB_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

class LimiteDiarioExcedido(Exception): pass
logger = logging.getLogger('API_Logger')

if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None

# ==========================================
# 1. REQUISIÇÃO TRANSPARENTE E SEGURA
# ==========================================
def fazer_requisicao(url, headers=None, tag=""):
    logger.debug(f"Req GET -> {url} {tag}")
    resp = requests.get(url, headers=headers, timeout=60) # Paciência de Sênior
    
    if resp.status_code == 429:
        logger.error(f"Rate Limit (429) atingido na API TMDB/OMDB. {tag}")
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
# 2. AVALIADOR DE CANDIDATOS E LIMPEZA
# ==========================================
def normalizar_titulo(titulo):
    """
    Normaliza a estrutura léxica do título original.
    Remove inconsistências de formatação para otimizar o pareamento na API.
    """
    t = titulo.upper()
    
    # Substituições essenciais
    t = t.replace('&', 'AND')
    t = t.replace("'", "")
    t = t.replace("#", "") # Remove hashtags que quebram as URLs (Fragment HTTP)
    
    # Tratamento de algarismos romanos de sequências
    t = re.sub(r'\bIII\b', '3', t)
    t = re.sub(r'\bII\b', '2', t)
    t = re.sub(r'\bIV\b', '4', t)
    
    return t.strip()

def avaliar_candidatos(resultados, ano_ancine, nome_pesquisa):
    """Filtra o lixo priorizando o ano correto (confiando no motor do TMDB) e entende relançamentos."""
    if not resultados: return None
    
    # O Pulo do Gato: O filme certo quase sempre é o mais votado da lista de resultados.
    candidatos_ordenados = sorted(resultados, key=lambda x: x.get('vote_count', 0), reverse=True)
    nome_pesquisa_limpo = re.sub(r'[^A-Z0-9]', '', nome_pesquisa.upper())
    
    # 🥇 PRIORIDADE 1: Janela de Lançamento (Abolimos o limite de votos e checagem de string!)
    for cand in candidatos_ordenados:
        data_tmdb = cand.get('release_date', '')
        ano_tmdb = int(data_tmdb[:4]) if data_tmdb else 0
        
        # Se a data bate com a tolerância de 2 anos, aceita na hora.
        if ano_tmdb and abs(ano_tmdb - ano_ancine) <= 2:
            return cand

    # 🥈 PRIORIDADE 2: Relançamentos e Clássicos Absolutos (Titanic, Avatar)
    # Aqui mantemos a checagem de string/votos porque a data já falhou na prioridade 1.
    for cand in candidatos_ordenados:
        votos = cand.get('vote_count', 0)
        titulo_tmdb = re.sub(r'[^A-Z0-9]', '', cand.get('original_title', '').upper())
        
        if titulo_tmdb == nome_pesquisa_limpo and votos > 1000:
            return cand
            
    return None

# ==========================================
# 3. O ORÁCULO DE IA (GEMINI 3.1 FLASH LITE - 500 RPD)
# ==========================================
def corrigir_titulo_via_gemini(nome_sujo, ano, tag):
    if not gemini_client:
        logger.warning(f"[Oráculo] Chave do Gemini não configurada. {tag}")
        return None
        
    logger.info(f"[Oráculo Gemini] Analisando o typo do governo para: '{nome_sujo}' {tag}")
    
    prompt = f"""
    Aja como um banco de dados de cinema.
    O governo brasileiro listou um filme como "{nome_sujo}" no ano {ano}.
    Este título pode conter erros ortográficos, numerais errados ou formatação suja.
    Sua tarefa:
    1. Descubra o filme real.
    2. Devolva APENAS o Título Original do filme, no idioma do país em que ele foi produzido.
    3. REGRA CRÍTICA: Se for um filme brasileiro, mantenha o título em Português. NÃO TRADUZA PARA INGLÊS.
    4. Responda apenas com o nome do filme, sem aspas, sem pontos e sem explicações.
    """
    
    # 💡 Usando o ÚNICO modelo com 500 de cota diária (provado pelo painel)
    modelo_oficial = 'gemini-3.1-flash-lite'
    
    tentativas = 0
    
    while tentativas < 3:
        try:
            response = gemini_client.models.generate_content(
                model=modelo_oficial,
                contents=prompt,
            )
            titulo_limpo = response.text.strip()
            logger.info(f"   ↳ [Oráculo - {modelo_oficial}] A IA limpou o título para: '{titulo_limpo}' {tag}")
            
            # Pausa obrigatória de 4 segundos (Garante que nunca passa de 15 RPM)
            time.sleep(4) 
            return titulo_limpo

        except Exception as erro_ia:
            erro_str = str(erro_ia)
            
            if "429" in erro_str or "Quota" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
                if "PerDay" in erro_str or "GenerateRequestsPerDay" in erro_str:
                    logger.error(f"   [Oráculo] Limite DIÁRIO (500) do {modelo_oficial} esgotado! {tag}")
                    return None # Abandona a IA e deixa o Main.py entrar em Cooldown
                        
                else:
                    # Se estourar a velocidade (RPM), pausa 60s
                    logger.warning(f"   [Oráculo] Limite por MINUTO (RPM) atingido. Esfriando por 60s... {tag}")
                    time.sleep(60)
                    tentativas += 1
            else:
                logger.warning(f"   ↳ [Oráculo Gemini] Erro interno inesperado: {erro_ia} {tag}")
                return None
                
    return None
# ==========================================
# 4. MOTOR PRINCIPAL DE EXTRAÇÃO
# ==========================================
def extrair_todas_as_infos(nome_filme, ano):
    headers_tmdb = {"accept": "application/json", "Authorization": f"Bearer {TMDB_READ_TOKEN}"}
    dados_completos = {}
    
    nome_pesquisa = normalizar_titulo(nome_filme)
    tag = f"@@{nome_filme}@@" 
    
    try:
        filme_valido = None
        
        # 🟢 CAMADA 1: Busca TMDB Direta
        logger.info(f"[Busca TMDB] Procurando original: {nome_pesquisa} {tag}")
        url_busca = f"https://api.themoviedb.org/3/search/movie?query={nome_pesquisa}&language=pt-BR"
        resp_busca = fazer_requisicao(url_busca, headers=headers_tmdb, tag=tag)
        
        filme_valido = avaliar_candidatos(resp_busca.get('results', []), ano, nome_pesquisa)
        if filme_valido:
            logger.info(f"[TMDB] Aprovado na Camada 1: {filme_valido.get('title')} {tag}")
            
        # 🟣 CAMADA 2: Oráculo (LLM Assisted ETL)
        if not filme_valido:
            titulo_ia_bruto = corrigir_titulo_via_gemini(nome_pesquisa, ano, tag)
            
            if titulo_ia_bruto:
                # 💡 A SUA SACADA: Sanitiza também o que a IA respondeu!
                titulo_ia = normalizar_titulo(titulo_ia_bruto)
                
                if titulo_ia != nome_pesquisa:
                    logger.info(f"[Busca TMDB] Retentando com Título Limpo pela IA: {titulo_ia} {tag}")
                    url_busca_ia = f"https://api.themoviedb.org/3/search/movie?query={titulo_ia}&language=pt-BR"
                    resp_busca_ia = fazer_requisicao(url_busca_ia, headers=headers_tmdb, tag=tag)
                    
                    filme_valido = avaliar_candidatos(resp_busca_ia.get('results', []), ano, titulo_ia)
                    if filme_valido:
                        logger.info(f"[TMDB] Aprovado após Correção IA: {filme_valido.get('title')} {tag}")

        if not filme_valido:
            logger.error(f"[FALHA TOTAL] Nenhuma camada encontrou o filme. {tag}")
            return {}

        # -----------------------------
        # CAPTURA DE DETALHES GERAIS (TMDB + OMDb)
        # -----------------------------
        filme_id = filme_valido['id']
        url_detalhes = f"https://api.themoviedb.org/3/movie/{filme_id}?language=pt-BR"
        detalhes = fazer_requisicao(url_detalhes, headers=headers_tmdb, tag=tag)
        
        for chave, valor in detalhes.items():
            dados_completos[f"TMDB_{chave}"] = valor
            
        imdb_id_final = detalhes.get('imdb_id')
        
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
                    dados_completos[f"OMDB_{chave}"] = valor

        return dados_completos
        
    except LimiteDiarioExcedido as e: 
        raise e
    except Exception as e:
        logger.error(f"Erro Crítico Geral: {e} {tag}")
        return dados_completos