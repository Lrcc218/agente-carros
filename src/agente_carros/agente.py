"""Montagem do agente: prompt, ferramentas e laco de execucao.

Esta e a unica camada que conhece LangChain. As ferramentas em si sao
funcoes puras; aqui elas apenas ganham uma descricao e um esquema de
argumentos para que o modelo saiba quando e como chama-las.
"""

from __future__ import annotations

import re
import time
from typing import Any, Literal

from pydantic import BaseModel, Field

from agente_carros import registro
from agente_carros.config import carregar_configuracao
from agente_carros.dominio.portas import (
    BaseVetorial,
    RepositorioCatalogo,
    RepositorioPrecosCombustivel,
)
from agente_carros.ferramentas import consultar_catalogo as catalogo_ferramentas
from agente_carros.ferramentas.buscar_documentos import buscar_nos_documentos
from agente_carros.ferramentas.consultar_precos import consultar_precos, ranking_estados
from agente_carros.ferramentas.formato import formatar_numero, formatar_reais
from agente_carros.ferramentas.simular_viagem import (
    PRECO_PADRAO_DIESEL,
    PRECO_PADRAO_ETANOL,
    PRECO_PADRAO_GASOLINA,
    simular_viagem,
)

INSTRUCOES = """\
Voce e o assistente interno da Autoluz Veiculos, uma rede de concessionarias.
Atende qualquer colaborador — vendas, produto, pos-venda e atendimento — sobre o
catalogo, os precos e os documentos oficiais da operacao.
Responda em portugues do Brasil, de forma direta e objetiva.

Voce tem um catalogo fechado de 28 modelos do ano 2024, que vai do hatch de
entrada ao superesportivo. Os precos vem da Tabela FIPE e os dados de consumo
vem do PBE Veicular do Inmetro.

Alem do catalogo, voce tem tres acervos de documentos indexados para busca:

- As politicas internas da Autoluz: garantia e pos-venda, politica comercial e
  de precificacao, privacidade e LGPD, perguntas frequentes, manual de
  onboarding, tabela de servicos e alcadas da oficina e o diretorio de areas
  responsaveis. Perguntas sobre prazo de garantia, alcada de desconto, avaliacao
  de usado, beneficios, prazos de atendimento ou conduta vem daqui.
- Os documentos do Inmetro sobre etiquetagem veicular.
- O manual do proprietario do Toyota Corolla, com 484 paginas. Perguntas sobre
  manutencao, revisao, fluidos, pneus ou operacao do Corolla vem dele. Para os
  outros 27 modelos ainda nao ha manual indexado; nesses casos diga que a
  informacao nao esta disponivel para aquele modelo.

Regras que voce sempre segue:

1. Nunca invente dados. Preco, consumo, potencia e ficha tecnica so podem vir
   das ferramentas. Se a ferramenta nao devolveu o dado, diga que nao tem a
   informacao.
1.0. Para dizer quais marcas ou quantos carros existem, use resumo_catalogo.
   Uma listagem vem truncada nos primeiros resultados, e responder a partir
   dela faz voce omitir marcas inteiras.
1.1. Nunca escreva o nome de um veiculo que nao tenha aparecido no resultado de
   uma ferramenta nesta conversa. Voce conhece muitos carros de fora deste
   catalogo, e citar um deles faz o usuario acreditar que ele esta disponivel.
   Antes de sugerir alternativas, chame listar_veiculos e ofereca apenas o que
   voltou de la.
2. Nunca faca contas de cabeca. Custo de viagem e consumo de combustivel sao
   sempre calculados pela ferramenta de simulacao, mesmo quando a conta parecer
   simples.
3. Se o usuario perguntar sobre um carro fora do catalogo, diga claramente que
   ele nao esta coberto. Para oferecer modelos parecidos, primeiro chame
   listar_veiculos com a categoria ou a marca adequada, e cite so o retorno.
4. Ao citar preco, informe o mes de referencia da FIPE. Ao citar consumo,
   informe que a fonte e o PBE Veicular do Inmetro.
5. Voce nao da conselhos financeiros, nao negocia, nao simula financiamento e
   nao opina sobre o valor de revenda futuro. Se pedirem, explique o limite e
   ofereca o que voce consegue fazer.
6. Para simular uma viagem voce precisa da distancia. Se ela nao foi informada,
   pergunte antes de chamar a ferramenta. Se o usuario nao disser a divisao
   entre cidade e estrada, use 30% cidade e avise que assumiu isso.
7. A ficha tecnica do catalogo ainda esta em conferencia; consumo e preco vem de
   fonte oficial. Se a pergunta depender de um dado da ficha, mencione essa
   ressalva uma vez.
8. Quando nao encontrar a resposta em nenhum documento, diga isso e indique a
   area responsavel pelo assunto, consultando o diretorio de areas no acervo
   interno. Nao improvise contato nem procedimento.
9. Nunca repita nem peca dado pessoal de cliente — nome, CPF, telefone, placa ou
   chassi. A politica de privacidade proibe isso. Se a pergunta trouxer um dado
   desses, responda pela regra geral e avise que o caso especifico deve ser
   tratado no sistema interno.
"""


