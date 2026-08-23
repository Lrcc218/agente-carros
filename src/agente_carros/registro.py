"""Registro de execucao: o que o agente respondeu, e com que material.

Cada pergunta vira uma linha de JSON num arquivo diario. O formato JSON
Lines e proposital: o arquivo pode ser lido, filtrado e agregado com
ferramentas de linha de comando, cresce por acrescimo e nunca precisa ser
reescrito inteiro.

Guardamos o suficiente para auditar uma resposta depois — pergunta, texto
devolvido, quais ferramentas foram chamadas, quais fontes foram
recuperadas e quanto tempo levou — e nada que identifique quem perguntou.

O registro nunca derruba a conversa: qualquer falha ao gravar e engolida.
Um disco cheio nao pode impedir o agente de responder.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Gravacoes vindas de sessoes simultaneas do Streamlit disputam o arquivo.
# A escrita e curta o bastante para um lock simples resolver.
_TRAVA = threading.Lock()

LIMITE_TEXTO = 4000


@dataclass
class Execucao:
    """Uma pergunta respondida, do ponto de vista da auditoria."""

    id: str
    momento: str
    pergunta: str
    resposta: str
    duracao_ms: int
    ferramentas: list[str] = field(default_factory=list)
    fontes: list[str] = field(default_factory=list)
    sessao: str | None = None
    interface: str = "desconhecida"
    provedor: str | None = None
    modelo: str | None = None
    erro: str | None = None


def novo_id() -> str:
    """Identificador curto, usado para ligar um feedback a sua execucao."""
    return uuid.uuid4().hex[:12]


def _agora() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _cortar(texto: str) -> str:
    """Evita que uma resposta gigante inche o arquivo de registro."""
    texto = texto or ""
    if len(texto) <= LIMITE_TEXTO:
        return texto
    return texto[:LIMITE_TEXTO] + f"... [cortado, {len(texto)} caracteres]"


def arquivo_do_dia(diretorio: Path, momento: datetime | None = None) -> Path:
    """Um arquivo por dia, o que mantem cada um legivel e facil de arquivar."""
    dia = (momento or datetime.now()).strftime("%Y-%m-%d")
    return diretorio / f"execucoes-{dia}.jsonl"


def habilitado() -> bool:
    """Desligar o registro e uma decisao de ambiente, nao de codigo."""
    return os.getenv("REGISTRAR_EXECUCOES", "1").strip().lower() not in {"0", "false", "nao"}


def gravar(diretorio: Path, evento: dict[str, Any]) -> None:
    """Acrescenta um evento ao arquivo do dia. Falha em silencio, de proposito."""
    if not habilitado():
        return
    try:
        with _TRAVA:
            diretorio.mkdir(parents=True, exist_ok=True)
            destino = arquivo_do_dia(diretorio)
            with destino.open("a", encoding="utf-8") as arquivo:
                arquivo.write(json.dumps(evento, ensure_ascii=False) + "\n")
    except OSError:
        # Registro e observabilidade, nao funcionalidade. Se o disco encheu
        # ou o caminho e somente leitura, a conversa continua.
        pass


def registrar_execucao(
    diretorio: Path,
    pergunta: str,
    resposta: str,
    duracao_ms: int,
    ferramentas: list[str] | None = None,
    fontes: list[str] | None = None,
    sessao: str | None = None,
    interface: str = "desconhecida",
    provedor: str | None = None,
    modelo: str | None = None,
    erro: str | None = None,
    id_execucao: str | None = None,
) -> str:
    """Grava uma execucao e devolve o id, para um feedback poder cita-lo."""
    execucao = Execucao(
        id=id_execucao or novo_id(),
        momento=_agora(),
        pergunta=_cortar(pergunta),
        resposta=_cortar(resposta),
        duracao_ms=duracao_ms,
        ferramentas=ferramentas or [],
        fontes=fontes or [],
        sessao=sessao,
        interface=interface,
        provedor=provedor,
        modelo=modelo,
        erro=erro,
    )
    gravar(diretorio, {"evento": "execucao", **asdict(execucao)})
    return execucao.id


def registrar_feedback(
    diretorio: Path,
    id_execucao: str,
    util: bool,
    comentario: str = "",
    sessao: str | None = None,
) -> None:
    """Grava a avaliacao que o usuario deu a uma resposta."""
    gravar(
        diretorio,
        {
            "evento": "feedback",
            "id": id_execucao,
            "momento": _agora(),
            "util": util,
            "comentario": _cortar(comentario),
            "sessao": sessao,
        },
    )


def ferramentas_usadas(passos: Any) -> list[str]:
    """Extrai os nomes das ferramentas dos passos intermediarios do executor.

    A forma exata do passo muda entre versoes do LangChain, entao aqui se
    tenta o atributo e depois a chave, aceitando nao encontrar nada.
    """
    nomes: list[str] = []
    for passo in passos or []:
        acao = passo[0] if isinstance(passo, tuple | list) and passo else passo
        nome = getattr(acao, "tool", None)
        if nome is None and isinstance(acao, dict):
            nome = acao.get("tool") or acao.get("name")
        if nome:
            nomes.append(str(nome))
    return nomes
