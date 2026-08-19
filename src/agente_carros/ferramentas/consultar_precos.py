"""Consultas aos precos de combustivel apurados pela ANP."""

from __future__ import annotations

from agente_carros.dominio.portas import RepositorioPrecosCombustivel
from agente_carros.ferramentas.formato import formatar_reais

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
            f"Não há apuração de preços para '{uf}'. "
            f"Estados disponíveis: {disponiveis}. Use BR para a mediana nacional."
        )

    referencia = next(iter(encontrados.values()))
    linhas.append(f"Preços medianos {escopo}, conforme o {referencia.descricao_periodo}:")
    for produto, preco in encontrados.items():
        linhas.append(
            f"  {NOMES[produto]}: {formatar_reais(preco.preco_mediano)} por litro "
            f"(varia de {formatar_reais(preco.preco_minimo)} a "
            f"{formatar_reais(preco.preco_maximo)} em {preco.amostras} postos)"
        )

    gasolina = encontrados.get("gasolina")
    etanol = encontrados.get("etanol")
    if gasolina and etanol:
        razao = etanol.preco_mediano / gasolina.preco_mediano
        veredito = "compensa" if razao <= LIMITE_VANTAGEM_ETANOL else "nao compensa"
        linhas.append(
            f"  O etanol está a {razao:.0%} do preço da gasolina, então, pela regra "
            f"dos 70%, ele {veredito} num flex típico. Para um carro específico, "
            f"use a simulação de viagem, que compara com o consumo real do modelo."
        )
    return "\n".join(linhas)


def ranking_estados(
    precos: RepositorioPrecosCombustivel, produto: str = "etanol", quantidade: int = 5
) -> str:
    """Estados mais baratos e mais caros para um combustivel."""
    lista = precos.por_estado(produto)
    if not lista:
        return f"Não há apuração por estado para '{produto}'."

    nome = NOMES.get(produto, produto)
    baratos = lista[:quantidade]
    caros = list(reversed(lista[-quantidade:]))

    linhas = [f"{nome}, por estado, conforme o {lista[0].descricao_periodo}:", "", "Mais baratos:"]
    linhas += [f"  {p.uf}: {formatar_reais(p.preco_mediano)} por litro" for p in baratos]
    linhas += ["", "Mais caros:"]
    linhas += [f"  {p.uf}: {formatar_reais(p.preco_mediano)} por litro" for p in caros]
    return "\n".join(linhas)
