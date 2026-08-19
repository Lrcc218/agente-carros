"""Repositorio de precos de combustivel lendo o resumo da ANP em CSV.

Satisfaz a porta `RepositorioPrecosCombustivel`. O dataset e gerado por
`scripts/coletar_precos_anp.py` a partir do levantamento oficial.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from agente_carros.dominio.modelos import PrecoCombustivel

NACIONAL = "BR"


class PrecosANP:
    """Precos medianos por estado e produto."""

    def __init__(self, caminho: Path) -> None:
        self._precos: dict[tuple[str, str], PrecoCombustivel] = {}
        if not caminho.exists():
            return

        tabela = pd.read_csv(caminho)
        for _, linha in tabela.iterrows():
            preco = PrecoCombustivel(
                uf=str(linha["uf"]).upper(),
                produto=str(linha["produto"]),
                preco_mediano=float(linha["preco_mediano"]),
                preco_minimo=float(linha["preco_minimo"]),
                preco_maximo=float(linha["preco_maximo"]),
                amostras=int(linha["amostras"]),
                periodo_inicio=str(linha["periodo_inicio"]),
                periodo_fim=str(linha["periodo_fim"]),
            )
            self._precos[(preco.produto, preco.uf)] = preco

    @property
    def disponivel(self) -> bool:
        return bool(self._precos)

    def preco(self, produto: str, uf: str = NACIONAL) -> PrecoCombustivel | None:
        """Preco no estado pedido, caindo para a mediana nacional se faltar.

        Diesel comum e S10 tem apuracao separada; quando o estado nao tem
        diesel comum, o S10 serve de referencia, e vice-versa.
        """
        alvo = (uf or NACIONAL).upper()
        alternativo = None
        if produto.startswith("diesel"):
            alternativo = "diesel_s10" if produto == "diesel" else "diesel"

        # A apuracao local do outro tipo de diesel representa melhor o preco
        # daquele estado do que a mediana nacional do tipo pedido. Antes o
        # nacional vinha primeiro, e o ramo do alternativo era inalcancavel.
        tentativas = [(produto, alvo)]
        if alternativo:
            tentativas.append((alternativo, alvo))
        tentativas.append((produto, NACIONAL))
        if alternativo:
            tentativas.append((alternativo, NACIONAL))

        for chave in tentativas:
            if chave in self._precos:
                return self._precos[chave]
        return None

    def por_estado(self, produto: str) -> list[PrecoCombustivel]:
        return sorted(
            (p for (prod, uf), p in self._precos.items() if prod == produto and uf != NACIONAL),
            key=lambda p: p.preco_mediano,
        )

    def estados_disponiveis(self) -> list[str]:
        return sorted({uf for _, uf in self._precos if uf != NACIONAL})
