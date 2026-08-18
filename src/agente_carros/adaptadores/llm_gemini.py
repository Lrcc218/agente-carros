"""Provedor de modelos do Google Gemini.

Satisfaz a mesma porta `ProvedorLLM` que o adaptador da NVIDIA. Os dois
convivem: qual entra em uso e decidido pela variavel PROVEDOR_LLM, sem
nenhuma alteracao no agente, nas ferramentas ou na interface.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any

from agente_carros.config import Configuracao

# Os modelos "lite" tem cota gratuita diaria bem maior que os completos,
# o que importa num agente: cada pergunta consome duas ou tres chamadas.
MODELO_CHAT_PADRAO = "gemini-3.5-flash-lite"
MODELO_EMBEDDING_PADRAO = "models/gemini-embedding-2"


class ProvedorGemini:
    """Modelos de chat e de embedding da API do Google Gemini."""

    def __init__(self, config: Configuracao) -> None:
        config.validar()
        self._config = config

    @property
    def _nome_chat(self) -> str:
        # Os nomes de modelo diferem entre provedores. Se a configuracao
        # ainda aponta para um modelo da NVIDIA, usa o padrao do Gemini.
        nome = self._config.modelo_chat
        return nome if "/" not in nome or nome.startswith("models/") else MODELO_CHAT_PADRAO

    @property
    def _nome_embedding(self) -> str:
        nome = self._config.modelo_embedding
        return nome if nome.startswith("models/") else MODELO_EMBEDDING_PADRAO

    @cached_property
    def _chat(self) -> Any:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=self._nome_chat,
            google_api_key=self._config.chave_api,
            temperature=self._config.temperatura,
        )

    @cached_property
    def _embedding(self) -> Any:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=self._nome_embedding,
            google_api_key=self._config.chave_api,
        )

    def modelo_chat(self) -> Any:
        return self._chat

    def modelo_embedding(self) -> Any:
        return self._embedding
