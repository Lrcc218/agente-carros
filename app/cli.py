"""Interface de linha de comando.

Existe para provar que a interface e substituivel: o mesmo agente responde
aqui sem nenhuma alteracao nas outras camadas. Tambem e util para testar o
agente sem subir o Streamlit.

Uso:
    python app/cli.py
    python app/cli.py "quanto gasto de Sao Paulo ao Rio com o Corolla?"
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from agente_carros.agente import responder  # noqa: E402
from agente_carros.fabrica import criar_agente  # noqa: E402


def main() -> None:
    montagem = criar_agente()
    if montagem.aviso:
        print(f"Aviso: {montagem.aviso}\n")

    if len(sys.argv) > 1:
        pergunta = " ".join(sys.argv[1:])
        print(responder(montagem.executor, pergunta))
        return

    print("Consultor de carros. Digite sua pergunta ou 'sair' para encerrar.\n")
    historico: list[tuple[str, str]] = []
    while True:
        try:
            pergunta = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if pergunta.lower() in {"sair", "exit", "quit"}:
            return
        if not pergunta:
            continue

        resposta = responder(montagem.executor, pergunta, historico)
        print(f"\n{resposta}\n")
        historico += [("human", pergunta), ("ai", resposta)]


if __name__ == "__main__":
    main()
