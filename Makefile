# Pipeline do projeto. Cada alvo e um passo isolado e repetivel.
#
#   make instalar      prepara o ambiente virtual
#   make chave ARQ=... grava a chave de API no .env
#   make dados         refaz a coleta das fontes oficiais
#   make indice        constroi o indice vetorial
#   make diagnostico   confere o que falta para rodar
#   make testar        roda a bateria de testes
#   make rodar         sobe a interface web
#   make tudo          do zero ate pronto para usar

PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: ajuda instalar chave dados indice diagnostico testar lint rodar terminal tudo limpar

ajuda:
	@grep -E '^#   ' Makefile | sed 's/^#   //'

.venv:
	python3 -m venv .venv

instalar: .venv
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -r requirements-dev.txt
	@echo "Ambiente pronto."

# Requer ARQ apontando para o arquivo que contem a chave.
#   make chave ARQ=/home/luan/geminikey
chave:
	@test -n "$(ARQ)" || (echo "Informe o arquivo: make chave ARQ=/caminho/da/chave"; exit 1)
	$(PY) scripts/configurar_chave.py "$(ARQ)"

# Recoleta tudo das fontes oficiais. Os datasets ja vem versionados no
# repositorio, entao isto so e necessario para atualizar os numeros.
dados:
	$(PY) scripts/coletar_fipe.py
	$(PY) scripts/coletar_precos_anp.py
	$(PY) scripts/baixar_documentos.py
	$(PY) scripts/extrair_consumo_pbev.py

documentos:
	$(PY) scripts/baixar_documentos.py

indice:
	$(PY) scripts/indexar_documentos.py

diagnostico:
	$(PY) scripts/diagnosticar.py

diagnostico-rapido:
	$(PY) scripts/diagnosticar.py --rapido

testar:
	$(PY) -m pytest -q

lint:
	.venv/bin/ruff check src scripts app testes

rodar:
	.venv/bin/streamlit run app/streamlit_app.py

terminal:
	$(PY) app/cli.py

tudo: instalar documentos indice testar diagnostico
	@echo "Pronto. Suba a interface com: make rodar"

limpar:
	rm -rf .pytest_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
