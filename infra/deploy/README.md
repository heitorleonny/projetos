> **05/11/2026:** o caminho Supabase abaixo é histórico. Heitor escolheu PostgreSQL próprio + Docker. Consulte `docs/entrega-tcc-2026-11-05.md` e o README da raiz para o estado da substituição. Não usar estas instruções antigas para o novo ambiente.

# Deploy de teste do Portal das Federações

O código está organizado em `backend/`, `frontend/` e `tools/cluster-calculator/`.
Os manifestos abaixo preparam dois caminhos. Nenhum deles cria recurso remoto até
ser executado/configurado na conta do operador. Não há migração dos usuários antigos.

## Antes de publicar qualquer opção

1. Criar um **projeto Supabase novo** e contas próprias para os participantes.
2. Aplicar as migrações canônicas `infra/db/init/01..NN`, em ordem, sem o shim
   `00-shim-auth-local.sql`. Usar `backend/scripts/migrar_banco.py` do monorepo e ler
   `infra/db/README.md`; o modo lab não deve ser usado no banco remoto.
3. Configurar e habilitar o Custom Access Token Hook `public.custom_access_token_hook`
   no Auth. Os manifestos de produção exigem `TENANT_CLAIM_OBRIGATORIO=true`.
4. Configurar SMTP, Site URL e URLs permitidas de retorno em Supabase Auth. Incluir
   `https://DOMINIO/definir-senha` para convites e recuperação; evitar wildcard amplo.
5. Criar login próprio membro de `ingestao`, sem ser dono, superusuário ou BYPASSRLS,
   para `INGESTAO_DSN`; exigir SSL. Confirmar o acesso por tenant com os testes de RLS.
6. Criar o operador inicial com o fluxo de bootstrap documentado no monorepo;
   não compartilhar a conta do operador com participantes. Convites usam a service key
   **apenas no backend** e exclusivamente em `convite_service.py`.
7. Conferir migração 21 no destino: RLS, grants mínimos, nenhum `TRUNCATE` a clientes
   e defaults dos roles criadores. A validação local não comprova grants remotos.

Configuração de IA é opcional para iniciar o portal: sem chave/modelo as funções de
IA respondem indisponíveis. Não habilitar modelos pagos sem configurar limites e
fazer a avaliação específica. Não versionar `.env`, DSNs, planilhas ou senhas.

## Vercel + Render + Supabase gerenciado

- Vercel: importar o repositório e selecionar **Root Directory `frontend`**.
  `frontend/vercel.json` usa `npm ci`, build Vite e fallback SPA (inclui `/definir-senha`).
- Copiar valores de `infra/deploy/vercel.env.example` para as variáveis da Vercel.
  `VITE_API_BASE_URL` é a URL HTTPS pública da API, terminada em `/api/v1`.
  Tudo com prefixo `VITE_` fica público no bundle. Ao mudar valores, rebuildar.
- Render: importar `render.yaml` da raiz. Docker usa contexto `backend` e imagem
  runtime sem pytest; o comando lê `PORT`. Healthcheck `/health`. O plano é `1c-2g`
  e o deploy automático está desligado, para publicar somente depois dos checks.
- Preencher as variáveis solicitadas: `CORS_ORIGINS` deve ser o endereço exato do
  frontend, sem caminho. `CONVITE_REDIRECT_URL` termina em `/definir-senha`.
  `SUPABASE_SERVICE_KEY`, `INGESTAO_DSN` e `IA_API_KEY` são exclusivos do Render.
- Como nomes/domínios só existem após provisionar, configurar primeiro a URL do
  frontend no backend e no Auth, então publicar/republicar o frontend com a URL da API.
- Aplicar também `IA_TIMEOUT_SEGUNDOS`, `IA_MAX_TOKENS_SAIDA`, `IA_RACIOCINIO` quando
  necessário. O padrão do backend é usado quando não há variável explícita.

Validação local, sem mostrar valores:

```sh
python3 infra/deploy/check-env.py --mode vercel --env frontend/.env.production
cp infra/deploy/render.env.example infra/deploy/.env.render
chmod 600 infra/deploy/.env.render
# Preencher o espelho local com os mesmos valores privados usados no Render.
python3 infra/deploy/check-env.py --mode render --env infra/deploy/.env.render
```

O modo Render exige origens HTTPS exatas, retorno de convite na mesma origem,
documentação fechada e claims obrigatórios. Também recusa chave secreta no caminho
público e login administrativo conhecido na conexão de ingestão. Essa inspeção não
valida assinatura/validade de chave nem membership, ownership ou BYPASSRLS no destino.
O arquivo preenchido é privado e não integra o pacote de entrega. IA precisa de
modelo e chave juntos; ambos vazios mantêm a função indisponível.

