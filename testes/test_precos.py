"""Testes dos precos de combustivel da ANP e da sua ligacao com a simulacao."""

from __future__ import annotations

import pytest

from agente_carros.adaptadores.precos_anp_csv import PrecosANP
from agente_carros.agente import _resolver_precos
from agente_carros.config import carregar_configuracao
from agente_carros.ferramentas.consultar_precos import consultar_precos, ranking_estados


@pytest.fixture
def precos() -> PrecosANP:
    caminhos = carregar_configuracao().caminhos
    return PrecosANP(caminhos.processados / "precos_combustivel_anp.csv")


def test_dataset_da_anp_esta_disponivel(precos):
    assert precos.disponivel


def test_cobre_as_27_unidades_da_federacao(precos):
    assert len(precos.estados_disponiveis()) == 27


def test_preco_por_estado_difere_da_media_nacional(precos):
    nacional = precos.preco("etanol", "BR")
    paulista = precos.preco("etanol", "SP")

    assert nacional.uf == "BR"
    assert paulista.uf == "SP"
    assert paulista.preco_mediano != nacional.preco_mediano


def test_estado_desconhecido_cai_para_a_media_nacional(precos):
    resultado = precos.preco("gasolina", "XX")
    assert resultado is not None
    assert resultado.uf == "BR"


def test_precos_estao_em_faixa_plausivel(precos):
    for produto in ("gasolina", "etanol", "diesel"):
        preco = precos.preco(produto, "BR")
        assert 2.0 < preco.preco_mediano < 12.0
        assert preco.amostras > 1000


def test_ranking_ordena_do_mais_barato_ao_mais_caro(precos):
    lista = precos.por_estado("etanol")
    valores = [p.preco_mediano for p in lista]
    assert valores == sorted(valores)


def test_consulta_traz_a_leitura_de_etanol_contra_gasolina(precos):
    texto = consultar_precos(precos, "SP")
    assert "Etanol hidratado" in texto
    assert "% do preco da gasolina" in texto


def test_consulta_a_estado_inexistente_sugere_os_validos(precos):
    texto = consultar_precos(precos, "ZZ")
    assert "Nao ha apuracao" in texto
    assert "SP" in texto


def test_ranking_separa_baratos_e_caros(precos):
    texto = ranking_estados(precos, "gasolina")
    assert "Mais baratos:" in texto
    assert "Mais caros:" in texto


def test_resolucao_usa_a_anp_quando_nada_e_informado(precos):
    vazios = {"preco_gasolina": None, "preco_etanol": None, "preco_diesel": None}

    valores, fonte = _resolver_precos(precos, "SP", vazios)

    assert valores["preco_gasolina"] == precos.preco("gasolina", "SP").preco_mediano
    assert "mediana de SP" in fonte
    assert "ANP" in fonte


def test_preco_informado_pelo_usuario_tem_prioridade(precos):
    informados = {"preco_gasolina": 7.5, "preco_etanol": None, "preco_diesel": None}

    valores, fonte = _resolver_precos(precos, "SP", informados)

    assert valores["preco_gasolina"] == 7.5
    assert valores["preco_etanol"] == precos.preco("etanol", "SP").preco_mediano
    # A procedencia precisa separar o que veio de quem: antes a frase dizia
    # que todos os precos eram do usuario, inclusive os que vieram da ANP.
    assert "gasolina: informado por voce" in fonte
    assert "mediana de SP" in fonte


def test_procedencia_distingue_estado_de_media_nacional(precos):
    """Uma UF sem apuracao alguma cai para a mediana nacional, e diz isso."""
    vazios = {"preco_gasolina": None, "preco_etanol": None, "preco_diesel": None}

    valores, fonte = _resolver_precos(precos, "XX", vazios)

    assert valores["preco_gasolina"] == precos.preco("gasolina", "BR").preco_mediano
    assert "mediana nacional" in fonte


def test_diesel_prefere_apuracao_local_a_mediana_nacional(precos):
    """No Amapa nao ha diesel comum apurado, mas ha S10.

    O ramo do alternativo era codigo morto: a mediana nacional vinha antes e
    sempre casava, entao o preco local do outro tipo de diesel era ignorado.
    """
    resultado = precos.preco("diesel", "AP")

    assert resultado is not None
    assert resultado.uf == "AP"
    assert resultado.produto == "diesel_s10"


def test_sem_dataset_usa_valores_de_referencia():
    vazios = {"preco_gasolina": None, "preco_etanol": None, "preco_diesel": None}

    valores, fonte = _resolver_precos(None, "SP", vazios)

    assert valores["preco_gasolina"] > 0
    assert "sem apuracao oficial" in fonte
