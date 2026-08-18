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

LIMITE_RESULTADOS = 10


def _reais(valor: float | None) -> str:
    if valor is None:
        return "nao informado"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _consumo_resumido(veiculo: Veiculo) -> str:
    if veiculo.e_eletrico:
        if veiculo.consumo_cidade_kmle is None:
            return "consumo nao publicado"
        return (
            f"{veiculo.consumo_cidade_kmle} km/l e na cidade e "
            f"{veiculo.consumo_estrada_kmle} km/l e na estrada, "
            f"autonomia de {veiculo.autonomia_eletrica_km} km"
        )
    if not veiculo.tem_dados_de_consumo:
        return "consumo nao publicado no PBE Veicular"

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
        f"  Potencia: {veiculo.potencia_cv} cv | Torque: {veiculo.torque_kgfm} kgfm",
        f"  Cambio: {veiculo.cambio} | Tracao: {veiculo.tracao}",
        f"  Portas: {veiculo.portas} | Lugares: {veiculo.lugares}",
        f"  Porta-malas: {veiculo.porta_malas_litros} litros",
        f"  Combustivel: {veiculo.combustivel}",
    ]
    if veiculo.tanque_litros:
        linhas.append(f"  Tanque: {veiculo.tanque_litros} litros")
    linhas.append(f"  Consumo: {_consumo_resumido(veiculo)}")
    if veiculo.classe_energetica:
        linhas.append(f"  Classificacao de eficiencia (Inmetro): {veiculo.classe_energetica}")
    linhas.append(f"  Preco FIPE: {_reais(veiculo.preco_fipe)}")
    if veiculo.mes_referencia_fipe:
        linhas.append(f"  Referencia FIPE: {veiculo.mes_referencia_fipe}")
    if veiculo.codigo_fipe:
        linhas.append(f"  Codigo FIPE: {veiculo.codigo_fipe}")
    if veiculo.versao_pbev:
        linhas.append(f"  Versao no PBE Veicular: {veiculo.versao_pbev}")
    return "\n".join(linhas)


def buscar_veiculo(catalogo: RepositorioCatalogo, termo: str) -> str:
    """Ficha tecnica completa dos veiculos que casam com o termo."""
    encontrados = catalogo.buscar_por_nome(termo)
    if not encontrados:
        disponiveis = sorted({v.marca for v in catalogo.listar()})
        return (
            f"Nenhum veiculo do catalogo corresponde a '{termo}'. "
            f"O catalogo cobre estas marcas: {', '.join(disponiveis)}."
        )
    return "\n\n".join(formatar_ficha(veiculo) for veiculo in encontrados[:LIMITE_RESULTADOS])


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
        return "Nenhum veiculo do catalogo atende a esses criterios."

    chaves = {
        "preco": lambda v: v.preco_fipe if v.preco_fipe is not None else float("inf"),
        "consumo_cidade": lambda v: -(v.consumo_cidade or 0),
        "consumo_estrada": lambda v: -(v.consumo_estrada or 0),
        "potencia": lambda v: -(v.potencia_cv or 0),
    }
    encontrados = sorted(encontrados, key=chaves.get(ordenar_por, chaves["preco"]))

    cabecalho = f"{len(encontrados)} veiculo(s), ordenados por {ordenar_por}:"
    corpo = "\n".join(formatar_resumo(v) for v in encontrados[:LIMITE_RESULTADOS])
    return f"{cabecalho}\n{corpo}"


def comparar_veiculos(catalogo: RepositorioCatalogo, termos: list[str]) -> str:
    """Coloca lado a lado a ficha dos veiculos indicados."""
    if len(termos) < 2:
        return "Informe pelo menos dois veiculos para comparar."

    blocos: list[str] = []
    for termo in termos:
        encontrados = catalogo.buscar_por_nome(termo)
        if not encontrados:
            blocos.append(f"'{termo}': nao encontrado no catalogo.")
        else:
            blocos.append(formatar_ficha(encontrados[0]))
    return "\n\n".join(blocos)
