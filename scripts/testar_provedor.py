"""Teste rapido e isolado do provedor de IA configurado.

Serve para separar problema de credencial de problema do agente. Se este
script passa e o agente falha, a causa esta no agente; se este falha, a
causa esta na chave ou na conta.

Uso:
    python scripts/testar_provedor.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from agente_carros.config import carregar_configuracao  # noqa: E402
from agente_carros.fabrica import criar_provedor  # noqa: E402


def main() -> None:
    config = carregar_configuracao()
    print(f"Provedor:  {config.provedor_llm}")
    print(f"Chat:      {config.modelo_chat}")
    print(f"Embedding: {config.modelo_embedding}")

    try:
        config.validar()
    except ValueError as erro:
        raise SystemExit(f"\n{erro}") from erro

    provedor = criar_provedor(config)

    print("\n1. Chamada de chat...")
    try:
        resposta = provedor.modelo_chat().invoke(
            "Em uma palavra, qual a capital do Brasil?"
        )
        print(f"   resposta: {getattr(resposta, 'content', resposta)!r}")
    except Exception as erro:  # noqa: BLE001
        raise SystemExit(f"   FALHOU: {type(erro).__name__}: {erro}") from erro

    print("\n2. Chamada de embedding...")
    try:
        vetor = provedor.modelo_embedding().embed_query("consumo de combustivel")
        print(f"   vetor de {len(vetor)} dimensoes")
    except Exception as erro:  # noqa: BLE001
        raise SystemExit(f"   FALHOU: {type(erro).__name__}: {erro}") from erro

    print("\n3. Chamada com ferramenta (tool calling)...")
    try:
        from langchain_core.tools import tool

        @tool
        def somar(a: int, b: int) -> int:
            """Soma dois numeros inteiros."""
            return a + b

        modelo = provedor.modelo_chat().bind_tools([somar])
        resposta = modelo.invoke("Quanto e 17 mais 25? Use a ferramenta.")
        chamadas = getattr(resposta, "tool_calls", [])
        if chamadas:
            print(f"   o modelo pediu para chamar: {chamadas[0]['name']}({chamadas[0]['args']})")
        else:
            print("   AVISO: o modelo nao usou a ferramenta. O agente pode responder mal.")
    except Exception as erro:  # noqa: BLE001
        raise SystemExit(f"   FALHOU: {type(erro).__name__}: {erro}") from erro

    print("\nProvedor funcionando. Proximo passo: python scripts/indexar_documentos.py")


if __name__ == "__main__":
    main()
