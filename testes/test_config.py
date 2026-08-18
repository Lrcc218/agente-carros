"""Testes da resolucao de provedor, chave e modelo.

Esta camada decide qual API sera chamada e com qual credencial. Um erro
aqui aparece como 403 no meio do uso, longe da causa, entao ela e testada
diretamente.
"""

from __future__ import annotations

import importlib

import pytest

import agente_carros.config as modulo_config


@pytest.fixture
def ambiente(monkeypatch):
    """Isola as variaveis de ambiente e recarrega a configuracao.

    Neutraliza o `load_dotenv`: sem isso o `.env` da maquina de quem roda os
    testes repovoa as variaveis durante o recarregamento do modulo, e o teste
    passa a medir a configuracao real em vez da configuracao do caso.
    """
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)

    def configurar(**valores):
        for nome in (
            "PROVEDOR_LLM",
            "GOOGLE_API_KEY",
            "GEMINI_API_KEY",
            "NVIDIA_API_KEY",
            "MODELO_CHAT",
            "MODELO_EMBEDDING",
        ):
            monkeypatch.delenv(nome, raising=False)
        for nome, valor in valores.items():
            monkeypatch.setenv(nome, valor)
        # A configuracao le o ambiente na definicao da classe.
        return importlib.reload(modulo_config).carregar_configuracao()

    yield configurar
    importlib.reload(modulo_config)


def test_gemini_e_o_provedor_padrao(ambiente):
    config = ambiente()
    assert config.provedor_llm == "gemini"


def test_cada_provedor_le_a_propria_variavel(ambiente):
    gemini = ambiente(PROVEDOR_LLM="gemini", GOOGLE_API_KEY="AIzaChaveGemini")
    assert gemini.chave_api == "AIzaChaveGemini"

    nvidia = ambiente(PROVEDOR_LLM="nvidia", NVIDIA_API_KEY="nvapi-ChaveNvidia")
    assert nvidia.chave_api == "nvapi-ChaveNvidia"


def test_chave_do_outro_provedor_nao_vaza(ambiente):
    """Ter a chave da NVIDIA no ambiente nao pode configurar o Gemini."""
    config = ambiente(PROVEDOR_LLM="gemini", NVIDIA_API_KEY="nvapi-ChaveNvidia")
    assert config.chave_api == ""


def test_gemini_aceita_variavel_alternativa(ambiente):
    config = ambiente(PROVEDOR_LLM="gemini", GEMINI_API_KEY="AIzaAlternativa")
    assert config.chave_api == "AIzaAlternativa"


def test_modelos_padrao_seguem_o_provedor(ambiente):
    gemini = ambiente(PROVEDOR_LLM="gemini", GOOGLE_API_KEY="AIzaX")
    assert gemini.modelo_chat.startswith("gemini")
    assert gemini.modelo_embedding.startswith("models/")

    nvidia = ambiente(PROVEDOR_LLM="nvidia", NVIDIA_API_KEY="nvapi-X")
    assert nvidia.modelo_chat == "meta/llama-3.3-70b-instruct"
    assert nvidia.modelo_embedding == "nvidia/nv-embedqa-e5-v5"


def test_modelo_definido_no_ambiente_prevalece(ambiente):
    config = ambiente(
        PROVEDOR_LLM="gemini", GOOGLE_API_KEY="AIzaX", MODELO_CHAT="gemini-2.5-pro"
    )
    assert config.modelo_chat == "gemini-2.5-pro"


def test_validar_falha_sem_chave_e_diz_qual_variavel(ambiente):
    config = ambiente(PROVEDOR_LLM="gemini")
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        config.validar()


def test_validar_passa_com_chave(ambiente):
    ambiente(PROVEDOR_LLM="nvidia", NVIDIA_API_KEY="nvapi-X").validar()


def test_espacos_em_volta_da_chave_sao_removidos(ambiente):
    config = ambiente(PROVEDOR_LLM="gemini", GOOGLE_API_KEY="  AIzaComEspaco  ")
    assert config.chave_api == "AIzaComEspaco"


def test_provedor_desconhecido_e_recusado_pela_fabrica(ambiente):
    from agente_carros.fabrica import criar_provedor

    config = ambiente(PROVEDOR_LLM="inexistente", GOOGLE_API_KEY="AIzaX")
    with pytest.raises(ValueError, match="desconhecido"):
        criar_provedor(config)


def test_fabrica_conhece_gemini_e_nvidia():
    from agente_carros.fabrica import PROVEDORES

    assert sorted(PROVEDORES) == ["gemini", "nvidia"]