[Blueprint Render](https://render.com/docs/blueprint-spec),
[configuração Vercel](https://vercel.com/docs/project-configuration/vercel-json).

## Aplicação em VPS (Hostinger, AWS ou outro) + Supabase gerenciado

Este é o caminho escolhido para a próxima implantação. O arquivo
`compose.aws.yml` conserva seu nome histórico e funciona em qualquer VPS Linux
com Docker Engine e Compose v2. Guia completo: [VPS](VPS.md).

Frontend nginx, FastAPI e Caddy compartilham a máquina. Somente Caddy publica portas
80/443; a API e o nginx não têm portas no host. Caddy emite/renova HTTPS automaticamente.
Supabase continua externo: este manifesto **não** fornece PostgREST/Auth nem troca
Supabase por PostgreSQL puro.

Na VM com Docker e Compose v2 instalados, da raiz do monorepo:

```sh
cp infra/deploy/aws.env.example infra/deploy/.env.aws
chmod 600 infra/deploy/.env.aws
# Preencher o arquivo, sem publicá-lo ou imprimir valores.
python3 infra/deploy/check-env.py --mode aws --env infra/deploy/.env.aws
docker compose --env-file infra/deploy/.env.aws -f infra/deploy/compose.aws.yml config --quiet
docker compose --env-file infra/deploy/.env.aws -f infra/deploy/compose.aws.yml up -d --build --wait
```

Apontar DNS do `PORTAL_DOMAIN` para o IP estável da VM antes da subida. Liberar
80 TCP, 443 TCP (UDP 443 opcional para HTTP/3) no firewall do provedor; SSH só para a origem
do operador. Não expor 8000/8080/5432. Conservar o volume `caddy_data` nos upgrades;
contém certificados. Atualização da aplicação: repetir `up -d --build --wait`.
Para parar sem apagar certificados, `down` sem `--volumes`.

`/api/*` vai direto do Caddy ao backend, conservando o protocolo HTTPS nos headers;
o nginx cuida da SPA e `/env-config.js` sem cache. Logs são limitados a 3 × 10 MB
por serviço. `/health` confirma o processo da API, sem testar Supabase externo.
Escolher tamanho da VM depois de medir memória nas importações e durante uso real.

[HTTPS e proxy Caddy](https://caddyserver.com/docs/quick-starts/reverse-proxy).

## Checks e limites da validação

```sh
make test                 # banco descartável, migrações completas, sem skips
cd frontend
npm ci
npm run lint
npm test
npm run build
```

CI em `.github/workflows/ci.yml` executa essas duas frentes, build da calculadora,
validação dos manifestos e smoke das imagens runtime. Não faz deploy e não
precisa de segredos externos. `make test` não apaga lab/demo e não acessa produção.
Construir e verificar imagens sem dados reais:

```sh
docker build --target runtime -t portal-api:beta backend
docker build -t portal-web:beta frontend
python3 infra/deploy/smoke-containers.py
```

O smoke não publica portas; verifica PORT customizada, usuário sem privilégios,
imagem da API sem pytest, fallback da SPA, configuração pública sem cache,
proxy de endpoint protegido (401) e documentação fechada (404).

Antes de distribuir o endereço público, verificar pelo endereço real: `/health`,
rotas da SPA após refresh, login, convite/definição de senha, recuperação, painel,
importação com a conta adequada, isolamento de duas federações e limites de IA.
Build/CI verdes não substituem esse teste externo nem uma sessão com participantes.

## Atualização e recuperação do ambiente

Antes de atualizar, registrar a versão/digest das imagens anterior e candidata,
o resultado da revisão de `migrar_banco.py` sem `--apply` e a política de backup disponível no plano
Supabase escolhido. Manter a imagem anterior no registry ou na VM. Não depender
de reconstrução da árvore local para recuperar uma versão.

No Render, usar o rollback para um deploy anterior somente depois de conferir que
essa API é compatível com o schema já aplicado. Na VM, voltar às imagens anteriores
por um override de Compose com `image:` e subir com `up -d --no-build --wait`.
Não apagar volumes do Caddy. Revalidar login, isolamento, convite e importação.

Rollback da aplicação não desfaz migração SQL. O migrador verifica checksums e
registra o ledger; correção de schema usa migração aditiva revisada. Antes de
restaurar um backup remoto, definir a janela de dados afetada e obter autorização
específica do operador. A disponibilidade de backup/PITR depende do plano e precisa
ser conferida no destino, sem inferir proteção a partir dos testes locais.

Fontes oficiais: [rollback Render](https://render.com/docs/rollbacks),
[backups Supabase](https://supabase.com/docs/guides/platform/backups).
