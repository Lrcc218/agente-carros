"""Montagem do agente: prompt, ferramentas e laco de execucao.

Esta e a unica camada que conhece LangChain. As ferramentas em si sao
funcoes puras; aqui elas apenas ganham uma descricao e um esquema de
argumentos para que o modelo saiba quando e como chama-las.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agente_carros.dominio.portas import (
    BaseVetorial,
    RepositorioCatalogo,
    RepositorioPrecosCombustivel,
)
from agente_carros.ferramentas import consultar_catalogo as catalogo_ferramentas
from agente_carros.ferramentas.buscar_documentos import buscar_nos_documentos
from agente_carros.ferramentas.consultar_precos import consultar_precos, ranking_estados
from agente_carros.ferramentas.simular_viagem import (
    PRECO_PADRAO_DIESEL,
    PRECO_PADRAO_ETANOL,
    PRECO_PADRAO_GASOLINA,
    DadosInsuficientes,
    simular_viagem,
)

INSTRUCOES = """\
Voce e um assistente de pesquisa para quem esta escolhendo um carro para comprar.
Responde em portugues do Brasil, de forma direta e objetiva.

Voce tem um catalogo fechado de 28 modelos do ano 2024, que vai do hatch de
entrada ao superesportivo. Os precos vem da Tabela FIPE e os dados de consumo
vem do PBE Veicular do Inmetro.

Regras que voce sempre segue:

