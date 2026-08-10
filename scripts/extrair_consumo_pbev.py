"""Extrai o consumo oficial dos modelos do catalogo a partir das tabelas do Inmetro.

O Inmetro publica o PBE Veicular apenas em PDF. Este script le o PDF, localiza
a linha de cada modelo do catalogo pelo padrao definido em `dados/mapa_pbev.csv`
e grava os valores em `dados/processados/consumo_pbev.csv`.

Cada linha do resultado guarda tambem o texto original extraido do PDF, para
que qualquer numero possa ser conferido contra a fonte sem reabrir o documento.

Estrutura das colunas numericas na tabela do Inmetro, sempre nessa ordem e
sempre no fim da linha, usando `\\` para celula vazia:

    3 colunas de CO2
    4 colunas de consumo   -> etanol cidade, etanol estrada, principal cidade,
                              principal estrada   (principal = gasolina ou diesel)
    2 colunas em km/l e    -> apenas veiculos eletricos
    1 razao de eficiencia
    1 autonomia eletrica
    2 classificacoes       -> comparacao relativa e absoluta

Uso:
    python scripts/extrair_consumo_pbev.py
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from agente_carros.config import carregar_configuracao  # noqa: E402

VAZIO = "\\"
FIM_DE_LINHA = ("-", "SIM")
ARQUIVOS = {
    "2026": "pbev_2026_tabela_consumo.pdf",
    "2025": "pbev_2025_tabela_consumo.pdf",
}


def ler_linhas(caminho: Path) -> list[str]:
    """Le o PDF e devolve uma linha logica por veiculo.

    A extracao de texto quebra registros longos em varias linhas fisicas.
    Como toda linha completa termina no marcador de fim de registro, basta
    concatenar as seguintes ate encontrar esse marcador.
    """
    leitor = PdfReader(caminho)
    bruto = "\n".join((pagina.extract_text() or "") for pagina in leitor.pages)

    linhas: list[str] = []
    for linha in (texto.strip() for texto in bruto.split("\n")):
        if not linha:
            continue
        if linhas and not linhas[-1].rstrip().endswith(FIM_DE_LINHA):
            linhas[-1] = f"{linhas[-1]} {linha}"
        else:
            linhas.append(linha)
    return linhas


def numero(token: str) -> float | None:
    if token == VAZIO:
        return None
    try:
        return float(token)
    except ValueError:
        return None


def inteiro(token: str) -> int | None:
    valor = numero(token)
    return int(valor) if valor is not None else None


def interpretar(linha: str) -> dict | None:
    """Le os valores da cauda numerica da linha, contando de tras para frente."""
    tokens = linha.split()
    if tokens and tokens[-1] in FIM_DE_LINHA:
        tokens = tokens[:-1]
    if len(tokens) < 12:
        return None

    classe_absoluta = tokens[-1]
    classe_relativa = tokens[-2]
    autonomia = tokens[-3]
    razao = tokens[-4]
    eletrico_estrada = tokens[-5]
    eletrico_cidade = tokens[-6]
    principal_estrada = tokens[-7]
    principal_cidade = tokens[-8]
    etanol_estrada = tokens[-9]
    etanol_cidade = tokens[-10]

    if numero(razao) is None:
        return None

    return {
        "etanol_cidade": numero(etanol_cidade),
        "etanol_estrada": numero(etanol_estrada),
        "principal_cidade": numero(principal_cidade),
        "principal_estrada": numero(principal_estrada),
        "eletrico_cidade_kmle": numero(eletrico_cidade),
        "eletrico_estrada_kmle": numero(eletrico_estrada),
        "razao_eficiencia": numero(razao),
        "autonomia_eletrica_km": inteiro(autonomia),
        "classe_relativa": classe_relativa if classe_relativa.isalpha() else "",
        "classe_absoluta": classe_absoluta if classe_absoluta.isalpha() else "",
    }


def descrever_versao(linha: str) -> str:
    """Extrai o nome do veiculo, entre a categoria e o tipo de motorizacao."""
    corte = re.split(r"\s(?:Combustão|Elétrico|Híbrido|Plug-in)\s", linha)[0]
    return re.sub(r"\s+", " ", corte).strip()


def extrair(mapa: Path, pasta_documentos: Path, destino: Path) -> None:
    with mapa.open(encoding="utf-8") as arquivo:
        entradas = list(csv.DictReader(arquivo))

    cache: dict[str, list[str]] = {}
    resultados: list[dict] = []
    falhas: list[str] = []

    for entrada in entradas:
        tabela = entrada["tabela"]
        if tabela not in cache:
            caminho = pasta_documentos / ARQUIVOS[tabela]
            if not caminho.exists():
                raise SystemExit(
                    f"{caminho} nao encontrado. Rode antes: python scripts/baixar_documentos.py"
                )
            cache[tabela] = ler_linhas(caminho)

        alvo = entrada["padrao"].upper()
        encontradas = [linha for linha in cache[tabela] if alvo in linha.upper()]
        if not encontradas:
            falhas.append(f"{entrada['id']}: padrao nao encontrado na tabela {tabela}")
            continue

        valores = interpretar(encontradas[0])
        if valores is None:
            falhas.append(f"{entrada['id']}: nao foi possivel interpretar a linha")
            continue

        resultados.append(
            {
                "id": entrada["id"],
                "tabela_pbev": tabela,
                "versao_pbev": descrever_versao(encontradas[0]),
                **valores,
                "linha_original": re.sub(r"\s+", " ", encontradas[0]),
            }
        )
        principal = valores["principal_cidade"] or valores["eletrico_cidade_kmle"]
        print(f"  ok  {entrada['id']:<22} cidade={principal}")

    destino.parent.mkdir(parents=True, exist_ok=True)
    campos = [
        "id",
        "tabela_pbev",
        "versao_pbev",
        "etanol_cidade",
        "etanol_estrada",
        "principal_cidade",
        "principal_estrada",
        "eletrico_cidade_kmle",
        "eletrico_estrada_kmle",
        "razao_eficiencia",
        "autonomia_eletrica_km",
        "classe_relativa",
        "classe_absoluta",
        "linha_original",
    ]
    with destino.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(sorted(resultados, key=lambda linha: linha["id"]))

    print(f"\n{len(resultados)} modelos extraidos para {destino.relative_to(RAIZ)}")
    if falhas:
        print(f"\n{len(falhas)} nao extraidos:")
        for falha in falhas:
            print(f"  - {falha}")


def main() -> None:
    config = carregar_configuracao()
    analisador = argparse.ArgumentParser(description="Extrai consumo do PBE Veicular")
    analisador.add_argument("--mapa", type=Path, default=config.caminhos.dados / "mapa_pbev.csv")
    analisador.add_argument("--documentos", type=Path, default=config.caminhos.documentos)
    analisador.add_argument(
        "--destino", type=Path, default=config.caminhos.processados / "consumo_pbev.csv"
    )
    argumentos = analisador.parse_args()
    extrair(argumentos.mapa, argumentos.documentos, argumentos.destino)


if __name__ == "__main__":
    main()
