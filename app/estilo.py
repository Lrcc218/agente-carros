"""Identidade visual da interface.

Fica separado do app para que a aparencia possa mudar sem tocar na logica
de conversa, e para que outra interface reaproveite os mesmos tokens.

Sobre a inspiracao: a composicao segue uma gramatica visual comum em
paginas de produto tecnico — tela escura, brilhos radiais mascarados nas
bordas, malha tenue ao fundo e um gradiente de destaque. Sao tecnicas de
CSS de dominio publico. A paleta, o motivo grafico e a tipografia foram
escolhidos para este projeto: asfalto noturno com as duas cores de
sinalizacao de um carro, ambar da seta e vermelho da lanterna.
"""

from __future__ import annotations

# Tokens da identidade. Alterar aqui muda a interface inteira.
TINTA_FUNDO = "#080A0F"
TINTA_FUNDO_ALTO = "#0E121B"
TINTA_SUPERFICIE = "rgba(255, 255, 255, 0.045)"
TINTA_BORDA = "rgba(255, 255, 255, 0.09)"
TEXTO = "#E9ECF3"
TEXTO_SUAVE = "#98A2B3"
AMBAR = "#FFB020"
LANTERNA = "#FF3B6B"
GRADIENTE = f"linear-gradient(100deg, {AMBAR} 0%, {LANTERNA} 100%)"

