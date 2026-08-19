"""Formatacao de numeros e datas no padrao brasileiro.

Fica separado porque mais de uma ferramenta precisa, e porque numero em
formato errado e o tipo de detalhe que passa despercebido no codigo e salta
aos olhos de quem le a resposta: "R$ 169.11" nao existe em portugues.
"""

from __future__ import annotations

SEM_VALOR = "não informado"


def _trocar_separadores(texto: str) -> str:
    """Converte 1,234.56 para 1.234,56, sem tocar no resto da frase."""
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_reais(valor: float | None) -> str:
    """Valor monetario: R$ 1.234,56."""
    if valor is None:
        return SEM_VALOR
    return f"R$ {_trocar_separadores(f'{valor:,.2f}')}"


def formatar_numero(valor: float | None, casas: int = 2) -> str:
    """Numero decimal com virgula: 1.234,56."""
    if valor is None:
        return SEM_VALOR
    return _trocar_separadores(f"{valor:,.{casas}f}")


def formatar_data(iso: str) -> str:
    """Converte 2026-07-01 em 01/07/2026."""
    partes = iso.split("-")
    return f"{partes[2]}/{partes[1]}/{partes[0]}" if len(partes) == 3 else iso
