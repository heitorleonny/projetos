# Correção de privilégios antes da homologação — 07/10/2026

## Problema reproduzido

Na stack Supabase local `portal-fejepe-demo`, `anon` e `authenticated` tinham
TRUNCATE em oito tabelas: `cluster_historico`, `empresa_junior`, `ingestao_carga`,
`ingestao_staging_ej`, `metas`, `monitoramento`, `nucleo` e `plano`. Eram 16
concessões. TRUNCATE não avalia RLS; o fato de PostgREST não oferecer uma rota
TRUNCATE não justifica o privilégio. Os defaults de `public` concediam ALL em
tabelas/sequências e EXECUTE em funções criadas por `postgres` e
`supabase_admin`. Não havia ACL global registrada antes da correção.

## Implementação

Fonte única: `infra/db/init/21-privilegios-minimos.sql`, transacional, aditiva
e reaplicável. Não modifica linhas, políticas RLS nem papéis de ingestão/IA.

| Acesso | Antes na demo | Depois |
|---|---|---|
| TRUNCATE de clientes | 8 tabelas × 2 papéis | Nenhuma tabela de public |
| INSERT/UPDATE/DELETE de tabela, REFERENCES e TRIGGER | Grants amplos herdados de defaults | Nenhum para clientes |
| Branding anônimo | SELECT amplo de federacao além do branding | Só slug, nome, logo e cores/slogan |
| Escrita administrativa | Colunas explícitas mais grants históricos em outras tabelas | Só colunas explícitas de usuario/federacao e RPCs existentes |
| Sequências dos clientes | ALL herdado | Nenhum acesso direto |
| Futuras tabelas/sequências do dono das migrações | ALL para clientes | Exigem GRANT explícito |
| Futuras funções do dono das migrações | EXECUTE automático | Exigem GRANT explícito |

As RPCs existentes mantêm suas ACLs. Leitura autenticada de dados do tenant,
catálogo e cargas permanece; tabelas privadas de controle IA permanecem
privadas. Quando a migração 20 está presente, leitura do dashboard e colunas
do snapshot público também são preservadas. As políticas RLS continuam a
decidir linhas e papéis de aplicação. `anon` e `authenticated` já não tinham
CREATE no schema public na demo; isso foi conferido sem alterar schemas.

Defaults pertencem ao **criador**, não ao schema. No destino gerenciado,
aplicar 21 sob o dono das migrações, normalmente `postgres`, e inventariar
outros criadores. Para objetos criados por outro role, suas ACLs/defaults
também precisam ser revisados sob identidade autorizada. Não conceder
membership administrativo para contornar essa restrição. Na demo local havia
acesso administrativo direto e a mesma 21 foi reaplicada sob `supabase_admin`;
os defaults de public de ambos ficaram sem concessões para clientes.
Schemas internos Supabase não foram revogados.

## Validação realizada

- `make test`: **524 passed, 0 skipped**, cinco avisos de depreciação de
  dependências. Banco PostgreSQL16 descartável inicializado com 00–21.
- Testes novos: tentativas reais de TRUNCATE CASCADE negadas a ambos os papéis
  em todas as tabelas; reprodução dos grants ALL e defaults globais/por-schema
  do Supabase; reaplicação idempotente; provas de que tabela/sequência/função
  criadas depois não ficam acessíveis; preservação de branding, coluna
  administrativa, RPC e escrita de ingestão.
- A simulação também comprova que ALL histórico não deixa SELECT em tabelas
  privadas `ia_controle_*`/`ia_creditos_*`, nem por tabela nem por coluna.
  Defaults globais explícitos de EXECUTE de anon/authenticated são revogados.
- Os três testes novos foram executados também contra PostgreSQL da **stack
  Supabase real local**, conectando como `postgres`: **3 passed**, nenhum skip.
  Suas alterações de teste foram revertidas por transação; não deixam probes
  ou grants de simulação persistentes.
- Aplicação aditiva apenas da 21 na demo local. Contagens e fingerprints de
  conteúdo das 12 tabelas foram iguais antes/depois. Nenhum dado foi apagado.
- Auditoria pós-aplicação: **zero** grants de tabela para clientes dos tipos
  INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER. Branding `slug`
  permitido e `id` negado para anon; UPDATE de `usuario.papel` permitido e
  de `auth_user_id` negado para authenticated.
- Probes transacionais de tabela, sequência e função criados sob **postgres
  e supabase_admin** na demo: SELECT/TRUNCATE/USAGE/EXECUTE negados para ambos
  os clientes nos dois criadores. Todas as probes foram removidas por rollback.
- `make demo-smoke`: login/branding/paginação/endpoints FEJEPE, FEJEMG e
  operador passaram; consultas cruzadas negadas; operador restrito ao próprio
  tenant nos dados EJ; 27 contas admin autenticadas e vinculadas.
- `git diff --check`: passou.

O primeiro `make test` teve 523 passes e uma falha por indisponibilidade do
arquivo da migração dentro da imagem de testes. Corrigido com montagem
read-only de `infra/db/init` no serviço `test` do Compose; o comando normal
passou integralmente depois. O teste não mantém cópia paralela do SQL.

## Limites

A demo existente estava somente até 18: não continha tabelas de 19/20. Elas
foram verificadas no banco descartável 00–21, não instaladas na demo nesta
tarefa. Nenhum deploy remoto, migração em produção ou teste de participantes
foi realizado. O destino de homologação ainda precisa receber as migrações,
inventário de privilégios/defaults e prova de RLS com seus próprios JWTs.
Convites/e-mail/recuperação de senha pelo domínio público continuam pendentes.

Nenhum commit, push, reset de volume ou troca de usuários foi realizado.
