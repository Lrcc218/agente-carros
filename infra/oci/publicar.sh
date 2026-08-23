#!/usr/bin/env bash
#
# Publica uma nova versao na instancia. Roda DENTRO do servidor.
#
#   sudo bash /opt/agente-carros/infra/oci/publicar.sh
#
# Traz o codigo novo, sincroniza as dependencias so quando o requirements.txt
# mudou, reinicia e confere a sonda de saude. Se a sonda falhar, volta para a
# revisao anterior em vez de deixar o ar caido.
#
set -euo pipefail

DIR_APP="${DIR_APP:-/opt/agente-carros}"
USUARIO="${USUARIO:-agente}"
RAMO="${RAMO:-main}"

titulo() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
info()   { printf '    %s\n' "$*"; }
erro()   { printf '\033[31merro: %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || erro "execute como root"
[ -d "$DIR_APP/.git" ] || erro "$DIR_APP nao e um repositorio; rode provisionar.sh antes"

ANTERIOR="$(sudo -u "$USUARIO" git -C "$DIR_APP" rev-parse HEAD)"
HASH_REQ_ANTES="$(sha256sum "$DIR_APP/requirements.txt" | cut -d' ' -f1)"

titulo "Trazendo o codigo"
sudo -u "$USUARIO" git -C "$DIR_APP" fetch --quiet origin "$RAMO"
sudo -u "$USUARIO" git -C "$DIR_APP" reset --quiet --hard "origin/$RAMO"
NOVO="$(sudo -u "$USUARIO" git -C "$DIR_APP" rev-parse HEAD)"

if [ "$ANTERIOR" = "$NOVO" ]; then
    info "ja estava na revisao ${NOVO:0:8}; seguindo assim mesmo para revalidar"
else
    info "${ANTERIOR:0:8} -> ${NOVO:0:8}"
fi

if [ "$HASH_REQ_ANTES" != "$(sha256sum "$DIR_APP/requirements.txt" | cut -d' ' -f1)" ]; then
    titulo "requirements.txt mudou; sincronizando dependencias"
    sudo -u "$USUARIO" "$DIR_APP/.venv/bin/pip" install --quiet -r "$DIR_APP/requirements.txt"
fi

# Unidades e configuracao de proxy tambem sao versionadas: republicar tem de
# propagar mudancas nelas, senao o servidor diverge silenciosamente do repo.
titulo "Sincronizando servico e proxy"
install -m 0644 "$DIR_APP/infra/oci/systemd/agente-carros.service" /etc/systemd/system/
install -m 0644 "$DIR_APP/infra/oci/systemd/agente-carros-vivo.service" /etc/systemd/system/
install -m 0644 "$DIR_APP/infra/oci/systemd/agente-carros-vivo.timer" /etc/systemd/system/
[ -d /etc/logrotate.d ] && install -m 0644 \
    "$DIR_APP/infra/oci/logrotate/agente-carros" /etc/logrotate.d/agente-carros
systemctl daemon-reload

if [ -f /etc/nginx/sites-available/agente-carros ]; then
    ALVO_NGINX=/etc/nginx/sites-available/agente-carros
else
    ALVO_NGINX=/etc/nginx/conf.d/agente-carros.conf
fi
# O certbot edita este arquivo ao emitir o certificado. Sobrescrever aqui
# apagaria o bloco TLS, entao so atualiza quando o certbot ainda nao passou.
if grep -q 'managed by Certbot' "$ALVO_NGINX" 2>/dev/null; then
    info "nginx com TLS gerenciado pelo certbot; arquivo preservado"
else
    install -m 0644 "$DIR_APP/infra/oci/nginx/agente-carros.conf" "$ALVO_NGINX"
    nginx -t && systemctl reload nginx
fi

titulo "Reiniciando"
systemctl restart agente-carros.service

for tentativa in $(seq 1 15); do
    if curl -fsS -m 5 -o /dev/null http://127.0.0.1/_stcore/health; then
        titulo "No ar na revisao ${NOVO:0:8}"
        exit 0
    fi
    sleep 3
done

printf '\033[31m'
titulo "A sonda de saude nao respondeu; revertendo para ${ANTERIOR:0:8}"
printf '\033[0m'
sudo -u "$USUARIO" git -C "$DIR_APP" reset --quiet --hard "$ANTERIOR"
systemctl restart agente-carros.service
erro "publicacao revertida; investigue com: journalctl -u agente-carros -n 80"
