"""Consultas ao catalogo estruturado.

Filtro, ordenacao e comparacao acontecem aqui, em Python, e nao por busca
semantica: comparar precos e consumos e trabalho de dados estruturados, e
um indice vetorial responderia isso muito mal.

As funcoes devolvem texto formatado porque o destinatario e o modelo de
linguagem, que precisa dos numeros ja legiveis para citar na resposta.
"""

from __future__ import annotations

from agente_carros.dominio.modelos import Veiculo
from agente_carros.dominio.portas import RepositorioCatalogo
from agente_carros.ferramentas.formato import formatar_numero, formatar_reais

LIMITE_RESULTADOS = 10
LIMITE_COMPARACAO = 5
LIMITE_TERMO = 80

# Rotulos legiveis para os criterios de ordenacao: sem isso a resposta ao
# usuario sai com o identificador interno, tipo "ordenados por consumo_cidade".
ROTULOS_ORDENACAO = {
    "preco": "preço",
    "consumo_cidade": "consumo na cidade",
    "consumo_estrada": "consumo na estrada",
    "potencia": "potência",
}


_reais = formatar_reais


def _consumo_resumido(veiculo: Veiculo) -> str:
    if veiculo.e_eletrico:
        if veiculo.consumo_cidade_kmle is None:
            return "consumo não publicado"
        return (
            f"{formatar_numero(veiculo.consumo_cidade_kmle)} km/l equivalente na cidade e "
            f"{formatar_numero(veiculo.consumo_estrada_kmle)} km/l equivalente na estrada, "
            f"autonomia de {veiculo.autonomia_eletrica_km} km"
        )
    if not veiculo.tem_dados_de_consumo:
        return "consumo não publicado no PBE Veicular"

    partes = [f"{veiculo.consumo_cidade} km/l cidade, {veiculo.consumo_estrada} km/l estrada"]
    if veiculo.e_flex:
        partes.append(
            f"com etanol: {veiculo.consumo_cidade_etanol} km/l cidade, "
            f"{veiculo.consumo_estrada_etanol} km/l estrada"
        )
    return "; ".join(partes)


def formatar_resumo(veiculo: Veiculo) -> str:
    """Uma linha por veiculo, para listagens e comparacoes."""
    return (
        f"- {veiculo.nome_completo} | {veiculo.categoria} | {_reais(veiculo.preco_fipe)} "
        f"| {veiculo.motor}, {veiculo.potencia_cv} cv | {_consumo_resumido(veiculo)}"
    )


def formatar_ficha(veiculo: Veiculo) -> str:
    """Ficha completa de um veiculo, com procedencia dos dados."""
    linhas = [
        f"{veiculo.nome_completo}",
        f"  Categoria: {veiculo.categoria}",
        f"  Motor: {veiculo.motor}",
        f"  Potência: {veiculo.potencia_cv} cv | Torque: {veiculo.torque_kgfm} kgfm",
        f"  Câmbio: {veiculo.cambio} | Tração: {veiculo.tracao}",
        f"  Portas: {veiculo.portas} | Lugares: {veiculo.lugares}",
        f"  Porta-malas: {veiculo.porta_malas_litros} litros",
        f"  Combustível: {veiculo.combustivel}",
    ]
    if veiculo.tanque_litros:
        linhas.append(f"  Tanque: {veiculo.tanque_litros} litros")
    linhas.append(f"  Consumo: {_consumo_resumido(veiculo)}")
    if veiculo.classe_energetica:
        linhas.append(f"  Classificação de eficiência (Inmetro): {veiculo.classe_energetica}")
    linhas.append(f"  Preço FIPE: {_reais(veiculo.preco_fipe)}")
    if veiculo.mes_referencia_fipe:
        linhas.append(f"  Referência FIPE: {veiculo.mes_referencia_fipe}")
    if veiculo.codigo_fipe:
        linhas.append(f"  Código FIPE: {veiculo.codigo_fipe}")
    if veiculo.versao_pbev:
        linhas.append(f"  Versão no PBE Veicular: {veiculo.versao_pbev}")
    return "\n".join(linhas)


def buscar_veiculo(catalogo: RepositorioCatalogo, termo: str) -> str:
    """Ficha tecnica completa dos veiculos que casam com o termo."""
    encontrados = catalogo.buscar_por_nome(termo)
    if not encontrados:
        disponiveis = sorted({v.marca for v in catalogo.listar()})
        return (
            f"Nenhum veículo do catálogo corresponde a '{termo}'. "
            f"O catálogo cobre estas marcas: {', '.join(disponiveis)}."
        )
    mostrados = encontrados[:LIMITE_RESULTADOS]
    fichas = "\n\n".join(formatar_ficha(veiculo) for veiculo in mostrados)
    if len(encontrados) > len(mostrados):
        return (
            f"{len(encontrados)} veículos correspondem a '{termo}'. "
            f"Mostrando os {len(mostrados)} primeiros.\n\n{fichas}"
        )
    return fichas


