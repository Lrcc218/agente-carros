#!/usr/bin/env bash
#
# Abre a porta 80 no firewall DA INSTANCIA.
#
# Atencao: isto e metade do caminho. A OCI filtra em dois lugares, e o
# esquecido e sempre um dos dois:
#
#   1. security list / network security group da VCN  (console ou OCI CLI)
#   2. iptables ou firewalld dentro da instancia      (este script)
#
# As imagens da OCI sobem com a cadeia INPUT fechada. Sem este passo, a porta
# responde no localhost e nao responde de fora, e a suspeita cai injustamente
# sobre a rede da Oracle.
#
set -euo pipefail

PORTAS="${PORTAS:-80 443}"

if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active --quiet firewalld; then
    for porta in $PORTAS; do
        firewall-cmd --permanent --add-port="${porta}/tcp" >/dev/null
    done
    firewall-cmd --reload >/dev/null
    echo "firewalld: portas $PORTAS liberadas"
    exit 0
fi

if command -v iptables >/dev/null 2>&1; then
    for porta in $PORTAS; do
        # A regra tem de entrar ANTES do REJECT final que a imagem da OCI
        # instala no fim da cadeia INPUT, por isso -I e nao -A.
        if ! iptables -C INPUT -p tcp --dport "$porta" -m state --state NEW -j ACCEPT 2>/dev/null; then
            iptables -I INPUT 1 -p tcp --dport "$porta" -m state --state NEW -j ACCEPT
        fi
    done
    if command -v netfilter-persistent >/dev/null 2>&1; then
        netfilter-persistent save >/dev/null
    elif [ -d /etc/iptables ]; then
        iptables-save > /etc/iptables/rules.v4
    else
        echo "aviso: regras aplicadas mas nao persistidas; instale iptables-persistent"
    fi
    echo "iptables: portas $PORTAS liberadas"
    exit 0
fi

echo "aviso: nem firewalld nem iptables encontrados; nada a fazer"
