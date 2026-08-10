"""Constroi o indice vetorial dos documentos oficiais.

Roda em tempo de construcao e grava o indice em
`dados/processados/indice_faiss`, que e versionado no repositorio.

Gerar embeddings consome creditos da API. Fazer isso uma vez, aqui, e
versionar o resultado evita reprocessar os documentos a cada inicializacao
da aplicacao — o que esgotaria a cota gratuita em poucas reinicializacoes.

Uso:
    python scripts/indexar_documentos.py
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from agente_carros.config import carregar_configuracao  # noqa: E402

TAMANHO_TRECHO = 1200
SOBREPOSICAO = 150


def carregar_titulos(pasta: Path) -> dict[str, str]:
    """Le o manifesto para associar cada arquivo ao titulo do documento."""
    manifesto = pasta / "MANIFESTO.md"
    if not manifesto.exists():
        return {}

    titulos: dict[str, str] = {}
    titulo_atual = ""
    for linha in manifesto.read_text(encoding="utf-8").splitlines():
        if linha.startswith("## "):
            titulo_atual = linha[3:].strip()
        elif linha.startswith("- Arquivo: `"):
            nome = linha.split("`")[1]
            titulos[nome] = titulo_atual
    return titulos


def indexar(pasta_documentos: Path, destino: Path) -> None:
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_community.vectorstores import FAISS
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    from agente_carros.adaptadores.llm_nvidia import ProvedorNVIDIA

    config = carregar_configuracao()
    pdfs = sorted(pasta_documentos.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(
            f"Nenhum PDF em {pasta_documentos}. "
            "Rode antes: python scripts/baixar_documentos.py"
        )

    titulos = carregar_titulos(pasta_documentos)
    paginas = []
    for pdf in pdfs:
        carregadas = PyPDFLoader(str(pdf)).load()
        for pagina in carregadas:
            pagina.metadata["titulo"] = titulos.get(pdf.name, pdf.stem)
            pagina.metadata["arquivo"] = pdf.name
        paginas.extend(carregadas)
        print(f"  lido  {pdf.name} ({len(carregadas)} paginas)")

    divisor = RecursiveCharacterTextSplitter(
        chunk_size=TAMANHO_TRECHO, chunk_overlap=SOBREPOSICAO
    )
    trechos = divisor.split_documents(paginas)
    print(f"\n{len(trechos)} trechos gerados. Calculando embeddings...")

    provedor = ProvedorNVIDIA(config)
    indice = FAISS.from_documents(trechos, provedor.modelo_embedding())

    if destino.exists():
        shutil.rmtree(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    indice.save_local(str(destino))

    (destino / "metadados.json").write_text(
        json.dumps(
            {
                "gerado_em": date.today().isoformat(),
                "modelo_embedding": config.modelo_embedding,
                "documentos": [pdf.name for pdf in pdfs],
                "trechos": len(trechos),
                "tamanho_trecho": TAMANHO_TRECHO,
                "sobreposicao": SOBREPOSICAO,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Indice gravado em {destino.relative_to(RAIZ)}")


def main() -> None:
    config = carregar_configuracao()
    analisador = argparse.ArgumentParser(description="Indexa os documentos oficiais")
    analisador.add_argument("--documentos", type=Path, default=config.caminhos.documentos)
    analisador.add_argument("--destino", type=Path, default=config.caminhos.indice_vetorial)
    argumentos = analisador.parse_args()
    indexar(argumentos.documentos, argumentos.destino)


if __name__ == "__main__":
    main()
