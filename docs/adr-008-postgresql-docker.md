# ADR 008 — PostgreSQL próprio e aplicação em Docker

Data: 05/11/2026. Status: decisão de arquitetura autorizada por Heitor;
implementação e validação registradas no mapa de entrega desta data.

## Contexto e decisão

O autor pediu retirar Supabase e usar PostgreSQL, com a aplicação empacotada em
Docker. O banco já era PostgreSQL; o acoplamento adicional incluía GoTrue/Auth,
PostgREST, SDKs e chaves de plataforma. Trocar apenas a imagem do banco não atende.

A aplicação passa a acessar PostgreSQL com psycopg e autenticar contas por API
própria. O Compose reúne frontend nginx, API FastAPI e banco; a aplicação mantém
as divisões atuais de services, regras e domínio. A calculadora auxiliar continua
fora do deploy principal. Nexo permanece configurável e não é habilitado com
credenciais pagas automaticamente.

Preservar políticas RLS, filtros de tenant independentes, autorização de escrita
pelo cadastro atual, paginação completa e fronteira de privilégios da ingestão.
A API não pode conectar como dono das tabelas, superusuário ou BYPASSRLS. Claims
usados pela RLS são construídos da identidade autenticada, nunca de colunas de
planilha ou argumentos de consulta do usuário/modelo. Conexões/transações não
podem transportar identidade de uma requisição para a seguinte.

## Alternativas

- Manter Supabase hospedado: contraria a decisão atual.
- Empacotar a stack Supabase inteira: preserva dependência explicitamente retirada.
- Reescrever cálculos e regras junto com persistência: amplia risco e impede
  distinguir regressão de mudança deliberada nos números.
- PostgreSQL compartilhando o mesmo container da API: acopla ciclos de vida e
  backups. Compose permite operar o pacote como uma aplicação com serviços separados.

## Consequências e limites

O projeto assume manutenção de autenticação, ciclo de sessões, criação de contas,
backups e atualizações de PostgreSQL. Convites não devem alegar envio de e-mail
quando apenas um link local foi gerado. Contas/senhas/dados existentes no Supabase
não são migrados por inferência; o novo ambiente nasce separado e sem dados reais.

Migrações históricas são preservadas. A nomenclatura SQL `auth`, `authenticated`
e `anon` pode permanecer por compatibilidade com as políticas, sem exigir o
serviço Supabase. Documentos e resultados anteriores conservam sua arquitetura
original: não os reinterpretar como testes desta versão.

## Fontes técnicas consultadas

- [PostgreSQL: Row Security Policies](https://www.postgresql.org/docs/17/ddl-rowsecurity.html): dono, superusuário e BYPASSRLS exigem separação de privilégios.
- [Psycopg: Transactions management](https://www.psycopg.org/psycopg3/docs/basic/transactions.html): fechamento de transações com commit/rollback.
- [Docker Compose: startup order](https://docs.docker.com/compose/how-tos/startup-order/): dependências por healthcheck e conclusão de migração.

Essas fontes fundamentam o desenho; não são evidência de teste da aplicação.