class SemArgumentos(BaseModel):
    """Ferramentas que nao precisam de parametro."""


class BuscaVeiculo(BaseModel):
    termo: str = Field(description="Nome ou parte do nome do carro, como 'corolla' ou 'onix'")


class ListagemVeiculos(BaseModel):
    marca: str | None = Field(default=None, description="Filtra por marca")
    categoria: str | None = Field(
        default=None,
        description=(
            "Filtra por categoria, como hatch_popular, suv_compacto, suv_medio, "
            "sedan_medio, sedan_premium, picape_compacta, picape_media, "
            "eletrico_hatch, eletrico_sedan, esportivo, esportivo_conversivel, "
            "superesportivo"
        ),
    )
    preco_maximo: float | None = Field(default=None, description="Preco FIPE maximo em reais")
    preco_minimo: float | None = Field(default=None, description="Preco FIPE minimo em reais")
    combustivel: str | None = Field(
        default=None, description="Filtra por flex, gasolina, diesel ou eletrico"
    )
    ordenar_por: Literal["preco", "consumo_cidade", "consumo_estrada", "potencia"] = Field(
        default="preco",
        description="Criterio de ordenacao",
    )


class ComparacaoVeiculos(BaseModel):
    termos: list[str] = Field(
        description="Nomes dos carros a comparar, de dois a cinco",
        min_length=2,
        max_length=5,
    )


class SimulacaoViagem(BaseModel):
    veiculo: str = Field(description="Nome do carro do catalogo")
    distancia_km: float = Field(
        description="Distância da viagem em quilômetros, apenas a ida",
        gt=0,
        le=100_000,
    )
    proporcao_cidade: float = Field(
        default=0.3, description="Fração do percurso em cidade, de 0 a 1", ge=0, le=1
    )
    ida_e_volta: bool = Field(default=False, description="Se a viagem inclui o retorno")
    estado: str = Field(
        default="BR",
        description=(
            "Sigla do estado onde o abastecimento acontece, como SP ou MG. "
            "Usa o preço oficial praticado lá. Deixe BR para a mediana nacional."
        ),
    )
    preco_gasolina: float | None = Field(
        default=None,
        gt=0,
        le=100,
        description=(
            "Preço do litro da gasolina. "
            "Só informe se o usuário disser o preço."
        ),
    )
    preco_etanol: float | None = Field(
        default=None,
        gt=0,
        le=100,
        description=(
            "Preço do litro do etanol. "
            "Só informe se o usuário disser o preço."
        ),
    )
    preco_diesel: float | None = Field(
        default=None,
        gt=0,
        le=100,
        description=(
            "Preço do litro do diesel. "
            "Só informe se o usuário disser o preço."
        ),
    )


