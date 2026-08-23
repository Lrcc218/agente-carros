"""Testes da camada de recuperacao.

Duas garantias: o filtro por tipo nao pode calar a busca quando for
estreito demais, e o limiar de relevancia precisa realmente descartar
trecho ruim — que e o mecanismo que impede o modelo de responder com
material irrelevante recuperado por falta de coisa melhor.
"""

from __future__ import annotations

from agente_carros.dominio.modelos import TrechoRecuperado
from agente_carros.ferramentas.buscar_documentos import SEM_RESULTADO, buscar_nos_documentos


class BaseFalsa:
    """Base vetorial de mentira, que registra como foi chamada."""

    def __init__(self, trechos: dict[str | None, list[TrechoRecuperado]]) -> None:
        self._trechos = trechos
        self.chamadas: list[str | None] = []

    def buscar(self, consulta, quantidade, tipo=None, limiar=0.0):
        self.chamadas.append(tipo)
        encontrados = self._trechos.get(tipo, [])
        return [t for t in encontrados if t.relevancia is None or t.relevancia >= limiar]


def trecho(conteudo="conteudo", fonte="Manual", pagina=None, relevancia=None):
    return TrechoRecuperado(
        conteudo=conteudo, fonte=fonte, pagina=pagina, relevancia=relevancia
    )


def test_cita_a_fonte_e_a_pagina():
    base = BaseFalsa({None: [trecho(fonte="Manual do Corolla", pagina=41)]})
    saida = buscar_nos_documentos(base, "troca de oleo")
    # A pagina e exibida em base 1, como no documento impresso.
    assert "[Trecho 1 — Manual do Corolla, pagina 42]" in saida


def test_filtro_por_tipo_e_repassado():
    base = BaseFalsa({"manual": [trecho()]})
    buscar_nos_documentos(base, "garantia", tipo="manual")
    assert base.chamadas == ["manual"]


def test_tipo_invalido_e_ignorado():
    """Se o modelo inventar um tipo, a busca vale no acervo inteiro."""
    base = BaseFalsa({None: [trecho()]})
    buscar_nos_documentos(base, "garantia", tipo="juridico")
    assert base.chamadas == [None]


def test_filtro_vazio_tenta_de_novo_sem_ele():
    """Filtro estreito demais nao pode virar 'nao encontrei'."""
    base = BaseFalsa({"manual": [], None: [trecho(fonte="PBE Veicular")]})
    saida = buscar_nos_documentos(base, "eficiencia", tipo="manual")

    assert base.chamadas == ["manual", None]
    assert "PBE Veicular" in saida


def test_limiar_descarta_trecho_irrelevante():
    base = BaseFalsa({None: [trecho(fonte="Ruim", relevancia=0.1)]})
    assert buscar_nos_documentos(base, "pergunta fora do escopo", limiar=0.5) == SEM_RESULTADO


def test_limiar_mantem_trecho_relevante():
    base = BaseFalsa({None: [trecho(fonte="Bom", relevancia=0.8)]})
    assert "Bom" in buscar_nos_documentos(base, "pergunta coberta", limiar=0.5)


def test_sem_nada_indexado_avisa_em_vez_de_inventar():
    assert buscar_nos_documentos(BaseFalsa({}), "qualquer coisa") == SEM_RESULTADO
