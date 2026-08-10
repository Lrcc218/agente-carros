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
    def indice_vetorial(self) -> Path:
        return self.processados / "indice_faiss"

    @property
    def documentos(self) -> Path:
        return self.brutos / "documentos"


@dataclass(frozen=True)
class Configuracao:
    """Parametros de execucao lidos do ambiente."""

    provedor_llm: str = os.getenv("PROVEDOR_LLM", "nvidia")
    chave_api: str = os.getenv("NVIDIA_API_KEY", "")
    modelo_chat: str = os.getenv("MODELO_CHAT", "meta/llama-3.3-70b-instruct")
    modelo_embedding: str = os.getenv("MODELO_EMBEDDING", "nvidia/nv-embedqa-e5-v5")
    temperatura: float = float(os.getenv("TEMPERATURA", "0.1"))
    trechos_recuperados: int = int(os.getenv("TRECHOS_RECUPERADOS", "4"))
    caminhos: Caminhos = field(default_factory=Caminhos)

    def validar(self) -> None:
        """Falha cedo e com mensagem util quando falta configuracao essencial."""
        if not self.chave_api:
            raise ValueError(
                "NVIDIA_API_KEY nao configurada. "
                "Copie .env.example para .env e preencha a chave, "
                "ou defina o segredo no painel da plataforma de deploy."
            )


def carregar_configuracao() -> Configuracao:
    """Ponto unico de acesso a configuracao."""
    return Configuracao()
