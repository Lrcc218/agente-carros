#!/usr/bin/env bash
#
# Emite o certificado TLS e passa o site para HTTPS. Roda DENTRO do servidor.
#
#   sudo DOMINIO=consultor-carros.duckdns.org EMAIL=voce@exemplo.com \
#        bash /opt/agente-carros/infra/oci/habilitar-https.sh
#
# Exige um dominio apontando para o IP publico da instancia. O Let's Encrypt
# nao emite certificado para endereco IP, entao HTTP puro no IP e o padrao e
# isto e o passo opcional. Um subdominio gratuito do DuckDNS resolve.
#
set -euo pipefail

DOMINIO="${DOMINIO:-}"
EMAIL="${EMAIL:-}"

[ "$(id -u)" -eq 0 ] || { echo "erro: execute como root" >&2; exit 1; }
[ -n "$DOMINIO" ] || { echo "erro: defina DOMINIO" >&2; exit 1; }
[ -n "$EMAIL" ]   || { echo "erro: defina EMAIL (avisos de expiracao)" >&2; exit 1; }

echo "==> Conferindo se $DOMINIO aponta para esta instancia"
IP_PUBLICO="$(curl -fsS -m 10 https://api.ipify.org || true)"
IP_DOMINIO="$(getent hosts "$DOMINIO" | awk '{print $1}' | head -1 || true)"
if [ -n "$IP_PUBLICO" ] && [ "$IP_PUBLICO" != "$IP_DOMINIO" ]; then
    echo "aviso: $DOMINIO resolve para '${IP_DOMINIO:-nada}', mas o IP daqui e $IP_PUBLICO"
    echo "       o certbot vai falhar na validacao se o DNS ainda nao propagou"
fi

echo "==> Liberando a porta 443"
PORTAS=443 bash "$(dirname "${BASH_SOURCE[0]}")/firewall.sh"
echo "    lembre-se de abrir 443 tambem na security list da VCN"

echo "==> Instalando o certbot"
if command -v apt-get >/dev/null 2>&1; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq certbot python3-certbot-nginx
else
    dnf install -y -q certbot python3-certbot-nginx
fi

echo "==> Ajustando o server_name antes da emissao"
if [ -f /etc/nginx/sites-available/agente-carros ]; then
    ALVO=/etc/nginx/sites-available/agente-carros
else
    ALVO=/etc/nginx/conf.d/agente-carros.conf
fi
sed -i "s/server_name .*/server_name $DOMINIO;/" "$ALVO"
nginx -t && systemctl reload nginx

echo "==> Emitindo o certificado"
certbot --nginx -d "$DOMINIO" --non-interactive --agree-tos -m "$EMAIL" --redirect

systemctl enable --now certbot.timer 2>/dev/null || true

echo
echo "==> Pronto: https://$DOMINIO/"
echo "    renovacao automatica pelo certbot.timer; confira com:"
echo "    systemctl list-timers certbot.timer"
