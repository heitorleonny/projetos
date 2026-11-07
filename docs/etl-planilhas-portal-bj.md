# ETL mínimo do Portal BJ para o portal

Levantamento de 04/10/2026. Foram inspecionados os cabeçalhos, a granularidade e
as dimensões dos nove arquivos em `~/Documents/TCC/dados/`; dados individuais
não foram copiados para o repositório. O critério é alimentar Dashboard,
Indicadores, Comparação, Perfil, Cluster Track e Simulação. Eventos ficou fora
do escopo pedido.

## Arquivo necessário

**Um tipo de arquivo:** `monitoring_acumulated_<ano>_*.xlsx`, aba
`EMPRESAS_JUNIORES`. Para iniciar 2026, basta a exportação acumulada de 2026.
Ela tem uma linha por EJ e mês e traz identidade e federação, núcleo, localidade,
universidade, clusters, metas, faturamento, contratos, contratos colaborativos,
CSAT e engajamento. A amostra de 21/09/2026 contém 1.507 EJs × 9 meses =
13.563 linhas em 27 federações. O ETL transforma essas linhas em
`empresa_junior`, `metas`, `cluster_historico` e `monitoramento`; `federacao` e
os 26 núcleos conhecidos já têm seed nas migrações 02 e 12. Os totais da rede
são calculados a partir das EJs.

Para **comparar anos com valores**, importe uma exportação acumulada *do mesmo
tipo para cada ano* desejado. O arquivo de 2026 só contém fatos mensais de
2026 e clusters de 2025/2026. Cluster de 2025 não substitui faturamento,
projetos, metas ou CSAT de 2025. A tela distingue ano sem fato de resultado
zero e deixa as células desse ano vazias até receber a série correspondente.

## Outros arquivos avaliados

| Exportação disponível | Granularidade | Necessária para as telas atuais? |
|---|---|---|
| `ejs_2026...` (aba Todas as Federações) | 26 núcleos × 9 meses | Não; o portal não exibe indicadores próprios do núcleo. Os vínculos EJ–núcleo vêm do monitoramento acumulado. |
| `federations_2026...` | 27 federações × 9 meses | Não; seus indicadores específicos (caixa, oportunidades, produtos de conexão) ainda não têm tela. Os indicadores atuais da rede usam fatos das EJs. |
| `monitoring_2026...` | contratos/projetos individuais de um recorte | Não; não é a série mensal consolidada de todas as EJs. |
| `ejs_2026_12...` (aba EMPRESAS_JUNIORES) | 22 EJs de um recorte | Não para a carga inicial nacional; a exportação acumulada já as cobre. |
| `ejs_members_2026...` | validação de cadastro de EJ | Não; o cadastro necessário já está no monitoramento. |
| `innovative_solutions_acumulated_2026...` | solução/produto individual, mais de 100 mil linhas | Não; não há tela por solução e ela não substitui o fato mensal de EJ. |
| `metrics_premiss_2026...` | premissas de EJ, federação e núcleo | Não; as regras atuais usam metas e constantes do backend. Qualquer adoção futura exige revisão de regra de negócio. |
| `universities_2026...` | universidade | Não; o nome exibido no Perfil/Dashboard está na coluna `UNIVERSIDADE` da exportação acumulada. |

## O que a carga faz

O operador da plataforma pode carregar todas as federações; o admin da
federação só grava a própria fatia, mesmo enviando o arquivo nacional. O
arquivo é validado por contrato e ano antes da escrita. **Simular** executa o
mesmo upsert sob RLS e desfaz a transação; **Gravar** aplica tudo ou nada. As
chaves naturais evitam duplicação, e um novo acumulado pode corrigir meses já
importados. O painel mostra contagens e histórico de cargas.

O campo `NUMERO_DE_CONTRATOS_QUE_REALIZOU_ACAO_COLABORATIVA` agora alimenta
`monitoramento.projetos_colab_mes` (migração 16); a UI usa a soma para projetos
colaborativos e seu filtro. `total_projetos` da rede soma `CONTRATOS` mensais.
`SOLUCOES` não é usado como total de projetos, pois representa outra medida.

## Limites de cobertura da origem

- Não há fato de 2025 em nenhuma exportação acumulada de 2026 disponível. Para
  comparação histórica, o usuário precisa exportar o acumulado do ano anterior.
- FEJEPE não tem núcleo no Portal BJ. O ETL não inventa essa classificação.
- `status` e `foto_url` de EJ não têm mapeamento confiável nesta exportação;
  aparecem vazios, sem impedir indicadores. Indicadores exclusivos de
  federação/núcleo e dados por solução exigiriam novos recursos do portal e
  então novas fontes, fora do conjunto mínimo atual.

## Evidência de validação

Simulação nacional com a exportação real no lab: 13.563 linhas, 1.507 EJs,
meses 1–9 e zero erro de contrato. A carga local na demo gravou a nova coluna
para as 13.563 linhas; 1.168 registros mensais têm contratos colaborativos
positivos. Testes sintéticos exercitam contrato, recorte, RLS, correção
retroativa, idempotência e a nova coluna. Após a remoção de comunidades,
`make test` passou com 376 testes, e build e lint passaram. `make demo-smoke`
passou para as 27 contas das federações e para o operador. Um upload
HTTP real em modo simulação, autenticado como admin da FEJEPE, aplicou apenas
387 linhas do arquivo nacional e ignorou 13.176 linhas das demais federações.
