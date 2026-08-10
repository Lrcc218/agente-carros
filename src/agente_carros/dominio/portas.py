"""Portas do sistema: contratos que as implementacoes concretas devem cumprir.

Sao `Protocol`, entao qualquer classe com os metodos corretos serve, sem
heranca e sem acoplamento. Trocar NVIDIA por outro provedor ou FAISS por
outra base vetorial significa escrever uma nova classe que satisfaca a
porta e alterar apenas a fabrica.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from agente_carros.dominio.modelos import TrechoRecuperado, Veiculo


@runtime_checkable
class ProvedorLLM(Protocol):
    """Fornece o modelo de chat usado pelo agente."""

    def modelo_chat(self) -> Any:
        """Devolve um modelo de chat compativel com tool calling do LangChain."""
        ...

    def modelo_embedding(self) -> Any:
        """Devolve o modelo de embeddings usado na indexacao e na busca."""
        ...


@runtime_checkable
class BaseVetorial(Protocol):
    """Armazena e recupera trechos de documentos por similaridade."""

    def buscar(self, consulta: str, quantidade: int) -> list[TrechoRecuperado]:
        """Recupera os trechos mais relevantes para a consulta."""
        ...


@runtime_checkable
class RepositorioCatalogo(Protocol):
    """Acesso aos dados estruturados dos veiculos."""

    def listar(self) -> list[Veiculo]:
        """Todos os veiculos do catalogo."""
        ...

    def buscar_por_nome(self, termo: str) -> list[Veiculo]:
        """Veiculos cujo nome corresponde ao termo informado."""
        ...

    def filtrar(
        self,
        marca: str | None = None,
        categoria: str | None = None,
        preco_maximo: float | None = None,
        preco_minimo: float | None = None,
        combustivel: str | None = None,
    ) -> list[Veiculo]:
        """Veiculos que atendem simultaneamente aos criterios informados."""
        ...
