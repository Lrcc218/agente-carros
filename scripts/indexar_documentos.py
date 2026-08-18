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
import csv
import json
import shutil
import sys
import time
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from agente_carros.config import carregar_configuracao  # noqa: E402

TAMANHO_TRECHO = 1200
SOBREPOSICAO = 150

# A camada gratuita das APIs de embedding limita requisicoes por minuto.
# Enviar centenas de trechos de uma vez estoura o limite e devolve 429, entao
# a indexacao vai em lotes pequenos, com pausa entre eles e reenvio com espera
# crescente quando o limite e atingido.
TAMANHO_LOTE = 16
PAUSA_ENTRE_LOTES = 1.5
TENTATIVAS = 5
ESPERA_INICIAL = 20


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


def carregar_titulos_de_manuais(catalogo_manuais: Path) -> dict[str, str]:
    """Le os titulos dos manuais adicionados a mao.

    Manuais de montadora nao podem ser baixados por script — os sites
    bloqueiam acesso automatizado. Quem quiser inclui-los baixa o PDF pelo
    navegador, coloca na pasta de manuais e declara o titulo aqui. Sem
    declaracao, o nome do arquivo vira o titulo.
    """
    if not catalogo_manuais.exists():
        return {}

    titulos: dict[str, str] = {}
    with catalogo_manuais.open(encoding="utf-8") as arquivo:
        for linha in csv.DictReader(arquivo):
            nome = (linha.get("arquivo") or "").strip()
            if not nome:
                continue
            partes = [
                (linha.get("marca") or "").strip(),
                (linha.get("modelo") or "").strip(),
                (linha.get("documento") or "Manual do proprietario").strip(),
            ]
            titulos[nome] = " ".join(parte for parte in partes if parte)
    return titulos


def nome_legivel(arquivo: Path) -> str:
    """Titulo de emergencia, derivado do nome do arquivo."""
    return arquivo.stem.replace("_", " ").replace("-", " ").strip()


def indexar_em_lotes(trechos: list, embeddings, FAISS) -> object:
    """Gera os embeddings aos poucos, respeitando o limite de requisicoes.

    Devolve o indice FAISS montado. O primeiro lote cria o indice e os
    seguintes sao anexados, o que tambem mantem o uso de memoria estavel em
    documentos grandes.
    """
    indice = None
    total = len(trechos)

    for inicio in range(0, total, TAMANHO_LOTE):
        lote = trechos[inicio : inicio + TAMANHO_LOTE]
        espera = ESPERA_INICIAL

        for tentativa in range(1, TENTATIVAS + 1):
            try:
                if indice is None:
                    indice = FAISS.from_documents(lote, embeddings)
                else:
                    indice.add_documents(lote)
                break
            except Exception as erro:  # noqa: BLE001 - o provedor sinaliza limite de varias formas
                limite_atingido = "429" in str(erro) or "quota" in str(erro).lower()
                if not limite_atingido or tentativa == TENTATIVAS:
                    raise
                print(
                    f"    limite de requisicoes atingido; "
                    f"aguardando {espera}s (tentativa {tentativa}/{TENTATIVAS})"
                )
                time.sleep(espera)
                espera *= 2

        processados = min(inicio + TAMANHO_LOTE, total)
        print(f"  embeddings: {processados}/{total} trechos", flush=True)
        if processados < total:
            time.sleep(PAUSA_ENTRE_LOTES)

    if indice is None:
        raise SystemExit("Nenhum trecho para indexar.")
    return indice


def indexar(pasta_documentos: Path, destino: Path) -> None:
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_community.vectorstores import FAISS
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    from agente_carros.fabrica import criar_provedor

    config = carregar_configuracao()
    # rglob para alcancar tambem a subpasta de manuais adicionados a mao.
    pdfs = sorted(pasta_documentos.rglob("*.pdf"))
    if not pdfs:
        raise SystemExit(
            f"Nenhum PDF em {pasta_documentos}. "
            "Rode antes: python scripts/baixar_documentos.py"
        )

    titulos = carregar_titulos(pasta_documentos)
    titulos |= carregar_titulos_de_manuais(config.caminhos.dados / "manuais.csv")

    paginas = []
    for pdf in pdfs:
        try:
            carregadas = PyPDFLoader(str(pdf)).load()
        except Exception as erro:  # noqa: BLE001 - um PDF ruim nao pode parar a indexacao
            print(f"  IGNORADO  {pdf.name}: nao foi possivel ler ({erro})")
            continue

        eh_manual = pdf.parent.name == "manuais"
        for pagina in carregadas:
            pagina.metadata["titulo"] = titulos.get(pdf.name, nome_legivel(pdf))
            pagina.metadata["arquivo"] = pdf.name
            pagina.metadata["tipo"] = "manual" if eh_manual else "documento_oficial"
        paginas.extend(carregadas)
        rotulo = "manual" if eh_manual else "oficial"
        print(f"  lido  [{rotulo}] {pdf.name} ({len(carregadas)} paginas)")

    divisor = RecursiveCharacterTextSplitter(
        chunk_size=TAMANHO_TRECHO, chunk_overlap=SOBREPOSICAO
    )
    trechos = divisor.split_documents(paginas)
    print(f"\n{len(trechos)} trechos gerados. Calculando embeddings...")

    # Pela fabrica, e nao por um adaptador especifico: o script deve
    # indexar com o mesmo provedor que a aplicacao usa para consultar.
    provedor = criar_provedor(config)
    indice = indexar_em_lotes(trechos, provedor.modelo_embedding(), FAISS)

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
