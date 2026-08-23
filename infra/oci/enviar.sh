#!/usr/bin/env bash
#
# Dispara a publicacao a partir da maquina local, por SSH.
#
#   ./infra/oci/enviar.sh                 # usa infra/oci/instancia.env
#   HOST=ubuntu@1.2.3.4 ./infra/oci/enviar.sh
#
# Empurra o ramo para o GitHub e manda o servidor puxar. O servidor nunca
# recebe arquivo por rsync: a unica fonte da verdade e o repositorio, e o que
# esta no ar corresponde sempre a um commit publicado.
#
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$AQUI/instancia.env" ] && . "$AQUI/instancia.env"

HOST="${HOST:-${SSH_HOST:-}}"
CHAVE_SSH="${CHAVE_SSH:-}"
RAMO="${RAMO:-main}"

[ -n "$HOST" ] || {
    echo "erro: defina HOST (usuario@ip) no ambiente ou em infra/oci/instancia.env" >&2
    exit 1
}

SSH=(ssh -o StrictHostKeyChecking=accept-new)
[ -n "$CHAVE_SSH" ] && SSH+=(-i "$CHAVE_SSH")

echo "==> Enviando $RAMO para o GitHub"
git push origin "$RAMO"

echo "==> Publicando em $HOST"
"${SSH[@]}" "$HOST" "sudo RAMO=$RAMO bash /opt/agente-carros/infra/oci/publicar.sh"
