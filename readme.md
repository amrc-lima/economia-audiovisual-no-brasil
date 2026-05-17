# 🎬 PROJETO: A Engenharia Econômica e o Valor do Cinema Nacional
**Data Analytics, Inteligência Competitiva e a Análise de Assimetrias no Mercado Audiovisual**

---

## 📌 1. Antecedentes e Contexto
O debate público sobre a indústria cinematográfica brasileira é frequentemente pautado por desinformação e desconhecimento sobre o real impacto da economia criativa. O senso comum dita que "o baixo consumo do cinema nacional ocorre por falta de apelo orgânico" e que o fomento público se resume a um "gasto sem retorno". 

No entanto, à luz da **Teoria do Desejo Mimético de René Girard**, compreende-se que a escolha do consumidor não é estritamente orgânica, mas fortemente mediada pelos modelos de distribuição e disponibilidade de prateleira. Quando uma rede multiplex destina 85% de suas salas a um único filme estrangeiro, configura-se uma severa **Falha de Mercado (Market Failure)** e uma assimetria competitiva (*Dumping*). Neste cenário de oligopólio, a distribuição dita o que o público deve desejar consumir.

Este projeto visa auditar o ecossistema audiovisual brasileiro entre **2015 e 2025** através da Ciência e Engenharia de Dados. O objetivo é provar, por meio de indicadores econômicos claros (**ROI, Geração de Empregos, Market Share e Matching de Investimentos**), que o cinema nacional é uma indústria de altíssimo valor agregado, e demonstrar como mecanismos regulatórios são essenciais para garantir a livre concorrência e a pluralidade no setor.

## 🏛️ 2. O Ecossistema de Apoio (A Engenharia Institucional)
Longe de ser apenas um "repasse de verbas", o fomento ao audiovisual brasileiro é uma engrenagem sofisticada que envolve os três poderes da República em todas as esferas:

*   **Poder Executivo (O Motor Logístico e Financeiro):** Atua via Fundo Setorial do Audiovisual (FSA), que funciona como *Venture Capital* (Capital Semente). Grande parte desse fundo não sai de impostos do cidadão comum, mas da **CONDECINE** (taxa cobrada das próprias superproduções estrangeiras e das empresas de telecomunicações para remeterem lucros ao exterior). Além disso, Municípios e Estados operam via **Film Commissions**, atraindo filmagens que injetam milhões em hotelaria, transporte e marcenaria local.
*   **Poder Legislativo (A Regulação Antitruste):** O Congresso Nacional desenhou a **Cota de Tela** e a **Lei do SeAC (TV Paga)** não como "mamatas", mas como leis de regulação antitruste para combater o monopólio e garantir prateleira para o produto nacional. Além disso, criaram engenharias de renúncia fiscal descentralizadas (ICMS nos Estados; ISS e IPTU nos Municípios).
*   **Poder Judiciário (O Fiador):** O Supremo Tribunal Federal (STF) validou, em repetidas ADPFs e ADIs, a constitucionalidade das cotas e das taxas do setor, protegendo o mercado interno contra as pressões monopolistas de *majors* transnacionais.

## ⚖️ 3. Metodologia: Remoção de Viés e a "Grama do Vizinho"
Para garantir o rigor estatístico desta análise e evitar o viés de confirmação, foi estabelecida uma **Regra de Exclusão de Outliers**. Filmes nacionalmente aclamados e inquestionáveis (as "cartas coringas" dos críticos) como *Cidade de Deus*, *Tropa de Elite (1 e 2)* e *O Auto da Compadecida* foram **removidos do dataset**. 

O objetivo é provar a qualidade da **média** do cinema nacional em comparação à **média** dos blockbusters (ex: *Marvel, Transformers, Pânico, Velozes e Furiosos*). Para chancelar a qualidade de forma imparcial, o projeto consome APIs de avaliação internacional (**Rotten Tomatoes e Metacritic** via OMDb API), provando que a crítica especializada estrangeira avalia o cinema brasileiro com notas substancialmente superiores ao que o brasileiro consome dos enlatados estrangeiros.

## 🗄️ 4. Arquitetura do Data Lake (Single Source of Truth)
O projeto adota uma esteira de **Raw Ingestion (Ingestão Bruta Constante)**, extraindo mais de 70 colunas de metadados das APIs para compor um *Data Warehouse* local, garantindo análises multidimensionais sem necessidade de reprocessamento. A arquitetura de pastas segue rígidos padrões de governança:

*   📁 `data/` **(Hot Data):** Ambiente de produção. Contém o `master_filmes_db.csv` (Base unificada com schema dinâmico mesclando a arrecadação oficial do governo com os metadados globais) e a área de Quarentena de Dados (`issues.csv`).
*   📁 `core/` **(The Engine):** Módulos Python isolados orquestrando o pipeline de forma escalável e tolerante a falhas.
*   📁 `logs/` **(Observability):** Histórico de execução diária (Dual Logging), isolando ruídos internos e garantindo rastreabilidade absoluta via Tagging individual por requisição.

## 🧠 5. Engenharia de Dados e Resiliência (The Engine)
Dados governamentais frequentemente contêm erros crônicos de digitação (typos), traduções forçadas e datas de lançamento divergentes. Para garantir 100% de precisão no cruzamento de dados, o motor opera com **Inteligência Sistêmica e Auto-Cura**:

1.  **Heurística Léxica e Lab de Testes (A/B Testing):** Normalização estrutural via *Regex* (algarismos romanos, caracteres de escape).
2.  **Avaliador Semântico (Gatekeeper):** Para evitar falsos positivos de curtas-metragens homônimos, o cérebro do pipeline cruza *Título* + *Window de Tolerância* temporal + *Volume de Votos Mínimo* do TMDB. Relançamentos mundiais possuem regra de exceção programada.
3.  **Oráculo OSINT (Fuzzy Matching via DuckDuckGo):** Em caso de falha nas APIs devido a erros severos de digitação do governo (Shadowbans/CAPTCHAs evitados), o script aciona a biblioteca DuckDuckGo (*Web Search*) sem aspas estritas, permitindo que a Inteligência do buscador corrija o typo e retorne o *IMDb ID* legítimo para reintrodução na esteira.
4.  **Auto-cura e Quarentena (Data Quality):** Um módulo paralelo (`issues.py`) atua como auditor, varrendo o banco mestre, extraindo linhas corrompidas para uma quarentena, filtrando seus respectivos *Trace Logs* por Tags (`@@`), e limpando a base oficial para forçar uma retentativa autônoma pelo sistema.
5.  **Checkpointing Atômico e Cooldown Intelligence:** O motor salva dados diretamente no disco a cada iteração de sucesso. Ao esbarrar no *Rate Limit* diário das APIs de terceiros, o algoritmo registra o *timestamp* da falha, envia Push Notifications nativas no Windows (win10toast), entra em Suspensão Profunda e **desperta automaticamente no milissegundo exato após 24 horas**, retomando a extração.

## 📊 6. Escopo do Dashboard e KPIs Definidos
O Master Database gerado alimenta um painel executivo (Power BI) estruturado via *Star Schema*, focado em Inteligência de Mercado e Economia Política:
1. **A Trilha do Dinheiro e Matching de Investimentos:** A métrica de alavancagem provando como o "Capital Semente" do Estado atrai o investimento privado.
2. **Market Share, Monopólio e o Desejo Mimético:** O domínio oligopolista da distribuição (ex: Globo Filmes/Paris Filmes atuando como barreira de entrada na indústria e *blockbusters* estrangeiros esmagando o circuito), evidenciando a indispensabilidade regulatória das Cotas de Tela.
3. **O Mito da Qualidade (Brasil vs. Mundo):** Gráfico de dispersão (*Scatter plot*) evidenciando as melhores obras brasileiras estranguladas na distribuição contra os piores filmes estrangeiros que dominam a bilheteria.
4. **Geração de Empregos (Cadeia Produtiva):** A diferença do multiplicador econômico e impacto regional logístico gerado pelo cinema brasileiro em comparação com a mera exibição de importados.
5. **O Efeito Oscar e Festivais (Soft Power e Timing):** A análise de como o reconhecimento internacional (Cannes, Berlim, Oscar) impacta a curva de bilheteria e alavanca a venda da propriedade intelectual brasileira para o exterior.

## 👤 7. Sobre o Autor
Projeto de Portfólio *End-to-End* desenhado e desenvolvido por **Eduardo Américo**, estudante de Sistemas de Informação (UNEB). Focado em demonstrar proficiência em Arquitetura de Dados (MDS), Programação Defensiva em Python, Integração de APIs, Governança de Dados, Rastreabilidade (Logs) e Inteligência de Negócios (BI) voltada a políticas públicas e economia criativa através de fatos comprováveis.