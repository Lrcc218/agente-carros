# Deploy na Oracle Cloud Infrastructure

Runbook do deploy do Consultor de carros numa instância Always Free da OCI.
Do zero ao app no ar, com os tropeços conhecidos apontados onde eles
acontecem.

- [O que a camada gratuita entrega](#o-que-a-camada-gratuita-entrega)
- [Desenho do servidor](#desenho-do-servidor)
- [ARM: as dependências rodam?](#arm-as-dependências-rodam)
- [Antes de começar](#antes-de-começar)
- [Passo a passo](#passo-a-passo)
- [HTTPS](#https)
- [Operação do dia a dia](#operação-do-dia-a-dia)
- [Registro de execução no servidor](#registro-de-execução-no-servidor)
- [Reivindicação por ociosidade](#reivindicação-por-ociosidade)
- [Quando dá errado](#quando-dá-errado)
- [Por que não Docker](#por-que-não-docker)
- [Custo](#custo)

## O que a camada gratuita entrega

| Recurso | Always Free | O que este projeto usa |
| --- | --- | --- |
| Computação ARM Ampere A1 | 4 OCPU e 24 GB, sem prazo | 1 OCPU e 6 GB |
| Block storage | 200 GB | 50 GB de boot |
| Tráfego de saída | 10 TB/mês | desprezível |
| IP público efêmero | incluso | 1 |

O app assenta em torno de 1 GB de memória residente com o índice FAISS
carregado. A cota sobra: o restante das 4 OCPUs fica livre para outra coisa.

As duas VMs AMD micro, também gratuitas, têm 1 GB de RAM cada e **não servem**
— LangChain e FAISS não cabem.

## Desenho do servidor

```
internet
   |
   :80 / :443   nginx            proxy reverso, TLS, WebSocket
   |
   :8501        streamlit        systemd: agente-carros.service
                                 usuário `agente`, sem shell
   |
   /opt/agente-carros            checkout do repositório + .venv
   /etc/agente-carros/ambiente   chave de API, 0640 root:agente
```

O Streamlit escuta **apenas em 127.0.0.1**. Nada além do nginx alcança a porta
8501, mesmo de dentro da VM. O segredo fica fora do diretório do aplicativo e
fora do repositório, num arquivo que o processo lê e o usuário comum não.

Os dados são versionados: catálogo, preços e índice FAISS chegam pelo `git
clone`. O servidor **não** roda script de coleta nem gera embeddings — a
separação entre tempo de construção e tempo de execução, que o
[README](../README.md#tempo-de-construcao-e-tempo-de-execucao) descreve, é o
que torna esse deploy trivial.

## ARM: as dependências rodam?

O Always Free generoso é o **ARM** Ampere A1 — as instâncias x86 gratuitas têm
1 GB e não servem. Então a pergunta que decide o deploy inteiro é se as
dependências compiladas têm wheel para `aarch64`. Verificado contra o PyPI,
para as versões fixadas no `requirements.txt` e o Python 3.12 do Ubuntu 24.04:

| Pacote | Wheel aarch64 |
| --- | --- |
| `faiss-cpu==1.15.0` | sim, `cp310-abi3-manylinux_2_28_aarch64` (o abi3 cobre 3.10+) |
| `pandas==3.0.5` | sim, `cp312-manylinux_2_28_aarch64` |
| `pillow==12.3.0` | sim, `cp310-manylinux_2_28_aarch64` |
| `pydantic-core` | sim, `cp312-manylinux2014_aarch64` |
| `python-docx`, `openpyxl`, `python-pptx`, `beautifulsoup4` | Python puro |
| Demais | Python puro (`py3-none-any`) |

Nenhuma compilação a partir do fonte, portanto. O `provisionar.sh` importa
`faiss`, `streamlit` e `pandas` logo depois do `pip install` e falha ali,
com mensagem clara, se algum dia isso mudar — melhor do que descobrir pelo
serviço reiniciando em laço.

Se um dia faltar wheel para a versão fixada, a saída é soltar o pin do pacote
em questão e refazer o `pip install`. As versões estão travadas por
reprodutibilidade, não por incompatibilidade conhecida.

## Antes de começar

1. **Conta na OCI** — cadastro em [oracle.com/cloud/free](https://www.oracle.com/cloud/free/).
   Exige cartão para verificação de identidade, com cobrança de cerca de US$ 1
   estornada. Escolha a região mais próxima **com atenção: a região da tenancy
   é definitiva**, não se troca depois.
2. **Chave SSH**

   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/oci_agente_carros -C agente-carros
   ```

3. **Rede** — uma VCN com sub-rede pública. O assistente *Create VCN with
   Internet Connectivity* do console cria tudo o que é preciso.
4. **Chave de API do Gemini** — [aistudio.google.com/apikey](https://aistudio.google.com/apikey),
   gratuita e sem cartão.
5. **OCI CLI**, apenas se for usar o `criar-instancia.sh`:

   ```bash
   bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"
   oci setup config
   ```

## Passo a passo

### 1. Criar a instância

**Pelo console** — Compute → Instances → Create instance:

| Campo | Valor |
| --- | --- |
| Image | Canonical Ubuntu 24.04 (**aarch64**) |
| Shape | `VM.Standard.A1.Flex`, 1 OCPU, 6 GB |
| Subnet | a sub-rede pública, com *Assign a public IPv4 address* |
| SSH keys | cole `~/.ssh/oci_agente_carros.pub` |
| Boot volume | 50 GB |
| Cloud-init script | conteúdo de [`infra/oci/cloud-init.yaml`](../infra/oci/cloud-init.yaml) |

Com o cloud-init preenchido, a VM já sobe com tudo instalado.

**Pela linha de comando**, com o laço que insiste enquanto não há capacidade:

```bash
cp infra/oci/instancia.env.exemplo infra/oci/instancia.env
$EDITOR infra/oci/instancia.env
./infra/oci/criar-instancia.sh
```

> **`Out of host capacity`.** É o obstáculo mais comum do Always Free em ARM, e
> não indica erro de configuração. Não existe fila: a instância sai para quem
> estiver pedindo no instante em que alguém libera. O script pede de novo a
> cada 3 minutos até passar — pode levar horas ou dias em regiões movimentadas.
>
> As regiões brasileiras têm **um único domínio de disponibilidade**, então
> "tente outro AD" não se aplica aqui: resta insistir.
>
> O caminho mais rápido é o **Cloud Shell**, embutido no console, que já traz a
> OCI CLI instalada e autenticada:
>
> ```bash
> git clone --depth 1 https://github.com/Lrcc218/agente-carros.git ~/ac
> cat > ~/agente-carros.pub    # cole a chave pública e encerre com Ctrl+D
> bash ~/ac/infra/oci/criar-instancia-cloudshell.sh
> ```
>
> O script descobre compartimento, sub-rede, domínio e imagem sozinho — não há
> OCID para procurar. Ele também **não fixa fault domain**, porque restringir o
> domínio reduz onde a OCI pode alocar.
>
> Contas *Pay As You Go* têm prioridade de alocação e continuam pagando zero
> pelos recursos Always Free. Quando a espera se arrasta, é o que resolve.

### 2. Abrir a porta na rede virtual

O filtro da OCI é **duplo**, e esquecer um dos lados é o erro clássico:

- **Security list da VCN** — Networking → Virtual Cloud Networks → sua VCN →
  Security Lists → Default → *Add Ingress Rule*:
  origem `0.0.0.0/0`, IP Protocol `TCP`, porta de destino `80`
  (e `443` depois, se habilitar HTTPS).
- **Firewall da instância** — resolvido por
  [`infra/oci/firewall.sh`](../infra/oci/firewall.sh), que o
  `provisionar.sh` já chama.

As imagens da OCI sobem com a cadeia `INPUT` do iptables fechada, com um
`REJECT` no fim. Por isso o script insere as regras com `-I`, no topo, e não
com `-A`: uma regra depois do `REJECT` é decorativa.

### 3. Provisionar, se não usou o cloud-init

```bash
ssh -i ~/.ssh/oci_agente_carros ubuntu@<ip-publico>
git clone --depth 1 https://github.com/Lrcc218/agente-carros.git /tmp/ac
sudo bash /tmp/ac/infra/oci/provisionar.sh
```

O script instala os pacotes, cria o usuário `agente`, obtém o repositório em
`/opt/agente-carros`, monta o virtualenv, registra o serviço, configura o
nginx e libera o firewall. Rodar de novo é seguro: ele atualiza o que mudou e
preserva o arquivo de segredo.

### 4. Preencher a chave e subir

A chave **não** entra no cloud-init: `user_data` fica legível no console e nos
metadados da instância. Ela é digitada uma vez, no servidor:

```bash
sudo nano /etc/agente-carros/ambiente     # preencha GOOGLE_API_KEY
sudo systemctl start agente-carros
```

### 5. Conferir

```bash
sudo systemctl status agente-carros --no-pager
curl -sf localhost/_stcore/health && echo ok
sudo -u agente /opt/agente-carros/.venv/bin/python \
     /opt/agente-carros/scripts/diagnosticar.py
```

O `diagnosticar.py` confere dados, catálogo, configuração, índice e uma
chamada real ao provedor. Com tudo verde, abra `http://<ip-publico>/`.

## HTTPS

Opcional, e o Let's Encrypt **não emite certificado para endereço IP**, então
é preciso um domínio. Um subdomínio gratuito do
[DuckDNS](https://www.duckdns.org) apontando para o IP resolve.

```bash
sudo DOMINIO=consultor-carros.duckdns.org EMAIL=voce@exemplo.com \
     bash /opt/agente-carros/infra/oci/habilitar-https.sh
```

O script libera a 443, instala o certbot, ajusta o `server_name`, emite o
certificado, força o redirecionamento e deixa a renovação no `certbot.timer`.
Abra a 443 também na security list da VCN.

## Operação do dia a dia

Publicar uma versão nova, da máquina local:

```bash
./infra/oci/enviar.sh
```

Empurra o ramo para o GitHub e manda o servidor puxar. O servidor nunca recebe
arquivo solto: a única fonte é o repositório, e o que está no ar corresponde
sempre a um commit publicado. Se a sonda de saúde não responder depois do
restart, o `publicar.sh` **volta sozinho para a revisão anterior** em vez de
deixar o ar caído.

| Tarefa | Comando |
| --- | --- |
| Estado | `sudo systemctl status agente-carros` |
| Logs ao vivo | `sudo journalctl -u agente-carros -f` |
| Reiniciar | `sudo systemctl restart agente-carros` |
| Publicar (no servidor) | `sudo bash /opt/agente-carros/infra/oci/publicar.sh` |
| Trocar a chave | editar `/etc/agente-carros/ambiente` e reiniciar |
| Logs do nginx | `sudo tail -f /var/log/nginx/agente-carros.error.log` |
| Memória em uso | `systemctl show agente-carros -p MemoryCurrent` |
| Relatório de uso | `sudo -u agente /opt/agente-carros/.venv/bin/python /opt/agente-carros/scripts/relatorio_execucoes.py` |
| Respostas mal avaliadas | o mesmo comando com `--ruins` |

Atualizar preços da FIPE e da ANP continua sendo trabalho de máquina local:
rodar os scripts, conferir o diff, commitar, `./infra/oci/enviar.sh`. O
servidor só lê.

## Registro de execução no servidor

O agente grava uma linha de JSON por pergunta respondida. No servidor esse
registro fica em `/var/log/agente-carros/`, fora do diretório da aplicação, para
sobreviver a um redeploy:

- a unidade do systemd declara `LogsDirectory=agente-carros`, o que cria o
  diretório com o dono correto sem precisar de `mkdir` no provisionamento;
- `infra/oci/logrotate/agente-carros` mantém 30 dias de histórico comprimido,
  para o acervo não crescer sem limite num disco de 50 GB;
- `DIR_REGISTROS=/var/log/agente-carros` no arquivo de ambiente aponta a
  aplicação para lá.

O relatório é a forma de saber se o agente está sendo útil de verdade — quais
perguntas não encontram material, o que foi avaliado com 👎, quanto ele demora:

```bash
sudo -u agente /opt/agente-carros/.venv/bin/python \
     /opt/agente-carros/scripts/relatorio_execucoes.py --dias 7
```

Para desligar o registro por completo, `REGISTRAR_EXECUCOES=0` no ambiente.

## Reivindicação por ociosidade

A Oracle **remove** instâncias Always Free ociosas por 7 dias seguidos — o
critério combina CPU, rede e memória abaixo do limiar. Um app de portfólio sem
visitas se encaixa nesse perfil, e o link do README pode morrer justamente na
semana em que alguém for avaliar o projeto.

Duas saídas:

1. **Migrar a conta para Pay As You Go.** É a correção de verdade: encerra a
   reivindicação e mantém os recursos Always Free gratuitos. Exige atenção
   para não provisionar nada fora da cota.
2. **O temporizador `agente-carros-vivo.timer`**, que acompanha este deploy.
   A cada 30 minutos gera um pouco de CPU e uma requisição de rede. É
   paliativo, não garantia — está desligado por padrão:

   ```bash
   sudo systemctl enable --now agente-carros-vivo.timer
   ```

Enquanto o link importar para a avaliação, vale checá-lo de vez em quando.

## Quando dá errado

| Sintoma | Causa provável |
| --- | --- |
| `Out of host capacity` | Sem ARM livre na região. Insista com o `criar-instancia.sh`; PAYG tem prioridade |
| A página não abre, e `curl localhost` funciona no servidor | Falta o ingress na security list da VCN, ou a regra de iptables |
| A página carrega e trava em `Connecting...` | WebSocket sem upgrade no proxy. Confira o bloco `map` no arquivo do nginx |
| `Chave de API não configurada` | `/etc/agente-carros/ambiente` vazio, ou `PROVEDOR_LLM` sem a variável correspondente |
| Serviço reiniciando em laço | `journalctl -u agente-carros -n 80`; quase sempre chave inválida ou cota do provedor estourada |
| `pip` falha compilando `faiss-cpu` | Falta wheel aarch64 para a versão fixada. Solte o pin do `faiss-cpu` no `requirements.txt` e refaça |
| Resposta corta em ~60 s | `proxy_read_timeout` perdido; o arquivo do nginx usa 3600s |
| Ficou sem memória durante o `pip install` | Shape com menos de 6 GB. Suba a memória ou crie swap |

Estado do cloud-init na primeira subida:

```bash
sudo cloud-init status --long
sudo tail -f /var/log/cloud-init-output.log
```

## Por que não Docker

Uma aplicação, uma VM, um processo. Container acrescentaria build de imagem,
registro e uma camada de rede a depurar, sem resolver nenhum problema que este
deploy tenha. O `systemd` já entrega supervisão, reinício, limite de memória e
isolamento — e o `provisionar.sh` é reproduzível do mesmo jeito.

A escolha se inverteria com mais de um serviço, com necessidade de replicar o
ambiente entre máquinas ou com um pipeline de CI publicando imagens.

## Custo

Zero, dentro do Always Free: 1 OCPU e 6 GB de um teto de 4 e 24, 50 GB de um
teto de 200, tráfego irrelevante perto dos 10 TB.

O que pode gerar cobrança é sair da cota — mais instâncias, load balancer além
do gratuito, IP reservado sobrando. Vale definir um **budget com alerta** em
Billing → Budgets, mesmo que de US$ 1, para saber no primeiro dia se algo
escapou.
