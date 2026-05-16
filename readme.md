# 🎬 PROJETO: A Engenharia Econômica e o Valor Oculto do Cinema Nacional
**Data Analytics, Soberania Cultural e a Desconstrução do "Livre Mercado" no Audiovisual**

---

## 📌 1. Antecedentes e Contexto
O debate público sobre a indústria cinematográfica brasileira é frequentemente pautado por desinformação, "síndrome de vira-lata" e desconhecimento sobre economia criativa. O senso comum, muitas vezes propagado por correntes liberais ou conservadoras, dita que "o brasileiro não assiste filme nacional porque é intrinsecamente ruim" e que o fomento público se resume a um "desperdício de impostos". 

No entanto, à luz da **Teoria do Desejo Mimético de René Girard**, compreende-se que o espectador não escolhe um *blockbuster* genérico hollywoodiano por seu "valor intrínseco", mas porque o seu desejo é mediado por um modelo de distribuição monopolista. Quando uma rede multiplex destina 85% de suas salas a um único filme estrangeiro, ocorre um *dumping* cultural. A "mão invisível do mercado", neste caso, dita de forma forçada o que o público deve desejar.

Este projeto visa auditar o ecossistema audiovisual brasileiro através da Ciência e Engenharia de Dados, provando por meio de indicadores matemáticos (ROI, Geração de Empregos, Market Share e Matching de Investimentos) que o cinema nacional é uma indústria de altíssimo valor agregado, que protege a soberania e movimenta a economia real.

## 🏛️ 2. O Ecossistema de Apoio (A Engenharia Institucional)
Longe de ser apenas um "repasse de verbas", o fomento ao audiovisual brasileiro é uma engrenagem sofisticada que envolve os três poderes da República em todas as esferas:

*   **Poder Executivo (O Motor Logístico e Financeiro):** Atua via Fundo Setorial do Audiovisual (FSA), que funciona como *Venture Capital* (Capital Semente). Grande parte desse fundo não sai de impostos do cidadão comum, mas da **CONDECINE** (taxa cobrada das próprias superproduções estrangeiras e das empresas de telecomunicações para remeterem lucros ao exterior). Além disso, Municípios e Estados operam via **Film Commissions**, atraindo filmagens que injetam milhões em hotelaria, transporte e marcenaria local.
*   **Poder Legislativo (A Regulação Antitruste):** O Congresso Nacional desenhou a **Cota de Tela** e a **Lei do SeAC (TV Paga)** não como "mamatas", mas como leis de regulação antitruste para combater o monopólio e garantir prateleira para o produto nacional. Além disso, criaram engenharias de renúncia fiscal descentralizadas (ICMS nos Estados; ISS e IPTU nos Municípios).
*   **Poder Judiciário (O Fiador):** O Supremo Tribunal Federal (STF) validou, em repetidas ADPFs e ADIs, a constitucionalidade das cotas e das taxas do setor, protegendo o mercado interno contra as pressões monopolistas de *majors* transnacionais.

## ⚖️ 3. Metodologia: Remoção de Viés e a "Grama do Vizinho"
Para garantir o rigor estatístico desta análise e evitar o viés de confirmação, foi estabelecida uma **Regra de Exclusão de Outliers**. Filmes nacionalmente aclamados e inquestionáveis (as "cartas coringas" dos críticos) como *Cidade de Deus*, *Tropa de Elite (1 e 2)* e *O Auto da Compadecida* foram **removidos do dataset**. 

O objetivo é provar a qualidade da **média** do cinema nacional em comparação à **média** dos blockbusters. Para chancelar a qualidade de forma imparcial, o projeto consome APIs de avaliação internacional (**Rotten Tomatoes e Metacritic** via OMDb API), provando que a crítica especializada estrangeira avalia o cinema brasileiro com notas substancialmente superiores ao que o brasileiro consome dos enlatados estrangeiros.

## 🗄️ 4. Arquitetura do Data Lake (Single Source of Truth)
O projeto abandonou a extração manual de APIs e adotou uma esteira de **Raw Ingestion (Ingestão Bruta Constante)**, extraindo mais de 70 colunas de metadados para garantir análises futuras sem reprocessamento. A arquitetura foi modularizada visando governança de dados:

*   📁 `allcsv/` **(Cold Storage):** Acervo morto. Dados brutos do governo federal (ANCINE) isolados e ignorados pelo controle de versão (Git) até serem auditados.
*   📁 `data/` **(Hot Data):** Ambiente de produção. Contém a base matriz em uso e o arquivo `master_filmes_db.csv` (O Data Warehouse local com o Schema dinâmico contendo dados financeiros do Brasil mesclados com dados globais das APIs).
*   📁 `core/` **(Engine):** Módulos Python isolados seguindo princípios de Clean Code.

## 🧠 5. Engenharia de Dados: Resiliência e "Google Dorking"
Dados governamentais frequentemente contêm erros crônicos de digitação (typos) ou adaptações não oficiais de títulos, o que quebra buscas convencionais em APIs internacionais. Para contornar isso, o projeto utiliza um algoritmo de **Busca Semântica em 4 Camadas (O Funil de Sobrevivência)** e forte tolerância a falhas:

1.  **Camada 1 (Exata):** Busca Título + Ano exato de lançamento no TMDB.
2.  **Camada 2 (Fuso Horário):** Remove o ano da requisição e aplica uma *Window de Tolerância* de ±1 ano no resultado para capturar filmes de festivais/Oscar (lançados no exterior em um ano e no Brasil no ano seguinte).
3.  **Camada 3 (Title Splitting):** Identifica caracteres de quebra de franquia (dois-pontos/traços) e "poda" o subtítulo que contém erro ortográfico do governo, buscando apenas pela raiz da franquia.
4.  **Camada 4 (Oráculo OSINT):** Em caso de falha sistêmica, o algoritmo utiliza biblioteca de busca e *Google Dorking* (`site:imdb.com/title/ "Nome Sujo"`) para localizar via inteligência semântica o *IMDb ID* real da obra, injetando-o de volta na esteira da API.
5.  **Persistência e Cooldown Intelligence:** O motor processa os dados atomicamente (*checkpointing* no SSD). Ao esbarrar no *Rate Limit* da API (Ex: limite diário de requisições), o algoritmo captura o Timestamp, entra em modo de Suspensão Profunda e **desperta automaticamente 24 horas depois**, retomando a extração sem intervenção humana.

## 📊 6. Estrutura do Dashboard (5 Páginas Analíticas)
1. **A Trilha do Dinheiro (O Ecossistema):** A macroeconomia do setor. De onde vem o dinheiro (CONDECINE, ISS, ICMS) e a métrica de *Alavancagem* (como R$ 1 público atrai R$ 3 privados).
2. **O Desejo Mimético e o Monopólio:** Análise do *Market Share* das salas de cinema, provando matematicamente o *dumping* de distribuição estrangeira e a necessidade das Cotas de Tela.
3. **O Mito da Qualidade (Brasil vs. Mundo):** Gráfico de dispersão (*Scatter plot*) cruzando as avaliações no Rotten Tomatoes (crítica gringa) vs. Bilheteria Nacional, evidenciando o padrão de qualidade da produção nacional frente à enxurrada estrangeira.
4. **O Efeito Multiplicador (Cadeia Produtiva):** A diferença de impacto local (empregos, hotelaria, logística) entre filmar um longa no interior do Brasil (Film Commissions) e exibir um blockbuster gravado em tela verde na Califórnia.
5. **O Efeito Oscar e Festivais (Timing e Soft Power):** A análise de como o reconhecimento em festivais (Cannes, Berlim, Oscar) impacta a curva de bilheteria e alavanca a venda internacional da propriedade intelectual brasileira.

## 👤 7. Sobre o Autor
Projeto de Portfólio *End-to-End* idealizado por **Eduardo Américo**, estudante de Sistemas de Informação (UNEB). Desenvolvido para demonstrar proficiência em Engenharia de Dados (Python, APIs, OSINT), Modelagem de Dados, Resiliência de Software e Inteligência de Negócios (BI) voltada a políticas públicas e eco