"""Testes do catalogo e das consultas estruturadas."""

from __future__ import annotations

from agente_carros.ferramentas.consultar_catalogo import (
    buscar_veiculo,
    comparar_veiculos,
    listar_veiculos,
    resumo_catalogo,
)


def test_catalogo_carrega_todos_os_modelos(catalogo):
    assert len(catalogo.listar()) == 28


def test_todo_veiculo_tem_preco_da_fipe(catalogo):
    sem_preco = [v.id for v in catalogo.listar() if v.preco_fipe is None]
    assert sem_preco == []


def test_todo_veiculo_a_combustao_tem_consumo(catalogo):
    """Regressao: o T-Cross ficava de fora por erro de casamento de texto.

    O PDF do Inmetro grafa "T CROSS" sem hifen, e o padrao do mapa procurava
    "T-CROSS". O dado sempre existiu na fonte.
    """
    sem_consumo = {
        v.id for v in catalogo.listar() if not v.tem_dados_de_consumo and not v.e_eletrico
    }
    assert sem_consumo == set()


def test_busca_exige_todas_as_palavras(catalogo):
    cross = catalogo.buscar_por_nome("corolla cross")
    assert [v.id for v in cross] == ["toyota_corolla_cross"]


def test_busca_ignora_acento_e_caixa(catalogo):
    assert catalogo.buscar_por_nome("MERCEDES")[0].marca == "Mercedes-Benz"


def test_filtro_por_preco_maximo(catalogo):
    baratos = catalogo.filtrar(preco_maximo=70000)
    assert baratos
    assert all(v.preco_fipe <= 70000 for v in baratos)


def test_filtro_por_marca_e_categoria(catalogo):
    suvs = catalogo.filtrar(categoria="suv_compacto")
    assert len(suvs) > 1
    assert all("suv_compacto" in v.categoria for v in suvs)


def test_filtro_combinado_aplica_todos_os_criterios(catalogo):
    resultado = catalogo.filtrar(combustivel="eletrico", preco_maximo=150000)
    assert [v.id for v in resultado] == ["byd_dolphin"]


def test_listagem_ordena_por_preco_crescente(catalogo):
    texto = listar_veiculos(catalogo, preco_maximo=80000, ordenar_por="preco")
    assert "Kwid" in texto
    assert texto.index("Kwid") < texto.index("Polo")


def test_listagem_sem_resultado_avisa(catalogo):
    assert "Nenhum veículo" in listar_veiculos(catalogo, preco_maximo=1000)


def test_ficha_cita_a_procedencia_dos_dados(catalogo):
    ficha = buscar_veiculo(catalogo, "hilux")
    assert "Preço FIPE" in ficha
    assert "Referência FIPE" in ficha
    assert "Versão no PBE Veicular" in ficha


def test_busca_sem_resultado_sugere_as_marcas(catalogo):
    resposta = buscar_veiculo(catalogo, "lamborghini")
    assert "Nenhum veículo" in resposta
    assert "Ferrari" in resposta


def test_tcross_tem_consumo_do_inmetro(catalogo):
    veiculo = catalogo.buscar_por_nome("t-cross")[0]

    assert veiculo.consumo_cidade == 12.1
    assert veiculo.consumo_estrada == 14.5
    assert "T CROSS SENSE" in veiculo.versao_pbev


def test_comparacao_traz_os_dois_veiculos(catalogo):
    texto = comparar_veiculos(catalogo, ["onix", "hb20"])
    assert "Onix" in texto and "HB20" in texto


def test_comparacao_exige_dois_veiculos(catalogo):
    assert "pelo menos dois" in comparar_veiculos(catalogo, ["onix"])


def test_listagem_avisa_quando_trunca(catalogo):
    """Sem esse aviso o agente descreve o catalogo inteiro a partir de 10 itens."""
    texto = listar_veiculos(catalogo)

    assert "28" in texto
    assert "incompleta" in texto.lower()
    assert "resumo_catalogo" in texto


def test_listagem_curta_nao_avisa_truncagem(catalogo):
    texto = listar_veiculos(catalogo, combustivel="eletrico")

    assert "incompleta" not in texto.lower()


def test_resumo_traz_todas_as_marcas(catalogo):
    texto = resumo_catalogo(catalogo)

    for marca in ("BMW", "Mercedes-Benz", "Porsche", "Ferrari", "BYD", "Fiat"):
        assert marca in texto, f"{marca} ausente do resumo"


def test_resumo_conta_certo(catalogo):
    texto = resumo_catalogo(catalogo)

    assert "28 veículos" in texto
    assert "14 marcas" in texto


def test_resumo_traz_a_faixa_de_preco(catalogo):
    texto = resumo_catalogo(catalogo)

    assert "Faixa de preço" in texto
    assert "3.309.948" in texto  # a Ferrari, o teto do catalogo


def test_marcas_premium_estao_no_catalogo(catalogo):
    """Regressao: o agente ja afirmou que o catalogo nao tinha essas marcas."""
    marcas = {v.marca for v in catalogo.listar()}

    assert {"BMW", "Mercedes-Benz", "Porsche", "Ferrari"} <= marcas
