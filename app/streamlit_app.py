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
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tutorial  # noqa: E402
from estilo import CSS, cabecalho, rodape  # noqa: E402

from agente_carros.agente import responder as responder_agente  # noqa: E402
from agente_carros.config import carregar_configuracao  # noqa: E402
from agente_carros.fabrica import criar_agente  # noqa: E402

TITULO = "Consultor de carros"
SELO = "Agente de IA · dados oficiais"
SUBTITULO = (
    "Ficha técnica, preço da Tabela FIPE, consumo do Inmetro e simulação do custo "
    "real de uma viagem, com o preço do combustível praticado no seu estado. "
    "28 modelos, do hatch de entrada ao superesportivo."
)
FONTES = ["Tabela FIPE", "PBE Veicular / Inmetro", "Levantamento de preços da ANP"]

EXEMPLOS = [
    "Quais carros custam até 70 mil?",
    "Quanto gasto de combustível indo de São Paulo ao Rio, 430 km, com o Corolla?",
    "Compare o Onix com o HB20",
    "No Compass, compensa mais a gasolina ou o etanol?",
    "Qual é o SUV mais econômico na estrada?",
]


@st.cache_resource(show_spinner="Carregando o catálogo e o agente...")
def carregar_agente():
    """Monta o agente uma unica vez por sessao do servidor."""
    return criar_agente()


def mostrar_barra_lateral(montagem) -> None:
    with st.sidebar:
        st.subheader("Sobre")
        st.write(
            "Preços da Tabela FIPE e consumo do PBE Veicular do Inmetro. "
            "As contas de viagem são feitas em Python, e não pelo modelo de linguagem."
        )

        veiculos = montagem.catalogo.listar()
        st.metric("Modelos no catálogo", len(veiculos))
        referencia = next((v.mes_referencia_fipe for v in veiculos if v.mes_referencia_fipe), "")
        if referencia:
            st.caption(f"Preços com referência de {referencia}.")

        if not montagem.tem_indice:
            st.warning(montagem.aviso)

        with st.expander("Ver os 28 modelos"):
            for veiculo in sorted(veiculos, key=lambda v: (v.marca, v.modelo)):
                st.write(f"- {veiculo.marca} {veiculo.modelo} {veiculo.versao}")

        st.divider()
        if st.button("📖 Tutorial", use_container_width=True, key="abrir_tutorial"):
            tutorial.abrir()
            st.rerun()
        if st.button(
            "Voltar a mostrar o tutorial",
            use_container_width=True,
            key="esquecer_tutorial",
            help="Apaga a preferência guardada neste navegador",
        ):
            tutorial.esquecer()
            st.toast("O tutorial voltará a abrir sozinho neste navegador.")
        if st.button("Limpar conversa", use_container_width=True, key="limpar_conversa"):
            st.session_state.mensagens = []
            st.rerun()

        st.caption(
            "A ficha técnica está em conferência. Preço e consumo vêm de fonte oficial."
        )


def mensagem_de_erro(erro: Exception) -> str:
    """Traduz falhas tecnicas em algo acionavel para quem esta usando."""
    texto = str(erro)
    if "429" in texto or "RESOURCE_EXHAUSTED" in texto or "quota" in texto.lower():
        return (
            "A cota gratuita do provedor de IA foi atingida. Os planos gratuitos "
            "limitam quantas perguntas podem ser feitas por dia. Tente de novo mais "
            "tarde."
        )
    if "API key" in texto or "401" in texto or "403" in texto:
        return (
            "A chave de API foi recusada pelo provedor. Confira se ela é válida e se "
            "a conta tem permissão de inferência."
        )
    return f"Não consegui responder agora. Detalhe técnico: {texto[:300]}"


# Quantas mensagens anteriores acompanham cada pergunta. Sem teto, uma
# conversa longa reenvia tudo a cada turno, o que gasta cota e chega a
# estourar o contexto do modelo.
TURNOS_DE_HISTORICO = 12


def responder(montagem, pergunta: str) -> str:
    historico = []
    for mensagem in st.session_state.mensagens[:-1][-TURNOS_DE_HISTORICO:]:
        papel = "human" if mensagem["papel"] == "user" else "ai"
        historico.append((papel, mensagem["conteudo"]))

    return responder_agente(montagem.executor, pergunta, historico)


def main() -> None:
    st.set_page_config(page_title=TITULO, page_icon="🚗", layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(cabecalho(TITULO, SUBTITULO, SELO), unsafe_allow_html=True)

    try:
        carregar_configuracao().validar()
    except ValueError as erro:
        st.error(str(erro))
        st.stop()

    try:
        montagem = carregar_agente()
    except Exception as erro:  # noqa: BLE001 - a interface precisa mostrar qualquer falha
        st.error(f"Não foi possível iniciar o agente: {erro}")
        st.stop()

    if "mensagens" not in st.session_state:
        st.session_state.mensagens = []

    # O tutorial ocupa a tela inteira: no primeiro acesso ele vem antes do
    # agente, e depois so reaparece se a pessoa pedir na barra lateral.
    tutorial.iniciar_estado()
    if tutorial.esta_aberto():
        tutorial.renderizar()
        return

    # Grava no navegador que o tutorial ja foi visto, logo apos ele fechar.
    tutorial.registrar_preferencia_pendente()

    mostrar_barra_lateral(montagem)

    if not st.session_state.mensagens:
        st.markdown("**Comece por aqui**")
        colunas = st.columns(2)
        for indice, exemplo in enumerate(EXEMPLOS):
            if colunas[indice % 2].button(exemplo, use_container_width=True):
                st.session_state.pergunta_pendente = exemplo
                st.rerun()

    for mensagem in st.session_state.mensagens:
        with st.chat_message(mensagem["papel"]):
            st.markdown(mensagem["conteudo"])

    if not st.session_state.mensagens:
        st.markdown(rodape(FONTES), unsafe_allow_html=True)

    pergunta = st.chat_input(
        "Pergunte sobre um carro, um preço ou uma viagem", max_chars=2000
    )
    if not pergunta:
        pergunta = st.session_state.pop("pergunta_pendente", None)
    if not pergunta:
        return

    st.session_state.mensagens.append({"papel": "user", "conteudo": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando o catálogo..."):
            try:
                resposta = responder(montagem, pergunta)
            except Exception as erro:  # noqa: BLE001 - falha de rede ou de cota
                resposta = mensagem_de_erro(erro)
        st.markdown(resposta)

    st.session_state.mensagens.append({"papel": "assistant", "conteudo": resposta})


if __name__ == "__main__":
    main()
