# Opções de deploy para o beta do Portal das Federações

Pesquisa em 07/10/2026. Decisão ainda aberta; nenhum recurso remoto criado.
Objetivo: permitir testes externos com poucas pessoas, contas novas e dados
limitados às federações participantes. Não há necessidade de migrar usuários,
senhas ou sessões da demo ou do portal anterior.

## O que o código exige

O frontend é uma SPA React/Vite. FastAPI faz cálculos, valida usuários com
Supabase Auth e consulta tabelas/RPCs via cliente Supabase/PostgREST. PostgreSQL
aplica RLS. O upload de XLSX usa pandas e conexão psycopg com papel de ingestão.
Isso permite trocar a hospedagem mantendo os serviços Supabase, mas PostgreSQL
puro não substitui Auth/PostgREST sem adaptação do código.

Fontes locais: `backend/app/dependencies.py`,
`backend/app/services/convite_service.py`,
`backend/app/services/importacao_service.py`,
`frontend/src/auth/AuthContext.tsx`, `docker-compose.yml`.

## Comparação

Valores de referência em USD/mês, uma API e um banco, tráfego baixo, sem
promoções, impostos, domínio ou IA. Dimensionamento é hipótese a verificar
com upload e navegação concorrente; os testes funcionais não medem capacidade.

| Opção | Onde fica cada parte | Custo de referência | Operação e decisão |
|---|---|---|---|
| Serviços separados | Vercel: frontend; Render pago: API; Supabase hospedado: banco/Auth/PostgREST | API 512 MB + Supabase Pro: US$32; API 2 GB + Pro: US$50; somar US$20 se Vercel Pro | Menor administração de infraestrutura. Recomendação para começar o beta. |
| Aplicação na AWS e Supabase hospedado | Lightsail com frontend, API e proxy HTTPS; Supabase externo | VM 2 GB + Supabase Pro: US$37; VM 4 GB + Pro: US$49; backups da VM à parte | Boa alternativa para usar AWS com custo previsível e manter o banco gerenciado. |
| Tudo na AWS em uma máquina | Lightsail com frontend, API e Supabase self-hosted em containers | VM 8 GB/2 vCPU: US$44; VM 16 GB/4 vCPU: US$84; backups à parte | Maior autonomia. Nós operamos Linux, banco, Auth, atualizações e restauração. Uma falha da máquina afeta toda a stack. |
| AWS em serviços separados | S3/CloudFront para frontend; ECS/Fargate para API e serviços de autenticação/dados; banco persistente | Exige cotação por região, tarefas, banco, rede e logs | Mais trabalho de implantação e compatibilidade. Não é a primeira escolha para este beta. |

