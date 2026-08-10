"""Repositorio de catalogo lendo os datasets em CSV.

Junta as tres fontes pelo `id`: ficha tecnica curada, precos da FIPE e
consumo do PBE Veicular. Manter as fontes separadas em disco preserva a
procedencia de cada dado; a juncao acontece so aqui.

Trocar para banco de dados significa escrever outra classe que satisfaca
`RepositorioCatalogo` e alterar apenas a fabrica.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

import pandas as pd

from agente_carros.dominio.modelos import Veiculo


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return sem_acento.casefold().strip()


def _texto(valor: object) -> str:
    return "" if pd.isna(valor) else str(valor).strip()


def _decimal(valor: object) -> float | None:
    return None if pd.isna(valor) else float(valor)


def _inteiro(valor: object) -> int | None:
    return None if pd.isna(valor) else int(valor)


class CatalogoCSV:
    """Implementacao de `RepositorioCatalogo` sobre arquivos CSV."""

    def __init__(self, fichas: Path, precos: Path, consumo: Path) -> None:
        self._veiculos = self._carregar(fichas, precos, consumo)

    @staticmethod
    def _carregar(fichas: Path, precos: Path, consumo: Path) -> list[Veiculo]:
        tabela = pd.read_csv(fichas)
        for caminho in (precos, consumo):
            if caminho.exists():
                tabela = tabela.merge(pd.read_csv(caminho), on="id", how="left")

        # Se um dataset opcional nao existir, as colunas dele faltam. Cria
        # vazias para que a montagem abaixo funcione de qualquer forma.
        for coluna in (
            "preco_fipe",
            "codigo_fipe",
            "mes_referencia",
            "etanol_cidade",
            "etanol_estrada",
            "principal_cidade",
            "principal_estrada",
            "eletrico_cidade_kmle",
            "eletrico_estrada_kmle",
            "autonomia_eletrica_km",
            "classe_absoluta",
            "versao_pbev",
        ):
            if coluna not in tabela.columns:
                tabela[coluna] = pd.NA

        return [
            Veiculo(
                id=linha["id"],
                marca=_texto(linha["marca"]),
                modelo=_texto(linha["modelo"]),
                versao=_texto(linha["versao"]),
                ano=int(linha["ano"]),
                categoria=_texto(linha["categoria"]),
                motor=_texto(linha["motor"]),
                cilindrada=_decimal(linha["cilindrada"]),
                potencia_cv=_inteiro(linha["potencia_cv"]),
                torque_kgfm=_decimal(linha["torque_kgfm"]),
                cambio=_texto(linha["cambio"]),
                tracao=_texto(linha["tracao"]),
                portas=int(linha["portas"]),
                lugares=int(linha["lugares"]),
                porta_malas_litros=_inteiro(linha["porta_malas_litros"]),
                combustivel=_texto(linha["combustivel"]),
                tanque_litros=_decimal(linha["tanque_litros"]),
                consumo_cidade=_decimal(linha["principal_cidade"]),
                consumo_estrada=_decimal(linha["principal_estrada"]),
                consumo_cidade_etanol=_decimal(linha["etanol_cidade"]),
                consumo_estrada_etanol=_decimal(linha["etanol_estrada"]),
                consumo_cidade_kmle=_decimal(linha["eletrico_cidade_kmle"]),
                consumo_estrada_kmle=_decimal(linha["eletrico_estrada_kmle"]),
                autonomia_eletrica_km=_inteiro(linha["autonomia_eletrica_km"]),
                classe_energetica=_texto(linha["classe_absoluta"]),
                versao_pbev=_texto(linha["versao_pbev"]),
                preco_fipe=_decimal(linha["preco_fipe"]),
                codigo_fipe=_texto(linha["codigo_fipe"]),
                mes_referencia_fipe=_texto(linha["mes_referencia"]),
                fonte_ficha=_texto(linha["fonte_ficha"]),
            )
            for _, linha in tabela.iterrows()
        ]

    def listar(self) -> list[Veiculo]:
        return list(self._veiculos)

    def buscar_por_nome(self, termo: str) -> list[Veiculo]:
        """Casa o termo contra id, marca, modelo e versao.

        Exige que todas as palavras do termo apareçam, o que faz
        "corolla cross" nao devolver o Corolla sedan.
        """
        palavras = _normalizar(termo).split()
        if not palavras:
            return []

        encontrados = []
        for veiculo in self._veiculos:
            alvo = _normalizar(
                f"{veiculo.id} {veiculo.marca} {veiculo.modelo} {veiculo.versao}"
            )
            if all(palavra in alvo for palavra in palavras):
                encontrados.append(veiculo)
        return encontrados

    def filtrar(
        self,
        marca: str | None = None,
        categoria: str | None = None,
        preco_maximo: float | None = None,
        preco_minimo: float | None = None,
        combustivel: str | None = None,
    ) -> list[Veiculo]:
        resultado = self._veiculos

        if marca:
            alvo = _normalizar(marca)
            resultado = [v for v in resultado if alvo in _normalizar(v.marca)]
        if categoria:
            alvo = _normalizar(categoria)
            resultado = [v for v in resultado if alvo in _normalizar(v.categoria)]
        if combustivel:
            alvo = _normalizar(combustivel)
            resultado = [v for v in resultado if alvo in _normalizar(v.combustivel)]
        if preco_maximo is not None:
            resultado = [
                v for v in resultado if v.preco_fipe is not None and v.preco_fipe <= preco_maximo
            ]
        if preco_minimo is not None:
            resultado = [
                v for v in resultado if v.preco_fipe is not None and v.preco_fipe >= preco_minimo
            ]
        return resultado
