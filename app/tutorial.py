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
        titulo="Um consultor para quem esta pesquisando carro",
        texto=(
            "Pesquisar carro hoje significa abrir uma aba para a ficha tecnica, outra "
            "para a tabela FIPE, outra para o consumo, e ainda fazer a conta da viagem "
            "no papel. Este agente junta tudo isso e responde em uma frase."
        ),
        itens=[
            "28 modelos do ano 2024, do hatch de entrada ao superesportivo",
            "14 marcas, da Fiat a Ferrari",
            "Conversa em portugues, sem formulario nem filtro para preencher",
        ],
    ),
    Passo(
        selo="Passo 1 de 5",
        titulo="De onde vem cada numero",
        texto=(
            "Nenhum dado aqui foi inventado nem estimado. Cada resposta cita a fonte, "
            "e voce pode conferir qualquer numero na origem."
        ),
        itens=[
            "Precos: Tabela FIPE, com o mes de referencia informado",
            "Consumo: PBE Veicular do Inmetro, o programa oficial de etiquetagem",
            "Combustivel: levantamento de precos da ANP, posto a posto, por estado",
        ],
        aviso=(
            "As contas de viagem sao feitas em Python, nao pelo modelo de linguagem. "
            "Modelos de IA erram aritmetica com frequencia e confianca."
        ),
    ),
    Passo(
        selo="Passo 2 de 5",
        titulo="O que ele consegue fazer",
        texto="Cinco tipos de pergunta, que podem ser combinados numa conversa.",
        itens=[
            "Ficha tecnica: motor, potencia, torque, cambio, tracao, porta-malas",
            "Preco: valor da FIPE de qualquer modelo do catalogo",
            "Busca e comparacao: filtrar por preco, categoria ou combustivel",
            "Simulacao de viagem: litros e reais, separando cidade e estrada",
            "Documentos do Inmetro: metodologia e faixas de eficiencia energetica",
        ],
    ),
    Passo(
        selo="Passo 3 de 5",
        titulo="Como perguntar",
        texto=(
            "Escreva como falaria com um vendedor que entende do assunto. Nao precisa "
            "de palavra-chave nem de formato especial. Quanto mais contexto voce der, "
            "melhor a resposta."
        ),
        exemplos=[
            "Quais carros custam ate 70 mil?",
            "Quanto gasto de Sao Paulo ao Rio, 430 km, ida e volta, com o Corolla?",
            "Compare o Onix com o HB20",
            "Qual o SUV mais economico na estrada?",
            "Compensa abastecer com etanol aqui em Minas?",
        ],
        aviso=(
            "Para simular viagem, informe a distancia. Diga tambem o seu estado, e o "
            "calculo usa o preco de combustivel praticado la."
        ),
    ),
    Passo(
        selo="Passo 4 de 5",
        titulo="A conversa tem memoria",
        texto=(
            "O agente lembra do que voce ja perguntou, entao da para refinar sem "
            "repetir tudo. Pergunte o preco de um carro e, em seguida, apenas "
            "'e o consumo dele?' — ele entende de quem voce esta falando."
        ),
        itens=[
            "Use a barra lateral para ver a lista completa dos 28 modelos",
            "O botao Limpar conversa recomeca do zero quando quiser",
            "O botao Tutorial reabre estas telas a qualquer momento",
        ],
    ),
    Passo(
        selo="Passo 5 de 5",
        titulo="O que ele nao faz, e diz que nao faz",
        texto=(
            "Um assistente util precisa saber onde para. Nestes casos ele recusa e "
            "explica o motivo, em vez de inventar uma resposta que parece boa."
        ),
        itens=[
            "Carros fora do catalogo: ele avisa e sugere modelos parecidos que tem",
            "T-Cross em viagem: sem consumo publicado no Inmetro, nao simula",
            "Eletricos em custo de viagem: ha autonomia, mas nao consumo em kWh",
            "Financiamento, negociacao e valor de revenda futuro: fora do escopo",
        ],
        aviso=(
            "A ficha tecnica ainda esta em conferencia contra o material das "
            "montadoras. Preco e consumo vem de fonte oficial."
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
        rotulo = "Comecar a usar ✓" if ultimo else "Avancar →"
        if st.button(
            rotulo, use_container_width=True, type="primary", key="tutorial_avancar"
        ):
            if ultimo:
                fechar()
            else:
                st.session_state.tutorial_passo = indice + 1
            st.rerun()