class ConsultaPrecos(BaseModel):
    estado: str = Field(
        default="BR", description="Sigla do estado, como SP. Use BR para a mediana nacional."
    )


class RankingPrecos(BaseModel):
    produto: str = Field(
        default="etanol", description="Combustivel: gasolina, etanol, diesel ou diesel_s10"
    )


class BuscaDocumentos(BaseModel):
    consulta: str = Field(
        description="O que procurar nos documentos do Inmetro ou no manual do Corolla"
    )
    tipo: Literal["documento_interno", "manual", "documento_oficial"] | None = Field(
        default=None,
        description=(
            "Restringe a busca antes de comparar similaridade. Use "
            "'documento_interno' para politicas da empresa: garantia, desconto, "
            "alcada, avaliacao de usado, LGPD, beneficios, prazos de atendimento e "
            "contatos das areas; 'manual' para revisao, fluidos, pneus e operacao "
            "do veiculo, conforme o manual do proprietario; 'documento_oficial' "
            "para metodologia do Inmetro e faixas de eficiencia. Deixe vazio "
            "quando nao tiver certeza."
        ),
    )


def extrair_texto(saida: Any) -> str:
    """Reduz a resposta do agente a texto puro.

    Modelos mais novos devolvem a resposta em blocos estruturados, cada um
    com o texto e metadados internos do modelo. As interfaces so querem o
    texto, entao a normalizacao acontece aqui e nao em cada uma delas.
    """
    if saida is None:
        return ""
    if isinstance(saida, str):
        return saida.strip()
    if hasattr(saida, "content"):
        return extrair_texto(saida.content)

    if isinstance(saida, list):
        partes = []
        for bloco in saida:
            if isinstance(bloco, str):
                partes.append(bloco)
            elif isinstance(bloco, dict) and bloco.get("type") == "text":
                partes.append(bloco.get("text", ""))
        return "\n".join(parte for parte in partes if parte).strip()

    if isinstance(saida, dict):
        return extrair_texto(saida.get("text") or saida.get("content") or "")

    return str(saida).strip()


PADRAO_FONTE = re.compile(r"\[Trecho \d+ — ([^,\]]+)")


def fontes_citadas(passos: Any) -> list[str]:
    """Le as fontes no proprio texto devolvido pela busca semantica.

    Refazer a busca so para saber a procedencia custaria uma segunda
    chamada de embedding por pergunta. O formato do trecho ja carrega o
    nome do documento, entao basta le-lo de volta.
    """
    fontes: list[str] = []
    for passo in passos or []:
        observacao = passo[1] if isinstance(passo, tuple | list) and len(passo) > 1 else None
        if isinstance(observacao, str):
            fontes.extend(PADRAO_FONTE.findall(observacao))
    return sorted({fonte.strip() for fonte in fontes if fonte.strip()})


def responder(
    executor: Any,
    pergunta: str,
    historico: list | None = None,
    sessao: str | None = None,
    interface: str = "desconhecida",
    id_execucao: str | None = None,
) -> str:
    """Faz uma pergunta ao agente e devolve a resposta ja em texto puro.

    De quebra, deixa a execucao registrada: sem esse rastro nao ha como
    auditar depois por que uma resposta saiu como saiu, nem medir quanto
    o agente demora ou com que frequencia ele nao encontra material.
    """
    entrada: dict[str, Any] = {"pergunta": pergunta}
    if historico:
        entrada["historico"] = historico

    config = carregar_configuracao()
    inicio = time.perf_counter()
    resposta, erro = "", None
    saida: dict[str, Any] = {}
    try:
        saida = executor.invoke(entrada)
        resposta = extrair_texto(saida["output"])
        return resposta
    except Exception as excecao:
        erro = f"{type(excecao).__name__}: {excecao}"
        raise
    finally:
        passos = saida.get("intermediate_steps") if isinstance(saida, dict) else None
        registro.registrar_execucao(
            diretorio=config.caminhos.registros,
            pergunta=pergunta,
            resposta=resposta,
            duracao_ms=int((time.perf_counter() - inicio) * 1000),
            ferramentas=registro.ferramentas_usadas(passos),
            fontes=fontes_citadas(passos),
            sessao=sessao,
            interface=interface,
            provedor=config.provedor_llm,
            modelo=config.modelo_chat,
            erro=erro,
            id_execucao=id_execucao,
        )


