"""Interface de chat em Streamlit.

Esta camada so cuida de apresentacao: recebe a pergunta, entrega ao agente
e mostra a resposta. Nenhuma regra de negocio mora aqui, de modo que
trocar por uma API, um bot ou uma CLI nao exige tocar no restante.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from agente_carros.agente import responder as responder_agente  # noqa: E402
from agente_carros.config import carregar_configuracao  # noqa: E402
from agente_carros.fabrica import criar_agente  # noqa: E402

TITULO = "Consultor de carros"
SUBTITULO = (
    "Ficha tecnica, preco da Tabela FIPE e simulacao de custo de viagem "
    "para 28 modelos, do popular ao esportivo."
)

EXEMPLOS = [
    "Quais carros custam ate 70 mil?",
    "Quanto gasto de combustivel indo de Sao Paulo ao Rio, 430 km, com o Corolla?",
    "Compare o Onix com o HB20",
    "No Compass, compensa mais gasolina ou etanol?",
    "Qual o SUV mais economico na estrada?",
]


@st.cache_resource(show_spinner="Carregando o catalogo e o agente...")
def carregar_agente():
    """Monta o agente uma unica vez por sessao do servidor."""
    return criar_agente()


def mostrar_barra_lateral(montagem) -> None:
    with st.sidebar:
        st.subheader("Sobre")
        st.write(
            "Precos da Tabela FIPE e consumo do PBE Veicular do Inmetro. "
            "As contas de viagem sao feitas em Python, nao pelo modelo de linguagem."
        )

        veiculos = montagem.catalogo.listar()
        st.metric("Modelos no catalogo", len(veiculos))
        referencia = next((v.mes_referencia_fipe for v in veiculos if v.mes_referencia_fipe), "")
        if referencia:
            st.caption(f"Precos com referencia de {referencia}.")

        if not montagem.tem_indice:
            st.warning(montagem.aviso)

        with st.expander("Ver os modelos"):
            for veiculo in sorted(veiculos, key=lambda v: (v.marca, v.modelo)):
                st.write(f"- {veiculo.marca} {veiculo.modelo} {veiculo.versao}")

        st.divider()
        st.caption(
            "A ficha tecnica esta em conferencia. Preco e consumo vem de fonte oficial."
        )
        if st.button("Limpar conversa", use_container_width=True):
            st.session_state.mensagens = []
            st.rerun()


def mensagem_de_erro(erro: Exception) -> str:
    """Traduz falhas tecnicas em algo acionavel para quem esta usando."""
    texto = str(erro)
    if "429" in texto or "RESOURCE_EXHAUSTED" in texto or "quota" in texto.lower():
        return (
            "A cota gratuita do provedor de IA foi atingida. As camadas gratuitas "
            "limitam quantas perguntas podem ser feitas por dia. Tente de novo mais "
            "tarde, ou configure outro modelo em `MODELO_CHAT`."
        )
    if "API key" in texto or "401" in texto or "403" in texto:
        return (
            "A chave de API foi recusada pelo provedor. Confira se ela e valida e se "
            "a conta tem permissao de inferencia."
        )
    return f"Nao consegui responder agora. Detalhe tecnico: {texto[:300]}"


def responder(montagem, pergunta: str) -> str:
    historico = []
    for mensagem in st.session_state.mensagens[:-1]:
        papel = "human" if mensagem["papel"] == "user" else "ai"
        historico.append((papel, mensagem["conteudo"]))

    return responder_agente(montagem.executor, pergunta, historico)


def main() -> None:
    st.set_page_config(page_title=TITULO, page_icon="🚗", layout="centered")
    st.title(f"🚗 {TITULO}")
    st.caption(SUBTITULO)

    try:
        carregar_configuracao().validar()
    except ValueError as erro:
        st.error(str(erro))
        st.stop()

    try:
        montagem = carregar_agente()
    except Exception as erro:  # noqa: BLE001 - a interface precisa mostrar qualquer falha
        st.error(f"Nao foi possivel iniciar o agente: {erro}")
        st.stop()

    mostrar_barra_lateral(montagem)

    if "mensagens" not in st.session_state:
        st.session_state.mensagens = []

    if not st.session_state.mensagens:
        st.write("Alguns exemplos do que da para perguntar:")
        colunas = st.columns(2)
        for indice, exemplo in enumerate(EXEMPLOS):
            if colunas[indice % 2].button(exemplo, use_container_width=True):
                st.session_state.pergunta_pendente = exemplo
                st.rerun()

    for mensagem in st.session_state.mensagens:
        with st.chat_message(mensagem["papel"]):
            st.markdown(mensagem["conteudo"])

    pergunta = st.chat_input("Pergunte sobre um carro, um preco ou uma viagem")
    if not pergunta:
        pergunta = st.session_state.pop("pergunta_pendente", None)
    if not pergunta:
        return

    st.session_state.mensagens.append({"papel": "user", "conteudo": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando o catalogo..."):
            try:
                resposta = responder(montagem, pergunta)
            except Exception as erro:  # noqa: BLE001 - falha de rede ou de cota
                resposta = mensagem_de_erro(erro)
        st.markdown(resposta)

    st.session_state.mensagens.append({"papel": "assistant", "conteudo": resposta})


if __name__ == "__main__":
    main()
