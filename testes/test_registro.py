"""Testes do registro de execucao.

O registro e observabilidade: precisa gravar o que promete, e precisa
falhar em silencio quando nao conseguir gravar. Um erro de disco nao pode
derrubar uma conversa.
"""

from __future__ import annotations

import json

import pytest

from agente_carros import registro


def ler(diretorio) -> list[dict]:
    linhas = []
    for arquivo in sorted(diretorio.glob("*.jsonl")):
        linhas.extend(json.loads(linha) for linha in arquivo.read_text().splitlines() if linha)
    return linhas


def test_grava_execucao_com_os_campos_de_auditoria(tmp_path):
    id_execucao = registro.registrar_execucao(
        diretorio=tmp_path,
        pergunta="quanto custa o Corolla?",
        resposta="R$ 145.000",
        duracao_ms=1234,
        ferramentas=["buscar_veiculo"],
        fontes=["Tabela FIPE"],
        interface="cli",
    )

    (evento,) = ler(tmp_path)
    assert evento["evento"] == "execucao"
    assert evento["id"] == id_execucao
    assert evento["pergunta"] == "quanto custa o Corolla?"
    assert evento["duracao_ms"] == 1234
    assert evento["ferramentas"] == ["buscar_veiculo"]
    assert evento["fontes"] == ["Tabela FIPE"]
    assert evento["momento"]


def test_feedback_referencia_a_execucao(tmp_path):
    id_execucao = registro.registrar_execucao(
        diretorio=tmp_path, pergunta="p", resposta="r", duracao_ms=1
    )
    registro.registrar_feedback(tmp_path, id_execucao, util=False, comentario="errou o preco")

    _, feedback = ler(tmp_path)
    assert feedback["evento"] == "feedback"
    assert feedback["id"] == id_execucao
    assert feedback["util"] is False


def test_corta_resposta_gigante(tmp_path):
    registro.registrar_execucao(
        diretorio=tmp_path, pergunta="p", resposta="x" * 9000, duracao_ms=1
    )
    (evento,) = ler(tmp_path)
    assert len(evento["resposta"]) < 9000
    assert "cortado" in evento["resposta"]


def test_falha_de_escrita_nao_propaga(tmp_path):
    """Disco cheio ou caminho invalido nao pode interromper a resposta."""
    arquivo = tmp_path / "ocupado"
    arquivo.write_text("nao sou um diretorio")

    # Nao levanta: o diretorio de destino e, na verdade, um arquivo.
    registro.registrar_execucao(
        diretorio=arquivo / "dentro", pergunta="p", resposta="r", duracao_ms=1
    )


def test_desligar_pelo_ambiente(tmp_path, monkeypatch):
    monkeypatch.setenv("REGISTRAR_EXECUCOES", "0")
    registro.registrar_execucao(diretorio=tmp_path, pergunta="p", resposta="r", duracao_ms=1)
    assert not list(tmp_path.glob("*.jsonl"))


def test_extrai_nomes_das_ferramentas():
    class Acao:
        tool = "simular_viagem"

    passos = [(Acao(), "saida"), ({"tool": "buscar_veiculo"}, "saida"), (None, "saida")]
    assert registro.ferramentas_usadas(passos) == ["simular_viagem", "buscar_veiculo"]
    assert registro.ferramentas_usadas(None) == []


def test_ids_sao_distintos():
    assert registro.novo_id() != registro.novo_id()


class ExecutorFalso:
    """Imita o AgentExecutor do LangChain, sem LangChain."""

    def __init__(self, saida=None, excecao=None):
        self._saida = saida
        self._excecao = excecao

    def invoke(self, entrada):
        if self._excecao:
            raise self._excecao
        return self._saida


def test_responder_registra_ferramentas_e_fontes(tmp_path, monkeypatch):
    from agente_carros.agente import responder

    monkeypatch.setenv("DIR_REGISTROS", str(tmp_path))

    class Acao:
        tool = "buscar_documentos_oficiais"

    executor = ExecutorFalso(
        {
            "output": "A revisão é a cada 10.000 km.",
            "intermediate_steps": [
                (Acao(), "[Trecho 1 — Manual do proprietario Corolla, pagina 42]\ntexto")
            ],
        }
    )

    resposta = responder(executor, "de quanto em quanto tempo revisar?")
    assert resposta == "A revisão é a cada 10.000 km."

    (evento,) = ler(tmp_path)
    assert evento["ferramentas"] == ["buscar_documentos_oficiais"]
    assert evento["fontes"] == ["Manual do proprietario Corolla"]
    assert evento["erro"] is None
    assert evento["duracao_ms"] >= 0


def test_responder_registra_a_falha_e_propaga(tmp_path, monkeypatch):
    """Uma falha de cota tem de ficar no registro, nao so na tela."""
    from agente_carros.agente import responder

    monkeypatch.setenv("DIR_REGISTROS", str(tmp_path))
    executor = ExecutorFalso(excecao=RuntimeError("cota esgotada"))

    with pytest.raises(RuntimeError):
        responder(executor, "qualquer pergunta")

    (evento,) = ler(tmp_path)
    assert "cota esgotada" in evento["erro"]
    assert evento["resposta"] == ""
