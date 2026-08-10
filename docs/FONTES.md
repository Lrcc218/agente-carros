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
| Arquivo | `dados/brutos/documentos/` (baixado pelo script) |
| Script | `scripts/baixar_documentos.py` |
| Estado | Documento oficial baixado; extracao dos valores feita manualmente |

O Inmetro publica a tabela apenas em PDF, sem versao em planilha. Para o
recorte deste projeto a extracao dos valores de consumo foi feita a mao,
modelo a modelo, em vez de automatizada — extracao de tabela em PDF e
pouco confiavel e erra em silencio, o que seria pior do que a curadoria
manual num catalogo deste tamanho.

O PDF permanece no projeto e e indexado para busca semantica, de modo que
o agente tambem responde sobre a metodologia da etiquetagem e o significado
das faixas de eficiencia.

## 3. Ficha tecnica

| Item | Valor |
| --- | --- |
| Arquivo | `dados/processados/fichas_tecnicas.csv` |
| Estado | **Curadoria manual — pendente de conferencia** |

Motor, potencia, torque, cambio, tracao, capacidade do tanque, porta-malas
e consumo foram preenchidos manualmente. A coluna `fonte_ficha` marca a
origem de cada linha.

> **Aviso.** Os valores da ficha tecnica ainda nao foram conferidos um a um
> contra o PBE Veicular e o material oficial das montadoras. Sao coerentes
> com as versoes indicadas e servem para exercitar o agente, mas nao devem
> ser tratados como referencia definitiva ate a revisao ser concluida. O
> agente informa essa limitacao ao usuario.

Conferencia pendente, por modelo:

- [ ] Consumo cidade e estrada (gasolina, etanol e diesel) contra o PBE Veicular
- [ ] Potencia e torque contra a ficha da montadora
- [ ] Capacidade do tanque e do porta-malas
- [ ] Autonomia dos eletricos (BYD Dolphin e BYD Seal)

## 4. Escopo do catalogo

28 modelos, ano 2024, cobrindo hatch de entrada, hatch popular, picape
compacta e media, SUV compacto e medio, sedan compacto, medio e premium,
eletricos, esportivos e superesportivo.

O catalogo e deliberadamente restrito. Ampliar significa acrescentar linhas
em `dados/catalogo_semente.csv` e em `dados/processados/fichas_tecnicas.csv`
usando o mesmo `id`, e rodar novamente a coleta de precos.
