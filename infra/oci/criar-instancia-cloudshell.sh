#!/usr/bin/env bash
#
# Cria a instancia insistindo ate haver capacidade. Roda no CLOUD SHELL da OCI.
#
# O Cloud Shell ja vem com a OCI CLI instalada e autenticada como voce, o que
# dispensa instalar ferramenta e configurar credencial. Este script descobre
# sozinho compartimento, sub-rede, dominio de disponibilidade e imagem — nao ha
# OCID para procurar a mao.
#
#   bash criar-instancia-cloudshell.sh
#
# Por que um laco: os shapes Ampere A1 gratuitos vivem esgotados, e a API
# responde "Out of host capacity". Nao ha fila nem reserva; consegue quem
# estiver pedindo no instante em que alguem libera. Entao o script pede de
# novo, em intervalo fixo, ate passar.
#
set -euo pipefail

NOME="${NOME:-agente-carros}"
VCN="${VCN:-vcn-agente-carros}"
SHAPE="${SHAPE:-VM.Standard.A1.Flex}"
OCPUS="${OCPUS:-1}"
MEMORIA_GB="${MEMORIA_GB:-6}"
BOOT_GB="${BOOT_GB:-50}"
CHAVE_PUB="${CHAVE_PUB:-$HOME/agente-carros.pub}"
INTERVALO="${INTERVALO:-180}"
CLOUD_INIT="${CLOUD_INIT:-}"

titulo() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
info()   { printf '    %s\n' "$*"; }
erro()   { printf '\033[31merro: %s\033[0m\n' "$*" >&2; exit 1; }

command -v oci >/dev/null 2>&1 || erro "OCI CLI ausente; rode este script no Cloud Shell"
[ -f "$CHAVE_PUB" ] || erro "chave publica nao encontrada em $CHAVE_PUB"
# Arquivo vazio ou sem formato de chave passa despercebido e produz uma
# instancia sem acesso SSH — que so se descobre na hora de conectar, depois
# de a capacidade ter sido conseguida.
grep -qE '^(ssh-(ed25519|rsa)|ecdsa-sha2-) [A-Za-z0-9+/]{20,}' "$CHAVE_PUB" \
    || erro "$CHAVE_PUB nao contem uma chave publica valida. Grave assim:
    echo 'ssh-ed25519 AAAA... comentario' > $CHAVE_PUB"

# No Cloud Shell a tenancy vem pronta no ambiente. O compartimento raiz tem o
# mesmo OCID da tenancy.
COMPARTIMENTO="${COMPARTIMENTO:-${OCI_TENANCY:-}}"
[ -n "$COMPARTIMENTO" ] || erro "defina COMPARTIMENTO com o OCID do compartimento"

titulo "Descobrindo os recursos"

VCN_ID="$(oci network vcn list --compartment-id "$COMPARTIMENTO" \
    --display-name "$VCN" --query 'data[0].id' --raw-output 2>/dev/null || true)"
[ -n "$VCN_ID" ] && [ "$VCN_ID" != "null" ] || erro "VCN '$VCN' nao encontrada neste compartimento"
info "vcn: $VCN"

# Sub-rede publica e a que tem ROTA para um Internet Gateway. O campo
# "prohibit-public-ip-on-vnic" nao serve para decidir: uma sub-rede pode
# aceitar IP publico e mesmo assim nao ter saida, e a instancia nasce com
# endereco que nao responde a nada - falha silenciosa e cara de achar.
SUBNET_ID=""
for candidata in $(oci network subnet list --compartment-id "$COMPARTIMENTO" \
        --vcn-id "$VCN_ID" --query 'data[].id' --raw-output | tr -d '[]", ' | grep -v '^$'); do
    rota="$(oci network subnet get --subnet-id "$candidata" \
        --query 'data."route-table-id"' --raw-output)"
    if oci network route-table get --rt-id "$rota" 2>/dev/null | grep -q "ocid1.internetgateway"; then
        SUBNET_ID="$candidata"
        break
    fi
