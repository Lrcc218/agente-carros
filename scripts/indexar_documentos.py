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
import hashlib
import json
import shutil
import sys
import time
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from agente_carros import documentos  # noqa: E402
from agente_carros.config import carregar_configuracao  # noqa: E402

# Trechos maiores reduzem o numero de requisicoes de embedding, o que
# importa porque a camada gratuita limita o total por dia, nao por minuto.
# Um manual de 484 paginas gera 1145 trechos a 1200 caracteres e apenas
# cerca de 570 a 2400, o que cabe na cota. A recuperacao fica um pouco
# menos precisa, mas continua boa: o trecho recuperado traz mais contexto.
TAMANHO_TRECHO = 2400
SOBREPOSICAO = 200

# A camada gratuita das APIs de embedding limita requisicoes por minuto.
# Enviar centenas de trechos de uma vez estoura o limite e devolve 429, entao
# a indexacao vai em lotes pequenos, com pausa entre eles e reenvio com espera
# crescente quando o limite e atingido.
# O limite da camada gratuita e por minuto, e cada texto do lote conta como
# uma requisicao. Um lote de 16 disparado de uma vez estoura a taxa mesmo
# com cota diaria sobrando — chamadas individuais passam, o lote nao. Lotes
# pequenos com pausa mantem o ritmo abaixo do teto.
TAMANHO_LOTE = 4
PAUSA_ENTRE_LOTES = 4.0
TENTATIVAS = 8
ESPERA_INICIAL = 20
ESPERA_MAXIMA = 90


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


# Falhas que valem reenviar: limite de requisicoes e indisponibilidade
# temporaria do servico. Erro de credencial ou de modelo inexistente nao
# melhora esperando, entao esses sobem na hora.
TRANSITORIOS = ("429", "500", "502", "503", "504")
TERMOS_TRANSITORIOS = ("quota", "rate limit", "unavailable", "internal", "timeout", "deadline")


def _vale_reenviar(erro: Exception) -> bool:
    texto = str(erro).lower()
    return any(c in texto for c in TRANSITORIOS) or any(t in texto for t in TERMOS_TRANSITORIOS)


def _assinatura(trechos: list, modelo: str) -> str:
    """Identifica esta indexacao, para so retomar o progresso equivalente."""
    marca = f"{modelo}|{TAMANHO_TRECHO}|{SOBREPOSICAO}|{len(trechos)}"
    return hashlib.sha256(marca.encode()).hexdigest()[:16]


def indexar_em_lotes(trechos: list, embeddings, FAISS, parcial: Path, modelo: str) -> object:
    """Gera os embeddings aos poucos, salvando o progresso a cada lote.

    A cota gratuita de embeddings e diaria, e o servico as vezes responde
    indisponivel. Sem progresso salvo, uma falha perto do fim descarta
    centenas de requisicoes ja gastas, que so voltam no dia seguinte. Por
    isso o indice parcial vai para o disco a cada lote e uma nova execucao
    retoma de onde parou.
    """
    total = len(trechos)
    assinatura = _assinatura(trechos, modelo)
    controle = parcial / "progresso.json"

    indice = None
    processados = 0

    if controle.exists():
        estado = json.loads(controle.read_text(encoding="utf-8"))
        if estado.get("assinatura") == assinatura:
            indice = FAISS.load_local(
                str(parcial), embeddings, allow_dangerous_deserialization=True
            )
            processados = estado["processados"]
            print(f"  retomando de {processados}/{total} trechos ja processados")
        else:
            print("  progresso anterior e de outra configuracao; recomecando")
            shutil.rmtree(parcial)

    for inicio in range(processados, total, TAMANHO_LOTE):
        lote = trechos[inicio : inicio + TAMANHO_LOTE]
        espera = ESPERA_INICIAL

        for tentativa in range(1, TENTATIVAS + 1):
            try:
                if indice is None:
                    indice = FAISS.from_documents(lote, embeddings)
                else:
                    indice.add_documents(lote)
                break
            except Exception as erro:  # noqa: BLE001 - o provedor sinaliza falhas de varias formas
                if not _vale_reenviar(erro) or tentativa == TENTATIVAS:
                    raise
                print(
                    f"    falha temporaria; aguardando {espera}s "
                    f"(tentativa {tentativa}/{TENTATIVAS})"
                )
                time.sleep(espera)
                espera = min(espera * 2, ESPERA_MAXIMA)

        processados = min(inicio + TAMANHO_LOTE, total)
        parcial.mkdir(parents=True, exist_ok=True)
        indice.save_local(str(parcial))
        controle.write_text(
            json.dumps({"assinatura": assinatura, "processados": processados}),
            encoding="utf-8",
        )
        print(f"  embeddings: {processados}/{total} trechos", flush=True)
        if processados < total:
            time.sleep(PAUSA_ENTRE_LOTES)

    if indice is None:
        raise SystemExit("Nenhum trecho para indexar.")
    return indice


