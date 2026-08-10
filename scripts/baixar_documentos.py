"""Baixa os documentos oficiais que alimentam a busca semantica do agente.

Roda em tempo de construcao. Os arquivos vao para `dados/brutos/documentos/`,
que fica fora do controle de versao: sao documentos publicos e grandes, e
este script os reproduz a qualquer momento.

Uso:
    python scripts/baixar_documentos.py
    python scripts/baixar_documentos.py --forcar
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from agente_carros.config import carregar_configuracao  # noqa: E402

TEMPO_LIMITE = 300
CABECALHOS = {"User-Agent": "Mozilla/5.0 (compativel; agente-carros/0.1)"}

BASE_INMETRO = (
    "https://www.gov.br/inmetro/pt-br/assuntos/regulamentacao/avaliacao-da-conformidade"
    "/programa-brasileiro-de-etiquetagem/tabelas-de-eficiencia-energetica"
    "/veiculos-automotivos-pbe-veicular"
)


@dataclass(frozen=True)
class Documento:
    """Um documento oficial a ser baixado e indexado."""

    nome_arquivo: str
    url: str
    titulo: str
    orgao: str


DOCUMENTOS: list[Documento] = [
    Documento(
        nome_arquivo="pbev_2026_tabela_consumo.pdf",
        url=f"{BASE_INMETRO}/mascara-pbev-2026_19_jan-rev01.pdf/@@download/file",
        titulo="Tabela PBE Veicular 2026 - consumo e eficiencia energetica de veiculos leves",
        orgao="Inmetro / Conpet",
    ),
    Documento(
        nome_arquivo="pbev_metodologia_consumo.pdf",
        url=f"{BASE_INMETRO}/metodologia-para-divulgacao-de-dados-de-consumo-veicular/@@download/file",
        titulo="Metodologia para divulgacao de dados de consumo veicular",
        orgao="Inmetro",
    ),
    Documento(
        nome_arquivo="pbev_2025_tabela_consumo.pdf",
        url=f"{BASE_INMETRO}/mascara-pbev-2025-mar-11.pdf/@@download/file",
        titulo="Tabela PBE Veicular 2025 - consumo e eficiencia energetica de veiculos leves",
        orgao="Inmetro / Conpet",
    ),
]


def baixar(documento: Documento, destino: Path, forcar: bool) -> bool:
    arquivo = destino / documento.nome_arquivo
    if arquivo.exists() and not forcar:
        print(f"  ja existe  {documento.nome_arquivo}")
        return True

    try:
        resposta = requests.get(
            documento.url, timeout=TEMPO_LIMITE, headers=CABECALHOS, allow_redirects=True
        )
        resposta.raise_for_status()
    except requests.RequestException as erro:
        print(f"  FALHOU     {documento.nome_arquivo}: {erro}")
        return False

    if not resposta.content.startswith(b"%PDF"):
        print(f"  FALHOU     {documento.nome_arquivo}: resposta nao e um PDF")
        return False

    arquivo.write_bytes(resposta.content)
    print(f"  baixado    {documento.nome_arquivo} ({len(resposta.content) // 1024} KB)")
    return True


def escrever_manifesto(destino: Path) -> None:
    """Registra titulo e orgao de cada documento, usados na citacao de fontes."""
    linhas = ["# Documentos oficiais indexados", ""]
    for documento in DOCUMENTOS:
        linhas += [
            f"## {documento.titulo}",
            "",
            f"- Arquivo: `{documento.nome_arquivo}`",
            f"- Orgao: {documento.orgao}",
            f"- Origem: {documento.url}",
            "",
        ]
    (destino / "MANIFESTO.md").write_text("\n".join(linhas), encoding="utf-8")


def main() -> None:
    config = carregar_configuracao()
    analisador = argparse.ArgumentParser(description="Baixa os documentos oficiais")
    analisador.add_argument(
        "--forcar", action="store_true", help="Rebaixa arquivos que ja existem"
    )
    argumentos = analisador.parse_args()

    destino = config.caminhos.documentos
    destino.mkdir(parents=True, exist_ok=True)
    # Manuais de montadora entram a mao aqui; ver docs/MANUAIS.md.
    (destino / "manuais").mkdir(exist_ok=True)

    print(f"Baixando {len(DOCUMENTOS)} documentos para {destino.relative_to(RAIZ)}/")
    sucessos = sum(baixar(documento, destino, argumentos.forcar) for documento in DOCUMENTOS)
    escrever_manifesto(destino)

    print(f"\n{sucessos}/{len(DOCUMENTOS)} documentos disponiveis")
    if sucessos < len(DOCUMENTOS):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
