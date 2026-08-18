# Fontes de dados

Este documento registra de onde vem cada dado usado pelo agente e qual o
estado de verificacao de cada conjunto. A intencao e que qualquer pessoa
consiga refazer a coleta e conferir os numeros.

## 1. Precos — Tabela FIPE

| Item | Valor |
| --- | --- |
| Fonte | Tabela FIPE, via API publica `fipe.parallelum.com.br` |
| Arquivo | `dados/processados/precos_fipe.csv` |
| Script | `scripts/coletar_fipe.py` |
| Estado | Coletado automaticamente |

A FIPE nao publica API oficial. A API utilizada espelha os dados da tabela
e mantem base propria, o que evita sobrecarregar o servico original. Cada
linha do dataset guarda o mes de referencia informado pela propria FIPE e a
data em que a coleta foi executada.

**Criterio de selecao.** Para cada modelo da semente, o script mantem apenas
as versoes ofertadas no ano desejado e escolhe a de menor preco, que
corresponde a versao de entrada. O filtro por ano e essencial: a FIPE lista
versoes homonimas de decadas diferentes, e sem ele um Polo 1997 entra no
lugar do Polo atual.

Para atualizar os precos:

```bash
python scripts/coletar_fipe.py
```

## 2. Consumo de combustivel — PBE Veicular / Inmetro

| Item | Valor |
| --- | --- |
| Fonte | Programa Brasileiro de Etiquetagem Veicular (Inmetro) |
| Pagina | https://www.gov.br/inmetro/pt-br/assuntos/avaliacao-da-conformidade/programa-brasileiro-de-etiquetagem/tabelas-de-eficiencia-energetica/veiculos-automotivos-pbe-veicular |
| PDFs | `dados/brutos/documentos/` (baixados pelo script) |
| Dataset | `dados/processados/consumo_pbev.csv` |
| Scripts | `scripts/baixar_documentos.py` e `scripts/extrair_consumo_pbev.py` |
| Estado | Extraido da fonte oficial |

O Inmetro publica a tabela apenas em PDF, sem versao em planilha. O arquivo
de 2026 reune 892 modelos e versoes de 42 marcas.

A extracao e automatizada, mas nao generica: em vez de tentar interpretar as
892 linhas, o script localiza apenas os modelos do catalogo, usando os
padroes declarados em `dados/mapa_pbev.csv`. As colunas numericas do Inmetro
tem posicao fixa no fim da linha, o que torna a leitura confiavel para um
conjunto conhecido de modelos.

Cada linha de `consumo_pbev.csv` guarda o texto original extraido do PDF na
coluna `linha_original`, de modo que qualquer valor pode ser conferido contra
a fonte sem reabrir o documento.

Os PDFs permanecem no projeto e sao indexados para busca semantica, de modo
que o agente tambem responde sobre a metodologia da etiquetagem e o
significado das faixas de eficiencia.

### Divergencias conhecidas entre FIPE e PBE Veicular

As duas fontes nomeiam versoes de maneira diferente e nem sempre cobrem o
mesmo conjunto. O que foi encontrado neste catalogo:

- **Volkswagen T-Cross** nao consta nas tabelas de 2025 nem de 2026. O modelo
  permanece no catalogo com preco e ficha tecnica, sem dados de consumo. O
  agente informa a ausencia em vez de estimar, e a simulacao de viagem nao
  esta disponivel para ele.
- **Fiat Strada** e **Mercedes-Benz C 200** so aparecem na tabela de 2025.
- **BMW X1** e **Porsche 718 Boxster** tiveram a versao do catalogo ajustada
  para a que existe em ambas as fontes (sDrive20i 2.0 e GTS 4.0).
- Nos demais casos em que a versao de entrada da FIPE nao esta no PBE
  Veicular, foi usada a versao mais proxima. A coluna `versao_pbev` registra
  exatamente qual linha do Inmetro alimentou cada modelo.

## 3. Precos de combustivel — ANP

| Item | Valor |
| --- | --- |
| Fonte | Levantamento de precos de combustiveis, ANP |
| Pagina | https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis |
| Dataset | `dados/processados/precos_combustivel_anp.csv` |
| Script | `scripts/coletar_precos_anp.py` |
| Estado | Coletado automaticamente |

A ANP publica o levantamento semanal em CSV aberto, posto a posto, com regiao,
estado, municipio, produto, data da coleta e valor de venda. O script baixa o
arquivo mais recente de gasolina/etanol e de diesel e agrega por estado.

