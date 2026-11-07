# Portal das Federações

Plataforma multi-tenant para gestão de desempenho de Empresas Juniores, com
autenticação, isolamento PostgreSQL/RLS, administração, ingestão XLSX, Nexo e
painéis convencionais por federação. React/TypeScript + FastAPI + PostgreSQL próprio.

Em 23/10/2026, dashboards gerados por IA foram retirados do escopo ativo do TCC.
O Nexo permanece. O [plano de retomada](docs/retomada-escopo-reduzido-2026-10-23.md)
define prioridades, critérios de conclusão e limites das evidências existentes.

## Organização

```text
backend/                  API, regras, ingestão, IA, scripts e testes
frontend/                 aplicação React/Vite e testes de interface
tools/cluster-calculator/ aplicação auxiliar independente
infra/db/init/            fonte única das migrações SQL
infra/deploy/             deploy AWS, variáveis, validação e instruções
scripts/                  execução local e preparação do pacote
docs/                     ADRs e evidências datadas
render.yaml               API Docker no Render
.github/workflows/ci.yml  verificação automatizada sem deploy
```

O repositório e seu histórico foram preservados. Em 07/10/2026,
`portal_fejepe` passou a `backend`, `front_portal_fejepe` a `frontend` e
`calculadora_cluster` a `tools/cluster-calculator`. Relatórios antigos mantêm os
nomes da época. O arquivo `portal-das-federacoes.code-workspace` abre o monorepo.

## Instalar e verificar

Requisitos para o pacote: Docker com Compose e Python 3 para gerar a configuração.
Para desenvolvimento/testes fora do container: Python 3.12 e Node 22.12+.

```sh
make setup              # dependências locais Python/Node pelos locks
make doctor             # ferramentas e ambiente; não imprime segredos
make check              # backend/RLS, testes/build/lint front e build auxiliar
```

`make test` usa PostgreSQL descartável, separado do banco da aplicação, com toda
a cadeia SQL e sem aceitar testes pulados. Nenhum check chama modelo pago.

## Executar com PostgreSQL e Docker

```sh
make docker-config      # cria .env.docker privado; recusa sobrescrever
make up                 # banco + migrações + API + frontend
make ps
```

Abra http://localhost:8080. O banco e a API ficam na rede interna; somente o
frontend é exposto no loopback. As senhas de banco são aleatórias, geradas no host.
Não há dependência de serviço Supabase, PostgREST ou GoTrue no novo runtime.
O volume `portal_postgres` conserva os dados; `make down` não o apaga.

O serviço `migrate` aplica a fonte única SQL com ledger/checksums antes da API.
Banco legado sem ledger ou migração aplicada com conteúdo alterado exige revisão,
não reset automático. Volumes anteriores de laboratório/demo não são convertidos.

A criação da conta inicial e os critérios de teste estão no
[mapa de entrega](docs/entrega-tcc-2026-11-05.md). A migração de contas/dados
existentes não está implícita na instalação nova. Não há senha de login padrão.

## Entrega e hospedagem

A decisão vigente está no [ADR 008](docs/adr-008-postgresql-docker.md).
Os guias antigos de Supabase/Render/VPS são históricos. A execução local não
prova publicação remota nem avaliação com participantes. Para hospedagem, preparar
HTTPS, backup/restauração, domínio e acesso; publicar somente com autorização.

Nexo exige provedor/modelo configurados no backend; sem configuração informa
indisponibilidade. Testes com provedor falso não equivalem à avaliação do modelo real.

## Pacote com todo o código atual

```sh
make package
```

Gera `artifacts/portal-das-federacoes-src.tar.gz`, incluindo arquivos novos ainda
não commitados. Exclui Git, dependências instaladas, builds, `.env`, exportações
reais, relatórios JSON brutos e consultas SQL avulsas locais. Verifica padrões de credenciais conhecidas,
mas não substitui revisão antes de compartilhar. O histórico permanece no Git.

## Referências

- [Banco, migrações e operador](infra/db/README.md)
- [Comparação de hospedagens](docs/opcoes-deploy-beta-2026-10-07.md)
- [Estado e limites para o TCC](ESTADO-PORTAL-PARA-TCC.md)
- [Contexto acadêmico e invariantes](CONTEXTO-TCC.md)
- [Contrato de ingestão](docs/etl-planilhas-portal-bj.md)
