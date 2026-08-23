#!/usr/bin/env bash
#
# Cria a instancia Always Free na OCI, insistindo ate haver capacidade.
#
#   cp infra/oci/instancia.env.exemplo infra/oci/instancia.env  # e preencher
#   ./infra/oci/criar-instancia.sh
#
# Por que um laco: os shapes Ampere A1 gratuitos vivem esgotados nas regioes
# movimentadas, e a API responde "Out of host capacity". Nao ha fila nem
# reserva — quem consegue e quem estava pedindo no instante em que alguem
# liberou. Entao o script pede de novo, em intervalo fixo, ate passar.
#
# Exige a OCI CLI configurada:
#   bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"
#   oci setup config
#
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARQ_CONF="$AQUI/instancia.env"

titulo() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
info()   { printf '    %s\n' "$*"; }
erro()   { printf '\033[31merro: %s\033[0m\n' "$*" >&2; exit 1; }

[ -f "$ARQ_CONF" ] || erro "crie $ARQ_CONF a partir de instancia.env.exemplo"
# shellcheck source=/dev/null
. "$ARQ_CONF"

command -v oci >/dev/null 2>&1 || erro "OCI CLI nao encontrada"

for obrigatoria in COMPARTMENT_OCID SUBNET_OCID AVAILABILITY_DOMAIN IMAGE_OCID CHAVE_SSH_PUBLICA; do
    [ -n "${!obrigatoria:-}" ] || erro "preencha $obrigatoria em instancia.env"
done

CHAVE_PUB="${CHAVE_SSH_PUBLICA/#\~/$HOME}"
[ -f "$CHAVE_PUB" ] || erro "chave publica nao encontrada em $CHAVE_PUB"

NOME_INSTANCIA="${NOME_INSTANCIA:-agente-carros}"
SHAPE="${SHAPE:-VM.Standard.A1.Flex}"
OCPUS="${OCPUS:-1}"
MEMORIA_GB="${MEMORIA_GB:-6}"
BOOT_GB="${BOOT_GB:-50}"
INTERVALO_TENTATIVA="${INTERVALO_TENTATIVA:-180}"
MAX_TENTATIVAS="${MAX_TENTATIVAS:-0}"

titulo "Instancia a criar"
info "nome:   $NOME_INSTANCIA"
info "shape:  $SHAPE  ($OCPUS OCPU, $MEMORIA_GB GB, boot $BOOT_GB GB)"
info "AD:     $AVAILABILITY_DOMAIN"
info "espera: ${INTERVALO_TENTATIVA}s entre tentativas"

tentativa=0
while :; do
    tentativa=$((tentativa + 1))
    printf '\n[%s] tentativa %d... ' "$(date '+%H:%M:%S')" "$tentativa"

    saida="$(oci compute instance launch \
        --compartment-id "$COMPARTMENT_OCID" \
        --availability-domain "$AVAILABILITY_DOMAIN" \
        --subnet-id "$SUBNET_OCID" \
        --image-id "$IMAGE_OCID" \
        --display-name "$NOME_INSTANCIA" \
        --shape "$SHAPE" \
        --shape-config "{\"ocpus\":$OCPUS,\"memoryInGBs\":$MEMORIA_GB}" \
        --boot-volume-size-in-gbs "$BOOT_GB" \
        --assign-public-ip true \
        --ssh-authorized-keys-file "$CHAVE_PUB" \
        --user-data-file "$AQUI/cloud-init.yaml" \
        --wait-for-state RUNNING \
        2>&1)" && codigo=0 || codigo=$?

    if [ $codigo -eq 0 ]; then
        echo "conseguiu."
        OCID="$(printf '%s' "$saida" | grep -o '"id": "ocid1.instance[^"]*"' | head -1 | cut -d'"' -f4)"
        titulo "Instancia no ar"
        info "ocid: $OCID"
        IP="$(oci compute instance list-vnics --instance-id "$OCID" \
              --query 'data[0]."public-ip"' --raw-output 2>/dev/null || true)"
        info "ip publico: ${IP:-consulte no console}"
        echo
        info "O cloud-init ainda esta instalando. Em 3 a 5 minutos:"
        info "  ssh -i ${CHAVE_SSH:-~/.ssh/sua_chave} ubuntu@${IP:-<ip>}"
        info "  sudo nano /etc/agente-carros/ambiente   # preencha a chave"
        info "  sudo systemctl start agente-carros"
        echo
        info "Nao esqueca da security list da VCN: ingress TCP 80 de 0.0.0.0/0."
        exit 0
    fi

    if printf '%s' "$saida" | grep -qi 'out of host capacity\|OutOfCapacity\|LimitExceeded'; then
        printf 'sem capacidade.'
    else
        echo "falhou."
        printf '%s\n' "$saida" >&2
        erro "a falha nao foi de capacidade; corrija antes de repetir"
    fi

    if [ "$MAX_TENTATIVAS" -gt 0 ] && [ "$tentativa" -ge "$MAX_TENTATIVAS" ]; then
        erro "limite de $MAX_TENTATIVAS tentativas atingido"
    fi
    printf ' aguardando %ss\n' "$INTERVALO_TENTATIVA"
    sleep "$INTERVALO_TENTATIVA"
done
