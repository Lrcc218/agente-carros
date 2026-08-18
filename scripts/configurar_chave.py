"""Grava a chave de API no arquivo .env a partir de um arquivo externo.

Evita dois erros comuns: digitar a chave no terminal, onde ela fica no
historico do shell, e edita-la a mao no .env, onde um espaco invisivel
gera um 403 dificil de diagnosticar.

O provedor e deduzido do prefixo da chave, entao nao ha como configurar o
Gemini apontando para a NVIDIA por engano.

Uso:
    python scripts/configurar_chave.py /home/luan/geminikey
    python scripts/configurar_chave.py /home/luan/nvidiakey --provedor nvidia
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from agente_carros.config import VARIAVEIS_DE_CHAVE  # noqa: E402

# Prefixos conhecidos, para deduzir o provedor sem o usuario informar.
# O Google trocou o formato das chaves do AI Studio: as antigas comecam
# com AIza, as novas com AQ. Ambas continuam validas.
PREFIXOS = {
    "nvapi-": "nvidia",
    "AIza": "gemini",
    "AQ.": "gemini",
}

MARCADORES = ("COLE_A_CHAVE_AQUI", "COLE_O_TOKEN_AQUI", "cole", "sua-chave")


def ler_chave(arquivo: Path) -> str:
    """Le a primeira linha util do arquivo, ignorando comentarios e vazios."""
    if not arquivo.exists():
        raise SystemExit(f"Arquivo nao encontrado: {arquivo}")

    for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
        limpa = linha.strip()
        if not limpa or limpa.startswith("#"):
            continue
        return limpa

    raise SystemExit(f"Nenhuma chave encontrada em {arquivo}. O arquivo so tem comentarios.")


def deduzir_provedor(chave: str) -> str | None:
    for prefixo, provedor in PREFIXOS.items():
        if chave.startswith(prefixo):
            return provedor
    return None


def validar(chave: str, arquivo: Path) -> None:
    if any(marcador in chave for marcador in MARCADORES):
        raise SystemExit(
            f"A linha da chave em {arquivo} ainda tem o texto de exemplo. "
            "Substitua pela chave real."
        )
    if len(chave) < 20:
        raise SystemExit(f"A chave lida tem apenas {len(chave)} caracteres. Parece incompleta.")
    if " " in chave:
        raise SystemExit("A chave contem espaco. Cole apenas o valor, sem aspas nem espacos.")


def gravar_env(env: Path, valores: dict[str, str]) -> None:
    """Atualiza as variaveis no .env preservando o resto do arquivo."""
    linhas = env.read_text(encoding="utf-8").splitlines() if env.exists() else []

    for nome, valor in valores.items():
        padrao = re.compile(rf"^\s*#?\s*{re.escape(nome)}\s*=")
        substituida = False
        for indice, linha in enumerate(linhas):
            if padrao.match(linha):
                linhas[indice] = f"{nome}={valor}"
                substituida = True
                break
        if not substituida:
            linhas.append(f"{nome}={valor}")

    env.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    env.chmod(0o600)


def main() -> None:
    analisador = argparse.ArgumentParser(description="Configura a chave de API no .env")
    analisador.add_argument("arquivo", type=Path, help="Arquivo que contem a chave")
    analisador.add_argument(
        "--provedor",
        choices=sorted(VARIAVEIS_DE_CHAVE),
        default=None,
        help="Forca o provedor, quando o prefixo da chave nao for reconhecido",
    )
    analisador.add_argument(
        "--env", type=Path, default=RAIZ / ".env", help="Arquivo .env de destino"
    )
    argumentos = analisador.parse_args()

    chave = ler_chave(argumentos.arquivo)
    validar(chave, argumentos.arquivo)

    provedor = argumentos.provedor or deduzir_provedor(chave)
    if provedor is None:
        raise SystemExit(
            "Nao reconheci o provedor pelo prefixo da chave. "
            "Informe com --provedor gemini ou --provedor nvidia."
        )

    variavel = VARIAVEIS_DE_CHAVE[provedor][0]
    gravar_env(argumentos.env, {"PROVEDOR_LLM": provedor, variavel: chave})

    # Nunca imprime a chave inteira.
    print(f"Provedor configurado: {provedor}")
    print(f"Variavel gravada:     {variavel}={chave[:6]}...{chave[-4:]}")
    print(f"Arquivo:              {argumentos.env.relative_to(RAIZ)} (permissao 600)")
    print("\nProximo passo: python scripts/diagnosticar.py")


if __name__ == "__main__":
    main()
