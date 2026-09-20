# Levantamento da semana 1 — modelagem multi-tenant

Data: 18/09/2026. Fontes: diagrama do Supabase (print), nove exportações do
Portal BJ em `~/Documents/TCC/dados/`, e o código em `portal_fejepe/`.

---

## 1. O schema real diverge da documentação

O diagrama do Supabase desmente `banco.md`, `infra/db/init/01-schema.sql` e os
models Pydantic em quatro pontos. Todos afetam a migração.

| Divergência | Documentação | Banco real | Consequência |
|---|---|---|---|
| Coluna `cluster` | existe, é o fallback | **não existe** | `utils/cluster.py` faz fallback para uma coluna inexistente; `EmpresaJunior.cluster` é campo morto |
| Colunas de cluster | `cluster_2023..2026` (4) | `cluster_2022..2026` (**5**) | a decisão de normalizar cobre 5 anos, não 4 |
| `monitoramento.faturamento_colab_acumulado` | existe | **não existe** | é calculado no service; o model declara com default 0 |
| `monitoramento.projetos_totais` | existe | **não existe** | idem |

Confirmado pelo diagrama: `metas.id_ej` e `monitoramento.id_ej` **têm FK real**
para `empresa_junior.id_ej`; `empresa_junior.id_ej` e `cnpj` têm índice único;
`federacao` é **nullable**.

**Ação:** `banco.md` e `init/01-schema.sql` precisam ser regerados de um
`pg_dump --schema-only` antes de qualquer `ALTER TABLE`. O bug de
`utils/cluster.py` é independente da multi-tenancy e vale corrigir agora.

---

## 2. O universo de tenants está resolvido

`federations_2026...xlsx` entrega **27 federações com ID estável do Portal BJ**.
`ejs_members_2026...xlsx` entrega as 1.484 EJs federadas com o nome da federação
em texto.

**Os 27 nomes batem exatamente entre as duas exportações — zero divergência de
grafia.** Isso significa que, se a coluna `federacao` do Supabase usar a mesma
grafia, o backfill é um `UPDATE ... FROM federacao WHERE nome = federacao`, sem
tabela de-para manual. É a pergunta que a query `03-diagnostico-tenant.sql`
responde.

Decisões que o dado sustenta:

- **PK da tabela `federacao` = ID do Portal BJ**, não serial próprio. O tenant
  passa a ter o mesmo identificador que o movimento já usa, e a ingestão das
  exportações dispensa de-para. A sequência tem buracos (não existem 1 e 27).
- **CNPJ não serve como chave alternativa:** nulo em 11 das 27, e FEJEMG e
  Tocantins Júnior aparecem com o mesmo CNPJ na origem.
- **`uf` não existe em nenhuma exportação.** Foi inferida do nome e cobre
  exatamente as 27 UFs, uma por federação — mas é inferência, marcada
  `[CONFIRMAR]` no SQL.

Distribuição de EJs por tenant: FEJEMG 285, FEJESP 221, FEJEPAR 138, UNIJr-BA
77, RioJunior 75, FEJESC 69, FEJECE 65, RN Júnior 64, FEJERS 61, Concentro 58,
PB júnior 44, **FEJEPE 42**, … até Roraima Júnior com 2.

---

## 3. Existe um segundo tenant com dado real — mas não é o que parecia

O `mapa_dados_portal_federacoes.md` descreve os arquivos de monitoramento como
"recorte FEJEPAR". Não são. São **Núcleo Maringá**: 22 EJs das 138 de FEJEPAR,
com 9 meses de série mensal.

Isso é bom e ruim ao mesmo tempo:

- **Bom:** dá um segundo tenant com dado real e diferente do de FEJEPE — que é
  exatamente o que a demonstração de isolamento precisa, e o que torna a
  validação com os três voluntários mais honesta que uma base sintética.
- **Ruim:** um tenant "FEJEPAR" no portal mostraria 22 de 138 EJs. Ou o recorte
  é rotulado explicitamente como parcial, ou vale pedir a um voluntário de
  FEJEPAR a exportação completa da federação.

