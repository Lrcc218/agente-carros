"""Tutorial de primeiro acesso.

O conteudo fica em `PASSOS`, como dados. Acrescentar ou reordenar uma tela
nao exige tocar na renderizacao, e o texto pode ser revisado por quem nao
programa.

O estado vive na sessao: o tutorial abre sozinho no primeiro acesso e pode
ser reaberto pela barra lateral a qualquer momento.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import streamlit as st
from streamlit.components.v1 import html as html_bruto

# Onde a preferencia fica gravada no navegador de quem usa.
CHAVE_ARMAZENAMENTO = "consultor_carros_tutorial_visto"
PARAMETRO = "tutorial"
VALOR_VISTO = "visto"


@dataclass(frozen=True)
class Passo:
    """Uma tela do tutorial."""

    selo: str
    titulo: str
    texto: str
    itens: list[str] = field(default_factory=list)
    exemplos: list[str] = field(default_factory=list)
    aviso: str = ""


PASSOS: list[Passo] = [
    Passo(
        selo="Bem-vindo",
        titulo="Um consultor para quem está pesquisando carro",
        texto=(
            "Pesquisar carro hoje significa abrir uma aba para a ficha técnica, outra "
            "para a Tabela FIPE, outra para o consumo, e ainda fazer a conta da viagem "
            "no papel. Este agente junta tudo isso e responde de uma vez só."
        ),
        itens=[
            "28 modelos do ano 2024, do hatch de entrada ao superesportivo",
            "14 marcas, da Fiat à Ferrari",
            "Conversa em português, sem formulário para preencher nem filtro para marcar",
        ],
    ),
    Passo(
        selo="Passo 1 de 5",
        titulo="De onde vem cada número",
        texto=(
            "Nenhum dado aqui foi inventado nem estimado. Cada resposta cita a fonte, "
            "e você pode conferir qualquer número na origem."
        ),
        itens=[
            "Preços: Tabela FIPE, com o mês de referência informado",
            "Consumo: PBE Veicular do Inmetro, o programa oficial de etiquetagem",
            "Combustível: levantamento de preços da ANP, posto a posto, por estado",
        ],
        aviso=(
            "As contas de viagem são feitas em Python, e não pelo modelo de linguagem. "
            "Modelos de IA erram contas com frequência — e com confiança."
        ),
    ),
    Passo(
        selo="Passo 2 de 5",
        titulo="O que ele consegue fazer",
        texto="Seis tipos de pergunta, que podem ser combinados numa mesma conversa.",
        itens=[
            "Ficha técnica: motor, potência, torque, câmbio, tração, porta-malas",
            "Preço: valor da FIPE de qualquer modelo do catálogo",
            "Busca e comparação: filtrar por preço, categoria ou combustível, "
            "e comparar modelos lado a lado",
            "Simulação de viagem: litros e reais, separando cidade e estrada",
            "Preços de combustível: quanto custa em cada estado, e onde o etanol compensa",
            "Manual do proprietário do Corolla: revisão, fluidos, pneus e garantia",
        ],
    ),
    Passo(
        selo="Passo 3 de 5",
        titulo="Como perguntar",
        texto=(
            "Escreva como falaria com um vendedor que entende do assunto. Não precisa "
            "de palavras-chave nem de formato especial. Quanto mais contexto você der, "
            "melhor a resposta."
        ),
        exemplos=[
            "Quais carros custam até 70 mil?",
            "Quanto gasto de São Paulo ao Rio, 430 km, ida e volta, com o Corolla?",
            "Compare o Onix com o HB20",
            "Qual é o SUV mais econômico na estrada?",
            "De quantas em quantas revisões troco o fluido de arrefecimento do Corolla?",
        ],
        aviso=(
            "Para simular uma viagem, informe a distância. Diga também o seu estado: "
            "o cálculo usa o preço do combustível praticado lá."
        ),
    ),
    Passo(
        selo="Passo 4 de 5",
        titulo="A conversa tem memória",
        texto=(
            "O agente lembra o que você já perguntou, então dá para refinar sem "
            "repetir tudo. Pergunte o preço de um carro e, em seguida, apenas "
            "'e o consumo dele?' — ele entende de qual carro você está falando."
        ),
        itens=[
            "Use a barra lateral para ver a lista completa dos 28 modelos",
            "O botão Limpar conversa recomeça do zero a qualquer momento",
            "O botão Tutorial reabre estas telas quando você quiser",
        ],
    ),
    Passo(
        selo="Passo 5 de 5",
        titulo="O que ele não faz — e diz que não faz",
        texto=(
            "Um assistente útil precisa saber onde parar. Nesses casos ele recusa e "
            "explica o motivo, em vez de inventar uma resposta que pareça boa."
        ),
        itens=[
            "Carros fora do catálogo: ele avisa e sugere modelos parecidos que existem "
            "no catálogo",
            "Manutenção de outros modelos: só o Corolla tem manual indexado até agora",
            "Elétricos no custo de viagem: o catálogo tem autonomia, mas não tem o "
            "consumo em kWh",
            "Financiamento, negociação e valor futuro de revenda: fora do escopo",
        ],
        aviso=(
            "A ficha técnica ainda está sendo conferida com o material das "
            "montadoras. Preço e consumo vêm de fonte oficial."
        ),
    ),
]


def _script_promover_preferencia() -> str:
    """Le o navegador e repassa a preferencia para o servidor.

    O Streamlit executa no servidor e nao enxerga o localStorage. A ponte e
    o endereco: se o navegador ja tem a marca de tutorial visto e ela ainda
    nao esta na URL, o script acrescenta o parametro e recarrega uma unica
    vez. A condicao evita laco de recarregamento.
    """
    return f"""
    <script>
    (function () {{
      try {{
        const visto = window.parent.localStorage.getItem("{CHAVE_ARMAZENAMENTO}");
        const url = new URL(window.parent.location.href);
        if (visto === "1" && url.searchParams.get("{PARAMETRO}") !== "{VALOR_VISTO}") {{
          url.searchParams.set("{PARAMETRO}", "{VALOR_VISTO}");
          window.parent.location.replace(url.toString());
        }}
      }} catch (erro) {{
        /* Armazenamento bloqueado no navegador: o tutorial volta a abrir,
           que era o comportamento anterior. Nada quebra. */
      }}
    }})();
    </script>
    """


def _script_gravar_preferencia() -> str:
    return f"""
    <script>
    (function () {{
      try {{
        window.parent.localStorage.setItem("{CHAVE_ARMAZENAMENTO}", "1");
      }} catch (erro) {{}}
    }})();
    </script>
    """


def _ja_viu() -> bool:
    return st.query_params.get(PARAMETRO) == VALOR_VISTO


def iniciar_estado() -> None:
    """Prepara o estado da sessao e consulta a preferencia do navegador."""
    html_bruto(_script_promover_preferencia(), height=0)
    if "tutorial_aberto" not in st.session_state:
        st.session_state.tutorial_aberto = not _ja_viu()
    st.session_state.setdefault("tutorial_passo", 0)


def registrar_preferencia_pendente() -> None:
    """Grava no navegador, na primeira renderizacao apos fechar o tutorial."""
    if st.session_state.pop("tutorial_gravar_preferencia", False):
        html_bruto(_script_gravar_preferencia(), height=0)


def esquecer() -> None:
    """Apaga a preferencia, fazendo o tutorial voltar a abrir sozinho."""
    st.query_params.pop(PARAMETRO, None)
    html_bruto(
        f"""
        <script>
        (function () {{
          try {{
            window.parent.localStorage.removeItem("{CHAVE_ARMAZENAMENTO}");
          }} catch (erro) {{}}
        }})();
        </script>
        """,
        height=0,
    )


def abrir(do_inicio: bool = True) -> None:
    st.session_state.tutorial_aberto = True
    if do_inicio:
        st.session_state.tutorial_passo = 0


def fechar() -> None:
    """Fecha o tutorial e registra que ja foi visto, no servidor e no navegador."""
    st.session_state.tutorial_aberto = False
    st.session_state.tutorial_passo = 0
    st.session_state.tutorial_gravar_preferencia = True
    st.query_params[PARAMETRO] = VALOR_VISTO


def esta_aberto() -> bool:
    return bool(st.session_state.get("tutorial_aberto", False))


def _marcadores(atual: int, total: int) -> str:
    pontos = "".join(
        f'<span class="ponto {"ativo" if i == atual else ""}"></span>' for i in range(total)
    )
    return f'<div class="marcadores">{pontos}</div>'


def _corpo(passo: Passo) -> str:
    partes = [
        f'<div class="tutorial-selo">{passo.selo}</div>',
        f'<h2 class="tutorial-titulo">{passo.titulo}</h2>',
        f'<p class="tutorial-texto">{passo.texto}</p>',
    ]
    if passo.itens:
        itens = "".join(f"<li>{item}</li>" for item in passo.itens)
        partes.append(f'<ul class="tutorial-lista">{itens}</ul>')
    if passo.exemplos:
        exemplos = "".join(f'<div class="tutorial-exemplo">{e}</div>' for e in passo.exemplos)
        partes.append(f'<div class="tutorial-exemplos">{exemplos}</div>')
    if passo.aviso:
        partes.append(f'<div class="tutorial-aviso">{passo.aviso}</div>')
    return "".join(partes)


def renderizar() -> None:
    """Desenha a tela atual do tutorial e trata a navegacao."""
    indice = st.session_state.tutorial_passo
    indice = max(0, min(indice, len(PASSOS) - 1))
    passo = PASSOS[indice]
    primeiro = indice == 0
    ultimo = indice == len(PASSOS) - 1

    st.markdown(
        f'<div class="tutorial-cartao">{_corpo(passo)}'
        f"{_marcadores(indice, len(PASSOS))}</div>",
        unsafe_allow_html=True,
    )

    esquerda, meio, direita = st.columns([1, 1, 1])

    with esquerda:
        if st.button(
            "← Voltar", use_container_width=True, disabled=primeiro, key="tutorial_voltar"
        ):
            st.session_state.tutorial_passo = indice - 1
            st.rerun()

    with meio:
        if not ultimo and st.button(
            "Pular tutorial", use_container_width=True, key="tutorial_pular"
        ):
            fechar()
            st.rerun()

    with direita:
        rotulo = "Começar a usar ✓" if ultimo else "Avançar →"
        if st.button(
            rotulo, use_container_width=True, type="primary", key="tutorial_avancar"
        ):
            if ultimo:
                fechar()
            else:
                st.session_state.tutorial_passo = indice + 1
            st.rerun()
