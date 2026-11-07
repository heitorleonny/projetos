# ADR-003 — Painel administrativo: papel `plataforma` e a única exceção da service key

- **Data:** 29/09/2026
- **Status:** aceito
- **Contexto:** o portal precisava de um painel para gerenciar as federações e os
  usuários, ver o último login de cada um e atualizar os dados por planilha sem
  passar pela linha de comando.

## Questões

1. Quem enxerga **todas** as federações, se a regra do projeto é "papel nunca
   amplia tenant"?
2. Como criar um usuário novo, se criar conta no Supabase Auth exige a service
   key e ela é proibida no caminho de request?
3. Como ler o último login, que mora em `auth.users`, tabela que a API não lê?
4. Como a planilha chega ao banco pela web sem abrir uma porta dos fundos na RLS?

## Decisões

### 1. Um terceiro papel, `plataforma`, com alcance estreito

`usuario.papel` passa a aceitar `plataforma` (migração 13), o operador do portal.
Ele é a **única** exceção a "papel nunca amplia tenant", e só nas três tabelas do
cadastro da plataforma: `federacao`, `usuario` e `ingestao_carga`. As políticas de
EJ, meta, monitoramento, cluster e staging **não foram tocadas**. No dashboard, o
operador vê a federação a que está vinculado, como qualquer usuário. Isso está
coberto por `tests/test_rls_painel_admin.py::TestPlataforma::test_nao_ve_ej_de_outra_federacao`.

| Papel | Federações | Usuários | Cargas | Importação |
|---|---|---|---|---|
| `membro` | a própria (leitura) | — | — | — |
| `admin` | a própria (leitura) | gere os da própria federação, exceto operadores | as da própria federação | só a própria federação |
| `plataforma` | todas; edita status e branding | todos | todas, inclusive as nacionais | nacional ou qualquer federação |

**Para escrever, vale o papel do banco, não o do token.** As políticas novas não
leem o claim `papel`. Elas perguntam a `usuario`, via funções `SECURITY DEFINER`
(`eh_plataforma()`, `eh_admin_da_federacao(id)`), se quem está na sessão
(`auth.uid()`) é hoje, e ativo, operador ou admin. O motivo: o claim é uma
fotografia do último login, e um admin rebaixado continuaria escrevendo até o
token expirar. A API segue a mesma regra e lê o papel por `public.usuario_atual()`.

### 2. A service key entra num arquivo só, depois da RLS

O convite por e-mail usa `auth.admin.invite_user_by_email`, que só aceita a
service key. A exceção fica em `app/services/convite_service.py` e é nominal em
`tests/test_papeis.py` (`EXCECOES`). A ordem é o que a mantém pequena:

1. A linha de `usuario` é inserida com o cliente **do usuário**, então a RLS
   decide se ele pode cadastrar alguém naquela federação e com aquele papel. Se
   ela recusar, a service key nem é criada.
2. A service key só manda o convite e grava `auth_user_id` na linha que o passo 1
   criou.
3. Se o convite falhar, a linha é desfeita. Se o vínculo falhar, a conta criada
   também é desfeita.

`auth_user_id` é justamente a coluna que nenhum papel da API pode escrever. Quem
a escrevesse poderia apontar uma linha da própria federação para a conta de
outra pessoa.

**Consequência operacional:** o container da API passa a receber
`SUPABASE_SERVICE_KEY`. Sem ela, o convite responde 500 e o resto funciona.

### 3. Último login por uma função, não por GRANT em `auth.users`

`public.admin_listar_usuarios()` (`SECURITY DEFINER`) devolve **só**
`last_sign_in_at`, e só das linhas que o chamador poderia gerir. A tabela
`auth.users` tem hash de senha e tokens de recuperação, e nada dela é exposto.
No laboratório, a migração 13 cria um shim mínimo de `auth.users` (id, email,
`last_sign_in_at`); no Supabase ela é do GoTrue e o bloco não faz nada.

### 4. A planilha entra pela mesma função da CLI

`POST /api/v1/admin/importacoes` chama `app.ingestao.importacao.importar`, a
mesma função de `make importar`, com `origem='upload'` e `carregado_por`. A
conexão é `INGESTAO_DSN`, com o papel `ingestao` (sujeito a RLS, sem DELETE). A
carga recusa dono das tabelas e BYPASSRLS, e o upload herda essa trava. O router
decide o escopo: o `admin` sempre recebe o recorte da própria federação. Com o
claim fixo, uma linha de outra federação que escapasse do filtro seria recusada
pela RLS.

O fluxo é em dois passos, **simular** e depois **gravar**, e é o mesmo
`--dry-run` da CLI: a carga roda inteira e é desfeita, então as contagens são as
reais.

## Achado que motivou uma revogação

Na demo (e portanto, muito provavelmente, no Supabase hospedado `[CONFIRMAR]`),
os default privileges do schema `public` dão **ALL**, inclusive TRUNCATE, a `anon`
e `authenticated` em toda tabela criada pelo `postgres`. Os GRANTs por coluna das
migrações 07 e 09 não restringem nada ali. Até a 13, isso não abria escrita
porque não existia política de escrita, e sem política a RLS nega.

A 13 abre escrita em `usuario` e `federacao`, então **revoga** INSERT, UPDATE,
DELETE e TRUNCATE dessas duas tabelas e concede escrita por coluna. As demais
tabelas continuam com ALL no Supabase. Não há escrita pela API nelas, mas:

- TRUNCATE **não passa pela RLS**. O PostgREST não o expõe, então hoje não é
  alcançável pela API, mas é um privilégio que não deveria existir.
- `anon` tem SELECT de tabela inteira em `federacao`, e o GRANT por coluna da 09
  (só branding) não vale lá. A política filtra as linhas (só as ativas), mas as
  colunas `id`, `uf` e `status` ficam legíveis sem login.

**Recomendação (não aplicada):** uma migração que revogue os privilégios de tabela
de `anon`/`authenticated` em todo o schema `public` e reconceda só o que 07, 09 e
13 declaram. Fica fora deste ADR porque mexe em todas as tabelas.

## Alternativas rejeitadas

- **Painel só da própria federação**, com a visão nacional na CLI: não atendia a
  "gerenciar todas as federações".
- **Backend administrativo separado com a service key**: ignora a RLS inteira,
  que é o que o projeto inteiro evita.
- **Vincular por trigger em `auth.users`** em vez de usar a service key: evita a
  chave, mas o cadastro não fica todo no painel, e criar trigger no schema do
  GoTrue depende de privilégio que a demo mostrou não ter (`auth` é do
  `supabase_admin`).
