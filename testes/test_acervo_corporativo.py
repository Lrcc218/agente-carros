"""Testes do acervo corporativo.

Estes documentos sao a base de conhecimento que o agente consulta. Se um
deles deixar de ser legivel, o agente passa a dizer que nao sabe — e o
sintoma so apareceria numa conversa. Aqui a falha aparece no CI.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from agente_carros.config import carregar_configuracao

RAIZ = Path(__file__).resolve().parents[1]

DECLARADOS = {
    "politica_garantia_pos_venda.pdf": "Manual de Garantia e Pós-venda",
    "politica_comercial_precificacao.pdf": "Política Comercial e de Precificação",
    "politica_privacidade_lgpd.pdf": "Política de Privacidade e Proteção de Dados",
    "faq_atendimento.pdf": "Manual de Perguntas Frequentes",
    "manual_onboarding.pdf": "Manual de Onboarding",
    "tabela_servicos_oficina.pdf": "Tabela de Serviços e Alçadas da Oficina",
    "contatos_areas.pdf": "Diretório de Áreas Responsáveis",
}


def texto_do_pdf(caminho: Path) -> str:
    from pypdf import PdfReader

    return "\n".join(p.extract_text() or "" for p in PdfReader(str(caminho)).pages)


@pytest.fixture(scope="module")
def indexador():
    """Carrega o script de indexacao como modulo, para testar suas funcoes."""
    caminho = RAIZ / "scripts" / "indexar_documentos.py"
    spec = importlib.util.spec_from_file_location("indexador", caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["indexador"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def acervo() -> Path:
    return carregar_configuracao().caminhos.corporativos


def test_todos_os_documentos_declarados_existem(acervo):
    faltando = [nome for nome in DECLARADOS if not (acervo / nome).exists()]
    assert not faltando, f"declarados no MANIFESTO mas ausentes: {faltando}"


def test_todo_documento_tem_titulo_declarado(acervo, indexador):
    """Sem declaracao, o agente cita o nome do arquivo em vez do titulo."""
    titulos = indexador.carregar_titulos(acervo)
    for arquivo, _ in indexador.reunir_arquivos([acervo]):
        assert titulos.get(arquivo.name), f"{arquivo.name} sem titulo no MANIFESTO"


def test_titulos_conferem_com_o_esperado(acervo, indexador):
    titulos = indexador.carregar_titulos(acervo)
    for nome, titulo in DECLARADOS.items():
        assert titulos[nome] == titulo


def test_manifesto_nao_entra_no_indice(acervo, indexador):
    """O manifesto descreve o acervo; nao e conteudo dele."""
    nomes = {arquivo.name for arquivo, _ in indexador.reunir_arquivos([acervo])}
    assert "MANIFESTO.md" not in nomes


def test_o_acervo_e_uniforme_em_pdf(acervo, indexador):
    """Formato unico no acervo: e o que se espera de base documental."""
    sufixos = {arquivo.suffix.lower() for arquivo, _ in indexador.reunir_arquivos([acervo])}
    assert sufixos == {".pdf"}


def test_toda_fonte_tem_pdf_correspondente(acervo):
    for fonte in (acervo / "_fontes").glob("*.md"):
        assert (acervo / f"{fonte.stem}.pdf").exists(), f"falta o PDF de {fonte.name}"


def test_pdfs_estao_em_dia_com_as_fontes(acervo):
    """PDF gerado de fonte antiga entrega politica desatualizada como vigente."""
    import hashlib
    import json

    controle = acervo / "_fontes" / ".assinaturas.json"
    assert controle.exists(), "rode: python scripts/gerar_pdfs.py"
    registradas = json.loads(controle.read_text(encoding="utf-8"))

    for fonte in sorted((acervo / "_fontes").glob("*.md")):
        atual = hashlib.sha256(fonte.read_bytes()).hexdigest()[:16]
        assert registradas.get(fonte.name) == atual, (
            f"{fonte.name} mudou desde a geracao; rode: python scripts/gerar_pdfs.py"
        )


def test_fontes_ficam_fora_do_indice(acervo, indexador):
    """Indexar fonte e PDF duplicaria cada trecho no indice."""
    caminhos = [str(arquivo) for arquivo, _ in indexador.reunir_arquivos([acervo])]
    assert not any("_fontes" in caminho for caminho in caminhos)


@pytest.mark.parametrize("nome", sorted(DECLARADOS))
def test_cada_documento_extrai_texto_util(acervo, nome):
    """O que importa nao e o PDF abrir, e o texto sair legivel para o indice."""
    texto = texto_do_pdf(acervo / nome)
    assert len(texto) > 4000, f"{nome} extraiu pouco texto: {len(texto)} caracteres"


@pytest.mark.parametrize("nome", sorted(DECLARADOS))
def test_cada_documento_declara_versao_e_area(acervo, nome):
    cabecalho = texto_do_pdf(acervo / nome)[:1200]
    assert "Versão:" in cabecalho
    assert "Departamento:" in cabecalho


def test_documentos_do_acervo_sao_classificados_como_internos(acervo, indexador):
    for arquivo, origem in indexador.reunir_arquivos([acervo]):
        assert indexador.classificar(arquivo, origem, acervo) == "documento_interno"


def test_manual_baixado_e_classificado_como_manual(tmp_path, indexador):
    """A classificacao distingue o acervo interno do material de terceiros."""
    manuais = tmp_path / "manuais"
    manuais.mkdir()
    arquivo = manuais / "toyota_corolla.pdf"
    arquivo.write_bytes(b"%PDF-1.4")
    assert indexador.classificar(arquivo, tmp_path, Path("/outro")) == "manual"


def test_diretorio_de_areas_cobre_os_assuntos_do_fallback(acervo):
    """Sem resposta, o agente indica a area responsavel. Ela tem de existir."""
    texto = texto_do_pdf(acervo / "contatos_areas.pdf").lower()

    for assunto in ["garantia", "desconto", "lgpd", "benefício", "recall", "senha"]:
        assert assunto in texto, f"sem área declarada para '{assunto}'"

    for area in ["posvenda@", "comercial@", "privacidade@", "rh@", "ouvidoria@", "suporte@"]:
        assert area in texto, f"contato ausente: {area}"


def test_manual_do_sistema_gerado(indexador):
    """A documentacao do projeto tambem sai em PDF, e fora do acervo."""
    manual = RAIZ / "docs" / "Manual_do_Sistema.pdf"
    assert manual.exists(), "rode: python scripts/gerar_pdfs.py"
    assert len(texto_do_pdf(manual)) > 20000
