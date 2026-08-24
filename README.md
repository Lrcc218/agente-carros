<h1 align="center">Consultor de Veículos</h1>

<p align="center">
  <em>Agente de IA que responde perguntas dos colaboradores de uma concessionária
  a partir dos documentos e dados oficiais da operação.</em>
</p>

<p align="center">
  <img alt="Status" src="https://img.shields.io/badge/status-no%20ar-brightgreen">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="LangChain" src="https://img.shields.io/badge/LangChain-1.3-1c3c3c">
  <img alt="Streamlit" src="https://img.shields.io/badge/Streamlit-1.61-ff4b4b">
  <img alt="Deploy" src="https://img.shields.io/badge/deploy-Oracle%20Cloud-c74634">
  <img alt="HTTPS" src="https://img.shields.io/badge/HTTPS-Let's%20Encrypt-003a70">
  <img alt="Testes" src="https://img.shields.io/badge/testes-124%20passando-brightgreen">
  <img alt="Licença" src="https://img.shields.io/badge/licen%C3%A7a-MIT-green">
</p>

> **Challenge Alura — ONE IA for Tech.** Agente corporativo de base de
> conhecimento, publicado na Oracle Cloud Infrastructure.

<!-- PENDENTE: imagem de capa. Sugestão: um print da conversa, 1280x640,
     salvo em docs/imagens/capa.png e referenciado aqui.
<p align="center">
  <img src="docs/imagens/capa.png" alt="Consultor de Veículos" width="720">
</p>
-->

## Status do projeto

✅ **No ar.** O agente responde, os dados estão coletados, o índice cobre os três
acervos e a aplicação está publicada e funcionando na Oracle Cloud
Infrastructure. Falta apenas registrar a evidência em imagem e vídeo.

| Etapa | Situação |
| --- | --- |
| Coleta e curadoria dos dados | ✅ concluída |
| Processamento e indexação | ✅ concluída |
| Agente, ferramentas e recuperação | ✅ concluída |
| Interface e registro de execução | ✅ concluída |
| Preparação do deploy na OCI | ✅ concluída |
| Publicação na OCI | ✅ concluída |
| Evidência em imagem e vídeo | ⏳ pendente |

## Demonstração

**🟢 Aplicação no ar:** **https://consultor-autoluz.duckdns.org**

Publicada em instância própria na **Oracle Cloud Infrastructure**, região
`sa-vinhedo-1`: Ubuntu 24.04, nginx como proxy reverso, HTTPS com certificado
Let's Encrypt e renovação automática, e o processo supervisionado por systemd.

Resposta real do agente rodando no servidor, à pergunta *"Até quanto de desconto
um consultor de vendas pode dar sozinho?"*:

```
O consultor de vendas pode conceder sozinho um desconto de até 2% sobre o preço
de venda anunciado do veículo (excluídos emplacamento e documentação).

Acima disso, as alçadas são:
- Até 2%:              Consultor de vendas
- Acima de 2% até 5%:  Gerente da unidade
- Acima de 5% até 8%:  Gerência Regional
- Acima de 8%:         Diretoria Comercial

Lembre-se de que a alçada é por negócio e o desconto deve ser registrado na
proposta com o respectivo motivo. Dividir o desconto entre veículo e acessórios
para caber na alçada é considerado burla e falta disciplinar.
```

O agente localizou a informação na **Política Comercial e de Precificação**,
citou a fonte e ainda trouxe a ressalva sobre burla de alçada — que está no
documento, não no modelo.

Registro de execução do servidor no mesmo instante, medido em produção:

```
Volume                     1 pergunta respondida, 0 falhas
Tempo de resposta          mediana 3,2 s
Ferramentas acionadas      1  buscar_documentos_oficiais
Documentos citados         1  Política Comercial e de Precificação
                           1  Manual de Perguntas Frequentes
```

> ⏳ **Pendente:** captura de tela e vídeo da conversa na interface web.

## O contexto

