"""Coleta os precos medios da Tabela FIPE para os modelos do catalogo.

Este script roda em tempo de construcao, nao em tempo de execucao. Ele
consulta a API publica e grava um dataset versionado em
`dados/processados/precos_fipe.csv`, com a data da coleta registrada.

A aplicacao nunca chama a API durante a conversa com o usuario: isso
evita latencia, limite de requisicoes e dependencia externa no caminho
critico, alem de tornar os numeros do README reproduziveis.

Uso:
    python scripts/coletar_fipe.py
    python scripts/coletar_fipe.py --semente dados/catalogo_semente.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from agente_carros.config import carregar_configuracao  # noqa: E402

URL_BASE = "https://fipe.parallelum.com.br/api/v2/cars"
PAUSA_ENTRE_CHAMADAS = 0.35
TEMPO_LIMITE = 30

# A API publica limita requisicoes diarias. Estes tetos mantem a coleta
# completa dentro da cota gratuita.
LIMITE_CANDIDATOS = 4
LIMITE_CONSULTAS_PRECO = 3


def normalizar(texto: str) -> str:
    """Remove acentos e caixa para comparar nomes vindos de fontes diferentes."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.upper().strip()


def obter(caminho: str) -> list[dict]:
    resposta = requests.get(f"{URL_BASE}{caminho}", timeout=TEMPO_LIMITE)
    resposta.raise_for_status()
    time.sleep(PAUSA_ENTRE_CHAMADAS)
    dados = resposta.json()
    return dados if isinstance(dados, list) else [dados]


def obter_um(caminho: str) -> dict:
    resposta = requests.get(f"{URL_BASE}{caminho}", timeout=TEMPO_LIMITE)
    resposta.raise_for_status()
    time.sleep(PAUSA_ENTRE_CHAMADAS)
    return resposta.json()


def achar_marca(marcas: list[dict], nome: str) -> dict | None:
    alvo = normalizar(nome)
    for marca in marcas:
        if normalizar(marca["name"]) == alvo:
            return marca
    for marca in marcas:
        if alvo in normalizar(marca["name"]):
            return marca
    return None


def achar_modelos(modelos: list[dict], termo: str) -> list[dict]:
    alvo = normalizar(termo)
    return [m for m in modelos if alvo in normalizar(m["name"])]


def achar_ano(anos: list[dict], ano_desejado: int) -> dict | None:
    """Devolve o ano pedido, ou None se o modelo nao for ofertado nesse ano.

    Nao ha fallback proposital: a FIPE lista versoes homonimas de decadas
    diferentes, e aceitar qualquer ano faz um Polo 1997 se passar pelo
    Polo atual. E preferivel falhar e ajustar a semente.
    """
    for ano in anos:
        if str(ano_desejado) in ano["name"]:
            return ano
    return None


def escolher_versao(
    codigo_marca: str,
    candidatos: list[dict],
    ano_desejado: int,
    limite_candidatos: int = LIMITE_CANDIDATOS,
) -> dict | None:
    """Escolhe a versao de entrada do modelo no ano desejado.

    Percorre os candidatos que o termo de busca retornou, mantem apenas os
    que sao ofertados no ano desejado e devolve o de menor preco, que e a
    versao de entrada. Os limites existem para nao estourar a cota diaria
    de requisicoes da API publica.
    """
    qualificados: list[tuple[dict, dict]] = []
    for modelo in sorted(candidatos, key=lambda m: len(m["name"]))[:limite_candidatos]:
        anos = obter(f"/brands/{codigo_marca}/models/{modelo['code']}/years")
        ano = achar_ano(anos, ano_desejado)
        if ano is not None:
            qualificados.append((modelo, ano))

    detalhes: list[dict] = []
    for modelo, ano in qualificados[:LIMITE_CONSULTAS_PRECO]:
        detalhes.append(
            obter_um(f"/brands/{codigo_marca}/models/{modelo['code']}/years/{ano['code']}")
        )

    validos = [d for d in detalhes if converter_preco(str(d.get("price", ""))) is not None]
    if not validos:
        return None
    return min(validos, key=lambda d: converter_preco(str(d["price"])) or float("inf"))


def converter_preco(texto: str) -> float | None:
    """Converte 'R$ 85.432,00' para 85432.0."""
    limpo = texto.replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(limpo)
    except ValueError:
        return None