def _formatar_simulacao(resultado) -> str:
    linhas = [
        f"Simulação para {resultado.veiculo}",
        f"  Distância total: {formatar_numero(resultado.distancia_km, 0)} km"
        + (" (ida e volta)" if resultado.ida_e_volta else ""),
        f"  Divisão do percurso: {resultado.proporcao_cidade:.0%} cidade, "
        f"{resultado.proporcao_estrada:.0%} estrada",
        "",
    ]
    for custo in resultado.custos:
        linhas += [
            f"  {custo.combustivel.capitalize()} a {formatar_reais(custo.preco_por_litro)} "
            f"por litro:",
            f"    Consumo médio na viagem: {formatar_numero(custo.consumo_medio_km_l)} km/l",
            f"    Combustível necessário: {formatar_numero(custo.litros_necessarios)} litros",
            f"    Custo total: {formatar_reais(custo.custo_total)}",
            f"    Custo por quilômetro: {formatar_reais(custo.custo_por_km)}",
        ]
        if custo.abastecimentos_necessarios is not None:
            linhas.append(
                f"    Tanques necessários: "
                f"{formatar_numero(custo.abastecimentos_necessarios)}"
            )
        linhas.append("")
    linhas += [f"  {observacao}" for observacao in resultado.observacoes]
    return "\n".join(linhas)


def _resolver_precos(
    precos: RepositorioPrecosCombustivel | None,
    estado: str,
    informados: dict[str, float | None],
) -> tuple[dict[str, float], str]:
    """Decide o preco de cada combustivel e descreve a procedencia de cada um.

    Preco dito pelo usuario tem prioridade. Sem isso, usa o levantamento da
    ANP no estado pedido, que pode cair para a mediana nacional se aquele
    estado nao tiver apuracao daquele produto. Sem o dataset, usa valores de
    referencia.

    A procedencia e montada por combustivel, e nao uma so para todos: numa
    mesma consulta a gasolina pode vir do estado e o diesel da mediana
    nacional, e declarar apenas uma origem seria falso.
    """
    padroes = {
        "preco_gasolina": ("gasolina", PRECO_PADRAO_GASOLINA),
        "preco_etanol": ("etanol", PRECO_PADRAO_ETANOL),
        "preco_diesel": ("diesel", PRECO_PADRAO_DIESEL),
    }
    rotulos = {"preco_gasolina": "gasolina", "preco_etanol": "etanol", "preco_diesel": "diesel"}

    alvo = (estado or "BR").upper()
    escolhidos: dict[str, float] = {}
    origens: dict[str, str] = {}
    periodo = ""

    for chave, (produto, padrao) in padroes.items():
        informado = informados.get(chave)
        if informado is not None:
            escolhidos[chave] = float(informado)
            origens[chave] = "informado por voce"
            continue

        apurado = precos.preco(produto, alvo) if precos is not None else None
        if apurado is not None:
            escolhidos[chave] = apurado.preco_mediano
            periodo = apurado.descricao_periodo
            origens[chave] = (
                "mediana nacional" if apurado.uf == "BR" else f"mediana de {apurado.uf}"
            )
        else:
            escolhidos[chave] = padrao
            origens[chave] = "valor de referencia, sem apuracao oficial"

    # Agrupa combustiveis que compartilham a mesma origem, para nao repetir.
    por_origem: dict[str, list[str]] = {}
    for chave, origem in origens.items():
        por_origem.setdefault(origem, []).append(rotulos[chave])

    partes = []
    for origem, combustiveis in por_origem.items():
        if len(por_origem) == 1:
            partes.append(origem)
        else:
            partes.append(f"{' e '.join(combustiveis)}: {origem}")
    fonte = "; ".join(partes)
    if periodo:
        fonte = f"{fonte} ({periodo})"
    return escolhidos, fonte


