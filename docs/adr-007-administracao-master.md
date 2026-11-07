# ADR-007 — Administração master e catálogo de planos

Data: 07/10/2026. Status: implementado e validado localmente.

O operador `plataforma` ganha uma tela própria em `/admin/master`, acessível pelo
menu Minha conta. O papel continua vindo de `usuario_atual()`, consultado no banco;
nenhum e-mail ou claim de papel concede esse acesso por si só.

A visão da plataforma agrega o cadastro de usuários no PostgreSQL, por federação,
antes da paginação do PostgREST. Inclui federações sem usuários, usuários inativos,
contagens de ativos e administradores ativos. Busca e filtro de status são locais.
O botão Ver usuários abre a gestão existente com a federação já selecionada.
Federações, usuários e importações reutilizam os componentes administrativos.

O catálogo permite criar e editar nome, preço mensal em reais, limite cadastral de
usuários e limite operacional de créditos de dashboards. A criação serializa os
IDs por advisory lock. Os campos numéricos aceitam zero e nulo, com teto de um
milhão; os limites são verificados na API e na função SQL. Não há exclusão de
plano nem atribuição automática. Os valores semeados na migração 03 permanecem
provisórios; a proposta comercial não é adotada automaticamente.

A migração 22 expõe três RPCs nominais, sem service key. Todas verificam o papel
ativo atual do banco, incluindo chamadas diretas via PostgREST. A agregação é
SECURITY INVOKER e usa a RLS já existente de federação e usuário. As funções de
escrita são SECURITY DEFINER com search_path fixo e validação nominal do operador.
Atribuir um plano NÃO concede UPDATE(plano_id) a authenticated: essa concessão
seria alcançável pela política de aparência dos admins comuns. O catálogo não
recebe escrita direta. anon e PUBLIC não executam as RPCs.

Preço não inicia cobrança. O limite de usuários continua informativo, sem bloqueio
de convite. O limite de créditos mantém a regra existente da migração 19: override
por federação tem prioridade sobre o plano e a cota de um mês já iniciado fica
congelada. Nexo não recebe franquia mensal por essa alteração. A visão nacional
não amplia leitura de EJs, metas, monitoramento ou resultados de dashboards.

Ativação: aplicar somente `infra/db/init/22-administracao-master.sql` após 21 e
reiniciar a API para carregar as rotas. A migração foi aplicada na demo local.
A conta local de operador é `op@teste.local`; nenhuma conta pessoal foi promovida.
Em um ambiente futuro, o vínculo deve usar a conta Auth existente e confirmada
pelo titular. A identidade pessoal de Heitor não foi inferida por nome/e-mail.

Validação: `make test` (561 aprovados, zero falhas, zero pulados, cinco avisos de
depreciação), `npm run build`, `npm run lint` e `make demo-smoke`. O smoke usa
TestClient com o código atual, Auth e PostgREST reais da demo, e confere totais por
federação contra o cadastro e recusas de admins comuns. A suíte SQL verifica
claim falso, operador inativo, edição/vínculo/remoção e manutenção do isolamento
das EJs. Não houve avaliação visual autenticada nem aplicação em produção.
