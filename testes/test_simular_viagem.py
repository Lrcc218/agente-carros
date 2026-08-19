"""Testes da simulacao de viagem.

Esta e a parte do projeto onde um erro numerico passa despercebido e vira
uma resposta errada com aparencia de certeza, entao ela e testada em
detalhe.
"""

from __future__ import annotations

import pytest

from agente_carros.ferramentas.simular_viagem import (
    DadosInsuficientes,
    simular_viagem,
)
from testes.conftest import montar_veiculo


def custo_de(resultado, combustivel: str):
    return next(c for c in resultado.custos if c.combustivel == combustivel)


def test_trecho_unico_de_estrada_usa_o_consumo_de_estrada():
    veiculo = montar_veiculo(consumo_cidade=10.0, consumo_estrada=15.0)

    resultado = simular_viagem(veiculo, distancia_km=300, proporcao_cidade=0.0, preco_gasolina=6.0)

    gasolina = custo_de(resultado, "gasolina")
    assert gasolina.litros_necessarios == 20.0  # 300 / 15
    assert gasolina.custo_total == 120.0
    assert gasolina.consumo_medio_km_l == 15.0


def test_mistura_soma_os_litros_de_cada_trecho():
    """A media aritmetica de km/l subestima o gasto e nao pode ser usada."""
    veiculo = montar_veiculo(consumo_cidade=10.0, consumo_estrada=15.0)

    resultado = simular_viagem(veiculo, distancia_km=300, proporcao_cidade=0.5, preco_gasolina=6.0)

    gasolina = custo_de(resultado, "gasolina")
    # 150/10 + 150/15 = 15 + 10 = 25 litros
    assert gasolina.litros_necessarios == 25.0
    assert gasolina.consumo_medio_km_l == 12.0  # 300/25, e nao (10+15)/2 = 12.5
    assert gasolina.custo_total == 150.0


def test_ida_e_volta_dobra_a_distancia():
    veiculo = montar_veiculo(consumo_cidade=10.0, consumo_estrada=10.0)

    ida = simular_viagem(veiculo, distancia_km=100, proporcao_cidade=0.5, preco_gasolina=5.0)
    volta = simular_viagem(
        veiculo, distancia_km=100, proporcao_cidade=0.5, ida_e_volta=True, preco_gasolina=5.0
    )

    assert volta.distancia_km == 2 * ida.distancia_km
    assert custo_de(volta, "gasolina").custo_total == 2 * custo_de(ida, "gasolina").custo_total


def test_custo_por_km_e_coerente_com_o_total():
    veiculo = montar_veiculo()

    resultado = simular_viagem(veiculo, distancia_km=400, proporcao_cidade=0.25)

    gasolina = custo_de(resultado, "gasolina")
    assert gasolina.custo_por_km == pytest.approx(gasolina.custo_total / 400, abs=0.01)


def test_flex_compara_gasolina_e_etanol():
    veiculo = montar_veiculo()

    resultado = simular_viagem(
        veiculo, distancia_km=500, preco_gasolina=6.00, preco_etanol=4.00
    )

    assert {c.combustivel for c in resultado.custos} == {"gasolina", "etanol"}
    assert resultado.mais_economico is not None


def test_etanol_vence_quando_o_preco_compensa():
    """Com etanol a 65% do preco da gasolina, o etanol passa a compensar."""
    veiculo = montar_veiculo(
        consumo_cidade=10.0,
        consumo_estrada=10.0,
        consumo_cidade_etanol=7.0,
        consumo_estrada_etanol=7.0,
    )

    caro = simular_viagem(veiculo, distancia_km=100, preco_gasolina=6.0, preco_etanol=5.0)
    barato = simular_viagem(veiculo, distancia_km=100, preco_gasolina=6.0, preco_etanol=3.9)

    assert caro.mais_economico.combustivel == "gasolina"
    assert barato.mais_economico.combustivel == "etanol"


def test_diesel_usa_o_preco_do_diesel_e_nao_compara_etanol():
    veiculo = montar_veiculo(
        combustivel="diesel",
        consumo_cidade=9.0,
        consumo_estrada=11.0,
        consumo_cidade_etanol=None,
        consumo_estrada_etanol=None,
    )

    resultado = simular_viagem(veiculo, distancia_km=200, proporcao_cidade=0.0, preco_diesel=6.5)

    assert [c.combustivel for c in resultado.custos] == ["diesel"]
    assert custo_de(resultado, "diesel").preco_por_litro == 6.5


