# Deploy do Portal das Federações na VPS da FEJEPE

Primeira publicação da stack PostgreSQL (ADR-008) em `federacoes.portalfejepe.cloud`,
numa VPS que **já roda produção**: a API da fase 1 (`api.portalfejepe.cloud`, projeto
`projetos` em `/root/projetos`) e o n8n (`/root/n8n`). Nada aqui toca nesses dois.

Desenho: código em `/opt/portal-federacoes/releases/<versão>`, link `atual` para a
versão no ar, `.env.prod` fora das versões. Projeto Compose `portal-federacoes`.
Só o frontend publica porta, e só em `127.0.0.1:8080`. O nginx do host recebe o
subdomínio e o certbot emite o certificado. Banco em volume nomeado
(`portal-federacoes_portal_postgres`), independente da pasta da versão.

Em todos os comandos abaixo, `PF` é este prefixo (copie para o shell do servidor):

```bash
PF='docker compose -p portal-federacoes -f docker-compose.yml -f infra/deploy/vps-fejepe/compose.prod.yml --env-file /opt/portal-federacoes/.env.prod'
```

## 0. No Mac: gerar o pacote

```bash
cd ~/Documents/TCC/projetos
git switch feat/analise-do-mes-deploy-vps && git pull
git tag -a v2026.11.17 -m "Primeira publicação na VPS da FEJEPE"
git push origin v2026.11.17
infra/deploy/vps-fejepe/pacote.sh v2026.11.17 /tmp
scp /tmp/portal-federacoes-v2026.11.17.tar.gz root@<IP-DA-VPS>:/tmp/
```

Anote o SHA-256 que o `pacote.sh` imprimiu.

## 1. No servidor: registrar o estado antes

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | tee /root/antes-portal-federacoes.txt
curl -s -o /dev/null -w 'n8n %{http_code}\n'  http://127.0.0.1:5678/ | tee -a /root/antes-portal-federacoes.txt
curl -s -o /dev/null -w 'api %{http_code}\n'  http://127.0.0.1:8000/ | tee -a /root/antes-portal-federacoes.txt
nginx -t
free -h && df -h /
```

## 2. Instalar a versão e gerar o `.env.prod`

```bash
sha256sum /tmp/portal-federacoes-v2026.11.17.tar.gz      # tem de bater com o do Mac
mkdir -p /opt/portal-federacoes/releases /opt/portal-federacoes/aceites
tar -xzf /tmp/portal-federacoes-v2026.11.17.tar.gz -C /opt/portal-federacoes/releases
ln -sfn /opt/portal-federacoes/releases/portal-federacoes-v2026.11.17 /opt/portal-federacoes/atual
cd /opt/portal-federacoes/atual
python3 scripts/configurar_docker.py --producao \
  --dominio federacoes.portalfejepe.cloud --destino /opt/portal-federacoes/.env.prod
ls -l /opt/portal-federacoes/.env.prod                   # -rw------- root
```

O gerador cria senhas aleatórias e nunca sobrescreve. **Guarde uma cópia do
`.env.prod` fora da VPS** (gerenciador de senhas): sem ele, os backups não
reconstroem as contas do banco.

## 3. Aceite no próprio servidor (sem tocar em produção)

```bash
cd /opt/portal-federacoes/atual
infra/deploy/vps-fejepe/aceite.sh /opt/portal-federacoes/aceites
```

Roda num projeto separado (`portal-federacoes-aceite`, porta 127.0.0.1:8090, volume
próprio) e apaga só esse projeto no fim. O primeiro build leva alguns minutos.
Precisa terminar em `RESULTADO: APROVADO`. Guarde o relatório
`/opt/portal-federacoes/aceites/aceite-*.txt` como evidência.

## 4. Subir produção

```bash
cd /opt/portal-federacoes/atual
$PF up -d --build --wait
$PF ps
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/healthz          # 200
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/api/v1/auth/me   # 401
```

## 5. Criar o seu operador

```bash
cd /opt/portal-federacoes/atual
$PF run --rm -it migrate python -m scripts.criar_operador_postgres \
  --email SEU-EMAIL --nome 'Seu nome' --federacao 12
