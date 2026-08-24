# infra/oci

Tudo o que sobe o Consultor de carros numa instância Always Free da OCI.

O runbook, com contexto e diagnóstico de falhas, está em
[`docs/DEPLOY.md`](../../docs/DEPLOY.md). Aqui fica só o inventário.

| Arquivo | Onde roda | Para quê |
| --- | --- | --- |
| `criar-instancia-cloudshell.sh` | Cloud Shell da OCI | Mesma coisa, sem instalar nada: descobre compartimento, sub-rede, domínio e imagem sozinho |
| `criar-instancia.sh` | máquina local | Cria a VM pela OCI CLI, insistindo enquanto não há capacidade ARM |
| `cloud-init.yaml` | primeiro boot da VM | Provisiona sozinho, sem SSH |
| `provisionar.sh` | servidor, como root | Instala tudo do zero. Idempotente |
| `firewall.sh` | servidor, como root | Abre 80 e 443 no iptables ou no firewalld |
| `publicar.sh` | servidor, como root | Atualiza a versão, com reversão automática se a saúde falhar |
| `enviar.sh` | máquina local | `git push` e dispara o `publicar.sh` por SSH |
| `habilitar-https.sh` | servidor, como root | Certificado Let's Encrypt e redirecionamento |
| `systemd/agente-carros.service` | servidor | Unidade do app |
| `systemd/agente-carros-vivo.{service,timer}` | servidor | Paliativo contra a reivindicação por ociosidade. Desligado por padrão |
| `nginx/agente-carros.conf` | servidor | Proxy reverso com upgrade de WebSocket |
| `logrotate/agente-carros` | servidor | Rotação do registro de execução, 30 dias |
| `instancia.env.exemplo` | máquina local | Modelo da configuração da tenancy. Copie para `instancia.env` |
| `servidor.env.exemplo` | servidor | Modelo de `/etc/agente-carros/ambiente` |

Nenhum arquivo deste diretório contém segredo. `instancia.env` e
`servidor.env`, os dois que conteriam, estão no `.gitignore` — o que vai para
o repositório são os `.exemplo`.
