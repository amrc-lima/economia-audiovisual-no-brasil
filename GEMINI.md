# Project Gemini - A Engenharia Econômica do Cinema Nacional

Este documento serve como a fonte da verdade para a arquitetura, convenções e fluxos de trabalho do projeto, cobrindo todos os módulos e diretórios.

## 🏗️ Estrutura Completa do Projeto

O projeto é um ecossistema de dados focado na auditoria econômica do audiovisual brasileiro, estruturado da seguinte forma:

### 📂 Diretórios e Funções
- **`core/` (The Engine):** Contém a lógica de processamento ETL, integração com APIs (TMDB, OMDb) e o "Oráculo" (Google Gemini).
- **`data/` (Lakehouse):** Armazena o banco de dados mestre (`master_filmes_db.parquet`), scripts de auditoria de qualidade (`issues.py`) e arquivos de controle (`api_cooldown.txt`).
- **`allcsv/` (Raw Data):** Repositório de arquivos CSV brutos da ANCINE. Contém o script `!run.py` para redução de volume e `headers.json` com metadados dos arquivos.
- **`smallcsv/` (Dev/Sandbox):** Versões reduzidas (primeiras 101 linhas) de todos os CSVs para testes rápidos e desenvolvimento sem sobrecarga de memória.
- **`textos/` (Research):** Documentos de fundamentação teórica sobre fomento, regulação e economia do audiovisual. Base para a narrativa do dashboard.
- **`htmls/` (Archive):** Cópias locais de páginas do BoxOfficeMojo e Rotten Tomatoes para referência de estrutura e validação offline.
- **`logs/` (Observability):** Logs detalhados de execução, particionados por data.

## ⚙️ Componentes e Scripts

1.  **Orquestrador (`core/main.py`):**
    - Ponto de entrada do pipeline. Gerencia o fluxo de sucesso/falha e persistência atômica no Parquet.
2.  **Motor de API (`core/modulo_api.py`):**
    - Implementa busca multi-camada. Se a busca direta falhar, aciona o `gemini-3.1-flash-lite` para "limpar" títulos com erros de digitação governamentais.
3.  **Auditoria (`data/issues.py`):**
    - Monitora o `master_filmes_db.parquet`, remove registros corrompidos e gera relatórios de "quarentena".
4.  **Utilitário de Dados (`allcsv/!run.py`):**
    - Varre o `allcsv/`, extrai cabeçalhos, conta linhas e gera o `smallcsv/`. Essencial para manter o ambiente de desenvolvimento ágil.

## 📜 Convenções e Padrões

### Rastreabilidade e Debug
- **Tagging:** O uso de `@@NOME_DO_FILME@@` em todos os logs é obrigatório. Isso permite que o `issues.py` recupere exatamente o que aconteceu com um filme que falhou.
- **Dual Logging:** Mensagens críticas aparecem no terminal; detalhes técnicos vão para os arquivos `.log`.

### Persistência e Segurança
- **Atomic Writes:** Sempre salvar em arquivos `.temp` antes de substituir o original (Parquet/JSON).
- **API Cooldown:** Bloqueio automático por 24h ao detectar limite do OMDb ou Gemini, persistido em `api_cooldown.txt`.
- **Secrets:** Nunca commitar o arquivo `.env`.

### Qualidade de Dados (DQ)
- **Schema Enforcement:** Todos os campos no Parquet são forçados como string para evitar quebras por tipos inferidos incorretamente pelo pandas.
- **Normalização Léxica:** Títulos são limpos (remoção de caracteres especiais, conversão de algarismos romanos) antes de qualquer requisição de API.

## 🚀 Fluxo de Operação Standard

1.  **Ingestão:** Coloque novos CSVs em `allcsv/`.
2.  **Preparação:** Rode `allcsv/!run.py` para atualizar o `smallcsv/` e `headers.json`.
3.  **Processamento:** Rode `core/main.py` para enriquecer a base com dados internacionais.
4.  **Validação:** Rode `data/issues.py` para garantir que apenas dados íntegros permaneçam no banco de produção.
5.  **Visualização:** O Power BI consome diretamente o `data/master_filmes_db.parquet`.