```

A senha (mínimo 12 caracteres) é digitada de forma oculta. Não há conta padrão.

## 6. DNS e nginx do host

1. No painel de DNS de `portalfejepe.cloud`, crie o registro **A** `federacoes` →
   IP da VPS. Confira com `dig +short federacoes.portalfejepe.cloud`.
2. Instale o site, sem mexer nos outros:

```bash
cd /opt/portal-federacoes/atual
PORTAL_DOMAIN=federacoes.portalfejepe.cloud FRONTEND_PORT=8080 \
  envsubst '${PORTAL_DOMAIN} ${FRONTEND_PORT}' \
  < infra/deploy/vps-fejepe/nginx-portal-federacoes.conf.template \
  > /etc/nginx/sites-available/portal-federacoes
ln -s /etc/nginx/sites-available/portal-federacoes /etc/nginx/sites-enabled/portal-federacoes
nginx -t && systemctl reload nginx
certbot --nginx -d federacoes.portalfejepe.cloud     # aceite o redirecionamento HTTP→HTTPS
nginx -t && systemctl reload nginx
```

## 7. Smoke externo (do Mac)

```bash
curl -sI http://federacoes.portalfejepe.cloud | head -1                       # 301
curl -s -o /dev/null -w '%{http_code}\n' https://federacoes.portalfejepe.cloud/healthz          # 200
curl -s -o /dev/null -w '%{http_code}\n' https://federacoes.portalfejepe.cloud/api/v1/auth/me   # 401
```

No navegador: abrir `https://federacoes.portalfejepe.cloud`, entrar com o operador,
conferir que cai na Análise do mês (vazia até a importação).

## 8. Importar os dados

O banco de produção começa vazio. Como operador, em **Administração → Importação**,
envie a exportação nacional do Portal BJ (`monitoring_acumulated_...xlsx`): primeiro
a simulação, confira os avisos, depois grave. Até 20 MB por arquivo.

## 9. Conferir que nada mais mudou

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
curl -s -o /dev/null -w 'n8n %{http_code}\n' http://127.0.0.1:5678/
curl -s -o /dev/null -w 'api %{http_code}\n' http://127.0.0.1:8000/
diff <(grep -E '^(n8n|api)' /root/antes-portal-federacoes.txt) \
     <(printf 'n8n %s\napi %s\n' "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5678/)" "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/)")
```

`n8n-n8n-1` e `projetos-backend-1` precisam continuar com o mesmo status de antes.

## 10. Backup

```bash
install -m 644 /opt/portal-federacoes/atual/infra/deploy/vps-fejepe/portal-federacoes-backup.cron \
  /etc/cron.d/portal-federacoes-backup
