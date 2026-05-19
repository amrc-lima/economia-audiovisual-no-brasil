# 🎬 PROJETO: A Engenharia Econômica e o Valor do Cinema Nacional
**Data Analytics, Inteligência Competitiva e a Análise de Assimetrias no Mercado Audiovisual**

---

## 📌 1. Antecedentes e Contexto
O debate público sobre a indústria cinematográfica brasileira é frequentemente pautado por desinformação e desconhecimento sobre o real impacto da economia criativa. O senso comum dita que "o baixo consumo do cinema nacional ocorre por falta de apelo orgânico" e que o fomento público se resume a um "gasto sem retorno". 

No entanto, à luz da **Teoria do Desejo Mimético de René Girard**, compreende-se que a escolha do consumidor não é estritamente autônoma, mas fortemente mediada pelos modelos de distribuição e disponibilidade de prateleira. Quando uma rede multiplex destina 85% de suas salas a um único filme estrangeiro, configura-se uma severa **Falha de Mercado (Market Failure)** e uma assimetria competitiva (*Dumping*). Neste cenário de oligopólio, a força da distribuição acaba por ditar o que o público deve desejar consumir.

Este projeto visa auditar o ecossistema audiovisual brasileiro entre **2015 e 2025** através da Ciência e Engenharia de Dados. O objetivo é provar, por meio de indicadores econômicos claros (**ROI, Geração de Empregos, Market Share e Matching de Investimentos**), que o cinema nacional é uma indústria de altíssimo valor agregado, e demonstrar como mecanismos regulatórios são essenciais para garantir a pluralidade e a livre concorrência no setor.

## 🏛️ 2. O Ecossistema de Apoio (A Engenharia Institucional)
Longe de ser apenas um "repasse de verbas", o fomento ao audiovisual brasileiro é uma engrenagem sofisticada que envolve os três poderes da República em todas as esferas:

*   **Poder Executivo (O Motor Logístico e Financeiro):** Atua via Fundo Setorial do Audiovisual (FSA), que funciona como *Venture Capital* (Capital Semente). Grande parte desse fundo é composta pela **CONDECINE** (taxa cobrada de superproduções estrangeiras e das empresas de telecomunicações). Além disso, Municípios e Estados operam via **Film Commissions**, atraindo filmagens que injetam milhões na infraestrutura, hotelaria, transporte e marcenaria local.
*   **Poder Legislativo (A Regulação Antitruste):** O Congresso Nacional desenhou a **Cota de Tela** e a **Lei do SeAC (TV Paga)** como leis de regulação antitruste para combater o monopólio de telas e garantir prateleira mínima para o produto nacional. Ademais, estruturaram leis de renúncia fiscal descentralizadas (ICMS nos Estados; ISS e IPTU nos Municípios).
*   **Poder Judiciário (O Fiador):** O Supremo Tribunal Federal (STF) validou, em repetidas ADPFs e ADIs, a constitucionalidade das cotas e das taxas setoriais, protegendo o mercado interno contra as pressões de *majors* transnacionais.

## ⚖️ 3. Metodologia: Remoção de Viés e a "Grama do Vizinho"
Para garantir o rigor estatístico desta análise e evitar o viés de confirmação, foi estabelecida uma **Regra de Exclusão de Outliers**. Filmes nacionalmente aclamados e inquestionáveis (as "cartas coringas" dos críticos) como *Cidade de Deus*, *Tropa de Elite (1 e 2)* e *O Auto da Compadecida* foram **removidos do dataset**. 

O objetivo é auditar a qualidade da **média** do cinema nacional em comparação à **média** dos blockbusters enlatados (ex: *Marvel, Transformers, Pânico, Velozes e Furiosos*). Para chancelar a qualidade de forma imparcial, o projeto consome APIs de avaliação internacional (**Rotten Tomatoes e Metacritic** via OMDb API), comprovando que a crítica especializada estrangeira avalia o cinema brasileiro independente com notas substancialmente superiores às dos produtos hegemônicos estrangeiros.

## 🗄️ 4. Arquitetura do Data Lake (Single Source of Truth)
O projeto adota uma esteira de **Raw Ingestion (Ingestão Bruta Constante)**, extraindo mais de 70 colunas de metadados de APIs globais para compor um *Data Warehouse* local, garantindo análises multidimensionais sem necessidade de reprocessamento. A arquitetura de pastas segue rigorosos padrões de governança e isolamento de ambiente:

*   📁 `data/` **(Hot Data):** Ambiente de produção. Contém o `master_filmes_db.csv` (Base unificada com schema dinâmico, mesclando a arrecadação oficial governamental com metadados globais) e a área de Quarentena de Dados (`issues.csv`).
*   📁 `core/` **(The Engine):** Módulos Python isolados (`main.py`, `modulo_ancine.py`, `modulo_api.py`, `issues.py`) orquestrando o pipeline de forma escalável e tolerante a falhas.
*   📁 `logs/` **(Observability):** Histórico de execução diária (Dual Logging), isolando ruídos internos das bibliotecas de rede e garantindo rastreabilidade absoluta via Tagging individual (`@@`) por requisição.

## 🧠 5. Engenharia de Dados e Resiliência (The Engine)
Bases governamentais frequentemente contêm erros crônicos de digitação (typos), traduções forçadas e datas de lançamento divergentes (fuso entre o lançamento internacional vs. brasileiro). Para garantir 100% de precisão no pareamento de dados, o motor opera com **Inteligência Sistêmica e Auto-Cura**:

1.  **Avaliador Semântico (Gatekeeper):** Para evitar falsos positivos de curtas-metragens homônimos, o cérebro do pipeline cruza *Título* + *Window de Tolerância* temporal (±2 anos) + *Volume de Votos Mínimo* do TMDB. Relançamentos mundiais possuem regra de exceção preditiva.
2.  **Oráculo de IA (LLM-Assisted ETL):** Em caso de falha nas APIs devido a erros severos do governo, o script aciona a API do **Google Gemini (3.0 Flash)**. O Modelo de Linguagem atua como corretor ortográfico e tradutor reverso, devolvendo o título original correto para reintrodução na esteira, evitando falsos negativos.
3.  **Auto-cura e Quarentena (Data Quality):** O módulo auditor (`issues.py`) varre o banco mestre em busca de *Bad Data* (Ex: filmes não encontrados), extrai as anomalias para uma quarentena, filtra os *Trace Logs* daquelas operações via Regex e higieniza a base oficial de forma autônoma para permitir retentativas.
4.  **Checkpointing Atômico e Cooldown Intelligence:** O motor persiste o estado diretamente no disco a cada iteração de sucesso. Ao esbarrar no *Rate Limit* de 1.000 requisições diárias de APIs terceiras (OMDb), o algoritmo registra o *timestamp* da falha, envia Notificações (Toasts) nativas no Windows, entra em Suspensão Profunda e **desperta automaticamente no milissegundo exato após 24 horas**, retomando a extração. Em caso de execução invisível em background, invoca um Popup interativo via Win32 API.

## 📊 6. Escopo do Dashboard e KPIs Definidos
O *Master Database* gerado alimenta um painel executivo (Power BI) estruturado via *Star Schema*, focado em Inteligência de Mercado e Economia Política:
1. **A Trilha do Dinheiro e Matching de Investimentos:** A métrica de alavancagem provando como o "Capital Semente" do Estado reduz o risco e atrai o investimento privado.
2. **Market Share, Monopólio e o Desejo Mimético:** O domínio oligopolista da distribuição interna (Globo Filmes, Paris Filmes) e das *Majors* estrangeiras, atuando como barreiras de entrada na indústria, evidenciando a necessidade sistêmica das Cotas de Tela.
3. **O Mito da Qualidade (Brasil vs. Mundo):** Gráfico de dispersão (*Scatter plot*) contrapondo as melhores obras brasileiras independentes (estranguladas na distribuição) aos piores filmes estrangeiros que dominam os complexos de exibição.
4. **Geração de Empregos (Cadeia Produtiva):** A diferença do multiplicador econômico e impacto logístico regional gerado pelas produções nacionais em comparação com a mera distribuição do catálogo internacional.
5. **O Efeito Oscar e Festivais (Soft Power e Timing):** A análise de como a chancela internacional (Cannes, Berlim, Oscar) atua no *valuation* e acelera a curva de rentabilidade e exportação da propriedade intelectual brasileira.

## 👤 7. Sobre o Autor
Projeto de Portfólio *End-to-End* desenhado e desenvolvido por **Eduardo Américo**, estudante de Sistemas de Informação (UNEB). Focado em demonstrar proficiência em Arquitetura de Dados (*Modern Data Stack*), Programação Defensiva em Python, Integração de APIs, Governança de Dados, Rastreabilidade (Logs) e Inteligência de Negócios (BI) focada em economia criativa e avaliação de mercado por meio de análise factual.