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
- **Documentos oficiais** — metodologia de medicao de consumo e significado das
  faixas de eficiencia energetica, respondidos por busca semantica nos PDFs do
  Inmetro

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
| "Quanto custa o Porsche 911 na FIPE?" | Consulta de preco com mes de referencia |

Resposta real do agente para a viagem Sao Paulo–Rio, ida e volta, no Corolla:

```
Simulacao para Toyota Corolla GLi 2.0 Flex 2024
  Distancia total: 860 km (ida e volta)
  Divisao do percurso: 10% cidade, 90% estrada

  Gasolina a R$ 6.20/litro:
    Consumo medio na viagem: 14.23 km/l
    Combustivel necessario: 60.43 litros
    Custo total: R$ 374.65
    Custo por km: R$ 0.436
    Tanques cheios: 1.21

  Etanol a R$ 4.40/litro:
    Consumo medio na viagem: 9.89 km/l
    Combustivel necessario: 87.0 litros
    Custo total: R$ 382.78
    Custo por km: R$ 0.445
    Tanques cheios: 1.74

  Nos precos informados, gasolina sai R$ 8.13 mais barato nesta viagem.
  Consumo conforme o PBE Veicular do Inmetro, versao TOYOTA COROLLA GLI 20 2.0-16V.
```

## O que ele nao faz

Recusar bem e parte do projeto. O agente responde que nao sabe, em vez de
inventar, nestes casos:

| Pergunta | Por que recusa |
| --- | --- |
| "Quanto gasta o Fiat Uno?" | Fora do catalogo. Ele diz isso e sugere modelos parecidos |
| "Quanto gasta o T-Cross numa viagem?" | O T-Cross nao consta no PBE Veicular; ele informa a ausencia em vez de estimar |
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
  listar_veiculos                |               (RAG semantico)
  comparar_veiculos              |                       |
        |                        |                       |
   pandas sobre CSV      calculo em Python         FAISS + embeddings
        |                        |                       |
  precos FIPE +            sem LLM na conta        PDFs do Inmetro
  ficha + consumo
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
    llm_nvidia.py      Implementacao com NVIDIA NIM
    vetorial_faiss.py  Implementacao com FAISS
    catalogo_csv.py    Implementacao com pandas sobre CSV
  ferramentas/
    consultar_catalogo.py  Busca, filtro, ordenacao e comparacao
    simular_viagem.py      Calculo do custo da viagem
    buscar_documentos.py   Busca semantica
  agente.py            Prompt, esquemas das ferramentas e executor
  fabrica.py           Wiring: liga implementacoes concretas as portas
app/
  streamlit_app.py     Interface web
  cli.py               Interface de terminal, mesmo agente
```

As portas sao `Protocol` do Python: qualquer classe com os metodos certos
serve, sem heranca. **Trocar de tecnologia mexe em um arquivo:**

| Trocar | O que fazer |
| --- | --- |
| Provedor de IA | Nova classe com `modelo_chat` e `modelo_embedding`, registrar em `PROVEDORES` na fabrica |
| Base vetorial | Nova classe com `buscar`, apontar `criar_base_vetorial` |
| Fonte de dados | Nova classe com `listar`, `buscar_por_nome` e `filtrar`, apontar `criar_catalogo` |
| Interface | Novo arquivo em `app/` chamando `criar_agente()`; a CLI ja demonstra isso |

## Tecnologias

| Tecnologia | Papel |
| --- | --- |
| Python 3.10+ | Linguagem |
| LangChain | Orquestracao do agente e tool calling |
| NVIDIA NIM | Modelo de chat e de embeddings |
| FAISS | Indice vetorial local |
| pandas | Consulta aos dados estruturados |
| pypdf | Leitura dos PDFs do Inmetro |
| Streamlit | Interface web e deploy |
| pytest | Testes |

## Como executar

Pre-requisitos: Python 3.10 ou superior e uma chave de API do
[build.nvidia.com](https://build.nvidia.com) (gratuita, sem cartao).

```bash
git clone <url-do-repositorio>
cd agente-carros
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Configure a chave:

```bash
cp .env.example .env
```

Abra o `.env` e preencha `NVIDIA_API_KEY`.

Os dados de preco e consumo ja vem no repositorio. Falta apenas construir o
indice dos documentos, que depende da chave de API:

```bash
python scripts/baixar_documentos.py
python scripts/indexar_documentos.py
```

Suba a aplicacao:

```bash
streamlit run app/streamlit_app.py
```

Ou use pelo terminal:

```bash
python app/cli.py "quanto gasto de Sao Paulo ao Rio com o Corolla?"
```

### Atualizar os dados

```bash
python scripts/coletar_fipe.py          # precos da FIPE
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
   NVIDIA_API_KEY = "sua-chave-aqui"
   ```

6. Clique em **Deploy**

O indice vetorial precisa estar versionado no repositorio antes do deploy,
porque a plataforma nao roda os scripts de construcao.

Como a arquitetura nao prende o projeto ao Streamlit, o mesmo agente roda em
Render, Vercel ou em um servidor proprio trocando apenas a camada de `app/`.

## Fontes de dados

| Dado | Fonte | Estado |
| --- | --- | --- |
| Preco | Tabela FIPE, via API publica | Coletado automaticamente |
| Consumo e autonomia | PBE Veicular 2026 e 2025, Inmetro | Extraido do PDF oficial |
| Metodologia de consumo | Inmetro | PDF oficial indexado |
| Ficha tecnica | Curadoria manual | Em conferencia |

Detalhes de procedencia, criterios de selecao e divergencias entre as fontes
estao em [`docs/FONTES.md`](docs/FONTES.md).

Cada registro de consumo guarda a linha original do PDF do Inmetro, de modo que
qualquer numero pode ser conferido contra a fonte.

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

30 testes cobrindo o calculo da viagem e as consultas ao catalogo — as partes
onde um erro numerico viraria uma resposta errada com aparencia de certeza.

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
- **T-Cross sem consumo.** Nao consta nas tabelas do Inmetro de 2025 nem de
  2026. Permanece no catalogo com preco e ficha, sem simulacao de viagem.
- **Eletricos sem custo de viagem.** O Inmetro publica km por litro equivalente
  e autonomia, mas nao o consumo em kWh. Incluir kWh/100km por modelo habilitaria
  a simulacao.
- **Preco congelado na coleta.** Os valores tem o mes de referencia registrado.
  Rodar `coletar_fipe.py` atualiza.
- **Consumo de ensaio.** Os numeros do Inmetro vem de condicoes controladas. O
  consumo real varia com carga, ar-condicionado, relevo e conducao. O agente
  informa isso em toda simulacao.
