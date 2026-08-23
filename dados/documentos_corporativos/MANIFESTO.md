# Acervo corporativo — Autoluz Veículos

Base de conhecimento interna da empresa fictícia que dá contexto ao projeto.
São **sete documentos em PDF, 32 páginas**, versionados no repositório — ao
contrário dos PDFs de `dados/brutos/documentos/`, que são baixados por script e
ficam fora do controle de versão.

O indexador lê esta pasta junto com a de documentos baixados e marca tudo o que
vem daqui com o metadado `tipo: documento_interno`, o que permite ao agente
restringir a busca antes de comparar similaridade.

> **Empresa fictícia.** A Autoluz Veículos não existe. Nomes, endereços de
> e-mail, telefones, valores de benefício e unidades são inventados para dar um
> contexto corporativo coerente ao agente, como o challenge propõe. Já os dados
> de veículos — preços FIPE, consumo do Inmetro, preços de combustível da ANP —
> são **reais e de fonte oficial**, com procedência registrada em `docs/FONTES.md`.

## PDF gerado, Markdown revisado

Os documentos são **distribuídos e indexados em PDF**, formato uniforme para
todo o acervo, como se espera de uma base documental corporativa. As fontes
ficam em `_fontes/`, em Markdown.

A separação tem três motivos:

- **Markdown se revisa.** Um diff de política mostra exatamente a cláusula que
  mudou; um diff de PDF mostra que o arquivo binário mudou.
- **PDF cita página.** O extrator preserva o número da página, então a resposta
  do agente aponta documento *e* página — rastreabilidade que Markdown não dá.
- **A pasta começa com sublinhado**, e por isso o indexador a ignora. Indexar
  fonte e PDF duplicaria cada trecho no índice, degradando a recuperação.

Para regerar os PDFs depois de editar uma fonte:

```
python scripts/gerar_pdfs.py              # regera tudo
python scripts/gerar_pdfs.py --conferir   # só verifica se estão em dia
```

O script guarda a assinatura de cada fonte, então `--conferir` acusa PDF
desatualizado — útil antes de indexar ou publicar.

## Documentos

## Manual de Garantia e Pós-venda
- Arquivo: `politica_garantia_pos_venda.pdf`
- Fonte: `_fontes/politica_garantia_pos_venda.md`
- Páginas: 6
- Área: Pós-venda / Qualidade
- Cobre: prazos de garantia, cobertura e exclusões, procedimento de atendimento,
  revisões e perda de garantia, elétricos e híbridos, casos de fronteira,
  prazos de resposta e fluxo de escalonamento.

## Política Comercial e de Precificação
- Arquivo: `politica_comercial_precificacao.pdf`
- Fonte: `_fontes/politica_comercial_precificacao.md`
- Páginas: 5
- Área: Diretoria Comercial
- Cobre: formação de preço, papel da Tabela FIPE, alçadas de desconto, avaliação
  de usados, sinal e reserva, financiamento e CET, test drive, frotas e PCD,
  publicidade e condutas vedadas.

## Política de Privacidade e Proteção de Dados
- Arquivo: `politica_privacidade_lgpd.pdf`
- Fonte: `_fontes/politica_privacidade_lgpd.md`
- Páginas: 5
- Área: Jurídico / Compliance
- Cobre: bases legais, dados tratados, prazos de retenção, direitos do titular,
  compartilhamento, segurança da informação, incidentes e regras de uso de
  inteligência artificial.

## Manual de Perguntas Frequentes
- Arquivo: `faq_atendimento.pdf`
- Fonte: `_fontes/faq_atendimento.md`
- Páginas: 4
- Área: Comunicação Corporativa
- Cobre: dúvidas de clientes sobre compra, entrega, garantia e elétricos; e
  dúvidas de colaboradores sobre alçadas, pós-venda, dados e recursos humanos.

## Manual de Onboarding
- Arquivo: `manual_onboarding.pdf`
- Fonte: `_fontes/manual_onboarding.md`
- Páginas: 4
- Área: Recursos Humanos
- Cobre: história e princípios da rede, estrutura, jornada e ponto, remuneração
  e benefícios, os primeiros trinta dias, ferramentas, conduta, carreira e canais.

## Tabela de Serviços e Alçadas da Oficina
- Arquivo: `tabela_servicos_oficina.pdf`
- Fonte: `_fontes/tabela_servicos_oficina.md`
- Páginas: 4
- Área: Pós-venda
- Cobre: preços de referência e prazos por serviço, alçadas de desconto por
  faixa, prazos máximos de atendimento e regras de cobrança.

## Diretório de Áreas Responsáveis
- Arquivo: `contatos_areas.pdf`
- Fonte: `_fontes/contatos_areas.md`
- Páginas: 4
- Área: Comunicação Corporativa
- Cobre: área responsável por cada assunto, com e-mail, telefone, horário e
  prazo de resposta; níveis de escalonamento do pós-venda; unidades da rede.
- **Por que importa:** quando o agente não encontra a resposta, ele deve indicar
  a área responsável em vez de arriscar. Este documento é a fonte dessa indicação.

## Como acrescentar um documento

1. Escreva a fonte em `_fontes/`, em Markdown, seguindo o padrão dos existentes:
   título, bloco de versão e departamento, sumário e seções numeradas.
2. Rode `python scripts/gerar_pdfs.py` para produzir o PDF.
3. Declare-o acima, no mesmo formato: um cabeçalho `##` com o título e uma linha
   ``- Arquivo: `nome.pdf` ``. O título declarado aqui é o que o agente cita como
   fonte ao responder.
4. Rode `python scripts/indexar_documentos.py`.
5. Confira com `python scripts/diagnosticar.py`.

Sem a declaração, o nome do arquivo vira o título — o que funciona, mas rende
citação feia na resposta.

**Documento em outro formato.** O extrator aceita Word, Excel, PowerPoint, HTML,
CSV, JSON e texto, além de PDF. Um documento que chegue pronto nesses formatos
pode ser colocado direto nesta pasta, sem fonte em Markdown. O que se recomenda
é o caminho acima, para manter o acervo uniforme e revisável.
