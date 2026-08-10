"""Testes do catalogo e das consultas estruturadas."""

from __future__ import annotations

from agente_carros.ferramentas.consultar_catalogo import (
    buscar_veiculo,
    comparar_veiculos,
    listar_veiculos,
)


def test_catalogo_carrega_todos_os_modelos(catalogo):
    assert len(catalogo.listar()) == 28


def test_todo_veiculo_tem_preco_da_fipe(catalogo):
    sem_preco = [v.id for v in catalogo.listar() if v.preco_fipe is None]
    assert sem_preco == []


def test_apenas_o_tcross_fica_sem_consumo(catalogo):
    """O T-Cross nao consta no PBE Veicular; os demais precisam ter consumo."""
    sem_consumo = {
        v.id for v in catalogo.listar() if not v.tem_dados_de_consumo and not v.e_eletrico
    }
    assert sem_consumo == {"vw_tcross"}


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
    assert "Nenhum veiculo" in listar_veiculos(catalogo, preco_maximo=1000)


def test_ficha_cita_a_procedencia_dos_dados(catalogo):
    ficha = buscar_veiculo(catalogo, "hilux")
    assert "Preco FIPE" in ficha
    assert "Referencia FIPE" in ficha
    assert "Versao no PBE Veicular" in ficha


def test_busca_sem_resultado_sugere_as_marcas(catalogo):
    resposta = buscar_veiculo(catalogo, "lamborghini")
    assert "Nenhum veiculo" in resposta
    assert "Ferrari" in resposta


def test_tcross_declara_a_ausencia_de_consumo(catalogo):
    assert "nao publicado" in buscar_veiculo(catalogo, "t-cross")


def test_comparacao_traz_os_dois_veiculos(catalogo):
    texto = comparar_veiculos(catalogo, ["onix", "hb20"])
    assert "Onix" in texto and "HB20" in texto


def test_comparacao_exige_dois_veiculos(catalogo):
    assert "pelo menos dois" in comparar_veiculos(catalogo, ["onix"])
