"""Configuracao central do projeto.

Todo caminho de arquivo e toda variavel de ambiente sao resolvidos aqui.
Nenhum outro modulo deve ler `os.environ` diretamente, para que trocar
provedor, modelo ou local de dados seja uma alteracao em um unico ponto.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RAIZ = Path(__file__).resolve().parents[2]

# Cada provedor le a sua propria variavel de ambiente. O nome do modelo
# padrao tambem muda, porque as nomenclaturas nao sao compativeis.
VARIAVEIS_DE_CHAVE = {
    "gemini": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    "nvidia": ("NVIDIA_API_KEY",),
}

MODELOS_PADRAO = {
    "gemini": ("gemini-2.0-flash", "models/text-embedding-004"),
    "nvidia": ("meta/llama-3.3-70b-instruct", "nvidia/nv-embedqa-e5-v5"),
}


@dataclass(frozen=True)
class Caminhos:
    """Localizacao dos artefatos de dados do projeto."""

    raiz: Path = RAIZ
    dados: Path = field(default_factory=lambda: RAIZ / "dados")
    brutos: Path = field(default_factory=lambda: RAIZ / "dados" / "brutos")
    processados: Path = field(default_factory=lambda: RAIZ / "dados" / "processados")

    @property
    def fichas_tecnicas(self) -> Path:
        return self.processados / "fichas_tecnicas.csv"

    @property
    def precos_fipe(self) -> Path:
        return self.processados / "precos_fipe.csv"

    @property
    def precos_combustivel(self) -> Path:
        return self.processados / "precos_combustivel_anp.csv"

    @property
    def consumo_pbev(self) -> Path:
        return self.processados / "consumo_pbev.csv"

    @property
    def indice_vetorial(self) -> Path:
        return self.processados / "indice_faiss"

    @property
    def documentos(self) -> Path:
        return self.brutos / "documentos"


def _chave_do_provedor(provedor: str) -> str:
    for variavel in VARIAVEIS_DE_CHAVE.get(provedor, ()):
        valor = os.getenv(variavel, "").strip()
        if valor:
            return valor
    return ""


def _modelo(indice: int, provedor: str, variavel: str) -> str:
    definido = os.getenv(variavel, "").strip()
    if definido:
        return definido
    return MODELOS_PADRAO.get(provedor, MODELOS_PADRAO["gemini"])[indice]


@dataclass(frozen=True)
class Configuracao:
    """Parametros de execucao lidos do ambiente."""

    provedor_llm: str = os.getenv("PROVEDOR_LLM", "gemini").strip().lower()
    temperatura: float = float(os.getenv("TEMPERATURA", "0.1"))
    trechos_recuperados: int = int(os.getenv("TRECHOS_RECUPERADOS", "4"))
    caminhos: Caminhos = field(default_factory=Caminhos)

    @property
    def chave_api(self) -> str:
        return _chave_do_provedor(self.provedor_llm)

    @property
    def modelo_chat(self) -> str:
        return _modelo(0, self.provedor_llm, "MODELO_CHAT")

    @property
    def modelo_embedding(self) -> str:
        return _modelo(1, self.provedor_llm, "MODELO_EMBEDDING")

    def validar(self) -> None:
        """Falha cedo e com mensagem util quando falta configuracao essencial."""
        if not self.chave_api:
            esperadas = " ou ".join(VARIAVEIS_DE_CHAVE.get(self.provedor_llm, ("?",)))
            raise ValueError(
                f"Chave de API nao configurada para o provedor '{self.provedor_llm}'. "
                f"Defina {esperadas} no arquivo .env, "
                "ou no painel de segredos da plataforma de deploy."
            )


def carregar_configuracao() -> Configuracao:
    """Ponto unico de acesso a configuracao."""
    return Configuracao()