Preços: [Vercel](https://vercel.com/pricing),
[Render](https://render.com/pricing), [Supabase](https://supabase.com/pricing),
[Lightsail](https://aws.amazon.com/lightsail/pricing/).

## Limites que mudam a escolha

- Vercel Hobby só pode ser usado quando o projeto se enquadrar em uso pessoal
  não comercial. TCC pessoal pode se enquadrar; uso institucional ou profissional
  deve ser avaliado conforme as condições. Pro parte de US$20/mês.
  [Condições Hobby](https://vercel.com/docs/plans/hobby).
- Render Starter custa US$7/mês e tem 512 MB; Standard custa US$25/mês e tem
  2 GB. Ainda não medimos o pico do upload nacional com pandas. O plano menor
  pode servir a um piloto com carga feita por CLI, mas sua capacidade para
  importação pela interface precisa ser verificada. Render Free suspende a API
  após 15 minutos ociosa e a retomada pode levar aproximadamente um minuto.
  [Preços](https://render.com/pricing), [Free](https://render.com/docs/free).
- Supabase Free pode servir a uma experiência curta, com backup externo próprio:
  pausa por inatividade e não inclui backups automáticos. Pro parte de US$25/mês
  e inclui backups diários com retenção de sete dias. Esses preços consideram
  um projeto no compute inicial, sem extras.
  [Planos](https://supabase.com/pricing),
  [Backups](https://supabase.com/docs/guides/platform/backups).
- Para Supabase self-hosted, a referência oficial é mínimo 4 GB RAM/2 cores e
  recomendação de 8 GB+/4 cores+. A VM de US$44 tem 8 GB, mas só 2 vCPU; a de
  US$84 tem 16 GB/4 vCPU. O portal e a ingestão consomem recursos adicionais.
  Remover serviços Supabase não utilizados é possível, após validar dependências.
  [Requisitos Docker](https://supabase.com/docs/guides/self-hosting/docker).
- Uma máquina com Docker Compose pode reunir vários containers e volumes.
  Não precisamos colocar todos os processos em uma única imagem. No self-host,
  usar a distribuição Docker própria para hospedagem, com HTTPS e segredos novos,
  e não publicar diretamente a stack de desenvolvimento da CLI.
  [Self-host](https://supabase.com/docs/guides/self-hosting).
- RDS/Aurora não é uma substituição direta do PostgreSQL distribuído pelo
  Supabase self-hosted. Há diferenças de extensões e privilégios a verificar.
  Existe um [template comunitário AWS](https://github.com/supabase-community/supabase-on-aws),
  que não elimina essa etapa. A opção AWS distribuída é um projeto de implantação
  próprio, não apenas mudança de variáveis.
  [Discussão sobre compatibilidade](https://github.com/orgs/supabase/discussions/43208).

## Região, email e custos adicionais

Render não oferece região no Brasil. Com Render, API e Supabase em Virginia são
uma combinação a avaliar para diminuir chamadas entre regiões. Se a prioridade
for API e dados em São Paulo, AWS para aplicação com Supabase São Paulo se
encaixa melhor. Não foi realizada medição de latência dessas combinações.
[Render regiões](https://render.com/docs/regions),
[Supabase regiões](https://supabase.com/docs/guides/platform/regions).

Convites e recuperação de senha precisam de SMTP externo: o SMTP padrão do
Supabase restringe destinatários aos membros da equipe do projeto. Resend e
SES são opções compatíveis. SES exige sair do sandbox para enviar a destinatários
não verificados. Não tratar email para voluntários como configurado só por
criar o banco. [Supabase SMTP](https://supabase.com/docs/guides/auth/auth-smtp),
[Resend SMTP](https://resend.com/docs/send-with-smtp),
[SES sandbox](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html).

IA, domínio, SMTP e backups próprios são itens separados do custo base. Para
VM, snapshots não substituem um procedimento de restauração testado do banco.
Lightsail cobra snapshots por GB armazenado; o total depende da retenção.
[Tarifas e snapshots](https://aws.amazon.com/lightsail/pricing/).

## Preparação comum às opções

Na preparação posterior desta mesma data, as migrações 19/20 foram aplicadas na
demo local com preservação dos dados. A migração aditiva 23 corrigiu ACLs das
RPCs IA e o executor canônico trata a precondição de membership do dono limitado.
O destino novo recebe a cadeia completa pelo migrador, sem o shim 00. Consulte
[verificação da entrega](verificacao-backend-entrega-2026-10-07.md).

1. Criar ambiente novo, aplicar migrações `infra/db/init/` na ordem, sem o shim
   `00` no Supabase real; não reaplicar cegamente migrações antigas não idempotentes.
2. Aplicar a migração de privilégios mínimos e conferir ACLs/RLS/defaults no destino.
   Os testes no laboratório não substituem essa conferência no Supabase hospedado.
3. Configurar o hook `custom_access_token_hook` para tenant/papel, validá-lo em
   login e renovação e então exigir `TENANT_CLAIM_OBRIGATORIO=true`.
4. Criar operador novo com credencial individual e contas dos participantes por
   convite, vinculando `auth_user_id`, federação e papel. Não copiar usuários de
   `seed_demo` nem usar a senha compartilhada da demo.
5. Configurar HTTPS, origens CORS, Site URL, redirects de `/definir-senha`,
   SMTP, chaves públicas no frontend e segredos somente no servidor.
6. Para upload, criar login de ingestão sob RLS e TLS. Em rede somente IPv4,
   avaliar o session pooler porta 5432 e usuário `[ROLE].[PROJECT-REF]`.
   Não usar conexão administrativa na aplicação de ingestão.
7. Importar a base necessária, configurar provedor/limites de IA e testar no
   endereço público: convite, senha, login, tenant, branding, dados, Nexo,
   dashboards e publicação/revogação, além do upload quando habilitado.
8. Configurar backup, ensaiar restauração e compartilhar o link após essa validação.

[Hook](https://supabase.com/docs/guides/auth/auth-hooks/custom-access-token-hook),
[Conexões](https://supabase.com/docs/guides/database/connecting-to-postgres).

## Proposta para decisão

Para iniciar com pouca operação, escolher serviços separados, com API paga e
Supabase Pro. US$50/mês com frontend Hobby elegível (US$70 com Pro) é uma
referência inicial que oferece mais memória para upload; ainda exige medição.
Para priorizar AWS, escolher aplicação em Lightsail e Supabase Pro, referência
de US$37–49/mês mais backups da VM. Escolher tudo na AWS quando a autonomia e
a operação própria de banco/Auth forem objetivos explícitos do projeto.

Nenhum desses valores constitui garantia de desempenho ou cotação final.
