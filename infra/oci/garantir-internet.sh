#!/usr/bin/env bash
#
# Da saida para a internet a uma VCN que nao tem. Roda no CLOUD SHELL.
#
#   bash garantir-internet.sh
#
# Uma VCN criada pelo "Create VCN" simples nasce sem Internet Gateway e com
# tabela de rotas vazia. As instancias recebem IP publico, as portas ficam
# abertas na security list, e nada responde — porque o pacote nao tem por
# onde sair. O sintoma nao aponta para a causa.
#
# Idempotente: reutiliza o gateway que ja existir e nao duplica regra de
# rota. Nao toca em sub-rede que roteia por NAT gateway, que e privada de
# proposito.
#
set -euo pipefail

VCN="${VCN:-vcn-agente-carros}"
COMPARTIMENTO="${COMPARTIMENTO:-${OCI_TENANCY:-}}"

titulo() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
info()   { printf '    %s\n' "$*"; }
ok()     { printf '    \033[32m%s\033[0m\n' "$*"; }
erro()   { printf '\033[31merro: %s\033[0m\n' "$*" >&2; exit 1; }

command -v oci >/dev/null 2>&1 || erro "rode no Cloud Shell"
command -v jq  >/dev/null 2>&1 || erro "jq nao encontrado"
[ -n "$COMPARTIMENTO" ] || erro "defina COMPARTIMENTO"

VCN_ID="$(oci network vcn list --compartment-id "$COMPARTIMENTO" \
    --display-name "$VCN" --query 'data[0].id' --raw-output 2>/dev/null || true)"
[ -n "$VCN_ID" ] && [ "$VCN_ID" != "null" ] || erro "VCN '$VCN' nao encontrada"

titulo "Internet Gateway"
IGW="$(oci network internet-gateway list --compartment-id "$COMPARTIMENTO" \
    --vcn-id "$VCN_ID" --query 'data[0].id' --raw-output 2>/dev/null || true)"
if [ -n "$IGW" ] && [ "$IGW" != "null" ]; then
    ok "ja existe"
else
    info "criando..."
    IGW="$(oci network internet-gateway create --compartment-id "$COMPARTIMENTO" \
        --vcn-id "$VCN_ID" --is-enabled true --display-name "igw-$VCN" \
        --wait-for-state AVAILABLE --query 'data.id' --raw-output)"
    ok "criado"
fi

titulo "Rotas das sub-redes"
ajustadas=0
for subnet in $(oci network subnet list --compartment-id "$COMPARTIMENTO" \
        --vcn-id "$VCN_ID" --query 'data[].id' --raw-output | jq -r '.[]? // empty' 2>/dev/null \
        || oci network subnet list --compartment-id "$COMPARTIMENTO" --vcn-id "$VCN_ID" \
           --query 'data[].id' --raw-output | tr -d '[]", ' | grep -v '^$'); do

    nome="$(oci network subnet get --subnet-id "$subnet" \
        --query 'data."display-name"' --raw-output)"
    rt="$(oci network subnet get --subnet-id "$subnet" \
        --query 'data."route-table-id"' --raw-output)"
    regras="$(oci network route-table get --rt-id "$rt" --query 'data."route-rules"')"

    if printf '%s' "$regras" | grep -q "ocid1.natgateway"; then
        info "$nome: roteia por NAT gateway, e privada. Preservada."
        continue
    fi
    if printf '%s' "$regras" | grep -q "ocid1.internetgateway"; then
        ok "$nome: ja tem rota para a internet"
        continue
    fi

    # A atualizacao substitui a lista inteira, entao as regras existentes
    # sao lidas e a nova e acrescentada a elas.
    nova="$(printf '%s' "$regras" | jq -c --arg igw "$IGW" \
        '. + [{"destination":"0.0.0.0/0","destinationType":"CIDR_BLOCK","networkEntityId":$igw}]')"
    oci network route-table update --rt-id "$rt" --route-rules "$nova" --force >/dev/null
    ok "$nome: rota 0.0.0.0/0 para o Internet Gateway acrescentada"
    ajustadas=$((ajustadas + 1))
done

titulo "Pronto"
info "sub-redes ajustadas: $ajustadas"
info "A mudanca vale de imediato; instancia existente nao precisa reiniciar."