O projeto simula a base de conhecimento interna da **Autoluz Veículos**, uma rede
de concessionárias fictícia. O agente é aberto a qualquer colaborador e responde
às perguntas que hoje obrigam a abrir quatro abas e ainda fazer conta na mão:

| Área | O que o agente cobre |
| --- | --- |
| **Comercial** | Tabela de preços FIPE, comparação entre modelos, filtro por faixa de preço |
| **Produto** | Ficha técnica, consumo oficial, eficiência energética |
| **Pós-venda** | Manual do proprietário: revisão, fluidos, pneus, garantia |
| **Atendimento** | Simulação do custo real de uma viagem, com o preço de combustível do estado do cliente |

Os dados de veículos são **reais e de fonte oficial** — Tabela FIPE, PBE Veicular
do Inmetro e levantamento de preços da ANP. Fictícios são a empresa e o seu
acervo de políticas internas, escrito para dar contexto corporativo ao agente:

| Documento | Páginas | Área |
| --- | --- | --- |
| Manual de Garantia e Pós-venda | 6 | Pós-venda |
| Política Comercial e de Precificação | 5 | Comercial |
| Política de Privacidade e Proteção de Dados | 5 | Jurídico |
| Manual de Perguntas Frequentes | 4 | Comunicação |
| Manual de Onboarding | 4 | Recursos Humanos |
| Tabela de Serviços e Alçadas da Oficina | 4 | Pós-venda |
| Diretório de Áreas Responsáveis | 4 | Comunicação |

**32 páginas em PDF**, formato uniforme, como se espera de uma base documental
corporativa. As fontes ficam em Markdown, em
[`dados/documentos_corporativos/_fontes/`](dados/documentos_corporativos/_fontes/),
e os PDFs são gerados por `python scripts/gerar_pdfs.py`.

A separação vale a pena por três motivos: Markdown se revisa em diff, cláusula a
cláusula, enquanto diff de PDF só diz que o binário mudou; PDF preserva o número
da página, então a resposta do agente cita documento **e** página; e a pasta de
fontes começa com sublinhado, ficando fora da indexação — indexar fonte e PDF
duplicaria cada trecho.

O **Diretório de Áreas** merece nota: quando o agente não encontra a resposta, ele
não pode simplesmente parar. Esse arquivo dá a ele a área responsável, o e-mail e
o prazo de resposta, para encaminhar em vez de improvisar.

## Estrutura do repositório

```
app/      interfaces: web (Streamlit) e terminal
src/      código do agente: domínio, adaptadores, ferramentas
dados/    catálogo, preços, acervo corporativo e índice vetorial
scripts/  pipeline de tempo de construção e utilitários
infra/    implantação na Oracle Cloud: provisionamento, systemd, nginx
docs/     documentação do projeto
testes/   suíte de testes
```

## Documentação

| Documento | O que cobre |
| --- | --- |
| Este README | Descrição, arquitetura, execução e exemplos |
| [Manual do Sistema](docs/Manual_do_Sistema.pdf) — [fonte](docs/MANUAL_DO_SISTEMA.md) | **17 páginas.** Referência técnica completa: arquitetura, catálogo de componentes e ferramentas, ciclo de vida de uma pergunta, decisões de arquitetura, operação e glossário |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Runbook da publicação na OCI |
| [docs/FONTES.md](docs/FONTES.md) | Procedência de cada dado |
| [docs/MANUAIS.md](docs/MANUAIS.md) | Como incluir manuais de montadora |

## Índice

