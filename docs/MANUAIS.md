# Como acrescentar manuais de montadora

Os PDFs do Inmetro sao baixados por script. Manuais de montadora, nao: os
sites bloqueiam acesso automatizado. Testes feitos durante a construcao do
projeto:

| Montadora | Situacao |
| --- | --- |
| Volkswagen | 279 PDFs com link direto, download automatizado funciona |
| Toyota | Pagina abre, mas o servidor dos PDFs devolve 403 |
| Honda | A propria pagina devolve 403 |

Por isso os manuais entram por inclusao manual. O agente os indexa junto com
os documentos oficiais e passa a responder sobre operacao e manutencao —
intervalos de revisao, pressao dos pneus, especificacao de oleo, capacidades,
cobertura da garantia.

## Passo a passo

**1. Baixe o PDF pelo navegador**, no site oficial da montadora.

- Volkswagen: <https://www.vw.com.br/pt/servicos-e-acessorios/servicos-e-produtos/manuais-e-garantia/manuais.html>
- Toyota: <https://www.toyota.com.br/manuais>
- Honda, Fiat, Chevrolet e demais: area de pos-venda do site da marca

**2. Salve em** `dados/brutos/documentos/manuais/`

A pasta e criada por `python scripts/baixar_documentos.py`. Se ainda nao
existir, crie a mao. Use nomes sem espaco, no padrao `marca_modelo_ano.pdf`:

```
dados/brutos/documentos/manuais/
  volkswagen_polo_2024.pdf
  toyota_corolla_2024.pdf
```

**3. Declare o manual em** `dados/manuais.csv`

Uma linha por arquivo. O titulo declarado aqui e o que o agente cita como
fonte ao responder:

```csv
arquivo,marca,modelo,documento,origem
volkswagen_polo_2024.pdf,Volkswagen,Polo 2024,Manual do proprietario,https://www.vw.com.br/...
toyota_corolla_2024.pdf,Toyota,Corolla 2024,Manual do proprietario,https://www.toyota.com.br/manuais
```

Se um arquivo nao for declarado, o indexador usa o nome dele como titulo e
segue normalmente — a declaracao serve para a citacao ficar apresentavel e
para registrar de onde o documento veio.

**4. Reconstrua o indice**

```bash
python scripts/indexar_documentos.py
```

O script varre a pasta de documentos recursivamente, entao os manuais entram
sem nenhuma outra alteracao. Cada trecho indexado guarda se veio de documento
oficial ou de manual.

## Pastas iniciadas por sublinhado ficam fora do indice

O indexador varre `dados/brutos/documentos/` recursivamente, mas **ignora
qualquer pasta cujo nome comece com sublinhado**. Isso permite guardar
documentos junto do projeto sem que entrem no indice:

```
dados/brutos/documentos/manuais/
  toyota_corolla_manual_proprietario.pdf   <- indexado
  _pendentes/                              <- guardado, fora do indice
  _fora_do_catalogo/                       <- guardado, fora do indice
```

- `_pendentes/` — material que sera indexado mais adiante. Indexar tudo de
  uma vez esbarra na cota gratuita de embeddings, entao o acervo entra aos
  poucos.
- `_fora_do_catalogo/` — documentos de modelos que nao estao no catalogo do
  agente. Indexa-los faria o agente responder sobre carros que ele nao tem,
  que e justamente o erro que o projeto evita.

Para incluir um documento no indice, mova-o para fora dessas pastas e rode
`python scripts/indexar_documentos.py` novamente.

## Duas observacoes

**Cobertura desigual.** Se voce indexar o manual de dois carros, o agente vai
responder em profundidade sobre esses dois e nada sobre os outros vinte e
seis. Isso parece falha para quem usa. Se for incluir poucos manuais, vale
declarar no README quais modelos tem manual indexado.

**Os PDFs ficam fora do controle de versao.** A pasta `dados/brutos/` esta no
`.gitignore`. Manuais sao arquivos grandes e de propriedade das montadoras;
mante-los fora do repositorio evita redistribui-los. Quem clonar o projeto
baixa os proprios seguindo este documento.

Consequencia para o deploy: como a plataforma nao roda os scripts de
construcao, o que vai para a nuvem e o **indice ja construido**, e nao os
PDFs. Construa o indice na sua maquina, com os manuais no lugar, e faca o
commit da pasta `dados/processados/indice_faiss/`.
