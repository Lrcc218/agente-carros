# Pipeline do projeto. Cada alvo e um passo isolado e repetivel.
#
#   make instalar      prepara o ambiente virtual
#   make chave ARQ=... grava a chave de API no .env
#   make dados         refaz a coleta das fontes oficiais
#   make documentos-pdf gera os PDFs do acervo e a documentacao
#   make indice        constroi o indice vetorial
#   make diagnostico   confere o que falta para rodar
#   make testar        roda a bateria de testes
#   make relatorio     resume o registro de execucao
#   make rodar         sobe a interface web
#   make tudo          do zero ate pronto para usar
#
#   make deploy-instancia   cria a VM na OCI (insiste ate haver capacidade)
#   make deploy             publica a versao atual no servidor
#   make deploy-estado      estado do servico no servidor
#   make deploy-logs        acompanha os logs do servidor

PY := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: ajuda instalar chave dados documentos-pdf indice diagnostico relatorio testar lint rodar terminal tudo limpar \
        deploy deploy-instancia deploy-estado deploy-logs

# HOST e CHAVE_SSH saem de infra/oci/instancia.env, fora do repositorio.
CONF_OCI := infra/oci/instancia.env
SSH_OCI = @test -f $(CONF_OCI) || { echo "crie $(CONF_OCI) a partir de $(CONF_OCI).exemplo"; exit 1; }; \
	. ./$(CONF_OCI); ssh -o StrictHostKeyChecking=accept-new $${CHAVE_SSH:+-i $$CHAVE_SSH} "$$HOST"

ajuda:
	@grep -E '^#   ' Makefile | sed 's/^#   //'

.venv:
	python3 -m venv .venv

instalar: .venv
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -r requirements-dev.txt
	@echo "Ambiente pronto."

# Requer ARQ apontando para o arquivo que contem a chave.
#   make chave ARQ=~/minha-chave.txt
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

documentos-pdf:
	$(PY) scripts/gerar_pdfs.py

indice: documentos-pdf
	$(PY) scripts/indexar_documentos.py

diagnostico:
	$(PY) scripts/diagnosticar.py

relatorio:
	$(PY) scripts/relatorio_execucoes.py

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

# ------------------------------------------------------------------ deploy
# O runbook completo esta em docs/DEPLOY.md.

deploy-instancia:
	./infra/oci/criar-instancia.sh

deploy:
	./infra/oci/enviar.sh

deploy-estado:
	$(SSH_OCI) "systemctl status agente-carros --no-pager; curl -sf localhost/_stcore/health && echo ' <- saude ok'"

deploy-logs:
	$(SSH_OCI) "sudo journalctl -u agente-carros -f"
