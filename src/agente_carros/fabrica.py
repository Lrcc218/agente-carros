"""Fabrica: monta o agente ligando as implementacoes concretas as portas.

Este e o unico arquivo que escolhe qual adaptador usar. Trocar de provedor
de IA, de base vetorial ou de fonte de dados se resume a alterar as
funcoes abaixo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agente_carros.adaptadores.catalogo_csv import CatalogoCSV
from agente_carros.adaptadores.llm_gemini import ProvedorGemini
from agente_carros.adaptadores.llm_nvidia import ProvedorNVIDIA
from agente_carros.adaptadores.precos_anp_csv import PrecosANP
from agente_carros.adaptadores.vetorial_faiss import IndiceNaoEncontrado, VetorialFAISS
from agente_carros.agente import montar_agente
from agente_carros.config import Configuracao, carregar_configuracao
from agente_carros.dominio.portas import (
    BaseVetorial,
    ProvedorLLM,
    RepositorioCatalogo,
    RepositorioPrecosCombustivel,
)

PROVEDORES = {"gemini": ProvedorGemini, "nvidia": ProvedorNVIDIA}


@dataclass
class Montagem:
    """O agente pronto, com as pecas usadas para monta-lo."""

    executor: Any
    catalogo: RepositorioCatalogo
    tem_indice: bool
    tem_precos: bool = False
    aviso: str = ""


def criar_provedor(config: Configuracao) -> ProvedorLLM:
    classe = PROVEDORES.get(config.provedor_llm)
    if classe is None:
        disponiveis = ", ".join(sorted(PROVEDORES))
        raise ValueError(
            f"Provedor '{config.provedor_llm}' desconhecido. Disponiveis: {disponiveis}."
        )
    return classe(config)


def criar_catalogo(config: Configuracao) -> RepositorioCatalogo:
    caminhos = config.caminhos
    return CatalogoCSV(
        fichas=caminhos.fichas_tecnicas,
        precos=caminhos.precos_fipe,
        consumo=caminhos.consumo_pbev,
    )


def criar_precos_combustivel(config: Configuracao) -> RepositorioPrecosCombustivel | None:
    """Devolve os precos da ANP, ou None se o dataset ainda nao foi coletado.

    Sem ele a simulacao continua funcionando com valores de referencia, mas
    perde o preco por estado.
    """
    repositorio = PrecosANP(config.caminhos.precos_combustivel)
    return repositorio if repositorio.disponivel else None


def criar_base_vetorial(config: Configuracao, provedor: ProvedorLLM) -> BaseVetorial | None:
    """Devolve a base vetorial, ou None se o indice ainda nao foi construido.

    A ausencia do indice nao impede o agente de funcionar: ele perde apenas
    as perguntas sobre os documentos do Inmetro, e segue respondendo sobre
    catalogo, precos e viagens.
    """
    try:
        return VetorialFAISS(config.caminhos.indice_vetorial, provedor.modelo_embedding())
    except IndiceNaoEncontrado:
        return None


def criar_agente(config: Configuracao | None = None) -> Montagem:
    config = config or carregar_configuracao()

    provedor = criar_provedor(config)
    catalogo = criar_catalogo(config)
    base_vetorial = criar_base_vetorial(config, provedor)
    precos = criar_precos_combustivel(config)

    executor = montar_agente(
        modelo_chat=provedor.modelo_chat(),
        catalogo=catalogo,
        base_vetorial=base_vetorial,
        trechos_recuperados=config.trechos_recuperados,
        precos=precos,
        limiar_relevancia=config.limiar_relevancia,
    )

    pendencias = []
    if base_vetorial is None:
        pendencias.append(
            "Índice de documentos não encontrado; perguntas sobre os documentos "
            "oficiais e sobre o manual não serão respondidas."
        )
    if precos is None:
        pendencias.append(
            "Preços da ANP não encontrados; a simulação usará valores de referência "
            "em vez do preço do seu estado."
        )

    return Montagem(
        executor=executor,
        catalogo=catalogo,
        tem_indice=base_vetorial is not None,
        tem_precos=precos is not None,
        aviso=" ".join(pendencias),
    )
