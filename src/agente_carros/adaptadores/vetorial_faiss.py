"""Base vetorial em FAISS, lida de um indice construido previamente.

O indice e gerado por `scripts/indexar_documentos.py` e versionado no
repositorio. Em execucao o projeto apenas carrega o arquivo, sem gastar
creditos de embedding para reprocessar os documentos a cada inicializacao.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agente_carros.dominio.modelos import TrechoRecuperado


class IndiceNaoEncontrado(RuntimeError):
    """O indice vetorial ainda nao foi construido."""


class VetorialFAISS:
    """Implementacao de `BaseVetorial` sobre um indice FAISS em disco."""

    def __init__(self, caminho: Path, embeddings: Any) -> None:
        from langchain_community.vectorstores import FAISS

        if not caminho.exists():
            raise IndiceNaoEncontrado(
                f"Indice vetorial nao encontrado em {caminho}. "
                "Rode antes: python scripts/indexar_documentos.py"
            )

        # A desserializacao usa pickle. E segura aqui porque o indice e
        # gerado pelo proprio projeto e versionado junto com o codigo.
        self._indice = FAISS.load_local(
            str(caminho), embeddings, allow_dangerous_deserialization=True
        )

    def buscar(
        self,
        consulta: str,
        quantidade: int,
        tipo: str | None = None,
        limiar: float = 0.0,
    ) -> list[TrechoRecuperado]:
        """Busca por similaridade, com filtro de metadado e corte por relevancia.

        O filtro por `tipo` e aplicado pelo proprio FAISS, antes da
        comparacao de vetores: perguntar sobre garantia nao deve trazer
        trecho da tabela do Inmetro so porque ele fala de veiculos.
        """
        filtro = {"tipo": tipo} if tipo else None
        pares = self._buscar_com_relevancia(consulta, quantidade, filtro)

        trechos = [
            TrechoRecuperado(
                conteudo=documento.page_content,
                fonte=documento.metadata.get("titulo", documento.metadata.get("source", "")),
                pagina=documento.metadata.get("page"),
                relevancia=relevancia,
                tipo=documento.metadata.get("tipo"),
            )
            for documento, relevancia in pares
        ]

        if limiar > 0:
            trechos = [
                trecho
                for trecho in trechos
                if trecho.relevancia is None or trecho.relevancia >= limiar
            ]
        return trechos

    def _buscar_com_relevancia(
        self, consulta: str, quantidade: int, filtro: dict | None
    ) -> list[tuple[Any, float | None]]:
        """Devolve (documento, relevancia), degradando quando nao da para pontuar.

        `similarity_search_with_relevance_scores` normaliza a distancia para
        uma escala de 0 a 1, que e a unica comparavel entre consultas. Nem
        toda versao do LangChain a expoe para todo tipo de indice, entao a
        busca simples continua valendo como alternativa — sem pontuacao, o
        que apenas desativa o limiar.
        """
        try:
            pares = self._indice.similarity_search_with_relevance_scores(
                consulta, k=quantidade, filter=filtro
            )
            return [(documento, float(nota)) for documento, nota in pares]
        except (AttributeError, TypeError, ValueError):
            documentos = self._indice.similarity_search(consulta, k=quantidade, filter=filtro)
            return [(documento, None) for documento in documentos]
