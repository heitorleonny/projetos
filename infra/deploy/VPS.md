# Portal em VPS + Supabase gerenciado

Guia para Hostinger VPS, AWS EC2 ou uma VM equivalente. `compose.aws.yml` e
`aws.env.example` mantêm os nomes históricos; não dependem de APIs AWS.
O portal roda frontend, API e Caddy na VPS. Banco, Auth e PostgREST ficam no
Supabase gerenciado. Não instalar o template de Supabase self-hosted nesta opção.

## Pré-requisitos e decisões antes da subida

Escolher região, domínio e plano depois de avaliar orçamento e proximidade dos
usuários/Supabase. Ubuntu 24.04 LTS é uma opção comum aos provedores. Instalar
Docker Engine, Buildx, plugin Compose v2 e Python 3. No template Docker da
Hostinger, conferir `docker compose version`: o guia do provedor também mostra
o comando legado, mas este projeto precisa do plugin v2 com `--wait`.

Usar acesso SSH por chave e conta de operação própria; acesso ao socket Docker
tem poderes administrativos. Confirmar acesso antes de restringir SSH. Não
instalar outro proxy que já ocupe 80/443. Na Hostinger, copiar o projeto completo
para a VPS e usar SSH/Compose é o fluxo de referência: colar só o YAML no Docker
Manager não fornece os contextos locais `../../backend` e `../../frontend`.

Não há dimensionamento sob carga realizado. Reservar espaço para sistema,
contextos/builds, cache de imagens, duas versões de recuperação e volumes Caddy.
Como hipótese inicial para piloto, avaliar 2 vCPU/4 GB RAM e 30 GB de SSD livres
antes do build; isso não é requisito medido nem garante a capacidade. Conferir
`df -h`, `free -h`, `docker system df` e `docker stats --no-stream` durante o piloto.

| Item | Hostinger VPS | AWS EC2 |
|---|---|---|
| Sistema | Template Ubuntu/Docker ou instalação oficial | Ubuntu oficial e instalação oficial |
| IP e DNS | Usar IP atribuído estável e conferir após mudança de plano | Reservar endereço estável e conferir associação |
| Firewall | Regras de entrada no painel da VPS | Security Group da instância |
| Disco/recuperação | Conferir disco, snapshot e retenção no plano | Conferir volume EBS, snapshot e retenção |
| Aplicação | Mesmo Compose e Caddy | Mesmo Compose e Caddy |
| Banco/Auth | Mesmo Supabase gerenciado | Mesmo Supabase gerenciado |

## DNS e rede

Criar registro A do domínio para IPv4 da VPS. Adicionar AAAA só se o IPv6 estiver
configurado e realmente alcançável. Conferir resolução antes de pedir certificado.
Para a primeira publicação, apontar DNS diretamente para a VPS, sem proxy adicional.

No firewall do provedor, liberar entrada TCP 80/443 para o público e SSH apenas
para origem do operador; UDP 443 é opcional para HTTP/3. API 8000, nginx e banco
não têm porta pública no Compose. Saída precisa de DNS, HTTPS para Supabase/ACME/
registries/provedor IA e porta da conexão PostgreSQL selecionada no Supabase.
Docker pode contornar regras UFW para portas publicadas: manter proteção no
firewall do provedor e conferir regras Docker, sem depender apenas de UFW.

Caddy recebe HTTPS e encaminha `/api/*` e `/health` diretamente ao backend,
preservando o protocolo externo nos headers. Uvicorn confia nos headers de proxy
na rede Docker (`FORWARDED_ALLOW_IPS=*`); essa confiança pressupõe que a API não
tem porta no host e que só serviços operacionais confiáveis participam da rede.
Não publicar a porta da API ao adaptar o manifesto. SPA vai ao nginx, que gera a
configuração pública sem cache. Caddy renova certificados nos volumes persistentes.

## Preparar e subir

Antes: seguir [README](README.md) para migrações no projeto Supabase novo,
hook, ACL/defaults, SMTP, redirect e operador. Entregar o código completo por
pacote revisado ou checkout autorizado; a árvore local ainda pode ter alterações
sem commit. O build da VPS precisa representar a versão verificada.

Na raiz do monorepo, na VPS:

```sh
docker version
docker compose version
cp infra/deploy/aws.env.example infra/deploy/.env.vps
chmod 600 infra/deploy/.env.vps
# Preencher em editor privado: nunca colar valores em logs ou Git.
python3 infra/deploy/check-env.py --mode vps --env infra/deploy/.env.vps
docker compose --env-file infra/deploy/.env.vps -f infra/deploy/compose.aws.yml config --quiet
docker compose --env-file infra/deploy/.env.vps -f infra/deploy/compose.aws.yml up -d --build --wait
docker compose --env-file infra/deploy/.env.vps -f infra/deploy/compose.aws.yml ps
```

`PORTAL_DOMAIN` é domínio sem protocolo; `ACME_EMAIL` é contato do operador.
Somente chave pública Supabase chega ao frontend. Service key, DSN e chave IA
ficam no backend. Modelo/chave IA podem permanecer ambos vazios. O preflight
verifica formato/configuração, não a autenticidade de chaves nem privilégios reais.
Não executar `docker compose config` sem `--quiet` com valores privados.

Conferir pelo domínio: HTTP redireciona para HTTPS, certificado válido, `/health`,
refresh em `/definir-senha`, login, recuperação, convite com SMTP, importação e
isolamento com dois tenants. `/health` testa processo, não dependência Supabase.
Não distribuir o endereço antes desse aceite operacional. Smoke Docker local e
CI não substituem essas verificações.

## Backup, atualização e rollback

Registrar os IDs/digests de backend/frontend/Caddy de cada versão e conservar
imagens anteriores. Logs têm rotação 3 × 10 MB por serviço; observar também cache
de builds e disco. Não usar limpeza de volumes ou prune sem revisar o que será
removido. Manter cópia protegida da configuração privada e do inventário de
versões fora da VPS; ela não deve integrar o pacote público.

Conservar `caddy_data` e `caddy_config`. Fazer backup protegido consistente dos
volumes durante janela de manutenção, copiando-os com Caddy parado e religando
logo após; o volume contém material de certificado. Confirmar restauração em
ambiente separado. Snapshot de VM complementa essa cópia e não cobre Supabase.

Confirmar backups/PITR do projeto Supabase no plano contratado. Backup de banco
não inclui os objetos de Storage e pode não guardar senhas de roles customizados;
documentar a recuperação do login de ingestão. Não supor backup automático no
plano gratuito. Restauração remota requer janela e autorização explícitas.

Atualização: validar versão, revisar migrador sem `--apply`, aplicar somente as
migrações aprovadas e executar `up -d --build --wait`. Não usar `down --volumes`.
Rollback da aplicação: selecionar imagens anteriores por digest em override
privado Compose, mantendo rede/variáveis/volumes, então `up -d --no-build --wait`.
Confirmar compatibilidade do código antigo com o schema atual antes de voltar.
Migração SQL não é desfeita pelo rollback; corrigir por migração aditiva revisada.

## Fontes oficiais

- [Template Docker Hostinger](https://www.hostinger.com/support/8306612-how-to-use-the-docker-vps-template-at-hostinger/).
- [Docker Engine no Ubuntu](https://docs.docker.com/engine/install/ubuntu/).
- [Plugin Compose Linux](https://docs.docker.com/compose/install/linux/).
- [Docker e firewall](https://docs.docker.com/engine/network/packet-filtering-firewalls/).
- [Caddy reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
- [Backups Supabase](https://supabase.com/docs/guides/platform/backups).
