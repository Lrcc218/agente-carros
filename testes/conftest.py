"""Fixtures compartilhadas pelos testes."""

from __future__ import annotations

import pytest

from agente_carros.adaptadores.catalogo_csv import CatalogoCSV
from agente_carros.config import carregar_configuracao
from agente_carros.dominio.modelos import Veiculo


def montar_veiculo(**alteracoes) -> Veiculo:
    """Cria um veiculo de teste, permitindo sobrescrever campos pontuais."""
    padrao = {
        "id": "teste",
        "marca": "Marca",
        "modelo": "Modelo",
        "versao": "Versao",
        "ano": 2024,
        "categoria": "hatch_popular",
        "motor": "1.0 aspirado",
        "cilindrada": 1.0,
        "potencia_cv": 80,
        "torque_kgfm": 10.0,
        "cambio": "Manual 5 marchas",
        "tracao": "Dianteira",
        "portas": 5,
        "lugares": 5,
        "porta_malas_litros": 300,
        "combustivel": "flex",
        "tanque_litros": 50.0,
        "consumo_cidade": 10.0,
        "consumo_estrada": 15.0,
        "consumo_cidade_etanol": 7.0,
        "consumo_estrada_etanol": 10.5,
        "consumo_cidade_kmle": None,
        "consumo_estrada_kmle": None,
        "autonomia_eletrica_km": None,
        "classe_energetica": "B",
        "versao_pbev": "MARCA MODELO 1.0",
        "preco_fipe": 70000.0,
        "codigo_fipe": "000000-0",
        "mes_referencia_fipe": "agosto de 2026",
        "fonte_ficha": "teste",
    }
    return Veiculo(**{**padrao, **alteracoes})


@pytest.fixture
def catalogo() -> CatalogoCSV:
    """Catalogo real do projeto, para testes de integracao com os datasets."""
    caminhos = carregar_configuracao().caminhos
    return CatalogoCSV(
        caminhos.fichas_tecnicas,
        caminhos.precos_fipe,
        caminhos.processados / "consumo_pbev.csv",
    )