def ler_existentes(destino: Path) -> list[dict]:
    if not destino.exists():
        return []
    with destino.open(encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def coletar(
    semente: Path,
    destino: Path,
    somente: set[str] | None = None,
    limite_candidatos: int = LIMITE_CANDIDATOS,
) -> None:
    with semente.open(encoding="utf-8") as arquivo:
        itens = list(csv.DictReader(arquivo))

    # Coleta incremental: reprocessar apenas alguns ids preserva os demais
    # ja coletados e economiza a cota diaria da API.
    preservados: list[dict] = []
    if somente:
        preservados = [linha for linha in ler_existentes(destino) if linha["id"] not in somente]
        itens = [item for item in itens if item["id"] in somente]

    print(f"Consultando a Tabela FIPE para {len(itens)} modelos...")
    marcas = obter("/brands")
    coletado_em = date.today().isoformat()
    linhas: list[dict] = []
    falhas: list[str] = []

    for item in itens:
        rotulo = f"{item['marca']} {item['termo_modelo']}"
        try:
            marca = achar_marca(marcas, item["marca"])
            if marca is None:
                falhas.append(f"{rotulo}: marca nao encontrada na FIPE")
                continue

            modelos = obter(f"/brands/{marca['code']}/models")
            candidatos = achar_modelos(modelos, item["termo_modelo"])
            if not candidatos:
                falhas.append(f"{rotulo}: nenhum modelo corresponde ao termo")
                continue

            ano_desejado = int(item["ano_desejado"])
            detalhe = escolher_versao(
                marca["code"], candidatos, ano_desejado, limite_candidatos
            )
            if detalhe is None:
                falhas.append(f"{rotulo}: nenhuma versao ofertada em {ano_desejado}")
                continue

            linhas.append(
                {
                    "id": item["id"],
                    "marca_fipe": detalhe.get("brand", ""),
                    "modelo_fipe": detalhe.get("model", ""),
                    "ano_fipe": detalhe.get("modelYear", ""),
                    "combustivel_fipe": detalhe.get("fuel", ""),
                    "codigo_fipe": detalhe.get("codeFipe", ""),
                    "preco_fipe": converter_preco(str(detalhe.get("price", ""))),
                    "mes_referencia": str(detalhe.get("referenceMonth", "")).strip(),
                    "coletado_em": coletado_em,
                }
            )
            print(f"  ok  {item['id']:<22} {detalhe.get('price', '')}")

        except requests.RequestException as erro:
            falhas.append(f"{rotulo}: erro de rede ({erro})")
        except (KeyError, ValueError) as erro:
            falhas.append(f"{rotulo}: resposta inesperada ({erro})")

    destino.parent.mkdir(parents=True, exist_ok=True)
    campos = [
        "id",
        "marca_fipe",
        "modelo_fipe",
        "ano_fipe",
        "combustivel_fipe",
        "codigo_fipe",
        "preco_fipe",
        "mes_referencia",
        "coletado_em",
    ]
    todas = sorted(preservados + linhas, key=lambda linha: linha["id"])
    with destino.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(todas)

    print(f"\n{len(todas)} precos gravados em {destino.relative_to(RAIZ)}")
    if falhas:
        print(f"\n{len(falhas)} modelos nao coletados:")
        for falha in falhas:
            print(f"  - {falha}")


def main() -> None:
    config = carregar_configuracao()
    analisador = argparse.ArgumentParser(description="Coleta precos da Tabela FIPE")
    analisador.add_argument(
        "--semente",
        type=Path,
        default=config.caminhos.dados / "catalogo_semente.csv",
        help="CSV com os modelos a consultar",
    )
    analisador.add_argument(
        "--destino",
        type=Path,
        default=config.caminhos.precos_fipe,
        help="CSV de saida com os precos coletados",
    )
    analisador.add_argument(
        "--somente",
        default=None,
        help="Lista de ids separados por virgula para reprocessar, preservando os demais",
    )
    analisador.add_argument(
        "--limite-candidatos",
        type=int,
        default=LIMITE_CANDIDATOS,
        help="Quantas versoes homonimas inspecionar por modelo",
    )
    argumentos = analisador.parse_args()
    somente = (
        {parte.strip() for parte in argumentos.somente.split(",") if parte.strip()}
        if argumentos.somente
        else None
    )
    coletar(argumentos.semente, argumentos.destino, somente, argumentos.limite_candidatos)


if __name__ == "__main__":
    main()