- [Estrutura do repositório](#estrutura-do-repositório)
- [Documentação](#documentação)
- [O que ele faz](#o-que-ele-faz)
- [Exemplos de perguntas](#exemplos-de-perguntas)
- [Exemplos de respostas](#exemplos-de-respostas)
- [O que ele nao faz](#o-que-ele-nao-faz)
- [Arquitetura](#arquitetura)
- [Registro de execução e qualidade](#registro-de-execução-e-qualidade)
- [Tecnologias](#tecnologias)
- [Como executar](#como-executar)
- [Deploy](#deploy)
- [Fontes de dados](#fontes-de-dados)
- [Testes](#testes)
- [Limitacoes conhecidas](#limitacoes-conhecidas)
- [Autor](#autor)
- [Licença](#licença)

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
carro nao custa o mesmo saindo de Sao Paulo e saindo do Amapa, e o agente
reflete isso.

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
| "Ate quanto de desconto posso dar sozinho?" | Politica Comercial, alcadas por faixa |
| "Cliente atrasou a revisao. Perdeu a garantia?" | Manual de Garantia, criterio de nexo causal |
| "Quanto custa a revisao de 40 mil km?" | Tabela de Servicos da oficina |
| "Cliente pediu para excluir os dados dele. O que faco?" | Politica de Privacidade e prazo da LGPD |
| "Qual o valor do vale-refeicao?" | Manual de Onboarding |
| "Com quem falo sobre um recall?" | Diretorio de Areas Responsaveis |

Resposta real da ferramenta de simulacao, para uma viagem de 300 km saindo de
Minas Gerais no Jeep Compass:

```
Simulação para Jeep Compass Serie S T270 1.3 Turbo 2024
  Distância total: 300 km
  Divisão do percurso: 40% cidade, 60% estrada

  Gasolina a R$ 6,32 por litro:
    Consumo médio na viagem: 11,21 km/l
    Combustível necessário: 26,76 litros
    Custo total: R$ 169,11
    Custo por quilômetro: R$ 0,56
    Tanques necessários: 0,49

  Etanol a R$ 3,99 por litro:
    Consumo médio na viagem: 8,03 km/l
    Combustível necessário: 37,37 litros
    Custo total: R$ 149,10
    Custo por quilômetro: R$ 0,50
    Tanques necessários: 0,68

  Com os preços informados, o etanol custa R$ 20,01 a menos nesta viagem.
  Preços de combustível: mediana de MG (levantamento da ANP de 01/07/2026 a 31/07/2026).
  Consumo conforme o PBE Veicular do Inmetro, versão Utilitário Esportivo Grande JEEP COMPASS SERIE S T 1.3T-16V.
  Valores de referência medidos em condições de ensaio. O consumo real varia com carga, ar-condicionado, relevo e estilo de condução.
```

## Exemplos de respostas

As saídas abaixo são **reais e reproduzíveis**: vêm das ferramentas, que são
determinísticas e não dependem do modelo de linguagem. Rodando o projeto com os
mesmos dados, você obtém exatamente isto.

Comparação entre dois modelos — `comparar_veiculos(["onix", "hb20"])`:

```
Chevrolet Onix LT 1.0 Turbo 2024
  Categoria: hatch_popular
  Motor: 1.0 turbo
  Potência: 116 cv | Torque: 16.8 kgfm
  Câmbio: Automatico 6 marchas | Tração: Dianteira
  Porta-malas: 275 litros
  Consumo: 12.1 km/l cidade, 15.3 km/l estrada; com etanol: 8.6 / 10.9 km/l
  Classificação de eficiência (Inmetro): C
  Preço FIPE: R$ 69.024,00
  Referência FIPE: agosto de 2026

Hyundai HB20 Sense 1.0 Flex 2024
  Categoria: hatch_popular
  Motor: 1.0 aspirado
  Potência: 80 cv | Torque: 10.2 kgfm
  Câmbio: Manual 5 marchas | Tração: Dianteira
  Porta-malas: 300 litros
  Consumo: 13.3 km/l cidade, 15.4 km/l estrada; com etanol: 9.9 / 10.7 km/l
  Classificação de eficiência (Inmetro): B
  Preço FIPE: R$ 66.644,00
  Referência FIPE: agosto de 2026
```

SUVs compactos ordenados por consumo na estrada —
`listar_veiculos(categoria="suv_compacto", ordenar_por="consumo_estrada")`:

```
8 veículos, ordenados por consumo na estrada:
- Volkswagen Nivus Comfortline 200 TSI 2024 | R$ 103.810,00 | 128 cv | 12.4 / 14.8 km/l
- Volkswagen T-Cross Sense 200 TSI 2024     | R$ 100.649,00 | 128 cv | 12.1 / 14.5 km/l
- Nissan Kicks Sense 1.0 Turbo 2024         | R$ 105.525,00 | 125 cv | 11.7 / 14.3 km/l
- Honda HR-V EX 1.5 Flex 2024               | R$ 136.896,00 | 126 cv | 12.5 / 13.9 km/l
- Chevrolet Tracker LT 1.0 Turbo 2024       | R$ 100.583,00 | 116 cv | 11.5 / 13.8 km/l
- Hyundai Creta Comfort 1.0 Turbo 2024      | R$ 101.814,00 | 120 cv | 12.0 / 12.7 km/l
- Jeep Renegade Longitude T270 2024         | R$ 101.940,00 | 185 cv | 11.1 / 12.4 km/l
- Renault Duster Iconic 1.6 CVT 2024        | R$  81.402,00 | 120 cv | 10.8 / 11.4 km/l
```

A simulação de viagem completa está na seção anterior.

> ⏳ **Conversas completas do agente** — pergunta do colaborador, escolha da
> ferramenta e texto final redigido pelo modelo — entram aqui junto com as
> capturas de tela, depois da publicação. Ver [Demonstração](#demonstração).

## O que ele nao faz

Recusar bem e parte do projeto. O agente responde que nao sabe, em vez de
inventar, nestes casos:

| Pergunta | Por que recusa |
| --- | --- |
| "Quanto gasta o Fiat Uno?" | Fora do catalogo. Ele diz isso e sugere modelos parecidos |
| "Quanto custa carregar o BYD Dolphin numa viagem?" | O catalogo tem km/l equivalente e autonomia, mas nao kWh, entao o custo em reais nao e calculavel |
| "Qual a pressao dos pneus do Honda City?" | So o Corolla tem manual indexado; ele diz isso em vez de estimar |
| "Quanto gasto com o Corolla?" | O termo casa com Corolla e Corolla Cross; ele pede para desambiguar antes de simular |
| "Vale a pena financiar em 48 vezes?" | Nao da conselho financeiro nem simula financiamento |
| "Quanto vai valer esse carro em 2030?" | Nao projeta valor de revenda |
| "Qual o melhor carro?" | Sem criterio nao ha resposta objetiva; ele pede o criterio |
| "O cliente Joao, CPF 123..., reclamou de..." | A politica de privacidade proibe tratar dado pessoal em IA; ele responde pela regra geral |
| "Qual a politica de home office?" | Nao ha documento sobre isso; ele indica o RH em vez de inventar |

## Arquitetura

O agente e **hibrido**: cada tipo de pergunta vai para o mecanismo certo.

```
                        pergunta do usuario
                                |
                        [ agente / tool calling ]
                                |
        +-----------------------------+-----------------------------+
        |                             |                             |
  resumo_catalogo               simular_viagem          buscar_documentos_oficiais
  buscar_veiculo         consultar_precos_combustivel      (RAG semantico)
  listar_veiculos        ranking_precos_por_estado                |
  comparar_veiculos                  |                            |
        |                            |                            |
   pandas sobre CSV          calculo em Python          FAISS + embeddings
        |                            |                            |
  precos FIPE +               precos da ANP              PDFs do Inmetro
  ficha + consumo             por estado                 + manual do Corolla
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

### O caminho de um documento até a resposta

```
documento              PDF, Word, Excel, PowerPoint, Markdown, CSV, JSON, HTML
   |
extração               PyPDF para PDF; leitores dedicados por formato.
   |                   Planilha vira uma frase por linha, com o cabeçalho
   |                   repetido — tabela em colunas perde a legenda no
   |                   primeiro corte e devolve número órfão.
   |
fatiamento             2400 caracteres, 200 de sobreposição
   |
metadados              título, arquivo, formato, tipo (manual ou oficial), página
   |
embeddings             gerados uma vez, em tempo de construção
   |
índice FAISS           versionado no repositório
   |
recuperação            filtro por tipo -> similaridade -> limiar de relevância
   |
resposta               o modelo redige citando documento e página; sem trecho
                       acima do limiar, ele diz que não encontrou
```

Duas salvaguardas contra a resposta confiante e errada:

- **Filtro por metadado antes da similaridade.** Uma pergunta sobre garantia não
  deve trazer trecho da tabela do Inmetro só porque ele também fala de veículos.
  O agente escolhe o `tipo` ao chamar a ferramenta; se o filtro ficar estreito
  demais e não devolver nada, a busca é refeita no acervo inteiro.
- **Limiar de relevância.** Busca vetorial sempre devolve alguma coisa, mesmo
  quando não há nada pertinente — os vizinhos mais próximos de uma pergunta fora
  do escopo continuam sendo vizinhos. O limiar descarta o que ficou abaixo da
  régua, e sem nada acima dela a ferramenta responde que não encontrou.

  O limiar vem **desligado por padrão**, de propósito: um corte sem calibração
  descarta trecho bom em silêncio, o que é pior do que trecho ruim visível. Para
  calibrar, rode perguntas reais e leia as relevâncias com
  `python scripts/relatorio_execucoes.py`, depois defina `LIMIAR_RELEVANCIA`.

### Tempo de construcao e tempo de execucao

Toda coleta e todo processamento pesado acontecem antes, em scripts, e o
resultado e versionado no repositorio:

```
tempo de construcao (scripts, rodam sob demanda)
  coletar_fipe.py           API da FIPE       -> dados/processados/precos_fipe.csv
  coletar_precos_anp.py     CSV aberto da ANP -> dados/processados/precos_combustivel_anp.csv
  baixar_documentos.py      Inmetro           -> dados/brutos/documentos/
  extrair_consumo_pbev.py   PDFs do Inmetro   -> dados/processados/consumo_pbev.csv
  gerar_pdfs.py             fontes Markdown   -> PDFs do acervo e docs/
  indexar_documentos.py     acervo + embeddings -> dados/processados/indice_faiss/

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
  registro.py          Registro de execucao e de feedback, em JSON Lines
  documentos.py        Leitura dos formatos do acervo: Word, Excel, PPT, HTML, CSV, JSON
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
  fabrica.py           Ligacao: une as implementacoes concretas as portas
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
  relatorio_execucoes.py  Resume o registro: latencia, ferramentas, qualidade
  gerar_pdfs.py           Gera os PDFs do acervo a partir das fontes Markdown
infra/oci/
  provisionar.sh          Instala tudo na instancia da OCI, de forma idempotente
  publicar.sh             Atualiza a versao no ar, com reversao automatica
  criar-instancia.sh      Cria a VM insistindo enquanto nao ha capacidade ARM
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

## Registro de execução e qualidade

Cada pergunta respondida vira uma linha de JSON num arquivo diário: pergunta,
resposta, ferramentas acionadas, documentos citados, duração, provedor, modelo e
sessão. Sem esse rastro não há como auditar depois por que uma resposta saiu como
saiu, nem medir com que frequência o agente não encontra material.

```
registros/execucoes-2026-08-23.jsonl
```

O formato **JSON Lines** é proposital: cresce por acréscimo, nunca precisa ser
reescrito inteiro e se lê com `grep` e `jq` sem infraestrutura nenhuma. O registro
**nunca derruba a conversa** — se o disco encher ou o caminho for somente leitura,
a falha de escrita é engolida e o agente continua respondendo. Há teste fixando
esse comportamento.

Cada resposta na interface traz **👍 / 👎**. O clique vira outra linha no mesmo
arquivo, referenciando o id da execução. Feedback só vale se voltar para quem
mantém o agente:

```bash
python scripts/relatorio_execucoes.py           # volume, latência, ferramentas, qualidade
python scripts/relatorio_execucoes.py --ruins   # só o que foi avaliado com 👎
```

O relatório responde às perguntas de manutenção: qual a mediana e o p95 do tempo
de resposta, quais ferramentas são realmente usadas, quais documentos são citados,
e **quais perguntas não encontraram material** — que é a lista de candidatas a
novo documento na base.

Não guardamos nada que identifique quem perguntou: a sessão é um id aleatório por
aba aberta, que serve só para ligar as perguntas de uma mesma conversa.

## Tecnologias

| Tecnologia | Papel |
| --- | --- |
| Python 3.10+ | Linguagem |
| LangChain | Orquestracao do agente e tool calling |
| Google Gemini | Modelo de chat e de embeddings (padrao) |
| NVIDIA NIM | Provedor alternativo, selecionavel por variavel de ambiente |
| FAISS | Indice vetorial local |
| pandas | Consulta aos dados estruturados |
| pypdf | Leitura dos PDFs |
| python-docx, openpyxl, python-pptx, beautifulsoup4 | Leitura de Word, Excel, PowerPoint e HTML |
| reportlab | Geração dos PDFs do acervo e da documentação |
| Streamlit | Interface web |
| pytest | Testes |
| Oracle Cloud (OCI) | Hospedagem, camada Always Free |
| nginx e systemd | Proxy reverso, TLS e supervisao do processo |

## Como executar

Pré-requisitos: Python 3.10 ou superior e uma chave de API gratuita de um dos
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
restrita e nunca imprime o valor. Se preferir fazer a mao, copie `.env.example` para
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

Ou pergunte direto pelo terminal:

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

O projeto e publicado numa instancia **Always Free da Oracle Cloud
Infrastructure**: Ubuntu 24.04 em ARM Ampere A1, com 1 OCPU e 6 GB.

```
internet -> nginx :80/:443 -> streamlit :8501 (loopback) -> agente
                              systemd, usuario proprio, sem shell
```

A preparacao inteira esta versionada em [`infra/oci/`](infra/oci/), e o
passo a passo com os tropecos conhecidos, em [`docs/DEPLOY.md`](docs/DEPLOY.md).
Resumido:

```bash
# 1. criar a VM, insistindo enquanto nao ha capacidade ARM livre
cp infra/oci/instancia.env.exemplo infra/oci/instancia.env
./infra/oci/criar-instancia.sh

# 2. a VM se provisiona sozinha pelo cloud-init; falta so o segredo
ssh ubuntu@<ip> 'sudo nano /etc/agente-carros/ambiente'
ssh ubuntu@<ip> 'sudo systemctl start agente-carros'

# 3. publicar versoes novas
./infra/oci/enviar.sh
```

Tres decisoes que valem registro:

- **A chave nunca entra no repositorio nem no `user_data`.** Ela vive em
  `/etc/agente-carros/ambiente`, com permissao 0640, fora do diretorio da
  aplicacao. O `user_data` de uma instancia fica legivel no console e nos
  metadados, entao segredo ali seria segredo exposto.
- **O servidor so consome o que ja foi construido.** Nenhum script de coleta
  e nenhuma geracao de embedding roda em producao: o `git clone` traz os CSVs
  e o indice FAISS prontos. E a mesma separacao entre tempo de construcao e
  tempo de execucao descrita acima, agora pagando o proprio custo.
- **Publicacao com reversao automatica.** Se a sonda de saude nao responder
  depois do restart, o `publicar.sh` volta para a revisao anterior em vez de
  deixar a aplicacao fora do ar.

O mesmo aplicativo sobe sem alteracao no **Streamlit Community Cloud** —
apontar `app/streamlit_app.py` e colocar `GOOGLE_API_KEY` nos secrets basta,
porque o indice vetorial ja esta versionado. Que os dois caminhos custem o
mesmo esforco e consequencia do desacoplamento: nada abaixo de `app/` sabe
onde esta rodando.

## Fontes de dados

| Dado | Fonte | Estado |
| --- | --- | --- |
| Preco do veiculo | Tabela FIPE, via API publica | Coletado automaticamente |
| Consumo e autonomia | PBE Veicular 2026 e 2025, Inmetro | Extraido do PDF oficial |
| Preco de combustivel | Levantamento de precos da ANP, CSV aberto | Coletado automaticamente |
| Metodologia de consumo | Inmetro | PDF oficial indexado |
| Manuais de montadora | Sites oficiais das marcas | Corolla indexado; 24 guardados |
| Ficha tecnica | Curadoria manual | Em conferencia |
| Politicas internas | Acervo da empresa ficticia | Escrito e versionado |

### Formatos aceitos na indexacao

Basta soltar o arquivo em `dados/brutos/documentos/` e rodar
`python scripts/indexar_documentos.py`:

| Formato | Tratamento |
| --- | --- |
| PDF | Texto por pagina, com o numero da pagina preservado na citacao |
| Word (.docx) | Paragrafos e tabelas |
| Excel (.xlsx) | Uma frase por linha, com o cabecalho repetido |
| PowerPoint (.pptx) | Texto de cada slide mais as notas do apresentador |
| HTML | Texto limpo, sem script, estilo, navegacao e rodape |
| CSV | Uma frase por linha; o separador e detectado |
| JSON | Achatado em `caminho.ate.folha: valor` |
| Markdown e texto | Direto |

As bibliotecas de cada formato sao importadas sob demanda: um acervo so de PDF
funciona sem elas, e a falta de uma vira aviso no arquivo que a exigia, nao erro
na inicializacao.

Para acrescentar manuais do proprietario ao indice, veja
[`docs/MANUAIS.md`](docs/MANUAIS.md). Os sites das montadoras bloqueiam
download automatizado, entao esses PDFs entram à mão.

Detalhes de procedencia, criterios de selecao e divergencias entre as fontes
estao em [`docs/FONTES.md`](docs/FONTES.md).

Cada registro de consumo guarda a linha original do PDF do Inmetro, de modo que
qualquer numero pode ser conferido contra a fonte.

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

124 testes cobrindo o calculo da viagem, as consultas ao catalogo, a resolucao de
precos por estado, a selecao de provedor e credencial, a camada de recuperacao, a
leitura dos formatos de documento e o registro de execucao — as partes onde um
erro viraria uma resposta errada com aparencia de certeza.

Dois merecem nota.

O primeiro: a simulacao **soma os litros gastos em cada trecho** em
vez de aplicar a media dos consumos sobre a distancia total. Media aritmetica
de km/l subestima o gasto, porque consumo e uma razao invertida. Ha teste
fixando esse comportamento.

O segundo: a leitura de planilha **repete o cabecalho em cada linha**, de modo
que "modelo: Corolla | preco: 145000" sobreviva ao fatiamento. Uma tabela em
colunas perde o cabecalho no primeiro corte, e o trecho recuperado vira uma
fileira de numeros sem legenda — que o modelo entao atribui ao carro errado.

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

## Autor

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/Lrcc218">
        <img src="https://github.com/Lrcc218.png" width="100" alt="Foto de perfil" style="border-radius:50%"><br>
        <sub><b>Lrcc218</b></sub>
      </a>
    </td>
  </tr>
</table>

Projeto desenvolvido para o **Challenge Alura — ONE IA for Tech**.

## Licença

Distribuído sob a licença MIT. Veja [`LICENSE`](LICENSE) para o texto completo.

Os documentos de terceiros usados pelo projeto — tabelas do PBE Veicular do
Inmetro, dados da Tabela FIPE, levantamento de preços da ANP e manuais de
proprietário das montadoras — permanecem sob os direitos de seus titulares e são
usados aqui para fins de estudo, com a fonte citada em
[`docs/FONTES.md`](docs/FONTES.md).
