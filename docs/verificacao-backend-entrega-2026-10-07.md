# Backend — entrega e validação local em 07/10/2026

## Implementado

- Diretório `backend/`; identificação da API e pacote `portal-das-federacoes-api`.
- Dependências diretas de produção separadas de teste/desenvolvimento. Locks
  transitivos com versões exatas e SHA256 gerados com `uv pip compile`, Python
  mínimo 3.11; build das imagens usa Python 3.12 e instalação `--require-hashes`.
- `backend/scripts/migrar_banco.py`: revisão padrão somente leitura, exclusão do
  shim 00, aplicação ordenada 01..23, ledger/checksum em schema privado, lock de
  sessão, transação por arquivo e confirmação do nome do banco antes da escrita.
  Banco já existente sem ledger é recusado, evitando reaplicar a migração 04.
- Executor mantém membership temporária de `ia_limitador` até concluir ACLs nas
  migrações históricas 18/19/20 e na corretiva 23; restaura concessões próprias e
  flags PG16 sem alterar outros grantors. Os arquivos históricos 19/20 não foram
  modificados.
- Migração aditiva 23 corrige ACLs de RPCs IA em bancos existentes. Foi observado
  que scripts antigos revogavam membership antes de REVOKE/GRANT das funções:
  o dono limitado do Supabase emitia WARNING e não aplicava essas ACLs. Uma suite
  executada apenas como superuser não detectava esse comportamento.
- `backend/scripts/criar_operador.py`: revisão padrão sem escrita, conta nova
  somente, confirmação do hostname, senha sem argumentos/eco e sem valor padrão,
  service key limitada ao script administrativo. Após Auth criar UUID, consulta
  `auth.users` do banco destino para provar alinhamento antes do vínculo. Se a
  escrita/vínculo falha, tenta compensar removendo apenas a conta recém-criada.
  Timeout Auth pode deixar resultado incerto: requer conferência no Dashboard.
- Instruções operacionais em `infra/db/README.md`, incluindo ativação explícita
  do hook Auth, SMTP, privilégios, RLS e login com JWT real no destino.

## Verificações concluídas

- 6 testes operacionais específicos passaram em PostgreSQL descartável real:
  todas as migrações e ledger/checksum; reaplicação sem repetir 04; recusa de banco
  legado; rollback conjunto schema/ledger; bootstrap/compensação com MockTransport
  Auth; recusa de Auth e banco desalinhados; dono SQL não superuser com concessão
  preexistente preservada e ACLs das RPCs verificadas.
- `make test`: **567 passaram, 0 falharam, 0 pulados**, 7 avisos (depreciações
  PostgREST/Starlette TestClient e cache pytest). Usa
  PostgreSQL 16 descartável, todas as migrações 00..23 e imagem de testes com lock.
- `make demo-smoke`: passou login, branding, paginação e endpoints FEJEPE/FEJEMG/
  operador; consultas cruzadas recusadas; operador restrito ao próprio tenant nos
  dados de EJs; master com agregados conferidos e admins comuns recusados;
  27 contas administrativas autenticadas e vinculadas.
- Demo existente: 19/20 estavam ausentes, 22 já presente. Foram aplicadas somente
  as pendências 19/20 e a corretiva aditiva 23, preservando volumes. A tentativa
  inicial sob dono limitado revelou falha SET ROLE e foi abortada pelo BEGIN;
  depois precondição temporária e ACLs foram corrigidas. Sem aplicar 04, reset,
  importação, nova seed ou substituição de usuários.
- Contagens preservadas antes/depois: 1.507 EJs, 15.065 registros de monitoramento,
  1.507 metas e 29 usuários. Zero tabelas públicas com TRUNCATE concedido a anon ou
  authenticated. RPCs `reservar_consulta_ia`, `persistir_dashboard_evento_ia`,
  `consultar_creditos_dashboard_ia`: anon não executa, authenticated executa;
  primitiva `reservar_creditos_ia`: nenhum dos dois executa.

## Limites

Não foram criados recursos remotos, contas externas, repositório, commit ou
implantação pública. Bootstrap Auth foi verificado por mock significativo e banco
real, sem criar conta remota. O smoke usa GoTrue/PostgREST locais e usuários já
existentes somente para preservar a demo; o destino novo terá contas novas.
Nenhum modelo pago ou chamada de IA foi usado. Isolamento no endereço público,
SMTP de convites/recuperação e hook no destino continuam sendo verificações após
provisionamento. Avisos de depreciação do cliente PostgREST/cache pytest não
representam falha funcional; estão separados de testes pulados.

## Auditoria de dependências de produção

`pip-audit` foi executado em ferramenta temporária isolada (`uv tool run`), sem
adicionar auditor ao runtime. O lock inicial apresentou 14 entradas em Starlette
0.46.2, equivalentes a 7 advisories distintos (fontes do serviço retornavam
entradas duplicadas). A versão de FastAPI 0.115 impedia atualizar o transitive.

Foram atualizados os requisitos mínimos compatíveis para FastAPI 0.133.*
(resolvido 0.133.1) e Starlette >=1.3.1,<1.4 (resolvido 1.3.1). Os locks PROD/DEV
foram regenerados com hashes. As [notas oficiais do FastAPI](https://fastapi.tiangolo.com/release-notes/#01330)
confirmam suporte a Starlette 1+; o [advisory do mantenedor de Starlette](https://github.com/Kludex/starlette/security/advisories/GHSA-82w8-qh3p-5jfq)
exige 1.3.1 para limites de formulários urlencoded. Não foram desativadas proteções
novas, suprimidos advisories nem alterados testes para acomodar a atualização.

Reauditoria de produção: **55 dependências auditadas, 0 vulnerabilidades conhecidas,
0 pacotes ignorados**. Evidência sanitizada em
`docs/auditoria-dependencias-backend-2026-10-07.json`. Esse resultado é uma consulta
à base de advisories em 07/10/2026, não garantia sobre vulnerabilidades futuras,
imagem de sistema operacional, Supabase ou configuração externa.

```bash
uv tool run --from pip-audit pip-audit -r backend/requirements.lock \
  --disable-pip --no-deps --format json
```

Após atualizar FastAPI/Starlette: `make test` repetido em banco descartável: **567
passaram, 0 falharam, 0 pulados**, 7 avisos. `make demo-smoke` repetido com o lock
novo no Python local também passou todos os checks anteriores. A depreciação nova
do TestClient com httpx não altera o cliente HTTP de produção.