done
[ -n "$SUBNET_ID" ] || erro "nenhuma sub-rede da VCN '$VCN' tem rota para um Internet Gateway"
info "sub-rede publica: rota para Internet Gateway confirmada"

IMAGEM_ID="$(oci compute image list --compartment-id "$COMPARTIMENTO" \
    --operating-system "Canonical Ubuntu" --operating-system-version "24.04" \
    --shape "$SHAPE" --sort-by TIMECREATED --sort-order DESC \
    --query 'data[0].id' --raw-output 2>/dev/null || true)"
[ -n "$IMAGEM_ID" ] && [ "$IMAGEM_ID" != "null" ] || erro "imagem Ubuntu 24.04 para $SHAPE nao encontrada"
info "imagem: Ubuntu 24.04 (aarch64), a mais recente"

mapfile -t DOMINIOS < <(oci iam availability-domain list --compartment-id "$COMPARTIMENTO" \
    --query 'data[].name' --raw-output | tr -d '[]", ' | grep -v '^$')
[ "${#DOMINIOS[@]}" -gt 0 ] || erro "nenhum dominio de disponibilidade encontrado"
info "dominios de disponibilidade: ${#DOMINIOS[@]}"

ARGUMENTOS=(
    --compartment-id "$COMPARTIMENTO"
    --subnet-id "$SUBNET_ID"
    --image-id "$IMAGEM_ID"
    --display-name "$NOME"
    --shape "$SHAPE"
    --shape-config "{\"ocpus\":$OCPUS,\"memoryInGBs\":$MEMORIA_GB}"
    --boot-volume-size-in-gbs "$BOOT_GB"
    --assign-public-ip true
    --ssh-authorized-keys-file "$CHAVE_PUB"
)
# Sem fault domain de proposito: fixar um reduz onde a OCI pode alocar, e a
# propria mensagem de erro sugere retirar a restricao.
[ -n "$CLOUD_INIT" ] && [ -f "$CLOUD_INIT" ] && ARGUMENTOS+=(--user-data-file "$CLOUD_INIT")

titulo "Tentando criar — Ctrl+C interrompe"
info "$SHAPE, $OCPUS OCPU, $MEMORIA_GB GB, boot $BOOT_GB GB"
info "intervalo entre rodadas: ${INTERVALO}s"

tentativa=0
while :; do
    tentativa=$((tentativa + 1))
    for dominio in "${DOMINIOS[@]}"; do
        printf '[%s] tentativa %d em %s... ' "$(date '+%H:%M:%S')" "$tentativa" "$dominio"
        if saida="$(oci compute instance launch "${ARGUMENTOS[@]}" \
                    --availability-domain "$dominio" --wait-for-state RUNNING 2>&1)"; then
            echo "conseguiu."
            OCID="$(printf '%s' "$saida" | grep -o '"id": "ocid1.instance[^"]*"' | head -1 | cut -d'"' -f4)"
            IP="$(oci compute instance list-vnics --instance-id "$OCID" \
                  --query 'data[0]."public-ip"' --raw-output 2>/dev/null || true)"
            titulo "Instancia no ar"
            info "ip publico: ${IP:-consulte no console}"
            echo
            info "Proximos passos, do seu terminal:"
            info "  ssh -i ~/.ssh/oci_agente_carros ubuntu@${IP:-<ip>}"
            info "  git clone --depth 1 https://github.com/Lrcc218/agente-carros.git /tmp/ac"
            info "  sudo bash /tmp/ac/infra/oci/provisionar.sh"
            exit 0
        fi

        if printf '%s' "$saida" | grep -qi 'out of host capacity\|OutOfCapacity'; then
            echo "sem capacidade."
        elif printf '%s' "$saida" | grep -qi 'LimitExceeded\|limit.*exceeded'; then
            echo "limite da conta atingido."
            printf '%s\n' "$saida" >&2
            erro "isto nao e falta de capacidade: confira Limits, Quotas and Usage no console"
        else
            echo "falhou."
            printf '%s\n' "$saida" >&2
            erro "a falha nao foi de capacidade; corrija antes de repetir"
        fi
    done
    sleep "$INTERVALO"
done