CSS = f"""
<style>
:root {{
  --fundo: {TINTA_FUNDO};
  --fundo-alto: {TINTA_FUNDO_ALTO};
  --superficie: {TINTA_SUPERFICIE};
  --borda: {TINTA_BORDA};
  --texto: {TEXTO};
  --texto-suave: {TEXTO_SUAVE};
  --ambar: {AMBAR};
  --lanterna: {LANTERNA};
  --gradiente: {GRADIENTE};
}}

/* ---------- tela ---------- */

.stApp {{
  background: var(--fundo);
  color: var(--texto);
}}

/* Camada de fundo: malha tenue de asfalto, com dois brilhos radiais
   mascarados que desvanecem antes de tocar as bordas. Fica atras de todo
   o conteudo e nao intercepta cliques. */
.stApp::before {{
  content: "";
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(ellipse 90% 55% at 50% -10%,
      rgba(255, 176, 32, 0.20) 0%,
      rgba(255, 176, 32, 0.06) 35%,
      transparent 70%),
    radial-gradient(ellipse 80% 50% at 50% 108%,
      rgba(255, 59, 107, 0.18) 0%,
      rgba(255, 59, 107, 0.05) 40%,
      transparent 72%),
    repeating-linear-gradient(90deg,
      rgba(255, 255, 255, 0.028) 0px,
      rgba(255, 255, 255, 0.028) 1px,
      transparent 1px,
      transparent 76px),
    repeating-linear-gradient(0deg,
      rgba(255, 255, 255, 0.022) 0px,
      rgba(255, 255, 255, 0.022) 1px,
      transparent 1px,
      transparent 76px),
    linear-gradient(180deg, var(--fundo-alto) 0%, var(--fundo) 55%);
  -webkit-mask-image: radial-gradient(ellipse 120% 100% at 50% 40%,
    #000 0%, #000 55%, transparent 92%);
  mask-image: radial-gradient(ellipse 120% 100% at 50% 40%,
    #000 0%, #000 55%, transparent 92%);
}}

.stApp > * {{ position: relative; z-index: 1; }}

[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stToolbar"] {{ right: 1rem; }}

/* ---------- cabecalho ---------- */

.faixa-marca {{
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.3rem 0.85rem;
  border: 1px solid var(--borda);
  border-radius: 999px;
  background: var(--superficie);
  font-size: 0.74rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--texto-suave);
  margin-bottom: 1.1rem;
}}

.faixa-marca .farol {{
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--ambar);
  box-shadow: 0 0 10px 2px rgba(255, 176, 32, 0.65);
}}

.titulo-agente {{
  font-size: clamp(2.1rem, 5.5vw, 3.4rem);
  font-weight: 700;
  line-height: 1.05;
  letter-spacing: -0.025em;
  margin: 0 0 0.6rem 0;
  background: var(--gradiente);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}}

.subtitulo-agente {{
  color: var(--texto-suave);
  font-size: 1.02rem;
  line-height: 1.6;
  max-width: 46rem;
  margin-bottom: 0.4rem;
}}

/* Linha de pista: faixa fina com o gradiente, sob o cabecalho. */
.faixa-pista {{
  height: 2px;
  width: 100%;
  margin: 1.4rem 0 1.8rem 0;
  background: var(--gradiente);
  opacity: 0.5;
  border-radius: 2px;
}}

/* ---------- conversa ---------- */

[data-testid="stChatMessage"] {{
  background: var(--superficie);
  border: 1px solid var(--borda);
  border-radius: 14px;
  padding: 1rem 1.15rem;
  margin-bottom: 0.85rem;
  backdrop-filter: blur(9px);
}}

/* A mensagem do agente ganha um filete ambar a esquerda, para separar
   visualmente quem fala sem precisar de cor de fundo diferente. */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {{
  border-left: 2px solid var(--ambar);
}}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li {{
  color: var(--texto);
  line-height: 1.65;
}}

[data-testid="stChatMessage"] strong {{ color: var(--ambar); }}

[data-testid="stChatMessage"] code {{
  background: rgba(255, 255, 255, 0.07);
  color: var(--ambar);
  border-radius: 5px;
  padding: 0.1rem 0.35rem;
}}

[data-testid="stChatInput"] {{
  background: var(--superficie);
  border: 1px solid var(--borda);
  border-radius: 14px;
  backdrop-filter: blur(9px);
}}

[data-testid="stChatInput"]:focus-within {{
  border-color: rgba(255, 176, 32, 0.55);
  box-shadow: 0 0 0 3px rgba(255, 176, 32, 0.10);
}}

[data-testid="stChatInput"] textarea {{ color: var(--texto); }}
[data-testid="stChatInput"] textarea::placeholder {{ color: var(--texto-suave); }}

/* ---------- botoes ---------- */

.stButton > button {{
  background: var(--superficie);
  border: 1px solid var(--borda);
  border-radius: 11px;
  color: var(--texto);
  font-size: 0.9rem;
  padding: 0.6rem 0.95rem;
  text-align: left;
  transition: border-color 0.18s ease, transform 0.18s ease, background 0.18s ease;
}}

.stButton > button:hover {{
  border-color: rgba(255, 176, 32, 0.5);
  background: rgba(255, 176, 32, 0.07);
  color: var(--texto);
  transform: translateY(-1px);
}}

.stButton > button:active,
.stButton > button:focus:not(:active) {{
  border-color: var(--ambar);
  color: var(--texto);
}}

/* ---------- barra lateral ---------- */

[data-testid="stSidebar"] {{
  background: rgba(8, 10, 15, 0.86);
  border-right: 1px solid var(--borda);
  backdrop-filter: blur(14px);
}}

[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{ color: var(--texto); }}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] label {{ color: var(--texto-suave); }}

[data-testid="stMetricValue"] {{
  background: var(--gradiente);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  font-weight: 700;
}}

[data-testid="stMetricLabel"] {{
  color: var(--texto-suave);
  text-transform: uppercase;
  letter-spacing: 0.09em;
  font-size: 0.7rem;
}}

[data-testid="stExpander"] {{
  background: var(--superficie);
  border: 1px solid var(--borda);
  border-radius: 11px;
}}

/* ---------- rodape de fontes ---------- */

.rodape-fontes {{
  margin-top: 2.2rem;
  padding-top: 1.1rem;
  border-top: 1px solid var(--borda);
  color: var(--texto-suave);
  font-size: 0.79rem;
  line-height: 1.75;
}}

.rodape-fontes .selo {{
  display: inline-block;
  padding: 0.16rem 0.55rem;
  margin-right: 0.4rem;
  border: 1px solid var(--borda);
  border-radius: 6px;
  font-size: 0.71rem;
  color: var(--texto);
}}

/* ---------- tutorial ---------- */

.tutorial-cartao {{
  background: var(--superficie);
  border: 1px solid var(--borda);
  border-radius: 18px;
  padding: 2.1rem 2.2rem 1.6rem 2.2rem;
  margin-bottom: 1.2rem;
  backdrop-filter: blur(12px);
  animation: entrar 0.32s ease-out;
}}

@keyframes entrar {{
  from {{ opacity: 0; transform: translateY(10px); }}
  to   {{ opacity: 1; transform: translateY(0); }}
}}

.tutorial-selo {{
  display: inline-block;
  padding: 0.22rem 0.7rem;
  border: 1px solid var(--borda);
  border-radius: 999px;
  font-size: 0.7rem;
  letter-spacing: 0.13em;
  text-transform: uppercase;
  color: var(--ambar);
  margin-bottom: 1rem;
}}

.tutorial-titulo {{
  font-size: 1.65rem;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.02em;
  color: var(--texto);
  margin: 0 0 0.85rem 0;
}}

.tutorial-texto {{
  color: var(--texto-suave);
  font-size: 1rem;
  line-height: 1.7;
  margin-bottom: 1.2rem;
}}

.tutorial-lista {{
  list-style: none;
  padding: 0;
  margin: 0 0 1.1rem 0;
}}

.tutorial-lista li {{
  position: relative;
  padding-left: 1.5rem;
  margin-bottom: 0.62rem;
  color: var(--texto);
  line-height: 1.6;
  font-size: 0.95rem;
}}

/* Marcador em forma de seta, no lugar do ponto padrao. */
.tutorial-lista li::before {{
  content: "";
  position: absolute;
  left: 0;
  top: 0.55rem;
  width: 8px;
  height: 8px;
  border-right: 2px solid var(--ambar);
  border-bottom: 2px solid var(--ambar);
  transform: rotate(-45deg);
}}

.tutorial-exemplos {{ margin-bottom: 1.1rem; }}

.tutorial-exemplo {{
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid var(--borda);
  border-left: 2px solid var(--lanterna);
  border-radius: 9px;
  padding: 0.6rem 0.85rem;
  margin-bottom: 0.5rem;
  color: var(--texto);
  font-size: 0.93rem;
}}

.tutorial-exemplo::before {{ content: "“"; color: var(--texto-suave); }}
.tutorial-exemplo::after  {{ content: "”"; color: var(--texto-suave); }}

.tutorial-aviso {{
  background: rgba(255, 176, 32, 0.07);
  border: 1px solid rgba(255, 176, 32, 0.22);
  border-radius: 10px;
  padding: 0.75rem 0.95rem;
  color: var(--texto);
  font-size: 0.89rem;
  line-height: 1.6;
}}

.marcadores {{
  display: flex;
  gap: 0.42rem;
  justify-content: center;
  margin-top: 1.7rem;
}}

.marcadores .ponto {{
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.16);
  transition: all 0.24s ease;
}}

.marcadores .ponto.ativo {{
  width: 26px;
  border-radius: 999px;
  background: var(--gradiente);
}}

/* Botao primario: o avancar do tutorial. */
.stButton > button[kind="primary"] {{
  background: var(--gradiente);
  border: none;
  color: #17110A;
  font-weight: 650;
  text-align: center;
}}

.stButton > button[kind="primary"]:hover {{
  filter: brightness(1.08);
  color: #17110A;
  transform: translateY(-1px);
}}

.stButton > button:disabled {{
  opacity: 0.32;
  cursor: not-allowed;
}}

#MainMenu, footer {{ visibility: hidden; }}

/* Em telas estreitas a malha some: em celular ela vira ruido. */
@media (max-width: 640px) {{
  .stApp::before {{ background-size: auto; }}
  .titulo-agente {{ font-size: 2rem; }}
}}
</style>
"""


def cabecalho(titulo: str, subtitulo: str, selo: str) -> str:
    """Bloco de abertura da pagina."""
    return f"""
    <div class="faixa-marca"><span class="farol"></span>{selo}</div>
    <h1 class="titulo-agente">{titulo}</h1>
    <p class="subtitulo-agente">{subtitulo}</p>
    <div class="faixa-pista"></div>
    """


def rodape(fontes: list[str]) -> str:
    """Creditos das fontes de dados, ao pe da pagina."""
    selos = "".join(f'<span class="selo">{fonte}</span>' for fonte in fontes)
    return f"""
    <div class="rodape-fontes">
      {selos}<br/>
      As contas de viagem são feitas em Python, com dados oficiais.
      O modelo de linguagem interpreta a pergunta e redige a resposta,
      mas não produz números por conta própria.
    </div>
    """
