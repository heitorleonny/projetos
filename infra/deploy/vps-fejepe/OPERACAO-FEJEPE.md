# Operação do Portal das Federações — guia para a FEJEPE

Para quem herdar o sistema. O passo a passo da primeira instalação está em
[DEPLOY-VPS-FEJEPE.md](DEPLOY-VPS-FEJEPE.md).

## Onde fica cada coisa

| O quê | Onde |
|---|---|
| Endereço | `https://federacoes.portalfejepe.cloud` |
| Versão no ar | `/opt/portal-federacoes/atual` (link para `releases/<versão>`) |
| Configuração com senhas | `/opt/portal-federacoes/.env.prod` (permissão 600; cópia guardada fora da VPS) |
| Banco | volume Docker `portal-federacoes_portal_postgres` |
| Backups | `/var/backups/portal-federacoes` (14 dias), log em `/var/log/portal-federacoes-backup.log` |
| Site nginx | `/etc/nginx/sites-available/portal-federacoes` |
| Relatórios de aceite | `/opt/portal-federacoes/aceites` |

Prefixo de todos os comandos (rodar em `/opt/portal-federacoes/atual`):

```bash
PF='docker compose -p portal-federacoes -f docker-compose.yml -f infra/deploy/vps-fejepe/compose.prod.yml --env-file /opt/portal-federacoes/.env.prod'
```

## Tarefas comuns

**Ver se está tudo de pé**

```bash
cd /opt/portal-federacoes/atual && $PF ps
curl -s -o /dev/null -w '%{http_code}\n' https://federacoes.portalfejepe.cloud/healthz   # 200
```

**Ver logs** (os de cada serviço rodam em 3 arquivos de 10 MB)

```bash
$PF logs --tail 200 backend      # ou frontend, postgres
```

**Reiniciar** (não apaga nada)

```bash
$PF restart            # ou só um serviço: $PF restart backend
```

**Criar um administrador**: pelo próprio portal, em Administração → Usuários
(convite com link de uso único, válido por 24 h; o portal não envia e-mail, copie o
link). Só o primeiro operador é criado pela linha de comando:

```bash
$PF run --rm -it migrate python -m scripts.criar_operador_postgres \
  --email EMAIL --nome 'Nome' --federacao 12
```

**Backup manual e teste de restauração**

```bash
infra/deploy/vps-fejepe/backup.sh
infra/deploy/vps-fejepe/restaurar-teste.sh
```

Restaurar **de verdade** sobre produção só com o sistema parado e depois de um backup
novo; peça ajuda antes (não há script para isso de propósito).

**Atualizar para uma nova versão**: seção "Atualizar" do DEPLOY-VPS-FEJEPE.md
(pacote novo, aceite, backup, `$PF up -d --build --wait`).

## Nunca

`down -v`, `docker system prune`, `docker volume prune`, comandos sem
`-p portal-federacoes`, mexer em `/root/projetos` ou `/root/n8n`, editar os sites
`api`, `default` ou `n8n` do nginx, recarregar o nginx sem `nginx -t`.

## Contato

O responsável pelo desenvolvimento, pelo contato indicado no rodapé do portal. Combine
com ele qualquer mudança fora das tarefas acima.