**Mediana, nao media.** A base inclui postos de rodovia e de regioes isoladas
com precos muito acima do restante. A media seria puxada por esses extremos; a
mediana representa melhor o que se paga. O dataset guarda tambem minimo, maximo
e numero de postos, para que a dispersao fique visivel.

**Descoberta dos links.** O script le a pagina da ANP e escolhe o arquivo mais
recente, em vez de montar a URL por regra. Os nomes mudam a cada mes — ha
`01-dados-abertos-precos-gasolina-etanol.csv`, mas tambem
`02-cados-abertos-preco-gasolina-etanol.csv`, com erro de digitacao, e
`06-dados-abertos-precos-2026-06-gasolina-etanol.csv`. Alem disso ha meses
faltando na sequencia. Montar a URL quebraria na proxima atualizacao.

Para atualizar:

```bash
python scripts/coletar_precos_anp.py
```

## 4. Manuais de montadora

| Item | Valor |
| --- | --- |
| Fonte | Sites oficiais das montadoras |
| Pasta | `dados/brutos/documentos/manuais/` |
| Catalogo | `dados/manuais.csv` |
| Estado | Inclusao manual, opcional |

Diferente das demais, esta fonte nao e automatizavel. Verificacao feita durante
a construcao do projeto:

- **Volkswagen** — 279 PDFs com link direto na pagina de manuais, download
  automatizado funciona
- **Toyota** — a pagina abre, mas o servidor que hospeda os PDFs devolve 403
- **Honda** — a propria pagina de manuais devolve 403

Como a cobertura seria desigual entre as marcas, nenhum manual entra por
padrao. Quem quiser inclui os seus seguindo [`MANUAIS.md`](MANUAIS.md).

## 5. Ficha tecnica

| Item | Valor |
| --- | --- |
| Arquivo | `dados/processados/fichas_tecnicas.csv` |
| Estado | **Curadoria manual — pendente de conferencia** |

Motor, potencia, torque, cambio, tracao, capacidade do tanque e porta-malas
foram preenchidos manualmente. **Consumo e autonomia nao estao neste arquivo**:
vem do PBE Veicular, para que cada arquivo tenha uma unica procedencia.

> **Aviso.** Os valores desta planilha ainda nao foram conferidos um a um
> contra o material oficial das montadoras. Sao coerentes com as versoes
> indicadas e servem para exercitar o agente, mas nao devem ser tratados como
> referencia definitiva ate a revisao ser concluida. O agente informa essa
> limitacao ao usuario.

Note que os dados que mais importam para as respostas do agente — preco e
consumo — vem de fonte oficial e nao dependem desta conferencia.

Conferencia pendente, por modelo:

- [ ] Potencia e torque contra a ficha da montadora
- [ ] Capacidade do tanque e do porta-malas
- [ ] Cambio e tracao da versao exata

## 6. Escopo do catalogo

28 modelos, ano 2024, cobrindo hatch de entrada, hatch popular, picape
compacta e media, SUV compacto e medio, sedan compacto, medio e premium,
eletricos, esportivos e superesportivo.

O catalogo e deliberadamente restrito. Ampliar significa acrescentar linhas
em `dados/catalogo_semente.csv` e em `dados/processados/fichas_tecnicas.csv`
usando o mesmo `id`, e rodar novamente a coleta de precos.


## 7. Provedor de modelos de IA

| Item | Valor |
| --- | --- |
| Padrao | Google Gemini (`gemini-2.0-flash` e `models/text-embedding-004`) |
| Alternativa | NVIDIA NIM (`meta/llama-3.3-70b-instruct` e `nvidia/nv-embedqa-e5-v5`) |
| Selecao | Variavel `PROVEDOR_LLM` no `.env` |

Os dois provedores implementam a mesma porta `ProvedorLLM`. Trocar entre eles
nao exige alteracao de codigo.

O Gemini e o padrao por decisao operacional: durante a construcao do projeto a
conta da NVIDIA ficou sem permissao de inferencia — a chave era gerada, mas
toda chamada a `/v1/chat/completions` e a `/v1/embeddings` respondia
`403 Authorization failed`, igual a uma chave invalida. Como a liberacao depende
do suporte da NVIDIA, o projeto passou a usar o Gemini, que libera a chave na
hora e sem cadastro adicional.

O adaptador da NVIDIA permanece no projeto e volta a ser usado trocando uma
linha no `.env`.
