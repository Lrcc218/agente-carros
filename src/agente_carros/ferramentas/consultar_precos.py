"""Consultas aos precos de combustivel apurados pela ANP."""

from __future__ import annotations

from agente_carros.dominio.portas import RepositorioPrecosCombustivel

# Acima desta razao entre o preco do etanol e o da gasolina, o etanol deixa
# de compensar num flex tipico, porque rende menos por litro. A regra dos
# 70% e uma referencia de mercado, nao uma medicao: o ponto exato depende do
# consumo de cada carro, e a simulacao de viagem calcula isso caso a caso.
LIMITE_VANTAGEM_ETANOL = 0.70

NOMES = {
    "gasolina": "Gasolina comum",
    "etanol": "Etanol hidratado",
    "diesel": "Diesel comum",
    "diesel_s10": "Diesel S10",
}


def consultar_precos(precos: RepositorioPrecosCombustivel, uf: str = "BR") -> str:
    """Precos praticados num estado, com a leitura de etanol contra gasolina."""
    alvo = (uf or "BR").upper()
    linhas: list[str] = []
    escopo = "no pais" if alvo == "BR" else f"em {alvo}"

    encontrados = {}
    for produto in NOMES:
        preco = precos.preco(produto, alvo)
        if preco is not None and preco.uf == alvo:
            encontrados[produto] = preco

    if not encontrados:
        disponiveis = ", ".join(precos.estados_disponiveis())
        return (
            f"Nao ha apuracao de precos para '{uf}'. "
            f"Estados disponiveis: {disponiveis}. Use BR para a media nacional."
        )

    referencia = next(iter(encontrados.values()))
    linhas.append(f"Precos medianos {escopo}, conforme o {referencia.descricao_periodo}:")
    for produto, preco in encontrados.items():
        linhas.append(
            f"  {NOMES[produto]}: R$ {preco.preco_mediano:.2f}/litro "
            f"(varia de R$ {preco.preco_minimo:.2f} a R$ {preco.preco_maximo:.2f} "
            f"em {preco.amostras} postos)"
        )

    gasolina = encontrados.get("gasolina")
    etanol = encontrados.get("etanol")
    if gasolina and etanol:
        razao = etanol.preco_mediano / gasolina.preco_mediano
        veredito = "compensa" if razao <= LIMITE_VANTAGEM_ETANOL else "nao compensa"
        linhas.append(
            f"  O etanol esta a {razao:.0%} do preco da gasolina, entao pela regra "
            f"dos 70% ele {veredito} num flex tipico. Para um carro especifico, "
            f"use a simulacao de viagem, que compara com o consumo real do modelo."
        )
    return "\n".join(linhas)


def ranking_estados(
    precos: RepositorioPrecosCombustivel, produto: str = "etanol", quantidade: int = 5
) -> str:
    """Estados mais baratos e mais caros para um combustivel."""
    lista = precos.por_estado(produto)
    if not lista:
        return f"Nao ha apuracao por estado para '{produto}'."

    nome = NOMES.get(produto, produto)
    baratos = lista[:quantidade]
    caros = list(reversed(lista[-quantidade:]))

    linhas = [f"{nome}, por estado, conforme o {lista[0].descricao_periodo}:", "", "Mais baratos:"]
    linhas += [f"  {p.uf}: R$ {p.preco_mediano:.2f}/litro" for p in baratos]
    linhas += ["", "Mais caros:"]
    linhas += [f"  {p.uf}: R$ {p.preco_mediano:.2f}/litro" for p in caros]
    return "\n".join(linhas)