/opt/portal-federacoes/atual/infra/deploy/vps-fejepe/backup.sh
/opt/portal-federacoes/atual/infra/deploy/vps-fejepe/restaurar-teste.sh
```

O backup roda todo dia às 03:15, guarda 14 dias em `/var/backups/portal-federacoes`
e registra em `/var/log/portal-federacoes-backup.log`. A restauração de teste sobe
um PostgreSQL descartável, compara as contagens das tabelas principais com produção
e remove só esse container.

**Cópia fora da VPS** (a mais simples, sem credencial nova): do Mac, periodicamente,

```bash
rsync -av --ignore-existing root@<IP-DA-VPS>:/var/backups/portal-federacoes/ ~/Backups/portal-federacoes/
```

Alternativa para a FEJEPE: `rclone` para um Drive da federação, configurado por quem
tem a conta (fora do escopo deste pacote).

## Rollback

Para tirar o portal do ar sem perder dados:

```bash
cd /opt/portal-federacoes/atual && $PF down          # SEM -v: o volume do banco fica
rm /etc/nginx/sites-enabled/portal-federacoes
nginx -t && systemctl reload nginx
```

Para voltar à versão anterior (as imagens antigas somem com a limpeza diária das
00:40, por isso o rollback reconstrói a partir do pacote):

```bash
ln -sfn /opt/portal-federacoes/releases/portal-federacoes-<versão-anterior> /opt/portal-federacoes/atual
cd /opt/portal-federacoes/atual && $PF up -d --build --wait
```

Migrações SQL não são desfeitas pelo rollback; o código anterior precisa ser
compatível com o schema atual. Mantenha só as duas últimas versões em `releases/`.

## Atualizar para uma nova versão

Repita o passo 0 com a nova tag, depois no servidor: passo 2 (sem gerar `.env.prod`
de novo), passo 3 (aceite), backup manual (`backup.sh`) e então
`cd /opt/portal-federacoes/atual && $PF up -d --build --wait`. As migrações novas são
aplicadas pelo serviço `migrate` com ledger; as antigas não são reaplicadas.

## Ligar o resumo por IA e o Nexo (opcional)

Sem `IA_*`, a Análise do mês mostra o resumo em frases fixas e o Nexo fica
indisponível. Para ligar, edite `/opt/portal-federacoes/.env.prod`
(`IA_MODELO`, `IA_API_KEY`) e rode `$PF up -d --wait backend`. Há custo por chamada
no provedor; o resumo do mês faz uma chamada por federação e mês.

## Nunca faça neste servidor

- Rodar qualquer comando dentro de `/root/projetos` ou `/root/n8n`.
- Usar Compose sem `-p portal-federacoes` (a única exceção é o `aceite.sh`).
- `docker system prune`, `docker volume prune` ou `down -v` em produção.
- Editar os sites `api`, `default` ou `n8n` do nginx.
- `systemctl reload nginx` sem `nginx -t` antes.
- Ativar `ufw` sem liberar o SSH antes.
- Atualizar Docker ou o sistema, ou reiniciar a VPS, sem combinar com a FEJEPE.

## Para a FEJEPE decidir (fora do caminho do TCC)

As portas **5678 (n8n)** e **8000 (API da fase 1)** estão publicadas em `0.0.0.0` e
acessíveis em HTTP direto pelo IP, contornando o nginx e o TLS. Recomendação: depois
de confirmar que nada acessa essas portas pelo IP, fechá-las no firewall do painel da
Hostinger, deixando só 22, 80 e 443.

## Verificação local feita em 17/11/2026 (Mac, Docker Compose 5.1.1)

- `compose config --quiet` com o exemplo sintético: válido; serviços padrão
  `postgres migrate backend frontend`; única porta `127.0.0.1:8080`; limites 1 GB /
  1 GB / 2 GB / 256 MB.
- Template do nginx renderizado e validado com `nginx -t` em `nginx:alpine`.
- `shellcheck` sem avisos no nível *warning*.
- `backup.sh` e `restaurar-teste.sh` contra a stack local: dump válido e 8 tabelas com
  contagens iguais; container de teste removido; volume local intacto.
- `aceite.sh` de ponta a ponta: suíte com 979 testes (0 falhas, 0 pulados) e 14/14
  checagens na stack de produção com volume vazio; projeto de aceite removido.

## Decisões tomadas sem consulta

- **Aceite pela suíte existente**: os itens 2–6 do roteiro já são cobertos por testes
  contra PostgreSQL real (RLS sem filtro Python, convite, desativação, importação
  idempotente, Nexo falso). O aceite roda essa suíte no projeto isolado em vez de
  reescrever o roteiro em shell; a parte B cobre volume vazio, operador e reinício.
- **`/healthz` em vez de `/health`** no smoke externo: o nginx do frontend só repassa
  `/api/` à API; `/healthz` responde do próprio frontend.
- **Cabeçalhos de proxy**: o host reescreve `X-Forwarded-*` (não anexa); o nginx do
  frontend só aceita `https` como protocolo repassado; o Uvicorn confia em proxies só
  na rede Docker (`FORWARDED_ALLOW_IPS=*`), já que a API não tem porta no host.
- **`client_max_body_size 21m`** e timeouts de 180 s: o limite da API é 20 MB
  (`UPLOAD_MAX_MB`) e o nginx do frontend espera 120 s pela importação.
- **Backup às 03:15**, fora da limpeza de imagens das 00:40.