def reunir_arquivos(pastas: list[Path]) -> list[tuple[Path, Path]]:
    """Devolve (arquivo, pasta_de_origem) de todas as pastas do acervo.

    Pastas iniciadas por sublinhado ficam de fora de proposito: guardam o
    que foi baixado mas nao deve entrar no indice, como documentos de
    modelos fora do catalogo ou material pendente de indexacao.

    O MANIFESTO tambem fica de fora: ele descreve o acervo, nao faz parte
    dele. Indexa-lo faria o agente citar o indice como se fosse a fonte.
    """
    encontrados: list[tuple[Path, Path]] = []
    for pasta in pastas:
        if not pasta.exists():
            continue
        for arquivo in sorted(pasta.rglob("*")):
            if not arquivo.is_file() or not documentos.eh_suportado(arquivo):
                continue
            if arquivo.name.upper().startswith("MANIFESTO"):
                continue
            if any(parte.startswith("_") for parte in arquivo.relative_to(pasta).parts):
                continue
            encontrados.append((arquivo, pasta))
    return encontrados


def classificar(arquivo: Path, origem: Path, corporativos: Path) -> str:
    """Tipo do documento, usado como filtro na recuperacao."""
    if origem == corporativos:
        return "documento_interno"
    return "manual" if arquivo.parent.name == "manuais" else "documento_oficial"


def documentos_ja_indexados(destino: Path) -> set[str]:
    """Nomes dos documentos que o indice atual contem."""
    metadados = destino / "metadados.json"
    if not metadados.exists():
        return set()
    try:
        return set(json.loads(metadados.read_text(encoding="utf-8")).get("documentos", []))
    except (json.JSONDecodeError, OSError):
        return set()


def conferir_perdas(destino: Path, encontrados: list[tuple[Path, Path]], forcar: bool) -> None:
    """Recusa reconstruir o indice quando isso apagaria documentos.

    A indexacao reconstroi do zero, entao ela so conhece o que esta em
    disco no momento. Os PDFs baixados nao sao versionados: num clone
    novo do repositorio a pasta esta vazia, e reindexar ali silenciosamente
    apagaria do indice o manual do proprietario e as tabelas do Inmetro.

    O sintoma nao apareceria aqui, e sim semanas depois, com o agente
    dizendo que nao sabe algo que ele sabia.
    """
    perdidos = documentos_ja_indexados(destino) - {a.name for a, _ in encontrados}
    if not perdidos or forcar:
        if perdidos:
            print(f"AVISO: {len(perdidos)} documento(s) sairao do indice, a seu pedido.")
        return

    print("\nO indice atual contem documentos que nao estao em disco:\n")
    for nome in sorted(perdidos):
        print(f"  - {nome}")
    raise SystemExit(
        "\nReconstruir agora apagaria esses documentos do indice.\n\n"
        "Para recuperar os documentos baixados por script:\n"
        "    python scripts/baixar_documentos.py\n\n"
        "Manuais de montadora entram a mao; veja docs/MANUAIS.md.\n"
        "Para reconstruir mesmo assim, sabendo o que perde:\n"
        "    python scripts/indexar_documentos.py --forcar"
    )