1. Nunca invente dados. Preco, consumo, potencia e ficha tecnica so podem vir
   das ferramentas. Se a ferramenta nao devolveu o dado, diga que nao tem a
   informacao.
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
"""


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
    ordenar_por: str = Field(
        default="preco",
        description="Ordena por preco, consumo_cidade, consumo_estrada ou potencia",
    )


class ComparacaoVeiculos(BaseModel):
    termos: list[str] = Field(description="Nomes dos carros a comparar, dois ou mais")


class SimulacaoViagem(BaseModel):
    veiculo: str = Field(description="Nome do carro do catalogo")
    distancia_km: float = Field(description="Distancia da viagem em quilometros, so a ida")
    proporcao_cidade: float = Field(
        default=0.3, description="Fracao do percurso em cidade, de 0 a 1"
    )
    ida_e_volta: bool = Field(default=False, description="Se a viagem inclui o retorno")
    estado: str = Field(
        default="BR",
        description=(
            "Sigla do estado onde o combustivel sera abastecido, como SP ou MG. "
            "Usa o preco oficial praticado la. Deixe BR para a mediana nacional."
        ),
    )
    preco_gasolina: float | None = Field(
        default=None,
        description="Preco do litro da gasolina. So informe se o usuario disser o preco dele.",
    )
    preco_etanol: float | None = Field(
        default=None,
        description="Preco do litro do etanol. So informe se o usuario disser o preco dele.",
    )
    preco_diesel: float | None = Field(
        default=None,
        description="Preco do litro do diesel. So informe se o usuario disser o preco dele.",
    )


class ConsultaPrecos(BaseModel):
    estado: str = Field(
        default="BR", description="Sigla do estado, como SP. Use BR para a media nacional."
    )


class RankingPrecos(BaseModel):
    produto: str = Field(
        default="etanol", description="Combustivel: gasolina, etanol, diesel ou diesel_s10"
    )


class BuscaDocumentos(BaseModel):
    consulta: str = Field(description="O que procurar nos documentos oficiais do Inmetro")


def extrair_texto(saida: Any) -> str:
    """Reduz a resposta do agente a texto puro.

    Modelos mais novos devolvem a resposta em blocos estruturados, cada um
    com o texto e metadados internos do modelo. As interfaces so querem o
    texto, entao a normalizacao acontece aqui e nao em cada uma delas.
    """
    if isinstance(saida, str):
        return saida.strip()

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


def responder(executor: Any, pergunta: str, historico: list | None = None) -> str:
    """Faz uma pergunta ao agente e devolve a resposta ja em texto puro."""
    entrada: dict[str, Any] = {"pergunta": pergunta}
    if historico:
        entrada["historico"] = historico
    return extrair_texto(executor.invoke(entrada)["output"])


def _formatar_simulacao(resultado) -> str:
    linhas = [
        f"Simulacao para {resultado.veiculo}",
        f"  Distancia total: {resultado.distancia_km:.0f} km"
        + (" (ida e volta)" if resultado.ida_e_volta else ""),
        f"  Divisao do percurso: {resultado.proporcao_cidade:.0%} cidade, "
        f"{resultado.proporcao_estrada:.0%} estrada",
        "",
    ]
    for custo in resultado.custos:
        linhas += [
            f"  {custo.combustivel.capitalize()} a R$ {custo.preco_por_litro:.2f}/litro:",
            f"    Consumo medio na viagem: {custo.consumo_medio_km_l} km/l",
            f"    Combustivel necessario: {custo.litros_necessarios} litros",
            f"    Custo total: R$ {custo.custo_total:.2f}",
            f"    Custo por km: R$ {custo.custo_por_km:.3f}",
        ]
        if custo.abastecimentos_necessarios is not None:
            linhas.append(f"    Tanques cheios: {custo.abastecimentos_necessarios}")
        linhas.append("")
    linhas += [f"  {observacao}" for observacao in resultado.observacoes]
    return "\n".join(linhas)


def _resolver_precos(
    precos: RepositorioPrecosCombustivel | None,
    estado: str,
    informados: dict[str, float | None],
) -> tuple[dict[str, float], str]:
    """Decide o preco de cada combustivel e descreve a procedencia.

    Preco dito pelo usuario tem prioridade. Sem isso, usa o levantamento da
    ANP no estado pedido. Sem o dataset, cai para os valores de referencia.
    """
    escolhidos = {
        "preco_gasolina": informados.get("preco_gasolina"),
        "preco_etanol": informados.get("preco_etanol"),
        "preco_diesel": informados.get("preco_diesel"),
    }
    padroes = {
        "preco_gasolina": ("gasolina", PRECO_PADRAO_GASOLINA),
        "preco_etanol": ("etanol", PRECO_PADRAO_ETANOL),
        "preco_diesel": ("diesel", PRECO_PADRAO_DIESEL),
    }

    alvo = (estado or "BR").upper()
    usou_anp = False
    periodo = ""
    uf_efetiva = alvo

    for chave, (produto, padrao) in padroes.items():
        if escolhidos[chave] is not None:
            continue
        apurado = precos.preco(produto, alvo) if precos is not None else None
        if apurado is not None:
            escolhidos[chave] = apurado.preco_mediano
            usou_anp = True
            periodo = apurado.descricao_periodo
            uf_efetiva = apurado.uf
        else:
            escolhidos[chave] = padrao

    if any(valor is not None for valor in informados.values()):
        fonte = "valores informados por voce"
    elif usou_anp:
        onde = "media nacional" if uf_efetiva == "BR" else f"mediana de {uf_efetiva}"
        fonte = f"{onde}, {periodo}"
    else:
        fonte = "valores de referencia, sem apuracao oficial disponivel"

    return {chave: float(valor) for chave, valor in escolhidos.items()}, fonte


def montar_ferramentas(
    catalogo: RepositorioCatalogo,
    base_vetorial: BaseVetorial | None,
    trechos_recuperados: int,
    precos: RepositorioPrecosCombustivel | None = None,
) -> list[Any]:
    """Embrulha as funcoes puras como ferramentas do LangChain."""
    from langchain_core.tools import StructuredTool

    def buscar(termo: str) -> str:
        return catalogo_ferramentas.buscar_veiculo(catalogo, termo)

    def listar(**argumentos) -> str:
        return catalogo_ferramentas.listar_veiculos(catalogo, **argumentos)

    def comparar(termos: list[str]) -> str:
        return catalogo_ferramentas.comparar_veiculos(catalogo, termos)

    def simular(veiculo: str, estado: str = "BR", **argumentos) -> str:
        encontrados = catalogo.buscar_por_nome(veiculo)
        if not encontrados:
            return f"'{veiculo}' nao esta no catalogo, entao nao da para simular a viagem."

        informados = {
            chave: argumentos.pop(chave, None)
            for chave in ("preco_gasolina", "preco_etanol", "preco_diesel")
        }
        valores, fonte = _resolver_precos(precos, estado, informados)
        try:
            resultado = simular_viagem(
                encontrados[0], **argumentos, **valores, fonte_precos=fonte
            )
        except (DadosInsuficientes, ValueError) as erro:
            return f"Nao foi possivel simular: {erro}"
        return _formatar_simulacao(resultado)

    ferramentas = [
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
                "Use para perguntas do tipo 'qual o mais economico ate tantos reais'."
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

        def documentos(consulta: str) -> str:
            return buscar_nos_documentos(base_vetorial, consulta, trechos_recuperados)

        ferramentas.append(
            StructuredTool.from_function(
                func=documentos,
                name="buscar_documentos_oficiais",
                description=(
                    "Busca trechos nos documentos oficiais do Inmetro sobre o "
                    "Programa Brasileiro de Etiquetagem Veicular: metodologia de "
                    "medicao de consumo, significado das faixas de eficiencia e "
                    "criterios do programa. Nao use para dados de carros "
                    "especificos, que vem do catalogo."
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
) -> Any:
    """Devolve um executor pronto para receber perguntas."""
    # A partir do LangChain 1.x a API de agentes migrou para create_agent e
    # a anterior passou a viver em langchain_classic. Mantemos a anterior
    # por ora: ela e estavel e o projeto ja esta construido em cima dela.
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    ferramentas = montar_ferramentas(catalogo, base_vetorial, trechos_recuperados, precos)
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
