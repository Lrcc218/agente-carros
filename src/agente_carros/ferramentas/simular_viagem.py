"""Simulacao do custo de combustivel de uma viagem.

Calculo deterministico em Python. O modelo de linguagem apenas extrai os
parametros da pergunta e apresenta o resultado — ele nunca faz a conta,
porque modelos de linguagem erram aritmetica com frequencia e confianca.
"""

from __future__ import annotations

from agente_carros.dominio.modelos import CustoPorCombustivel, ResultadoViagem, Veiculo
from agente_carros.ferramentas.formato import formatar_reais

# Usados apenas se o levantamento da ANP nao estiver disponivel. Em operacao
# normal os precos vem do dataset oficial, ja no estado de quem pergunta.
PRECO_PADRAO_GASOLINA = 6.59
PRECO_PADRAO_ETANOL = 4.28
PRECO_PADRAO_DIESEL = 6.69


class DadosInsuficientes(ValueError):
    """O veiculo nao tem dados de consumo para simular a viagem."""


def _litros_necessarios(
    distancia_cidade: float,
    distancia_estrada: float,
    consumo_cidade: float,
    consumo_estrada: float,
) -> float:
    """Soma o combustivel gasto em cada trecho.

    Somar os litros de cada trecho e diferente de aplicar a media dos dois
    consumos sobre a distancia total: a media aritmetica de km/l subestima
    o gasto, porque consumo e uma razao invertida.
    """
    return distancia_cidade / consumo_cidade + distancia_estrada / consumo_estrada


def _montar_custo(
    combustivel: str,
    distancia_total: float,
    litros: float,
    preco_por_litro: float,
    tanque_litros: float | None,
) -> CustoPorCombustivel:
    custo_total = litros * preco_por_litro
    return CustoPorCombustivel(
        combustivel=combustivel,
        consumo_medio_km_l=round(distancia_total / litros, 2),
        litros_necessarios=round(litros, 2),
        preco_por_litro=preco_por_litro,
        custo_total=round(custo_total, 2),
        custo_por_km=round(custo_total / distancia_total, 3),
        abastecimentos_necessarios=(
            round(litros / tanque_litros, 2) if tanque_litros else None
        ),
    )


def simular_viagem(
    veiculo: Veiculo,
    distancia_km: float,
    proporcao_cidade: float = 0.3,
    ida_e_volta: bool = False,
    preco_gasolina: float = PRECO_PADRAO_GASOLINA,
    preco_etanol: float = PRECO_PADRAO_ETANOL,
    preco_diesel: float = PRECO_PADRAO_DIESEL,
    fonte_precos: str = "",
) -> ResultadoViagem:
    """Calcula o custo de combustivel de uma viagem.

    Em veiculos flex devolve gasolina e etanol lado a lado, o que permite
    responder qual dos dois compensa naquele preco.

    Levanta `DadosInsuficientes` quando o veiculo nao tem consumo publicado
    no PBE Veicular — e preferivel recusar a estimar um numero inventado.
    """
    if distancia_km <= 0:
        raise ValueError("A distância precisa ser maior que zero.")
    if not 0.0 <= proporcao_cidade <= 1.0:
        raise ValueError("A parcela do percurso em cidade precisa estar entre 0% e 100%.")

    if veiculo.e_eletrico:
        raise DadosInsuficientes(
            f"{veiculo.nome_completo} e eletrico. O catalogo registra a eficiencia em "
            "km por litro equivalente e a autonomia da bateria, mas nao o consumo em "
            "kWh, entao o custo em reais da viagem nao pode ser calculado."
        )
    if not veiculo.tem_dados_de_consumo:
        raise DadosInsuficientes(
            f"{veiculo.nome_completo} nao consta nas tabelas do PBE Veicular usadas "
            "neste projeto, entao nao ha dados de consumo para simular a viagem."
        )

    distancia_total = distancia_km * (2 if ida_e_volta else 1)
    distancia_cidade = distancia_total * proporcao_cidade
    distancia_estrada = distancia_total - distancia_cidade

    custos: list[CustoPorCombustivel] = []
    observacoes: list[str] = []

    combustivel = veiculo.combustivel.lower()
    preco_principal = preco_diesel if combustivel == "diesel" else preco_gasolina
    nome_principal = "diesel" if combustivel == "diesel" else "gasolina"

    litros = _litros_necessarios(
        distancia_cidade,
        distancia_estrada,
        veiculo.consumo_cidade,
        veiculo.consumo_estrada,
    )
    custos.append(
        _montar_custo(
            nome_principal, distancia_total, litros, preco_principal, veiculo.tanque_litros
        )
    )

    if veiculo.e_flex:
        litros_etanol = _litros_necessarios(
            distancia_cidade,
            distancia_estrada,
            veiculo.consumo_cidade_etanol,
            veiculo.consumo_estrada_etanol,
        )
        custos.append(
            _montar_custo(
                "etanol", distancia_total, litros_etanol, preco_etanol, veiculo.tanque_litros
            )
        )

        gasolina, etanol = custos[0], custos[1]
        diferenca = abs(gasolina.custo_total - etanol.custo_total)
        if diferenca < 0.01:
            observacoes.append(
                "Com esses preços, gasolina e etanol custam praticamente o mesmo nesta viagem."
            )
        else:
            vencedor = "o etanol" if etanol.custo_total < gasolina.custo_total else "a gasolina"
            observacoes.append(
                f"Com os preços informados, {vencedor} custa "
                f"{formatar_reais(diferenca)} a menos nesta viagem."
            )

    if fonte_precos:
        observacoes.append(f"Preços de combustível: {fonte_precos}.")
    if veiculo.versao_pbev:
        observacoes.append(
            f"Consumo conforme o PBE Veicular do Inmetro, versão {veiculo.versao_pbev}."
        )
    observacoes.append(
        "Valores de referência medidos em condições de ensaio. O consumo real varia "
        "com carga, ar-condicionado, relevo e estilo de condução."
    )

    return ResultadoViagem(
        veiculo=veiculo.nome_completo,
        distancia_km=distancia_total,
        proporcao_cidade=proporcao_cidade,
        proporcao_estrada=round(1 - proporcao_cidade, 2),
        ida_e_volta=ida_e_volta,
        custos=custos,
        observacoes=observacoes,
    )
