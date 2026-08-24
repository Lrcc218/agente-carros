#!/usr/bin/env bash
#
# Diz por que a instancia nao responde. Roda no CLOUD SHELL da OCI.
#
#   bash diagnosticar-rede.sh              # procura a instancia 'agente-carros'
#   NOME=outra-instancia bash diagnosticar-rede.sh
#
# A OCI filtra trafego em dois lugares, e o esquecido e sempre um deles: a
# security list da VCN e o firewall dentro da maquina. Este script cobre o
# primeiro, que e o unico verificavel de fora.
#
set -euo pipefail

NOME="${NOME:-agente-carros}"
COMPARTIMENTO="${COMPARTIMENTO:-${OCI_TENANCY:-}}"

titulo() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
info()   { printf '    %s\n' "$*"; }
falta()  { printf '    \033[31m%s\033[0m\n' "$*"; }
ok()     { printf '    \033[32m%s\033[0m\n' "$*"; }

command -v oci >/dev/null 2>&1 || { echo "rode no Cloud Shell"; exit 1; }
[ -n "$COMPARTIMENTO" ] || { echo "defina COMPARTIMENTO"; exit 1; }

titulo "Instancia"
INSTANCIA="$(oci compute instance list --compartment-id "$COMPARTIMENTO" \
    --display-name "$NOME" --query 'data[0].id' --raw-output 2>/dev/null || true)"
[ -n "$INSTANCIA" ] && [ "$INSTANCIA" != "null" ] || { falta "instancia '$NOME' nao encontrada"; exit 1; }

ESTADO="$(oci compute instance get --instance-id "$INSTANCIA" \
    --query 'data."lifecycle-state"' --raw-output)"
info "estado: $ESTADO"
[ "$ESTADO" = "RUNNING" ] || falta "a instancia nao esta RUNNING"

VNIC="$(oci compute instance list-vnics --instance-id "$INSTANCIA")"
IP_PUBLICO="$(printf '%s' "$VNIC" | grep -o '"public-ip": "[^"]*"' | head -1 | cut -d'"' -f4)"
SUBNET="$(printf '%s' "$VNIC" | grep -o '"subnet-id": "[^"]*"' | head -1 | cut -d'"' -f4)"
[ -n "$IP_PUBLICO" ] && ok "ip publico: $IP_PUBLICO" || falta "sem IP publico atribuido"

titulo "Sub-rede"
DADOS="$(oci network subnet get --subnet-id "$SUBNET")"
info "nome: $(printf '%s' "$DADOS" | grep -o '"display-name": "[^"]*"' | head -1 | cut -d'"' -f4)"
PROIBE="$(printf '%s' "$DADOS" | grep -o '"prohibit-public-ip-on-vnic": [a-z]*' | cut -d' ' -f2)"
[ "$PROIBE" = "false" ] && ok "aceita IP publico" || falta "sub-rede privada: proibe IP publico"

titulo "Rota para a internet"
ROTA="$(printf '%s' "$DADOS" | grep -o '"route-table-id": "[^"]*"' | head -1 | cut -d'"' -f4)"
if oci network route-table get --rt-id "$ROTA" | grep -q "internetgateway"; then
    ok "rota 0.0.0.0/0 apontando para um Internet Gateway"
else
    falta "a tabela de rotas NAO aponta para um Internet Gateway"
    info "e o que faz a sub-rede parecer publica sem ser alcancavel"
fi

titulo "Portas liberadas na security list"
LISTAS="$(printf '%s' "$DADOS" | grep -A20 '"security-list-ids"' | grep -o 'ocid1.securitylist[^"]*')"
PORTAS=""
for lista in $LISTAS; do
    REGRAS="$(oci network security-list get --security-list-id "$lista")"
    ABERTAS="$(printf '%s' "$REGRAS" | grep -o '"max": [0-9]*' | grep -o '[0-9]*' | sort -un | tr '\n' ' ')"
    TODAS=$(printf '%s' "$REGRAS" | grep -c '"protocol": "all"' || true)
    info "$(basename "$lista" | cut -c1-24)...: portas TCP [${ABERTAS:-nenhuma}]"
    PORTAS="$PORTAS $ABERTAS"
    [ "$TODAS" -gt 0 ] && info "  (ha regra liberando todos os protocolos)"
done

echo
for porta in 22 80 443; do
    if printf '%s' "$PORTAS" | grep -qw "$porta"; then
        ok "porta $porta: liberada"
    else
        falta "porta $porta: FECHADA na security list"
    fi
done

titulo "Conclusao"
if ! printf '%s' "$PORTAS" | grep -qw 22; then
    falta "A porta 22 esta fechada. Sem ela nao ha SSH."
    info "Console -> Networking -> Virtual cloud networks -> sua VCN ->"
    info "Subnets -> sub-rede publica -> Security Lists -> a lista ->"
    info "Add Ingress Rules: origem 0.0.0.0/0, TCP, porta de destino 22"
elif ! printf '%s' "$PORTAS" | grep -qw 80; then
    falta "SSH ok, mas a porta 80 esta fechada: a aplicacao nao sera alcancavel."
else
    ok "A rede esta correta. Se ainda nao conecta, a instancia pode estar"
    info "terminando de subir: espere um minuto e tente de novo."
fi
