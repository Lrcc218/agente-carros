"""Verificacao de saude do projeto.

Confere, em ordem, tudo que o agente precisa para funcionar e aponta o
comando exato que resolve cada pendencia. Serve tanto para diagnosticar um
ambiente novo quanto para conferir se o deploy vai subir.

Uso:
    python scripts/diagnosticar.py
    python scripts/diagnosticar.py --rapido    # nao chama a API
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from agente_carros.config import carregar_configuracao  # noqa: E402

OK = "  [ok]   "
FALHA = "  [FALTA]"
AVISO = "  [aviso]"


class Relatorio:
    """Acumula o resultado das verificacoes."""

    def __init__(self) -> None:
        self.pendencias: list[str] = []

    def ok(self, mensagem: str) -> None:
        print(f"{OK} {mensagem}")

    def aviso(self, mensagem: str) -> None:
        print(f"{AVISO} {mensagem}")

    def falha(self, mensagem: str, correcao: str) -> None:
        print(f"{FALHA} {mensagem}")
        print(f"          -> {correcao}")
        self.pendencias.append(correcao)


def verificar_dados(relatorio: Relatorio) -> None:
    print("\nDados")
    caminhos = carregar_configuracao().caminhos
    esperados = [
        (caminhos.fichas_tecnicas, "ficha tecnica", None),
        (caminhos.precos_fipe, "precos da FIPE", "python scripts/coletar_fipe.py"),
        (caminhos.consumo_pbev, "consumo do Inmetro", "python scripts/extrair_consumo_pbev.py"),
        (
            caminhos.precos_combustivel,
            "precos da ANP",
            "python scripts/coletar_precos_anp.py",
        ),
    ]
    for caminho, rotulo, correcao in esperados:
        if caminho.exists():
            linhas = len(caminho.read_text(encoding="utf-8").splitlines()) - 1
            relatorio.ok(f"{rotulo}: {linhas} registros")
        elif correcao:
            relatorio.falha(f"{rotulo}: arquivo ausente", correcao)
        else:
            relatorio.falha(f"{rotulo}: arquivo ausente", f"restaure {caminho.name}")


def verificar_catalogo(relatorio: Relatorio) -> None:
    print("\nCatalogo")
    try:
        from agente_carros.fabrica import criar_catalogo

        veiculos = criar_catalogo(carregar_configuracao()).listar()
    except Exception as erro:  # noqa: BLE001
        relatorio.falha(f"nao foi possivel montar o catalogo: {erro}", "confira os CSVs de dados")
        return

    relatorio.ok(f"{len(veiculos)} veiculos carregados")
    sem_preco = [v.id for v in veiculos if v.preco_fipe is None]
    sem_consumo = [v.id for v in veiculos if not v.tem_dados_de_consumo and not v.e_eletrico]
    if sem_preco:
        relatorio.aviso(f"sem preco: {', '.join(sem_preco)}")
    if sem_consumo:
        relatorio.aviso(f"sem consumo (esperado para o T-Cross): {', '.join(sem_consumo)}")


def verificar_configuracao(relatorio: Relatorio) -> bool:
    print("\nConfiguracao")
    config = carregar_configuracao()
    relatorio.ok(f"provedor: {config.provedor_llm}")
    relatorio.ok(f"modelo de chat: {config.modelo_chat}")
    relatorio.ok(f"modelo de embedding: {config.modelo_embedding}")

    if not (RAIZ / ".env").exists():
        relatorio.falha(
            "arquivo .env ausente",
            "python scripts/configurar_chave.py /caminho/da/chave",
        )
        return False

    try:
        config.validar()
    except ValueError as erro:
        relatorio.falha(str(erro), "python scripts/configurar_chave.py /caminho/da/chave")
        return False

    chave = config.chave_api
    relatorio.ok(f"chave presente: {chave[:6]}...{chave[-4:]} ({len(chave)} caracteres)")
    return True


def verificar_provedor(relatorio: Relatorio) -> bool:
    print("\nProvedor de IA")
    config = carregar_configuracao()
    try:
        from agente_carros.fabrica import criar_provedor

        provedor = criar_provedor(config)
    except Exception as erro:  # noqa: BLE001
        relatorio.falha(f"nao foi possivel criar o provedor: {erro}", "confira PROVEDOR_LLM")
        return False

    try:
        resposta = provedor.modelo_chat().invoke("Responda apenas: ok")
        texto = getattr(resposta, "content", str(resposta)).strip()
        relatorio.ok(f"chat respondeu: {texto[:60]!r}")
    except Exception as erro:  # noqa: BLE001
        relatorio.falha(
            f"o modelo de chat recusou a chamada: {type(erro).__name__}: {str(erro)[:160]}",
            "verifique se a chave tem permissao de inferencia no provedor",
        )
        return False

    try:
        vetor = provedor.modelo_embedding().embed_query("teste")
        relatorio.ok(f"embeddings responderam: vetor de {len(vetor)} dimensoes")
    except Exception as erro:  # noqa: BLE001
        relatorio.falha(
            f"o modelo de embedding recusou a chamada: {type(erro).__name__}: {str(erro)[:160]}",
            "verifique o modelo de embedding do provedor",
        )
        return False
    return True


def verificar_indice(relatorio: Relatorio) -> None:
    print("\nIndice vetorial")
    caminhos = carregar_configuracao().caminhos
    documentos = list(caminhos.documentos.rglob("*.pdf")) if caminhos.documentos.exists() else []
    if documentos:
        relatorio.ok(f"{len(documentos)} PDFs disponiveis para indexacao")
    else:
        relatorio.falha("nenhum PDF baixado", "python scripts/baixar_documentos.py")

    if caminhos.indice_vetorial.exists():
        relatorio.ok(f"indice presente em {caminhos.indice_vetorial.name}")
    else:
        relatorio.falha(
            "indice ausente; o agente responde sem os documentos do Inmetro",
            "python scripts/indexar_documentos.py",
        )


def main() -> None:
    analisador = argparse.ArgumentParser(description="Diagnostico do ambiente")
    analisador.add_argument(
        "--rapido", action="store_true", help="Pula as chamadas de rede ao provedor"
    )
    argumentos = analisador.parse_args()

    print("=" * 62)
    print("Diagnostico do projeto")
    print("=" * 62)

    relatorio = Relatorio()
    verificar_dados(relatorio)
    verificar_catalogo(relatorio)
    configurado = verificar_configuracao(relatorio)
    if configurado and not argumentos.rapido:
        verificar_provedor(relatorio)
    elif argumentos.rapido:
        print("\nProvedor de IA")
        relatorio.aviso("verificacao de rede pulada (--rapido)")
    verificar_indice(relatorio)

    print("\n" + "=" * 62)
    if relatorio.pendencias:
        print(f"{len(relatorio.pendencias)} pendencia(s). Execute, nesta ordem:\n")
        for passo, correcao in enumerate(relatorio.pendencias, start=1):
            print(f"  {passo}. {correcao}")
        raise SystemExit(1)
    print("Tudo pronto. Suba a interface com: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()
