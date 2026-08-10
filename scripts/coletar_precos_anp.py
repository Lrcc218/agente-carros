"""Coleta os precos de combustivel praticados no pais, publicados pela ANP.

A ANP divulga o levantamento semanal de precos em CSV aberto, posto a posto.
Este script baixa o arquivo mais recente de cada produto, agrega por estado e
grava `dados/processados/precos_combustivel_anp.csv`.

Com isso a simulacao de viagem deixa de usar preco arbitrado e passa a usar o
preco oficial praticado no estado de quem pergunta.

Os links sao descobertos na propria pagina da ANP, e nao montados por regra:
os nomes dos arquivos mudam de mes para mes e ha meses faltando na sequencia.

Uso:
    python scripts/coletar_precos_anp.py
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from agente_carros.config import carregar_configuracao  # noqa: E402

PAGINA_ANP = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos"
    "/serie-historica-de-precos-de-combustiveis"
)
CABECALHOS = {"User-Agent": "Mozilla/5.0 (compativel; agente-carros/0.1)"}
TEMPO_LIMITE = 300

# Produtos da ANP que interessam, e o nome usado no projeto. A gasolina
# aditivada fica de fora para nao puxar a media da gasolina comum para cima.
PRODUTOS = {
    "GASOLINA": "gasolina",
    "ETANOL": "etanol",
    "OLEO DIESEL": "diesel",
    "OLEO DIESEL S10": "diesel_s10",
    "DIESEL": "diesel",
    "DIESEL S10": "diesel_s10",
}

GRUPOS = {
    "gasolina-etanol": ("gasolina", "etanol"),
    "diesel-gnv": ("diesel", "diesel_s10"),
}


def descobrir_arquivos(pagina: str) -> dict[str, str]:
    """Devolve a URL mais recente de cada grupo de produtos.

    Os arquivos ficam sob `shpc/dsan/<ano>/` e o nome comeca com o numero do
    mes. Ordenar por (ano, mes) e pegar o ultimo dispensa saber o padrao exato
    do nome, que a ANP altera com frequencia.
    """
    resposta = requests.get(pagina, timeout=TEMPO_LIMITE, headers=CABECALHOS)
    resposta.raise_for_status()

    encontrados: dict[str, list[tuple[int, int, str]]] = {grupo: [] for grupo in GRUPOS}
    padrao = re.compile(r'https://[^"\']*?/shpc/dsan/(\d{4})/([^"\']*?\.csv)')

    for url_ano, nome in padrao.findall(resposta.text):
        url = f"https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsan/{url_ano}/{nome}"
        for grupo in GRUPOS:
            # 'gasolina-etanol' aparece com grafias variadas; casar pelo par
            # de produtos evita depender do prefixo do nome do arquivo.
            partes = grupo.split("-")
            if all(parte in nome.lower() for parte in partes):
                mes = int(nome[:2]) if nome[:2].isdigit() else 0
                encontrados[grupo].append((int(url_ano), mes, url))

    escolhidos: dict[str, str] = {}
    for grupo, itens in encontrados.items():
        if itens:
            escolhidos[grupo] = max(itens)[2]
    return escolhidos


def baixar_csv(url: str) -> pd.DataFrame:
    resposta = requests.get(url, timeout=TEMPO_LIMITE, headers=CABECALHOS)
    resposta.raise_for_status()
    return pd.read_csv(
        io.BytesIO(resposta.content),
        sep=";",
        encoding="utf-8-sig",
        dtype=str,
        low_memory=False,
    )


def normalizar(tabela: pd.DataFrame) -> pd.DataFrame:
    """Reduz o arquivo da ANP as colunas usadas, ja com tipos corretos."""
    colunas = {c.strip().lower(): c for c in tabela.columns}
    coluna_uf = colunas.get("estado - sigla")
    coluna_produto = colunas.get("produto")
    coluna_valor = colunas.get("valor de venda")
    coluna_data = colunas.get("data da coleta")
    if not all([coluna_uf, coluna_produto, coluna_valor, coluna_data]):
        raise SystemExit(f"Colunas inesperadas no arquivo da ANP: {list(tabela.columns)}")

    reduzida = pd.DataFrame(
        {
            "uf": tabela[coluna_uf].str.strip().str.upper(),
            "produto_anp": tabela[coluna_produto].str.strip().str.upper(),
            "valor": pd.to_numeric(
                tabela[coluna_valor].str.replace(",", ".", regex=False), errors="coerce"
            ),
            "data": pd.to_datetime(tabela[coluna_data], format="%d/%m/%Y", errors="coerce"),
        }
    )
    reduzida["produto"] = reduzida["produto_anp"].map(PRODUTOS)
    return reduzida.dropna(subset=["produto", "valor", "uf"])


def agregar(dados: pd.DataFrame) -> pd.DataFrame:
    """Resume os precos por estado e produto, e acrescenta a media nacional.

    Usa a mediana, e nao a media, porque a base traz postos de rodovia e de
    regioes isoladas com precos muito acima do resto — a media seria puxada
    por esses extremos.
    """
    por_uf = (
        dados.groupby(["uf", "produto"])
        .agg(
            preco_mediano=("valor", "median"),
            preco_medio=("valor", "mean"),
            preco_minimo=("valor", "min"),
            preco_maximo=("valor", "max"),
            amostras=("valor", "size"),
        )
        .reset_index()
    )

    nacional = (
        dados.groupby("produto")
        .agg(
            preco_mediano=("valor", "median"),
            preco_medio=("valor", "mean"),
            preco_minimo=("valor", "min"),
            preco_maximo=("valor", "max"),
            amostras=("valor", "size"),
        )
        .reset_index()
    )
    nacional.insert(0, "uf", "BR")

    resultado = pd.concat([nacional, por_uf], ignore_index=True)
    for coluna in ("preco_mediano", "preco_medio", "preco_minimo", "preco_maximo"):
        resultado[coluna] = resultado[coluna].round(3)
    return resultado


def coletar(destino: Path) -> None:
    print("Procurando os arquivos mais recentes na pagina da ANP...")
    arquivos = descobrir_arquivos(PAGINA_ANP)
    if not arquivos:
        raise SystemExit("Nenhum arquivo de precos encontrado na pagina da ANP.")

    partes: list[pd.DataFrame] = []
    for grupo, url in sorted(arquivos.items()):
        print(f"  baixando {grupo}: {url.rsplit('/', 1)[-1]}")
        partes.append(normalizar(baixar_csv(url)))

    dados = pd.concat(partes, ignore_index=True)
    resumo = agregar(dados)

    resumo["periodo_inicio"] = dados["data"].min().date().isoformat()
    resumo["periodo_fim"] = dados["data"].max().date().isoformat()
    resumo["coletado_em"] = date.today().isoformat()

    destino.parent.mkdir(parents=True, exist_ok=True)
    resumo.to_csv(destino, index=False)

    print(f"\n{len(resumo)} combinacoes de estado e produto gravadas em {destino.name}")
    print(f"Periodo coberto: {resumo['periodo_inicio'][0]} a {resumo['periodo_fim'][0]}")
    print("\nMedianas nacionais:")
    for _, linha in resumo[resumo["uf"] == "BR"].iterrows():
        print(
            f"  {linha['produto']:<12} R$ {linha['preco_mediano']:.3f}/litro "
            f"({int(linha['amostras'])} postos)"
        )


def main() -> None:
    config = carregar_configuracao()
    analisador = argparse.ArgumentParser(description="Coleta precos de combustivel da ANP")
    analisador.add_argument(
        "--destino",
        type=Path,
        default=config.caminhos.processados / "precos_combustivel_anp.csv",
    )
    argumentos = analisador.parse_args()
    coletar(argumentos.destino)


if __name__ == "__main__":
    main()