Os IDs de EJ são globais no Portal BJ: os 22 de Maringá estão contidos nas 1.484
e **não colidem** com os 42 de FEJEPE. Ou seja, `id_ej` continua único
globalmente depois da multi-tenancy — o `UNIQUE (id_ej)` atual não precisa cair.

De FEJEPE, as exportações trazem só `universities` (120 universidades). O dado
rico de FEJEPE está no Supabase, não aqui.

---

## 4. Uma entidade que falta na lista da semana 1: núcleo / comunidade

`empresa_junior.comunidade` é hoje texto livre, e é **vocabulário exclusivo de
FEJEPE**. As exportações mostram que:

- o movimento chama isso de **núcleo**, com 26 núcleos que têm **ID próprio** no
  Portal BJ e **fato mensal próprio** (26 núcleos × 9 meses);
- eles existem em apenas 6 federações — FEJEMG (7), FEJEPAR (7), FEJESC (4),
  FEJESP (4), UNIJr-BA (4);
- **FEJEPE não tem núcleo registrado na BJ.** As "comunidades" do portal são uma
  subdivisão interna que só existe na base de FEJEPE.

Então `comunidade` é a terceira coluna implicitamente monotenant, junto com
`federacao` e os logos fixos do frontend. Um tenant novo ou não tem subdivisão,
ou tem uma com outro nome e outros valores. Isso precisa entrar na modelagem da
semana 1 — mesmo que a decisão seja adiar —, porque hoje a coluna é filtrada e
indexada, e mudar depois mexe em índice, em service e em frontend.

Três saídas, em ordem crescente de custo:

1. **Manter texto livre, escopado ao tenant.** Zero migração; o índice vira
   `(federacao_id, comunidade)`. Cada federação digita o que quiser. Aceita que
   não dá para cruzar subdivisão entre federações.
2. **Tabela `subdivisao (id, federacao_id, nome)` com rótulo por federação**
   ("comunidade" em FEJEPE, "núcleo" nas demais) e FK em `empresa_junior`.
   Custo médio, e permite importar os 26 núcleos com o ID da BJ.
3. **Adotar o modelo da BJ direto** (`nucleo`, ID da BJ, fato mensal próprio).
   Mais fiel à origem, mas obriga FEJEPE a se encaixar num conceito que ela não
   usa — e o dado de FEJEPE é justamente o mais rico que você tem.

A opção 2 é a que eu defenderia: preserva o vocabulário de cada federação sem
abrir mão da chave da origem. Mas é decisão de escopo, não técnica — se a semana
apertar, a 1 não cria dívida grave, desde que o índice já nasça composto.

---

## 5. O bloqueio que a lista da semana 1 não cobre

`app/dependencies.py` cria o cliente Supabase como **singleton com chave fixa** e
nunca propaga o JWT do usuário para o PostgREST. Com isso, `auth.uid()` dentro de
qualquer policy é `NULL`: a RLS ou não filtra nada, ou bloqueia tudo.

O diagrama confirma que não há tabela de vínculo usuário ↔ federação. Sem ela e
sem cliente por requisição com a `anon key`, `federacao_id` é uma coluna
decorativa. Não precisa ser implementado na semana 1, mas a **modelagem** da
semana 1 precisa incluir esse vínculo — senão a semana 2 refaz migração.

---

## 6. O que fica pendente de rodar no Supabase

`infra/db/queries/02-inventario-schema.sql` e `03-diagnostico-tenant.sql`
respondem, nesta ordem de importância:

1. A grafia de `federacao` no banco bate com os 27 nomes da BJ? (decide se o
   backfill é automático)
2. Quantas EJs FEJEPE tem no portal, contra as 42 federadas da BJ? (a diferença
   são EJs não federadas ou dado velho)
3. Há órfãos em `metas`/`monitoramento`? (decide se a FK composta passa)
4. Qual o preenchimento real de `cluster_2022..2026`? (decide normalizar ou
   documentar a dívida)
5. A RLS está ligada em alguma tabela hoje? (linha de base do Cap. 5)
