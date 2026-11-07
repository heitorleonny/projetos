# Preparação de deploy — 13/10/2026

Estado: configuração e verificação locais, sem publicação ou recurso contratado.

## Lacuna e implementação

O deploy Render já tinha Dockerfile, Blueprint e healthcheck, mas o preflight
`infra/deploy/check-env.py` só reconhecia AWS e Vercel. Adicionado modo Render e
`render.env.example`, com verificação de origens HTTPS exatas, retorno de convite
na origem autorizada, `DOCS_ENABLED=false` e `TENANT_CLAIM_OBRIGATORIO=true`.
A configuração recusa chave secreta no caminho público, login administrativo
conhecido na ingestão (inclusive percent-encoded), DSN sem SSL ou ainda de exemplo,
e IA com modelo/chave incompletos. As mensagens não exibem valores.

Adicionadas sete regressões sintéticas ao job deploy-config da CI. O guia de
operação ganhou comandos de preflight Render e recuperação de aplicação,
distinguindo rollback de imagens da restauração de banco e migração aditiva.

## Pesquisa oficial consultada

- [Render Blueprint](https://render.com/docs/blueprint-spec): campos existentes
  `plan: 1c-2g`, `autoDeployTrigger: off` e healthcheck seguem a documentação vigente.
- [Chaves Supabase](https://supabase.com/docs/guides/getting-started/api-keys):
  chaves publishable/anon no cliente; secret/service_role exclusivas do servidor.
- [Ordem de startup Docker](https://docs.docker.com/compose/how-tos/startup-order/):
  mantido `depends_on` com `service_healthy` já existente.
- [Rollback Render](https://render.com/docs/rollbacks): recuperação depende de
  artefato retido; digest identifica a imagem exata.
- [Backups Supabase](https://supabase.com/docs/guides/platform/backups): proteção
  depende do plano; confirmar política no destino antes de atualizar.

As melhorias são operacionais; não provam SLA, tolerância a falhas ou desempenho.

## Verificação reproduzível

Da raiz `projetos/`:

```sh
python3 infra/deploy/test-check-env.py
docker compose --env-file infra/deploy/aws.env.example -f infra/deploy/compose.aws.yml config --quiet
docker run --rm -e PORTAL_DOMAIN=portal.example.com -e ACME_EMAIL=operador@example.com -v "$PWD/infra/deploy/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker build --target runtime -t portal-api:beta backend
docker build -t portal-web:beta frontend
python3 infra/deploy/smoke-containers.py
```

Resultados: sete testes passaram, zero falhas e zero pulados; Compose e Caddy
válidos; smoke Docker passou PORT customizado, UID sem privilégios, runtime sem
pytest, SPA, configuração pública sem cache, proxy protegido 401 e docs 404.
Após o agente de implementação confirmar que backend/app e frontend estavam
finalizados, as duas imagens runtime foram reconstruídas e o smoke repetido
com sucesso. Identificadores locais finais:

- API: `sha256:5a065115e803e2adf1b1e2bcb17141be5f41e6f5ef39287efd5438799d0a7473`.
- Web: `sha256:4a2a76abcbfe48123cd174c0a667ae2e5dd136c53f47b90cc951e29930bdf725`.

O build web mostrou dois avisos `SecretsUsedInArgOrEnv` para
`VITE_SUPABASE_ANON_KEY`, cuja natureza pública é intencional; nenhuma chave de
serviço/segredo foi fornecida. O backend reutilizou camadas válidas de cache.
Esse smoke não autentica usuários nem substitui Auth/PostgREST da demo real.
O preflight com `render.env.example` saiu com código 1, como esperado, recusando
os placeholders sem imprimir seus valores. Os cinco testes sintéticos do
comparador de regressão do executor principal também passaram e foram incluídos
na CI.

## O que falta no destino

Escolher conta, domínio, provedor e plano; criar Supabase novo; aplicar migrações
canônicas sem shim; conferir ledger, ACLs e defaults de todos os criadores;
habilitar hook; configurar SMTP/retornos e bootstrap do operador; confirmar que
o login de ingestão é membro do papel correto, sem ownership/BYPASSRLS.

Executar login/convite/recuperação/upload com contas próprias e isolamento de duas
federações pelo endereço real; avaliar modelo e catálogo antes de habilitar IA.
A checagem local não autentica chaves nem valida privilégios remotos. CI foi
configurada, mas não executada no GitHub. Não houve migração remota, email externo,
chamada paga, recurso contratado, commit ou push nesta frente.