def listar_veiculos(
    catalogo: RepositorioCatalogo,
    marca: str | None = None,
    categoria: str | None = None,
    preco_maximo: float | None = None,
    preco_minimo: float | None = None,
    combustivel: str | None = None,
    ordenar_por: str = "preco",
) -> str:
    """Lista os veiculos que atendem aos filtros, ordenados."""
    encontrados = catalogo.filtrar(
        marca=marca,
        categoria=categoria,
        preco_maximo=preco_maximo,
        preco_minimo=preco_minimo,
        combustivel=combustivel,
    )
    if not encontrados:
        return "Nenhum veículo do catálogo atende a esses critérios."

    chaves = {
        "preco": lambda v: v.preco_fipe if v.preco_fipe is not None else float("inf"),
        "consumo_cidade": lambda v: -(v.consumo_cidade or 0),
        "consumo_estrada": lambda v: -(v.consumo_estrada or 0),
        "potencia": lambda v: -(v.potencia_cv or 0),
    }
    ordenar_por = ordenar_por if ordenar_por in chaves else "preco"
    encontrados = sorted(encontrados, key=chaves[ordenar_por])

    total = len(encontrados)
    mostrados = encontrados[:LIMITE_RESULTADOS]
    corpo = "\n".join(formatar_resumo(v) for v in mostrados)

    if total > len(mostrados):
        # Sem este aviso o modelo trata a lista parcial como se fosse o
        # catalogo inteiro, e conclui, por exemplo, que so existem as marcas
        # dos carros mais baratos.
        cabecalho = (
            f"{total} veículos atendem aos critérios. "
            f"Mostrando os {len(mostrados)} primeiros, ordenados por "
            f"{ROTULOS_ORDENACAO[ordenar_por]}. "
            f"Atenção: esta lista está incompleta; não conclua nada sobre o "
            f"catálogo inteiro a partir dela. Para o panorama completo use "
            f"resumo_catalogo, ou refine os filtros."
        )
    else:
        plural = "veículo" if total == 1 else "veículos"
        cabecalho = f"{total} {plural}, ordenados por {ROTULOS_ORDENACAO[ordenar_por]}:"
    return f"{cabecalho}\n{corpo}"


def comparar_veiculos(catalogo: RepositorioCatalogo, termos: list[str]) -> str:
    """Coloca lado a lado a ficha dos veiculos indicados."""
    if len(termos) < 2:
        return "Informe pelo menos dois veículos para comparar."

    # Teto no numero de termos e no tamanho de cada um: o resultado volta
    # para o contexto do modelo, e uma lista longa vira centenas de milhares
    # de caracteres reenviados a cada passo.
    blocos: list[str] = []
    for termo in termos[:LIMITE_COMPARACAO]:
        recortado = termo[:LIMITE_TERMO]
        encontrados = catalogo.buscar_por_nome(recortado)
        if not encontrados:
            blocos.append(f"'{recortado}': não encontrado no catálogo.")
        else:
            blocos.append(formatar_ficha(encontrados[0]))

    if len(termos) > LIMITE_COMPARACAO:
        blocos.append(
            f"Foram informados {len(termos)} veículos; comparei os "
            f"{LIMITE_COMPARACAO} primeiros."
        )
    return "\n\n".join(blocos)


def resumo_catalogo(catalogo: RepositorioCatalogo) -> str:
    """Panorama completo do catalogo: marcas, categorias e faixa de preco.

    Existe para que o agente possa responder "o que voce tem?" sem depender
    de uma listagem truncada, que o levaria a descrever apenas parte do
    acervo como se fosse o todo.
    """
    veiculos = catalogo.listar()
    if not veiculos:
        return "O catálogo está vazio."

    por_marca: dict[str, int] = {}
    por_categoria: dict[str, int] = {}
    for veiculo in veiculos:
        por_marca[veiculo.marca] = por_marca.get(veiculo.marca, 0) + 1
        por_categoria[veiculo.categoria] = por_categoria.get(veiculo.categoria, 0) + 1

    precos = [v.preco_fipe for v in veiculos if v.preco_fipe is not None]
    linhas = [
        f"O catálogo tem {len(veiculos)} veículos de {len(por_marca)} marcas, todos do ano 2024.",
        "",
        "Marcas, com a quantidade de modelos de cada uma:",
    ]
    linhas += [f"  {marca}: {qtd}" for marca, qtd in sorted(por_marca.items())]
    linhas += ["", "Categorias:"]
    linhas += [f"  {cat}: {qtd}" for cat, qtd in sorted(por_categoria.items())]
    if precos:
        linhas += [
            "",
            f"Faixa de preço: de {_reais(min(precos))} a {_reais(max(precos))}.",
        ]
    return "\n".join(linhas)
