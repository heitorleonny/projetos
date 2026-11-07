# Achado — o que os limites fixos da 9.17 fazem com uma federação grande

- **Data:** 22/09/2026
- **Como foi observado:** ambiente de demonstração local (`make demo`), portal
  aberto e navegado com login real, como `um@teste.local` (FEJEPE) e
  `dois@teste.local` (FEJEMG). Ver `docs/adr-002-rls-local-sem-stack-completa.md`,
  adendo dos dois ambientes.
- **Status:** **corrigido em 29/09/2026** — ver a seção abaixo. O texto
  original, de 22/09, segue logo depois, com uma conclusão que se mostrou errada.
- **Evidência:** capturas em
  `~/Documents/TCC/validacao/screenshots-demo-multitenant/{fejepe,fejemg}/`.

## Atualização de 29/09/2026 — a causa era outra, e o viés não existia

Reteste com os mesmos dois usuários, conferindo cada número contra SQL direto
no banco da demo. A FEJEPE bateu em tudo. A FEJEMG não, e o motivo não era o
limite de 100 do frontend:

**O PostgREST devolve no máximo 1000 linhas por consulta** (`max_rows` em
`supabase/config.toml`, e também o padrão do Supabase). Os services liam
`monitoramento` sem paginar; a FEJEMG tem 2.619 linhas em 2026, chegavam 1000,
e **139 das 291 EJs apareciam com faturamento R$ 0** em todas as telas. O corte
não dá erro, só devolve menos. O `.limit(10000)` do SDE não adiantava, porque o
teto é do servidor.

| FEJEMG | Antes (API) | Banco | Depois (API) |
|---|---|---|---|
| Faturamento total | R$ 3.428.751,01 | R$ 4.924.112,28 | R$ 4.924.112,28 |
| EJs fora do zero | 104 | 243 | 243 |
| EJs com faturamento errado na lista | 139 de 291 | — | 0 de 291 |

**O que isso muda neste documento.** A seção "O viés: some exatamente quem está
em risco" foi medida sobre os dados cortados. As "191 ocultas, 187 zeradas"
estavam zeradas pelo corte, não de fato. A conclusão de viés **não vale**. O
"170 EJs" da Comparação, que tinha ficado sem explicação, era a união do top-100
de 2025 com o top-100 de 2026. E os totais do topo do Dashboard **não** vêm de
`/rede/indicadores`: somam a página carregada (divergência 9.16).

**O que foi corrigido:**

- `app/services/leitura.py`: toda consulta de várias EJs lê página por página e
  falha (em vez de devolver número errado) se a contagem não fechar.
- Frontend: Indicadores, Comparação e Cluster Track buscam todas as páginas
  (`fetchTodasEmpresas`); o "Carregar mais" do Dashboard pede páginas de até 100
  em vez de subir o `page_size` até o 422.
- `get_federacao_id`/`get_papel` leem os claims do JWT. Liam o `app_metadata`
  do cadastro no GoTrue, onde o hook não escreve: o tenant era sempre `None` e o
  papel sempre `membro`.
- O branding segue o usuário logado (`GET /federacao/minha`); o `TENANT_SLUG`
  do deploy vale só para a tela de login. Com isso, o "achado de arquitetura" do
  fim deste documento também foi resolvido.
- Perfil da EJ mostra o nome da federação (lia a coluna renomeada na migração 04).
- O slogan do Dashboard virou coluna (`federacao.slogan`, migração 14). A seção
  de comunidades foi retirada do portal. O evento Ciranda passou a ser só da FEJEPE.

## Por que só aparece agora

A FEJEPE tem 43 EJs e nunca encostou em nenhum limite. A FEJEMG tem **291** — e
é o primeiro tenant que estoura. O isolamento multi-tenant está correto (cada
usuário só enxerga a própria federação, verificado via PostgREST e na tela); o
problema é o que acontece **depois** do isolamento, na paginação.

> Correção de números: a linha 9.17 de `docs/regras-de-negocio.md` diz "FEJEPE
> tem 42" e "FEJEMG tem 285". Contados na exportação de 21/09 e confirmados no
> banco carregado, são **43** e **291**. A linha continua como está — corrigi-la
> é outra decisão.

## O que a API faz (e faz certo)

`GET /api/v1/empresas` **pagina corretamente** e é honesta sobre o tamanho:

```json
"meta": {"page": 1, "page_size": 100, "total": 291, "total_pages": 3}
```

Páginas 1, 2 e 3 devolvem 100 + 100 + 91 = 291. O `page_size` é limitado a 100
(`app/routers/empresas.py:65`, `le=100`), mas isso é teto de página, não de
resultado. `GET /api/v1/rede/sde` também calcula sobre as 291
(`total_ejs: 291`), e `GET /api/v1/rede/indicadores` soma a rede inteira.

**O defeito não está na API. Está em quem a consome.**

## O que cada tela faz, medido

Comparação entre os dois usuários, lendo o rótulo que a tela **mostra**:

| Tela | FEJEPE (43 no banco) | FEJEMG (291 no banco) | Veredito |
|---|---|---|---|
| Dashboard | `Exibindo 20 de 43 EJs` | `Exibindo 20 de 291 EJs` | honesto, mas **quebra** (abaixo) |
| Indicadores (Escalonado) | 9 zeradas, 14 vermelho, 7 amarelo, 3 verde (**33**) | 64 zeradas, 14 vermelho, 5 amarelo, 6 verde (**89**) | classifica 89 de 291, sem dizer |
| Comparação | `43 EJs` | `100 EJs` | mostra 100 como se fosse tudo |
| Cluster Track | `43 EJs encontradas` | `100 EJs encontradas` | "encontradas" sugere resultado completo |
| Perfil de EJ | carrega | carrega | sem limite envolvido |

### 1. Dashboard — quebra a lista inteira no 5º clique

`DashboardPage.tsx:154` faz `page_size: (prev.page_size ?? 20) + 20` a cada
"Carregar mais". A API limita `page_size` a 100. A sequência real, medida:

```
inicio:    Exibindo 20 de 291 EJs
clique 1:  Exibindo 40 de 291 EJs
clique 2:  Exibindo 60 de 291 EJs
clique 3:  Exibindo 80 de 291 EJs
clique 4:  Exibindo 100 de 291 EJs
clique 5:  HTTP 422 — page_size=120 → "Input should be less than or equal to 100"
```

**O que o gestor vê:** a lista de EJs desaparece por completo e é substituída
por um card de erro — *"Erro ao carregar dados / Request failed with status
code 422"*. Não é uma página que falta: é a tela inteira que some, depois de
ter funcionado quatro vezes. Captura:
`fejemg/dashboard-carregar-mais-quebrado.png`.

Na FEJEPE isso nunca acontece: a lista acaba em 43, antes do teto.

### 2. Indicadores, Comparação e Cluster Track — buscam só a página 1

As três chamam a API com `page_size: 100` e **nunca leem `meta.total` nem
`meta.total_pages`**:

- `features/indicadores/useIndicadores.ts:46` e `:61`
- `features/comparacao/comparacaoService.ts:20`
- `features/cluster-track/ClusterTrackPage.tsx:30`

Como as três pedem `ordem_por: 'faturamento', direcao: 'desc'`, as 100 que
aparecem são **as 100 maiores**. E é aqui que o achado deixa de ser cosmético.

## O viés: some exatamente quem está em risco

Somando as 291 EJs da FEJEMG por faturamento acumulado:

| | EJs | Faturamento somado |
|---|---|---|
| Visíveis na tela (top 100) | 100 | R$ 3.428.071,01 |
| **Ocultas (nunca carregadas)** | **191** | **R$ 680,00** |

- Faturamento da 100ª colocada: **R$ 386,00**
- Faturamento da 291ª colocada: **R$ 0,00**
- Das 191 ocultas, **187 estão com faturamento zero**.

O corte por "top 100 de faturamento" remove da tela quase exclusivamente EJs
sem faturamento. **Para um portal cuja função é acompanhar risco, o filtro
acidental elimina justamente a população de risco.** Um gestor da FEJEMG que
abra o Cluster Track lê "100 EJs encontradas" e não tem nenhum sinal de que
191 EJs — quase todas zeradas — ficaram fora.

Isso também importa para o TCC: qualquer avaliação do baseline de
acompanhamento feita pela tela estaria medindo sobre a população errada.

## Observação adicional, não investigada

Na Comparação da FEJEMG aparecem **dois números diferentes na mesma tela**:
`100 EJs` e `170 EJs · Acumulado`. Na FEJEPE os dois são `43`. Não foi
investigado de onde vem o 170 — fica registrado para quem for mexer na tela.

Também vale notar que os baldes do Escalonado não fecham com o total nem na
FEJEPE (33 classificadas de 43). Isso é anterior ao multi-tenant e independe
deste achado.

## O que NÃO está quebrado

Registrado para que o achado não seja lido como maior do que é:

- **O isolamento funciona.** Via PostgREST, com o JWT de cada usuário:
  FEJEPE vê 43 EJs / 387 linhas de monitoramento / 43 metas; FEJEMG vê 291 /
  2.619 / 291. Nenhuma enxerga a outra, e `federacao_id` distinto na consulta
  confirma (12 e 7).
- **O SDE calcula sobre a rede toda** (`total_ejs: 291`), não sobre as 100.
- **Os totais do topo do Dashboard** vêm de `/rede/indicadores`, que soma as
  291 (R$ 3.428.751,01 = R$ 3.428.071,01 visíveis + R$ 680,00 ocultos).
- **O branding cai no fallback sem quebrar.** A FEJEPE tem `logo_url` e
  `cor_primaria` (migração 09); a FEJEMG tem os dois `NULL` e a tela renderiza
  normalmente, com "Portal FEJEMG" e o tema padrão.

## Um achado de arquitetura, de graça

O frontend resolve o branding por `TENANT_SLUG`, que é **variável do deploy**,
não a federação do usuário logado. Logado como `dois@teste.local` (FEJEMG) com
`VITE_TENANT_SLUG=fejepe`, a tela pede
`GET /federacao/branding?slug=fejepe` — branding de uma federação, dados de
outra. Para capturar a FEJEMG foi preciso reiniciar o Vite com o slug dela.

Isso já está declarado como provisório no `docker-compose.yml` ("serve um
tenant declarado no deploy, não N tenants simultâneos") e em
`src/config/env.ts`. Fica aqui a confirmação empírica: **uma instância não
serve duas federações ao mesmo tempo hoje.** Os dados isolam por usuário; a
identidade visual, não.
