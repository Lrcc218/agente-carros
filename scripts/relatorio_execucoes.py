"""Relatorio do registro de execucao.

Le os arquivos JSON Lines gravados pelo agente e responde as perguntas de
manutencao da etapa de monitoramento: quanto ele demora, com que
frequencia nao encontra material, quais ferramentas realmente sao usadas e
o que as pessoas avaliaram mal.

    python scripts/relatorio_execucoes.py
    python scripts/relatorio_execucoes.py --dias 7
    python scripts/relatorio_execucoes.py --ruins      # so o que foi mal avaliado

Nao depende de nada alem da biblioteca padrao: um dashboard que so roda
com infraestrutura extra nao e consultado quando precisa.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from agente_carros.config import carregar_configuracao  # noqa: E402
from agente_carros.ferramentas.buscar_documentos import SEM_RESULTADO  # noqa: E402


def carregar(diretorio: Path, dias: int) -> tuple[list[dict], list[dict]]:
    """Devolve (execucoes, feedbacks) dos ultimos `dias` dias."""
    execucoes, feedbacks = [], []
    hoje = date.today()
    for salto in range(dias):
        arquivo = diretorio / f"execucoes-{(hoje - timedelta(days=salto)).isoformat()}.jsonl"
        if not arquivo.exists():
            continue
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            if not linha.strip():
                continue
            try:
                evento = json.loads(linha)
            except json.JSONDecodeError:
                # Linha truncada por uma escrita interrompida. Ignorar uma
                # linha e melhor do que perder o relatorio inteiro.
                continue
            (feedbacks if evento.get("evento") == "feedback" else execucoes).append(evento)
    return execucoes, feedbacks


def percentil(valores: list[int], fracao: float) -> int:
    if not valores:
        return 0
    ordenados = sorted(valores)
    posicao = min(int(len(ordenados) * fracao), len(ordenados) - 1)
    return ordenados[posicao]


def titulo(texto: str) -> None:
    print(f"\n\033[1m{texto}\033[0m")


def relatar(execucoes: list[dict], feedbacks: list[dict], dias: int) -> None:
    if not execucoes:
        print(f"Nenhuma execucao registrada nos ultimos {dias} dias.")
        print("O registro e gravado quando o agente responde. Faca uma pergunta e repita.")
        return

    duracoes = [e.get("duracao_ms", 0) for e in execucoes]
    erros = [e for e in execucoes if e.get("erro")]
    sem_material = [e for e in execucoes if SEM_RESULTADO in (e.get("resposta") or "")]

    titulo(f"Volume — ultimos {dias} dias")
    print(f"  perguntas respondidas: {len(execucoes)}")
    sessoes = {e.get("sessao") for e in execucoes if e.get("sessao")}
    print(f"  sessoes distintas:     {len(sessoes)}")
    print(f"  falhas de execucao:    {len(erros)}")

    titulo("Tempo de resposta")
    print(f"  mediana: {percentil(duracoes, 0.50) / 1000:.1f} s")
    print(f"  p95:     {percentil(duracoes, 0.95) / 1000:.1f} s")
    print(f"  maximo:  {max(duracoes) / 1000:.1f} s")

    titulo("Ferramentas acionadas")
    contagem = Counter(nome for e in execucoes for nome in e.get("ferramentas", []))
    if contagem:
        for nome, vezes in contagem.most_common():
            print(f"  {vezes:4d}  {nome}")
    else:
        print("  nenhuma; o modelo respondeu sem consultar dados")

    titulo("Documentos citados")
    fontes = Counter(fonte for e in execucoes for fonte in e.get("fontes", []))
    if fontes:
        for fonte, vezes in fontes.most_common(10):
            print(f"  {vezes:4d}  {fonte}")
    else:
        print("  nenhum; nenhuma pergunta chegou a busca semantica")

    titulo("Qualidade")
    positivos = sum(1 for f in feedbacks if f.get("util"))
    negativos = sum(1 for f in feedbacks if not f.get("util"))
    avaliadas = positivos + negativos
    print(f"  respostas avaliadas: {avaliadas} de {len(execucoes)}")
    if avaliadas:
        print(f"  uteis:    {positivos} ({positivos / avaliadas:.0%})")
        print(f"  ruins:    {negativos} ({negativos / avaliadas:.0%})")
    print(f"  sem material nos documentos: {len(sem_material)}")

    if sem_material:
        titulo("Perguntas sem material — candidatas a novo documento na base")
        for evento in sem_material[:10]:
            print(f"  - {evento.get('pergunta', '')[:100]}")


def listar_ruins(execucoes: list[dict], feedbacks: list[dict]) -> None:
    """Perguntas avaliadas com polegar para baixo, para revisao manual."""
    ruins = {f["id"] for f in feedbacks if not f.get("util") and f.get("id")}
    encontradas = [e for e in execucoes if e.get("id") in ruins]
    if not encontradas:
        print("Nenhuma resposta avaliada negativamente no periodo.")
        return
    for evento in encontradas:
        print("=" * 70)
        print(f"{evento.get('momento')}  ({evento.get('duracao_ms', 0) / 1000:.1f}s)")
        print(f"ferramentas: {', '.join(evento.get('ferramentas') or ['nenhuma'])}")
        print(f"\nP: {evento.get('pergunta')}")
        print(f"\nR: {evento.get('resposta')}\n")


def main() -> None:
    analisador = argparse.ArgumentParser(description="Relatorio do registro de execucao")
    analisador.add_argument("--dias", type=int, default=30, help="Janela a considerar")
    analisador.add_argument(
        "--ruins", action="store_true", help="Lista as respostas mal avaliadas"
    )
    argumentos = analisador.parse_args()

    diretorio = carregar_configuracao().caminhos.registros
    if not diretorio.exists():
        print(f"Nenhum registro em {diretorio}.")
        print("O diretorio e criado na primeira pergunta respondida.")
        return

    execucoes, feedbacks = carregar(diretorio, argumentos.dias)
    if argumentos.ruins:
        listar_ruins(execucoes, feedbacks)
    else:
        relatar(execucoes, feedbacks, argumentos.dias)


if __name__ == "__main__":
    main()
