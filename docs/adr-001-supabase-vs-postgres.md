# ADR-001 — Manter o Supabase como banco da aplicação

- **Data:** 15/09/2026
- **Status:** aceito
- **Contexto:** avaliação pedida durante a reorganização da stack, a ~9 semanas da entrega do TCC

## Questão

Vale substituir o Supabase por um PostgreSQL próprio rodando em Docker, para
empacotar tudo em uma stack só e simplificar deploy e testes?

## Decisão

**Não.** O Supabase continua sendo o banco e o provedor de autenticação da
aplicação. Um PostgreSQL em Docker foi adicionado, mas com outro propósito:
servir de laboratório local para a modelagem preditiva do TCC.

## Por quê

O Supabase neste projeto não é "apenas o Postgres". Ele entrega três coisas, e
duas delas estão acopladas ao código:

**1. Acesso a dados via PostgREST, não via SQL.** Os serviços recebem o cliente
Supabase e usam o query builder dele:

```python
sb.table("monitoramento").select("*").eq("ano", ano).in_("id_ej", ids).execute()
```

São **22 chamadas desse tipo**, concentradas em `empresa_service.py` (10) e
`rede_service.py` (12). Trocar por Postgres puro significa reescrever todas em
SQL ou num ORM, e reescrever junto os testes que hoje injetam um cliente falso.

**2. Autenticação (GoTrue), que atravessa os dois lados.** No backend,
`get_current_user` valida o JWT com `sb.auth.get_user(token)`. No frontend, o
Supabase Auth é quem mantém a sessão: `getSession`, `onAuthStateChange`,
`signInWithPassword`, `signOut`, e a injeção do token no interceptor do axios.
Sair do Supabase aqui não é trocar de biblioteca — é passar a ser responsável
por armazenamento de usuários, hash de senha, emissão e renovação de JWT, e
recuperação de senha. Isso é trabalho de semanas, e é trabalho de segurança,
onde errar é caro.

**3. Operação gerenciada.** Backup, disponibilidade e atualização do Postgres
hoje são problema de outra pessoa. Assumir isso numa VPS, no meio do TCC,
adiciona um modo de falha que não existe hoje.

## O que se ganharia, e por que não compensa agora

Ganhos reais de migrar: independência de fornecedor, custo previsível, e uma
stack local que sobe inteira sem credencial externa. Nenhum deles é avaliado
pela banca, e nenhum é urgente. O custo — reescrita da camada de dados mais
substituição completa da autenticação — cai exatamente sobre as nove semanas
que precisam produzir o pipeline de dados, o modelo preditivo, a integração do
alerta e a monografia.

A decisão seria outra em outro momento do projeto. Registrada aqui como
**trabalho futuro**, junto com a arquitetura multi-tenant.

## Consequências

- A stack local **não sobe 100% offline**: backend e frontend precisam das
  credenciais do Supabase para funcionar de verdade. O frontend tem
  `VITE_USE_MOCK=true`, que permite trabalhar na interface sem backend.
- Foi adicionado o perfil `lab` no compose, com um Postgres local e o schema
  das três tabelas em `infra/db/init/`. É onde a modelagem do TCC roda, sobre
  uma cópia exportada dos dados — sem risco para a base de produção.
- Se um dia a migração acontecer, o caminho de menor risco é em duas etapas,
  nunca de uma vez: primeiro isolar o acesso a dados atrás de um repositório
  (deixando os 22 pontos de acesso concentrados), depois trocar a
  autenticação.

## Alternativa considerada e descartada

**Auto-hospedar o Supabase completo em Docker** (Postgres + PostgREST + GoTrue
+ Studio) manteria o código intacto e daria uma stack local fechada. Foi
descartado por peso: são sete containers adicionais para uma necessidade que o
perfil `lab` resolve com um. Continua sendo a melhor opção *se* o objetivo
virar independência de fornecedor sem reescrita.
