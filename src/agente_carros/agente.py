"""Montagem do agente: prompt, ferramentas e laco de execucao.

Esta e a unica camada que conhece LangChain. As ferramentas em si sao
funcoes puras; aqui elas apenas ganham uma descricao e um esquema de
argumentos para que o modelo saiba quando e como chama-las.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agente_carros.dominio.portas import BaseVetorial, RepositorioCatalogo
from agente_carros.ferramentas import consultar_catalogo as catalogo_ferramentas
from agente_carros.ferramentas.buscar_documentos import buscar_nos_documentos
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
2. Nunca faca contas de cabeca. Custo de viagem e consumo de combustivel sao
   sempre calculados pela ferramenta de simulacao, mesmo quando a conta parecer
   simples.
3. Se o usuario perguntar sobre um carro fora do catalogo, diga claramente que
   ele nao esta coberto e ofereca os modelos parecidos que voce tem.
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
    preco_gasolina: float = Field(
        default=PRECO_PADRAO_GASOLINA, description="Preco do litro da gasolina em reais"
    )
    preco_etanol: float = Field(
        default=PRECO_PADRAO_ETANOL, description="Preco do litro do etanol em reais"
    )
    preco_diesel: float = Field(
        default=PRECO_PADRAO_DIESEL, description="Preco do litro do diesel em reais"
    )


class BuscaDocumentos(BaseModel):
    consulta: str = Field(description="O que procurar nos documentos oficiais do Inmetro")


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


def montar_ferramentas(
    catalogo: RepositorioCatalogo,
    base_vetorial: BaseVetorial | None,
    trechos_recuperados: int,
) -> list[Any]:
    """Embrulha as funcoes puras como ferramentas do LangChain."""
    from langchain_core.tools import StructuredTool

    def buscar(termo: str) -> str:
        return catalogo_ferramentas.buscar_veiculo(catalogo, termo)

    def listar(**argumentos) -> str:
        return catalogo_ferramentas.listar_veiculos(catalogo, **argumentos)

    def comparar(termos: list[str]) -> str:
        return catalogo_ferramentas.comparar_veiculos(catalogo, termos)

    def simular(veiculo: str, **argumentos) -> str:
        encontrados = catalogo.buscar_por_nome(veiculo)
        if not encontrados:
            return f"'{veiculo}' nao esta no catalogo, entao nao da para simular a viagem."
        try:
            return _formatar_simulacao(simular_viagem(encontrados[0], **argumentos))
        except (DadosInsuficientes, ValueError) as erro:
            return f"Nao foi possivel simular: {erro}"

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
) -> Any:
    """Devolve um executor pronto para receber perguntas."""
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

    ferramentas = montar_ferramentas(catalogo, base_vetorial, trechos_recuperados)
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
