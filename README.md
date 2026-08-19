# Consultor de carros

Agente de IA que responde perguntas de quem esta pesquisando um carro para
comprar: ficha tecnica, preco da Tabela FIPE e simulacao do custo de
combustivel de uma viagem.

Quem pesquisa carro hoje abre uma aba para a ficha tecnica, outra para a FIPE,
outra para o consumo e ainda faz a conta da viagem na mao. O agente junta as
tres fontes e responde em uma frase.

> **Evidencia do deploy:** _(link da aplicacao, video ou captura de tela)_

## Indice

- [O que ele faz](#o-que-ele-faz)
- [Exemplos de perguntas](#exemplos-de-perguntas)
- [O que ele nao faz](#o-que-ele-nao-faz)
- [Arquitetura](#arquitetura)
- [Tecnologias](#tecnologias)
- [Como executar](#como-executar)
- [Deploy](#deploy)
- [Fontes de dados](#fontes-de-dados)
- [Testes](#testes)
- [Limitacoes conhecidas](#limitacoes-conhecidas)

## O que ele faz

O catalogo cobre **28 modelos do ano 2024**, do hatch de entrada ao
superesportivo: Fiat, Volkswagen, Chevrolet, Hyundai, Renault, Nissan, Toyota,
Honda, Jeep, BYD, BMW, Mercedes-Benz, Porsche e Ferrari.

Sobre esse catalogo o agente sabe:

- **Ficha tecnica** — motor, potencia, torque, cambio, tracao, porta-malas, tanque
- **Preco** — valor da Tabela FIPE, com o mes de referencia
- **Consumo** — cidade e estrada, gasolina e etanol nos flex, conforme o Inmetro
- **Busca e comparacao** — filtrar por faixa de preco, categoria ou combustivel,
  ordenar por consumo ou potencia, comparar modelos lado a lado
- **Simulacao de viagem** — quantos litros e quantos reais uma viagem custa,
  separando cidade e estrada, comparando gasolina com etanol e informando
  quantos tanques cheios sao necessarios
- **Precos de combustivel** — gasolina, etanol e diesel praticados em cada
  estado, apurados pela ANP, e onde o etanol compensa
- **Documentos oficiais** — metodologia de medicao de consumo e faixas de
  eficiencia energetica, do Inmetro, e o **manual do proprietario do Corolla**,
  com 484 paginas: revisao periodica, fluidos, pneus, garantia e operacao

A simulacao usa o preco do **estado** de quem pergunta. A mesma viagem no mesmo
carro custa diferente saindo de Sao Paulo e do Amapa, e o agente reflete isso.

## Exemplos de perguntas

Perguntas que o agente responde:

| Pergunta | O que acontece por tras |
| --- | --- |
| "Quais carros custam ate 70 mil?" | Filtro e ordenacao sobre o catalogo |
| "Quanto gasto de combustivel de Sao Paulo ao Rio, 430 km, com o Corolla?" | Simulacao em Python |
| "Nessa viagem, compensa gasolina ou etanol?" | Simulacao com os dois combustiveis |
| "Compare o Onix com o HB20" | Consulta estruturada dos dois modelos |
| "Qual o SUV mais economico na estrada?" | Filtro por categoria com ordenacao por consumo |
| "Qual a potencia e o torque do Compass?" | Ficha tecnica |
| "O que significa a classificacao A na etiqueta do Inmetro?" | Busca semantica nos PDFs oficiais |
| "De quantas em quantas revisoes troca o fluido de arrefecimento do Corolla?" | Busca no manual do proprietario, 484 paginas |
| "Quanto custa o Porsche 911 na FIPE?" | Consulta de preco com mes de referencia |
| "Onde o etanol e mais barato no Brasil?" | Ranking por estado com dados da ANP |
| "Compensa abastecer com etanol aqui em Minas?" | Precos da ANP em MG e razao etanol/gasolina |

Resposta real da ferramenta de simulacao, para uma viagem de 300 km saindo de
Minas Gerais no Jeep Compass:

```
Simulacao para Jeep Compass Serie S T270 1.3 Turbo 2024
  Distancia total: 300 km
  Divisao do percurso: 40% cidade, 60% estrada

  Gasolina a R$ 6.32/litro:
    Consumo medio na viagem: 11.21 km/l
    Combustivel necessario: 26.76 litros
    Custo total: R$ 169.11
    Custo por km: R$ 0.564
    Tanques cheios: 0.49

  Etanol a R$ 3.99/litro:
    Consumo medio na viagem: 8.03 km/l
    Combustivel necessario: 37.37 litros
    Custo total: R$ 149.10
    Custo por km: R$ 0.497
    Tanques cheios: 0.68

  Nos precos informados, etanol sai R$ 20.01 mais barato nesta viagem.
  Precos de combustivel: mediana de MG, levantamento da ANP de 2026-07-01 a 2026-07-31.
  Consumo conforme o PBE Veicular do Inmetro, versao JEEP COMPASS SERIE S T 1.3T-16V.
  Valores de referencia em condicoes de ensaio.
```

## O que ele nao faz

Recusar bem e parte do projeto. O agente responde que nao sabe, em vez de
inventar, nestes casos:

| Pergunta | Por que recusa |
| --- | --- |
| "Quanto gasta o Fiat Uno?" | Fora do catalogo. Ele diz isso e sugere modelos parecidos |
| "Quanto custa carregar o BYD Dolphin numa viagem?" | O catalogo tem km/l equivalente e autonomia, mas nao kWh, entao o custo em reais nao e calculavel |
| "Vale a pena financiar em 48 vezes?" | Nao da conselho financeiro nem simula financiamento |
| "Quanto vai valer esse carro em 2030?" | Nao projeta valor de revenda |
| "Qual o melhor carro?" | Sem criterio nao ha resposta objetiva; ele pede o criterio |

## Arquitetura

O agente e **hibrido**: cada tipo de pergunta vai para o mecanismo certo.

```
                        pergunta do usuario
                                |
                        [ agente / tool calling ]
                                |
        +-----------------------+-----------------------+
        |                       |                       |
  buscar_veiculo          simular_viagem        buscar_documentos
  listar_veiculos       consultar_precos         (RAG semantico)
  comparar_veiculos      ranking_precos                  |
        |                        |                       |
   pandas sobre CSV      calculo em Python         FAISS + embeddings
        |                        |                       |
  precos FIPE +           precos da ANP           PDFs do Inmetro
  ficha + consumo         por estado              + manual do Corolla
```

A razao para esse desenho: **RAG nao faz conta nem comparacao numerica**. Busca
por similaridade e boa para texto corrido e ruim para "o mais economico ate 100
mil" ou "quanto custa a viagem". Jogar tudo num indice vetorial produziria
respostas confiantes e erradas. Entao:

- Dados estruturados sao consultados com pandas
- A conta de viagem e uma funcao Python determinista, coberta por testes
- Busca semantica fica restrita ao que ela faz bem: texto corrido

O modelo de linguagem so interpreta a pergunta, escolhe a ferramenta e redige a
resposta. Ele nunca produz um numero por conta propria.

### Tempo de construcao e tempo de execucao

Toda coleta e todo processamento pesado acontecem antes, em scripts, e o
resultado e versionado no repositorio:

```
tempo de construcao (scripts, rodam sob demanda)
  coletar_fipe.py           API da FIPE       -> dados/processados/precos_fipe.csv
  coletar_precos_anp.py     CSV aberto da ANP -> dados/processados/precos_combustivel_anp.csv
  baixar_documentos.py      Inmetro           -> dados/brutos/documentos/
  extrair_consumo_pbev.py   PDFs do Inmetro   -> dados/processados/consumo_pbev.csv
  indexar_documentos.py     PDFs + embeddings -> dados/processados/indice_faiss/

tempo de execucao (a aplicacao apenas le)
  Streamlit -> fabrica -> agente -> ferramentas -> CSVs e indice em disco
```

A aplicacao nunca chama a API da FIPE durante a conversa nem recalcula
embeddings ao iniciar. Isso evita latencia, limite de requisicoes e dependencia
externa no caminho critico, preserva a cota gratuita da API de IA e torna os
numeros deste README reproduziveis por quem clonar o projeto.

### Organizacao do codigo

```
src/agente_carros/
  config.py            Configuracao e caminhos, ponto unico de leitura do ambiente
  dominio/
    modelos.py         Veiculo, ResultadoViagem, CustoPorCombustivel
    portas.py          Contratos: ProvedorLLM, BaseVetorial, RepositorioCatalogo
  adaptadores/
    llm_gemini.py      Implementacao com Google Gemini
    llm_nvidia.py      Implementacao com NVIDIA NIM
    vetorial_faiss.py  Implementacao com FAISS
    catalogo_csv.py    Implementacao com pandas sobre CSV
    precos_anp_csv.py  Precos de combustivel por estado
  ferramentas/
    consultar_catalogo.py  Busca, filtro, ordenacao e comparacao
    simular_viagem.py      Calculo do custo da viagem
    consultar_precos.py    Precos de combustivel e ranking por estado
    buscar_documentos.py   Busca semantica
  agente.py            Prompt, esquemas das ferramentas e executor
  fabrica.py           Wiring: liga implementacoes concretas as portas
app/
  streamlit_app.py     Interface web
  cli.py               Interface de terminal, mesmo agente
scripts/
  configurar_chave.py     Grava a chave de API no .env
  coletar_fipe.py         Precos dos veiculos
  coletar_precos_anp.py   Precos de combustivel por estado
  baixar_documentos.py    PDFs oficiais do Inmetro
  extrair_consumo_pbev.py Consumo oficial, extraido dos PDFs
  indexar_documentos.py   Indice vetorial
  testar_provedor.py      Testa a chave isoladamente
  diagnosticar.py         Confere o ambiente inteiro
```

As portas sao `Protocol` do Python: qualquer classe com os metodos certos
serve, sem heranca. **Trocar de tecnologia mexe em um arquivo:**

| Trocar | O que fazer |
| --- | --- |
| Provedor de IA | Nova classe com `modelo_chat` e `modelo_embedding`, registrar em `PROVEDORES` na fabrica |
| Entre Gemini e NVIDIA | Trocar `PROVEDOR_LLM` no `.env`; nada mais muda |
| Base vetorial | Nova classe com `buscar`, apontar `criar_base_vetorial` |
| Fonte de dados | Nova classe com `listar`, `buscar_por_nome` e `filtrar`, apontar `criar_catalogo` |
| Interface | Novo arquivo em `app/` chamando `criar_agente()`; a CLI ja demonstra isso |

Essa intercambialidade nao e teorica. Durante a construcao do projeto o acesso
a API da NVIDIA foi bloqueado na verificacao de conta, e a migracao para o
Gemini custou **um arquivo novo e uma linha na fabrica**. Agente, ferramentas,
dados, testes e interface nao foram tocados. O historico de commits registra a
mudanca inteira.

## Tecnologias

| Tecnologia | Papel |
| --- | --- |
| Python 3.10+ | Linguagem |
| LangChain | Orquestracao do agente e tool calling |
| Google Gemini | Modelo de chat e de embeddings (padrao) |
| NVIDIA NIM | Provedor alternativo, selecionavel por variavel de ambiente |
| FAISS | Indice vetorial local |
| pandas | Consulta aos dados estruturados |
| pypdf | Leitura dos PDFs do Inmetro |
| Streamlit | Interface web e deploy |
| pytest | Testes |

## Como executar

Pre-requisitos: Python 3.10 ou superior e uma chave de API gratuita de um dos
provedores suportados — [Google AI Studio](https://aistudio.google.com/apikey)
ou [build.nvidia.com](https://build.nvidia.com). Nenhum dos dois pede cartao.

```bash
git clone <url-do-repositorio>
cd agente-carros
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Salve a chave num arquivo de texto fora do projeto e registre-a:

```bash
python scripts/configurar_chave.py /caminho/da/chave
```

O script deduz o provedor pelo prefixo da chave, grava o `.env` com permissao
restrita e nunca imprime o valor. Se preferir a mao, copie `.env.example` para
`.env` e preencha `GOOGLE_API_KEY` ou `NVIDIA_API_KEY`.

Os dados de preco e consumo ja vem no repositorio. Falta baixar os PDFs e
construir o indice, que depende da chave:

```bash
python scripts/baixar_documentos.py
python scripts/indexar_documentos.py
```

Confira se esta tudo no lugar:

```bash
python scripts/diagnosticar.py
```

Suba a aplicacao:

```bash
streamlit run app/streamlit_app.py
```

Quem preferir, o `Makefile` encadeia tudo:

```bash
make instalar
make chave ARQ=/caminho/da/chave
make tudo
make rodar
```

Ou use pelo terminal:

```bash
python app/cli.py "quanto gasto de Sao Paulo ao Rio com o Corolla?"
```

### Atualizar os dados

```bash
python scripts/coletar_fipe.py          # precos dos veiculos, FIPE
python scripts/coletar_precos_anp.py    # precos de combustivel por estado, ANP
python scripts/baixar_documentos.py     # PDFs do Inmetro
python scripts/extrair_consumo_pbev.py  # consumo oficial
python scripts/indexar_documentos.py    # indice vetorial
```

Para incluir novos modelos, acrescente uma linha em `dados/catalogo_semente.csv`,
outra em `dados/processados/fichas_tecnicas.csv` e outra em `dados/mapa_pbev.csv`,
sempre com o mesmo `id`, e rode os scripts acima.

## Deploy

O projeto foi publicado no **Streamlit Community Cloud**:

1. Envie o repositorio para o GitHub como publico
2. Acesse [share.streamlit.io](https://share.streamlit.io) e entre com a conta do GitHub
3. Clique em **Create app** e escolha o repositorio
4. Em **Main file path**, informe `app/streamlit_app.py`
5. Em **Advanced settings → Secrets**, adicione a chave:

   ```toml
   PROVEDOR_LLM = "gemini"
   GOOGLE_API_KEY = "sua-chave-aqui"
   ```

6. Clique em **Deploy**

O indice vetorial precisa estar versionado no repositorio antes do deploy,
porque a plataforma nao roda os scripts de construcao.

Como a arquitetura nao prende o projeto ao Streamlit, o mesmo agente roda em
Render, Vercel ou em um servidor proprio trocando apenas a camada de `app/`.

## Fontes de dados

| Dado | Fonte | Estado |
| --- | --- | --- |
| Preco do veiculo | Tabela FIPE, via API publica | Coletado automaticamente |
| Consumo e autonomia | PBE Veicular 2026 e 2025, Inmetro | Extraido do PDF oficial |
| Preco de combustivel | Levantamento de precos da ANP, CSV aberto | Coletado automaticamente |
| Metodologia de consumo | Inmetro | PDF oficial indexado |
| Manuais de montadora | Sites oficiais das marcas | Corolla indexado; 24 guardados |
| Ficha tecnica | Curadoria manual | Em conferencia |

Para acrescentar manuais do proprietario ao indice, veja
[`docs/MANUAIS.md`](docs/MANUAIS.md). Os sites das montadoras bloqueiam
download automatizado, entao esses PDFs entram a mao.

Detalhes de procedencia, criterios de selecao e divergencias entre as fontes
estao em [`docs/FONTES.md`](docs/FONTES.md).

Cada registro de consumo guarda a linha original do PDF do Inmetro, de modo que
qualquer numero pode ser conferido contra a fonte.

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

53 testes cobrindo o calculo da viagem, as consultas ao catalogo, a resolucao
de precos por estado e a selecao de provedor e credencial — as partes onde um erro numerico viraria uma resposta
errada com aparencia de certeza.

Um deles merece nota: a simulacao **soma os litros gastos em cada trecho** em
vez de aplicar a media dos consumos sobre a distancia total. Media aritmetica
de km/l subestima o gasto, porque consumo e uma razao invertida. Ha teste
fixando esse comportamento.

## Limitacoes conhecidas

- **Catalogo fechado.** 28 modelos, ano 2024. Carros fora dessa lista nao sao
  respondidos, e o agente diz isso.
- **Ficha tecnica em conferencia.** Motor, potencia, torque, cambio, tanque e
  porta-malas foram preenchidos manualmente e ainda nao foram conferidos contra
  o material das montadoras. Preco e consumo, que sustentam a maior parte das
  respostas, vem de fonte oficial.
- **Eletricos sem custo de viagem.** O Inmetro publica km por litro equivalente
  e autonomia, mas nao o consumo em kWh. Incluir kWh/100km por modelo habilitaria
  a simulacao.
- **Precos congelados na coleta.** Valores da FIPE e da ANP tem o periodo de
  referencia registrado. Rodar os scripts de coleta atualiza.
- **Preco de combustivel por estado, nao por cidade.** A ANP publica posto a
  posto, mas o resumo agrega por unidade da federacao. Dentro de um estado o
  preco varia bastante — a consulta informa a faixa entre o menor e o maior.
- **So o Corolla tem manual indexado.** Perguntas sobre revisao, fluidos ou
  garantia funcionam para ele e nao para os outros 27 modelos, e o agente diz
  isso. Ha mais 24 documentos guardados no projeto, aguardando indexacao: a
  camada gratuita limita as requisicoes de embedding por dia, entao o acervo
  entra aos poucos. Veja [`docs/MANUAIS.md`](docs/MANUAIS.md).
- **Consumo de ensaio.** Os numeros do Inmetro vem de condicoes controladas. O
  consumo real varia com carga, ar-condicionado, relevo e conducao. O agente
  informa isso em toda simulacao.
