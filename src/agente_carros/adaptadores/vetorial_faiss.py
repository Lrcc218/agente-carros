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

    def buscar(self, consulta: str, quantidade: int) -> list[TrechoRecuperado]:
        documentos = self._indice.similarity_search(consulta, k=quantidade)
        return [
            TrechoRecuperado(
                conteudo=documento.page_content,
                fonte=documento.metadata.get("titulo", documento.metadata.get("source", "")),
                pagina=documento.metadata.get("page"),
            )
            for documento in documentos
        ]
