# Segundo tenant com dados reais — verificação de 04/10/2026

Esta verificação usa a **demo local**, sem publicar a exportação do Portal BJ ou
abrir acesso de uma pessoa da federação. A conta de FEJEPAR é sintética
(`fejepar@teste.local`); os dados de EJ vieram da exportação nacional.

## Origem e carga

A exportação `monitoring_acumulated_2026_1220261004-1-xflnk9.xlsx`, aba
`EMPRESAS_JUNIORES`, tem **15.020 linhas**, uma por EJ e mês: **1.502 EJs**,
10 meses e 27 federações. Ela substitui como referência corrente a amostra
de 21/09 (1.507 EJs × 9 meses). O ETL EJ versionado valida o contrato, grava
staging, aplica upserts idempotentes sob RLS e separa os clusters por ano.
FEJEPAR tem **139 EJs**, 1.390 fatos mensais, sete núcleos cadastrados;
**22 EJs** estão ligadas ao Núcleo Maringá.

Cinco EJs da RioJunior presentes em setembro estão ausentes da nova
exportação. O upsert preserva as linhas antigas e seus 45 fatos; por isso o
cadastro da demo contém 1.507 EJs e 15.065 fatos de 2026. Antes de publicar
um total nacional corrente, é preciso definir se ausência na exportação
significa desativação ou apenas omissão temporária.

## Isolamento e telas

O teste autenticou FEJEPE e FEJEPAR no GoTrue e consultou a API e o PostgREST
reais. Nas nove tabelas verificadas não houve linha cruzada. FEJEPE acessou
43 EJs/430 fatos; FEJEPAR, 139 EJs/1.390 fatos. Perfil de EJ de outro tenant
respondeu 404; comparação não retornou EJ alheia.

Uma sessão de FEJEPAR em origem de navegador separada da sessão FEJECE do
usuário navegou Dashboard, Cluster Track, Comparação, Indicadores, Simulação,
perfil de EJ do Núcleo Maringá e Admin. Essas telas carregaram os dados
isolados; Eventos ficou fora do escopo funcional. Isso é validação de
funcionamento da **demo**, não validação por representante real da FEJEPAR nem
implantação remota.

## Tempo e código necessários

Em ambiente **já preparado**, a reimportação idempotente de FEJEPAR a partir
do arquivo nacional leu 15.020 linhas, aplicou 1.390 e ignorou 13.630:
**4,39 s**; nenhum registro mudou. A bateria Auth/API/PostgREST levou
**4,43 s**. O procedimento medido totaliza **8,82 s**, excluindo instalação,
schema, primeiro cadastro, criação de conta, revisão de branding e validação
humana. Não é o tempo de provisionar uma nova federação do zero.

**Linhas de lógica de aplicação específicas para FEJEPAR nesta ativação: 0.**
O roteamento de dados e a RLS são genéricos; federação e núcleos já constavam
dos seeds de configuração. Essa contagem não mede as linhas do esforço
original de transformar o portal em multi-tenant.

## Itens ainda não concluídos do S4–S5

- O ETL das planilhas com **fatos próprios de núcleo e federação** e o
  despivotamento de `RESULTADO` 2016–2024 não existem. As telas atuais usam
  métricas no nível EJ; qualquer gráfico específico dessas entidades ou
  comparação financeira histórica exige fonte e modelagem adicionais.
- A medição de **provisão inicial limpa** de uma nova federação não foi feita.
  Reexecutar a carga em uma base já preparada mede somente o custo marginal
  desta etapa.
- O teste técnico de isolamento não substitui o aceite de uma pessoa da
  federação e a validação com usuários prevista no TCC.

## Regra de publicação dos dados

A exportação traz CNPJ e desempenho financeiro por EJ e fica **fora do Git**.
`git ls-files` não encontrou XLSX/CSV/TSV rastreados; `.gitignore` agora bloqueia
esses formatos e a pasta local de validação. O repositório pode conter código,
schema, testes com dados sintéticos e resultados **agregados/anônimos**.
Capturas da demo com nome e valores de EJs também ficam fora do repositório.
Antes de citar nominalmente participantes, federações ou EJs junto de
desempenho individual em texto ou imagem pública, registrar aceite explícito
dos responsáveis; nenhum aceite externo foi obtido nesta verificação.