def montar_ferramentas(
    catalogo: RepositorioCatalogo,
    base_vetorial: BaseVetorial | None,
    trechos_recuperados: int,
    precos: RepositorioPrecosCombustivel | None = None,
    limiar_relevancia: float = 0.0,
) -> list[Any]:
    """Embrulha as funcoes puras como ferramentas do LangChain."""
    from langchain_core.tools import StructuredTool

    def buscar(termo: str) -> str:
        return catalogo_ferramentas.buscar_veiculo(catalogo, termo)

    def listar(**argumentos) -> str:
        return catalogo_ferramentas.listar_veiculos(catalogo, **argumentos)

    def comparar(termos: list[str]) -> str:
        return catalogo_ferramentas.comparar_veiculos(catalogo, termos)

    def resumo() -> str:
        return catalogo_ferramentas.resumo_catalogo(catalogo)

    def simular(veiculo: str, estado: str = "BR", **argumentos) -> str:
        encontrados = catalogo.buscar_por_nome(veiculo)
        if not encontrados:
            return (
                f"'{veiculo}' não está no catálogo, então não dá para simular a viagem."
            )
        if len(encontrados) > 1:
            # Escolher o primeiro em silencio faria o agente simular um carro
            # e o usuario acreditar que era outro.
            nomes = ", ".join(v.nome_completo for v in encontrados[:5])
            return (
                f"'{veiculo}' corresponde a mais de um veículo do catálogo: {nomes}. "
                "Pergunte qual deles antes de simular."
            )

        informados = {
            chave: argumentos.pop(chave, None)
            for chave in ("preco_gasolina", "preco_etanol", "preco_diesel")
        }
        valores, fonte = _resolver_precos(precos, estado, informados)
        try:
            resultado = simular_viagem(
                encontrados[0], **argumentos, **valores, fonte_precos=fonte
            )
        except Exception as erro:  # noqa: BLE001 - falha aqui nao pode derrubar o agente
            return f"Não foi possível simular: {erro}"
        return _formatar_simulacao(resultado)

    ferramentas = [
        StructuredTool.from_function(
            func=resumo,
            name="resumo_catalogo",
            description=(
                "Panorama completo do catalogo: todas as marcas com a quantidade "
                "de modelos de cada uma, todas as categorias e a faixa de preco. "
                "Use SEMPRE que a pergunta for sobre o que o catalogo cobre, quais "
                "marcas existem ou quantos carros tem. Nunca responda isso a partir "
                "de uma listagem, que vem truncada e daria uma resposta incompleta."
            ),
            args_schema=SemArgumentos,
        ),
        StructuredTool.from_function(
            func=buscar,
            name="buscar_veiculo",
            description=(
                "Devolve a ficha tecnica completa de um carro do catalogo: motor, "
                "potencia, cambio, consumo, preco FIPE e procedencia dos dados. "
                "Use sempre que a pergunta for sobre um carro especifico."
            ),
            args_schema=BuscaVeiculo,
        ),
        StructuredTool.from_function(
            func=listar,
            name="listar_veiculos",
            description=(
                "Lista carros do catalogo filtrando por marca, categoria, faixa de "
                "preco ou combustivel, com ordenacao por preco, consumo ou potencia. "
                "Use para perguntas do tipo 'qual o mais economico ate tantos reais'. "
                "O resultado vem limitado aos primeiros itens e avisa quando ha mais: "
                "nesse caso nao trate a lista como o catalogo completo."
            ),
            args_schema=ListagemVeiculos,
        ),
        StructuredTool.from_function(
            func=comparar,
            name="comparar_veiculos",
            description=(
                "Coloca lado a lado a ficha de dois ou mais carros do catalogo. "
                "Use quando a pergunta pedir comparacao direta."
            ),
            args_schema=ComparacaoVeiculos,
        ),
        StructuredTool.from_function(
            func=simular,
            name="simular_viagem",
            description=(
                "Calcula quanto de combustivel um carro gasta numa viagem e quanto "
                "isso custa, separando cidade e estrada e comparando gasolina com "
                "etanol nos flex. Use sempre que a pergunta envolver gasto de "
                "combustivel, custo de viagem ou autonomia em uma distancia. "
                "Nunca faca essa conta por conta propria."
            ),
            args_schema=SimulacaoViagem,
        ),
    ]

    if precos is not None:

        def consultar(estado: str = "BR") -> str:
            return consultar_precos(precos, estado)

        def ranking(produto: str = "etanol") -> str:
            return ranking_estados(precos, produto)

        ferramentas += [
            StructuredTool.from_function(
                func=consultar,
                name="consultar_precos_combustivel",
                description=(
                    "Precos de gasolina, etanol e diesel praticados num estado, "
                    "apurados pela ANP, com a leitura de se o etanol compensa ali. "
                    "Use quando a pergunta for sobre preco de combustivel e nao "
                    "sobre uma viagem especifica."
                ),
                args_schema=ConsultaPrecos,
            ),
            StructuredTool.from_function(
                func=ranking,
                name="ranking_precos_por_estado",
                description=(
                    "Estados mais baratos e mais caros para um combustivel. "
                    "Use para perguntas do tipo 'onde o etanol e mais barato'."
                ),
                args_schema=RankingPrecos,
            ),
        ]

    if base_vetorial is not None:

        def documentos(consulta: str, tipo: str | None = None) -> str:
            return buscar_nos_documentos(
                base_vetorial,
                consulta,
                trechos_recuperados,
                tipo=tipo,
                limiar=limiar_relevancia,
            )

        ferramentas.append(
            StructuredTool.from_function(
                func=documentos,
                name="buscar_documentos_oficiais",
                description=(
                    "Busca trechos nos documentos indexados. Cobre tres acervos: "
                    "as politicas internas da Autoluz (garantia e pos-venda, "
                    "politica comercial, alcadas de desconto, avaliacao de usado, "
                    "LGPD, beneficios, prazos de atendimento, areas responsaveis); "
                    "os documentos do Inmetro sobre o Programa Brasileiro de "
                    "Etiquetagem Veicular; e o manual do proprietario do Toyota "
                    "Corolla, com revisao periodica, fluidos, pneus, luzes de "
                    "advertencia e operacao. Use sempre que a pergunta for sobre "
                    "politica da empresa, procedimento, manutencao ou manual. "
                    "Preco, potencia e consumo continuam vindo do catalogo."
                ),
                args_schema=BuscaDocumentos,
            )
        )

    return ferramentas


def montar_agente(
    modelo_chat: Any,
    catalogo: RepositorioCatalogo,
    base_vetorial: BaseVetorial | None,
    trechos_recuperados: int = 4,
    precos: RepositorioPrecosCombustivel | None = None,
    limiar_relevancia: float = 0.0,
) -> Any:
    """Devolve um executor pronto para receber perguntas."""
    # A partir do LangChain 1.x a API de agentes migrou para create_agent e
    # a anterior passou a viver em langchain_classic. Mantemos a anterior
    # por ora: ela e estavel e o projeto ja esta construido em cima dela.
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    ferramentas = montar_ferramentas(
        catalogo, base_vetorial, trechos_recuperados, precos, limiar_relevancia
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", INSTRUCOES),
            MessagesPlaceholder("historico", optional=True),
            ("human", "{pergunta}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    agente = create_tool_calling_agent(modelo_chat, ferramentas, prompt)
    return AgentExecutor(
        agent=agente,
        tools=ferramentas,
        verbose=False,
        max_iterations=6,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )
