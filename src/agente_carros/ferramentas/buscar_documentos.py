"""Busca semantica nos documentos indexados.

Usada para perguntas sobre texto corrido — metodologia da etiquetagem,
significado das faixas de eficiencia, procedimentos do manual — e nao para
numeros de veiculos, que vem do catalogo estruturado.

Duas salvaguardas contra a resposta confiante e errada:

- o filtro por tipo restringe o universo de busca antes da comparacao de
  vetores, quando a pergunta e claramente sobre manual ou claramente sobre
  documento oficial;
- o limiar de relevancia descarta trecho que a busca devolveu por falta de
  coisa melhor. Sem nada acima do limiar, a ferramenta diz que nao achou,
  em vez de entregar material irrelevante que o modelo tentaria usar.
"""

from __future__ import annotations

from agente_carros.dominio.portas import BaseVetorial

TIPOS = {"documento_interno", "manual", "documento_oficial"}

SEM_RESULTADO = "Nenhum trecho relevante encontrado nos documentos indexados."


def buscar_nos_documentos(
    base: BaseVetorial,
    consulta: str,
    quantidade: int = 4,
    tipo: str | None = None,
    limiar: float = 0.0,
) -> str:
    """Devolve os trechos mais relevantes, cada um com a fonte citada."""
    tipo = tipo if tipo in TIPOS else None

    trechos = base.buscar(consulta, quantidade, tipo=tipo, limiar=limiar)
    if not trechos and tipo:
        # O filtro pode ter sido estreito demais. Antes de dizer que nao ha
        # nada, tenta de novo no acervo inteiro.
        trechos = base.buscar(consulta, quantidade, tipo=None, limiar=limiar)

    if not trechos:
        return SEM_RESULTADO

    blocos = []
    for indice, trecho in enumerate(trechos, start=1):
        pagina = f", pagina {trecho.pagina + 1}" if trecho.pagina is not None else ""
        blocos.append(f"[Trecho {indice} — {trecho.fonte}{pagina}]\n{trecho.conteudo}")
    return "\n\n".join(blocos)

