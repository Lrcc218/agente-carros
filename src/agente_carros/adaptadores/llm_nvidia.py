"""Provedor de modelos hospedados no NVIDIA NIM.

Satisfaz a porta `ProvedorLLM`. Para trocar de provedor, escreva outra
classe com os mesmos dois metodos e aponte a fabrica para ela — nenhuma
outra parte do projeto conhece a NVIDIA.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any

from agente_carros.config import Configuracao


class ProvedorNVIDIA:
    """Modelos de chat e de embedding do catalogo da NVIDIA."""

    def __init__(self, config: Configuracao) -> None:
        config.validar()
        self._config = config

    @cached_property
    def _chat(self) -> Any:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA

        return ChatNVIDIA(
            model=self._config.modelo_chat,
            api_key=self._config.chave_api,
            temperature=self._config.temperatura,
        )

    @cached_property
    def _embedding(self) -> Any:
        from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

        return NVIDIAEmbeddings(
            model=self._config.modelo_embedding,
            api_key=self._config.chave_api,
        )

    def modelo_chat(self) -> Any:
        return self._chat

    def modelo_embedding(self) -> Any:
        return self._embedding