def test_abastecimentos_consideram_o_tanque():
    veiculo = montar_veiculo(consumo_cidade=10.0, consumo_estrada=10.0, tanque_litros=50.0)

    resultado = simular_viagem(veiculo, distancia_km=1000, proporcao_cidade=0.5)

    assert custo_de(resultado, "gasolina").abastecimentos_necessarios == 2.0  # 100 L / 50 L


def test_recusa_veiculo_sem_dados_de_consumo():
    veiculo = montar_veiculo(consumo_cidade=None, consumo_estrada=None)

    with pytest.raises(DadosInsuficientes, match="PBE Veicular"):
        simular_viagem(veiculo, distancia_km=100)


def test_recusa_veiculo_eletrico():
    veiculo = montar_veiculo(combustivel="eletrico", consumo_cidade=None, consumo_estrada=None)

    with pytest.raises(DadosInsuficientes, match="[eé]l[eé]trico"):
        simular_viagem(veiculo, distancia_km=100)


@pytest.mark.parametrize("distancia", [0, -50])
def test_recusa_distancia_invalida(distancia):
    with pytest.raises(ValueError, match="[Dd]ist[âa]ncia"):
        simular_viagem(montar_veiculo(), distancia_km=distancia)


@pytest.mark.parametrize("proporcao", [-0.1, 1.5])
def test_recusa_proporcao_invalida(proporcao):
    with pytest.raises(ValueError, match="percurso em cidade"):
        simular_viagem(montar_veiculo(), distancia_km=100, proporcao_cidade=proporcao)


def test_viagem_real_com_dados_do_catalogo(catalogo):
    """Sao Paulo a Rio de Janeiro, cerca de 430 km, quase toda em estrada."""
    corolla = catalogo.buscar_por_nome("corolla gli")[0]

    resultado = simular_viagem(corolla, distancia_km=430, proporcao_cidade=0.1, ida_e_volta=True)

    gasolina = custo_de(resultado, "gasolina")
    assert resultado.distancia_km == 860
    assert 50 < gasolina.litros_necessarios < 90
    assert gasolina.custo_total > 0
    assert any("PBE Veicular" in obs for obs in resultado.observacoes)


@pytest.mark.parametrize("distancia", [float("nan"), float("inf"), 1e12])
def test_recusa_distancia_absurda(distancia):
    """Sem isso a resposta saia com 'R$ nan' ou custos de bilhoes."""
    with pytest.raises(ValueError):
        simular_viagem(montar_veiculo(), distancia_km=distancia)


@pytest.mark.parametrize("preco", [-50.0, 0.0, float("nan"), 1e6])
def test_recusa_preco_de_combustivel_implausivel(preco):
    with pytest.raises(ValueError, match="plausível"):
        simular_viagem(montar_veiculo(), distancia_km=100, preco_gasolina=preco)


def test_recusa_consumo_zero_ou_negativo():
    veiculo = montar_veiculo(consumo_cidade=-10.0, consumo_estrada=-15.0)

    with pytest.raises(DadosInsuficientes, match="não é utilizável"):
        simular_viagem(veiculo, distancia_km=300)


def test_trecho_vazio_nao_exige_o_consumo_daquele_tipo():
    """0 km de cidade nao pode estourar quando falta o consumo urbano."""
    veiculo = montar_veiculo(consumo_cidade=10.0, consumo_estrada=15.0)

    resultado = simular_viagem(veiculo, distancia_km=300, proporcao_cidade=0.0)

    assert custo_de(resultado, "gasolina").litros_necessarios == 20.0


def test_diesel_reconhecido_por_conteudo():
    """Uma ficha com 'Diesel S10' nao pode ser precificada como gasolina."""
    veiculo = montar_veiculo(
        combustivel="Diesel S10",
        consumo_cidade=9.0,
        consumo_estrada=11.0,
        consumo_cidade_etanol=None,
        consumo_estrada_etanol=None,
    )

    resultado = simular_viagem(veiculo, distancia_km=200, preco_diesel=6.9)

    assert custo_de(resultado, "diesel").preco_por_litro == 6.9


def test_flex_exige_as_duas_medidas_de_etanol():
    """Meia coluna de etanol fazia a conta dividir por None."""
    veiculo = montar_veiculo(consumo_estrada_etanol=None)

    resultado = simular_viagem(veiculo, distancia_km=200, proporcao_cidade=0.5)

    assert [c.combustivel for c in resultado.custos] == ["gasolina"]
