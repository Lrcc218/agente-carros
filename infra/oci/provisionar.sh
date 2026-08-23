#!/usr/bin/env bash
#
# Prepara uma instancia da OCI para servir o Consultor de carros.
#
# Idempotente: rodar de novo atualiza o que mudou e nao quebra o que ja
# esta no lugar. Testado em Ubuntu 24.04 ARM (Ampere A1) e Oracle Linux 9.
#
#   sudo bash provisionar.sh
#   sudo REPO_URL=https://github.com/fulano/agente-carros.git bash provisionar.sh
#
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Lrcc218/agente-carros.git}"
RAMO="${RAMO:-main}"
DIR_APP="${DIR_APP:-/opt/agente-carros}"
USUARIO="${USUARIO:-agente}"
DIR_CONF="/etc/agente-carros"
ARQ_AMBIENTE="$DIR_CONF/ambiente"

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

titulo() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
info()   { printf '    %s\n' "$*"; }
erro()   { printf '\033[31merro: %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || erro "execute como root (sudo bash provisionar.sh)"

# ---------------------------------------------------------------- pacotes
titulo "Instalando pacotes do sistema"

if command -v apt-get >/dev/null 2>&1; then
    GERENCIADOR=apt
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq git curl nginx python3 python3-venv python3-pip
elif command -v dnf >/dev/null 2>&1; then
    GERENCIADOR=dnf
    dnf install -y -q git curl nginx python3 python3-pip
else
    erro "gerenciador de pacotes nao reconhecido (esperado apt ou dnf)"
fi
info "gerenciador: $GERENCIADOR"

VERSAO_PY="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
info "python: $VERSAO_PY"
python3 - <<'PY' || erro "o projeto exige Python 3.10 ou superior"
import sys
sys.exit(0 if sys.version_info >= (3, 10) else 1)
PY

# ------------------------------------------------------------------ usuario
titulo "Preparando o usuario de servico"

if ! id "$USUARIO" >/dev/null 2>&1; then
    useradd --system --create-home --home-dir "$DIR_APP" --shell /usr/sbin/nologin "$USUARIO" 2>/dev/null \
        || useradd --system --create-home --home-dir "$DIR_APP" --shell /sbin/nologin "$USUARIO"
    info "usuario $USUARIO criado"
else
    info "usuario $USUARIO ja existe"
fi
install -d -o "$USUARIO" -g "$USUARIO" -m 0755 "$DIR_APP"

# -------------------------------------------------------------------- codigo
titulo "Obtendo o codigo"

if [ -d "$DIR_APP/.git" ]; then
    sudo -u "$USUARIO" git -C "$DIR_APP" fetch --quiet origin "$RAMO"
    sudo -u "$USUARIO" git -C "$DIR_APP" reset --quiet --hard "origin/$RAMO"
    info "repositorio atualizado em $RAMO"
else
    # O diretorio ja existe e tem os arquivos de esqueleto do useradd, entao
    # `git clone` recusaria. Init + fetch chega no mesmo lugar sem mover nada.
    sudo -u "$USUARIO" git -C "$DIR_APP" init --quiet
    sudo -u "$USUARIO" git -C "$DIR_APP" remote add origin "$REPO_URL" 2>/dev/null \
        || sudo -u "$USUARIO" git -C "$DIR_APP" remote set-url origin "$REPO_URL"
    sudo -u "$USUARIO" git -C "$DIR_APP" fetch --quiet --depth 1 origin "$RAMO"
    sudo -u "$USUARIO" git -C "$DIR_APP" checkout --quiet -B "$RAMO" "origin/$RAMO"
    info "repositorio obtido de $REPO_URL"
fi

git config --global --add safe.directory "$DIR_APP" 2>/dev/null || true

# ---------------------------------------------------------------- dependencias
titulo "Montando o ambiente virtual"

if [ ! -x "$DIR_APP/.venv/bin/python" ]; then
    sudo -u "$USUARIO" python3 -m venv "$DIR_APP/.venv"
fi
sudo -u "$USUARIO" "$DIR_APP/.venv/bin/pip" install --quiet --upgrade pip wheel
sudo -u "$USUARIO" "$DIR_APP/.venv/bin/pip" install --quiet -r "$DIR_APP/requirements.txt"

# faiss-cpu e a unica dependencia com risco real de nao ter wheel para
# aarch64. Falha aqui e melhor do que falha as 3h da manha no systemd.
sudo -u "$USUARIO" "$DIR_APP/.venv/bin/python" - <<'PY' || erro "faiss nao importou; veja docs/DEPLOY.md, secao ARM"
import faiss, streamlit, pandas  # noqa: F401
PY
info "dependencias instaladas e importaveis"

# -------------------------------------------------------------------- segredo
titulo "Arquivo de ambiente"

install -d -o root -g "$USUARIO" -m 0750 "$DIR_CONF"
if [ ! -f "$ARQ_AMBIENTE" ]; then
    install -o root -g "$USUARIO" -m 0640 "$AQUI/servidor.env.exemplo" "$ARQ_AMBIENTE" 2>/dev/null \
        || install -o root -g "$USUARIO" -m 0640 "$DIR_APP/infra/oci/servidor.env.exemplo" "$ARQ_AMBIENTE"
    info "criado $ARQ_AMBIENTE a partir do exemplo"
    info "PREENCHA a chave antes de subir o servico"
else
    chown root:"$USUARIO" "$ARQ_AMBIENTE"
    chmod 0640 "$ARQ_AMBIENTE"
    info "$ARQ_AMBIENTE preservado"
fi

# --------------------------------------------------------------------- systemd
titulo "Registrando o servico"

install -m 0644 "$DIR_APP/infra/oci/systemd/agente-carros.service" /etc/systemd/system/
install -m 0644 "$DIR_APP/infra/oci/systemd/agente-carros-vivo.service" /etc/systemd/system/
install -m 0644 "$DIR_APP/infra/oci/systemd/agente-carros-vivo.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --quiet agente-carros.service
info "agente-carros.service habilitado"

# ------------------------------------------------------------------ logrotate
titulo "Rotacao do registro de execucao"
if [ -d /etc/logrotate.d ]; then
    install -m 0644 "$DIR_APP/infra/oci/logrotate/agente-carros" /etc/logrotate.d/agente-carros
    info "registro rotacionado diariamente, 30 dias de historico"
else
    info "logrotate ausente; o registro cresce sem rotacao"
fi

# ----------------------------------------------------------------------- nginx
titulo "Configurando o nginx"

if [ -d /etc/nginx/sites-available ]; then
    install -m 0644 "$DIR_APP/infra/oci/nginx/agente-carros.conf" /etc/nginx/sites-available/agente-carros
    ln -sf /etc/nginx/sites-available/agente-carros /etc/nginx/sites-enabled/agente-carros
    rm -f /etc/nginx/sites-enabled/default
else
    install -m 0644 "$DIR_APP/infra/oci/nginx/agente-carros.conf" /etc/nginx/conf.d/agente-carros.conf
    # Oracle Linux traz um server padrao no nginx.conf que rouba a porta 80.
    sed -i 's/^\( *\)listen \+80 \+default_server;/\1listen 8080 default_server;/' /etc/nginx/nginx.conf || true
    sed -i 's/^\( *\)listen \+\[::\]:80 \+default_server;/\1listen [::]:8080 default_server;/' /etc/nginx/nginx.conf || true
    command -v setsebool >/dev/null 2>&1 && setsebool -P httpd_can_network_connect 1 || true
fi
nginx -t
systemctl enable --quiet nginx
systemctl reload nginx 2>/dev/null || systemctl restart nginx
info "nginx servindo na porta 80"

# -------------------------------------------------------------------- firewall
titulo "Abrindo a porta 80 no firewall da instancia"
bash "$DIR_APP/infra/oci/firewall.sh"

# ------------------------------------------------------------------- subir app
titulo "Subindo a aplicacao"

if grep -qE '^(GOOGLE_API_KEY|GEMINI_API_KEY|NVIDIA_API_KEY)=.+' "$ARQ_AMBIENTE"; then
    systemctl restart agente-carros.service
    sleep 8
    if curl -fsS -m 10 -o /dev/null http://127.0.0.1/_stcore/health; then
        IP="$(curl -fsS -m 5 http://169.254.169.254/opc/v2/vnics/ -H 'Authorization: Bearer Oracle' 2>/dev/null \
              | grep -o '"publicIp"[^,]*' | head -1 | cut -d'"' -f4 || true)"
        titulo "Pronto"
        info "aplicacao no ar em http://${IP:-<ip-publico-da-instancia>}/"
        info "logs: journalctl -u agente-carros -f"
    else
        erro "o servico subiu mas a sonda de saude falhou; veja: journalctl -u agente-carros -n 50"
    fi
else
    titulo "Falta a chave de API"
    info "1. edite $ARQ_AMBIENTE e preencha GOOGLE_API_KEY"
    info "2. sudo systemctl start agente-carros"
    info "A infraestrutura ja esta pronta; so o segredo falta."
fi