def indexar(pastas: list[Path], destino: Path, forcar: bool = False) -> None:
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    from agente_carros.fabrica import criar_provedor

    config = carregar_configuracao()
    # rglob para alcancar as subpastas de manuais adicionados a mao. Pastas
    # iniciadas por sublinhado ficam de fora de proposito: guardam o que foi
    # baixado mas nao deve entrar no indice, como documentos de modelos que
    # nao estao no catalogo ou material ainda pendente de indexacao.
    encontrados = reunir_arquivos(pastas)
    if not encontrados:
        formatos = ", ".join(documentos.formatos_suportados())
        locais = ", ".join(str(p) for p in pastas)
        raise SystemExit(
            f"Nenhum documento em {locais} (formatos aceitos: {formatos}). "
            "Rode antes: python scripts/baixar_documentos.py"
        )
    conferir_perdas(destino, encontrados, forcar)
    arquivos = [arquivo for arquivo, _ in encontrados]

    titulos: dict[str, str] = {}
    for pasta in pastas:
        titulos |= carregar_titulos(pasta)
    titulos |= carregar_titulos_de_manuais(config.caminhos.dados / "manuais.csv")

    paginas = []
    for arquivo, origem in encontrados:
        eh_pdf = arquivo.suffix.lower() == ".pdf"
        try:
            if eh_pdf:
                carregadas = PyPDFLoader(str(arquivo)).load()
            else:
                texto = documentos.extrair_texto(arquivo)
                if not texto.strip():
                    print(f"  IGNORADO  {arquivo.name}: nenhum texto extraido")
                    continue
                carregadas = [Document(page_content=texto, metadata={"source": str(arquivo)})]
        except documentos.DependenciaAusente as erro:
            print(f"  IGNORADO  {arquivo.name}: {erro}")
            continue
        except Exception as erro:  # noqa: BLE001 - um arquivo ruim nao para a indexacao
            print(f"  IGNORADO  {arquivo.name}: nao foi possivel ler ({erro})")
            continue

        tipo = classificar(arquivo, origem, config.caminhos.corporativos)
        formato = documentos.FORMATOS.get(arquivo.suffix.lower(), arquivo.suffix)
        for pagina in carregadas:
            pagina.metadata["titulo"] = titulos.get(arquivo.name, nome_legivel(arquivo))
            pagina.metadata["arquivo"] = arquivo.name
            pagina.metadata["tipo"] = tipo
            pagina.metadata["formato"] = formato
        paginas.extend(carregadas)
        unidade = "paginas" if eh_pdf else "bloco"
        print(f"  lido  [{tipo}/{formato}] {arquivo.name} ({len(carregadas)} {unidade})")

    divisor = RecursiveCharacterTextSplitter(
        chunk_size=TAMANHO_TRECHO, chunk_overlap=SOBREPOSICAO
    )
    trechos = divisor.split_documents(paginas)
    print(f"\n{len(trechos)} trechos gerados. Calculando embeddings...")

    # Pela fabrica, e nao por um adaptador especifico: o script deve
    # indexar com o mesmo provedor que a aplicacao usa para consultar.
    provedor = criar_provedor(config)
    parcial = destino.parent / f"{destino.name}_parcial"
    indice = indexar_em_lotes(
        trechos, provedor.modelo_embedding(), FAISS, parcial, config.modelo_embedding
    )

    if destino.exists():
        shutil.rmtree(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    indice.save_local(str(destino))

    (destino / "metadados.json").write_text(
        json.dumps(
            {
                "gerado_em": date.today().isoformat(),
                "modelo_embedding": config.modelo_embedding,
                "documentos": [arquivo.name for arquivo in arquivos],
                "formatos": sorted(
                    {
                        documentos.FORMATOS.get(a.suffix.lower(), a.suffix)
                        for a in arquivos
                    }
                ),
                "trechos": len(trechos),
                "tamanho_trecho": TAMANHO_TRECHO,
                "sobreposicao": SOBREPOSICAO,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    # O parcial so e descartado depois que o definitivo esta no lugar.
    if parcial.exists():
        shutil.rmtree(parcial)
    print(f"Indice gravado em {destino.relative_to(RAIZ)}")


def main() -> None:
    config = carregar_configuracao()
    analisador = argparse.ArgumentParser(description="Indexa os documentos oficiais")
    analisador.add_argument(
        "--documentos",
        type=Path,
        nargs="*",
        default=[config.caminhos.corporativos, config.caminhos.documentos],
        help="Pastas do acervo. Por padrao, o acervo interno e os documentos baixados.",
    )
    analisador.add_argument("--destino", type=Path, default=config.caminhos.indice_vetorial)
    analisador.add_argument(
        "--forcar",
        action="store_true",
        help="Reconstroi mesmo que documentos ja indexados saiam do indice",
    )
    argumentos = analisador.parse_args()
    indexar(list(argumentos.documentos), argumentos.destino, argumentos.forcar)


if __name__ == "__main__":
    main()
