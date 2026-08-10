"""Busca semantica nos documentos oficiais indexados.

Usada para perguntas sobre texto corrido — metodologia da etiquetagem,
significado das faixas de eficiencia, criterios do programa — e nao para
numeros de veiculos, que vem do catalogo estruturado.
"""

from __future__ import annotations

from agente_carros.dominio.portas import BaseVetorial


def buscar_nos_documentos(base: BaseVetorial, consulta: str, quantidade: int = 4) -> str:
    """Devolve os trechos mais relevantes, cada um com a fonte citada."""
    trechos = base.buscar(consulta, quantidade)
    if not trechos:
        return "Nenhum trecho relevante encontrado nos documentos oficiais indexados."

    blocos = []
    for indice, trecho in enumerate(trechos, start=1):
        pagina = f", pagina {trecho.pagina + 1}" if trecho.pagina is not None else ""
        blocos.append(f"[Trecho {indice} — {trecho.fonte}{pagina}]\n{trecho.conteudo}")
    return "\n\n".join(blocos)
