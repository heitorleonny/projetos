# Nexo, interface, fotos e paleta — verificação integrada

Data: 05/10/2026 (America/Recife). Implementação local com três agentes e integração pelo agente principal. Nenhum commit, alteração na monografia ou publicação em produção.

## Resultado por solicitação

1. **Nexo:** esclarecimentos com opções para perguntas ambíguas; contexto e filtros visíveis; sugestões que preservam cluster/período; nome/slug da própria federação normalizados a partir da identidade autenticada; declaração de outra federação rejeitada pelo backend. Busca literal exige intenção explícita de nome, impedindo o modelo de transformar cidade em nome de EJ. A substituição de aliases preserva os demais caracteres/acentos da pergunta. Limites operacionais compartilhados no PostgreSQL: 6 chamadas por usuário e 30 por federação em janela fixa de um minuto, configuráveis por SQL administrativo. Sem mudança nos créditos comerciais dos planos.
2. **Interface:** superfícies sólidas, tipografia uniforme, cabeçalhos simples, navegação com nomes de função, cartões mais compactos, retirada de grelha/glass/glow e gradientes decorativos. O mascote permanece discreto. A visão geral mostra moeda formatada em português, com cartões de resumo empilhados no celular. Fórmulas e resultados continuam vindo do backend.
3. **Fotos:** foram examinados nove XLSX e onze abas, incluindo cabeçalhos, conteúdo OOXML, hiperlinks, fórmulas e mídia embutida. Não foi encontrada origem de fotos/logos. O campo `foto_url` e sua propagação já existiam; o componente passou a validar URLs, preservar assets locais seguros e manter fallback de iniciais. Nenhuma coluna foi inventada, URL acessada ou backfill executado sem fonte.
4. **Paleta:** nova aba Administração → Aparência, com até três cores, prévia e restauração. Salvamento limitado à federação autenticada, com papel/vínculo/ativo atuais verificados no banco. As cores são compartilhadas entre usuários; sessões abertas atualizam os metadados ao focar ou em até um minuto. Troca de tenant/restauração remove as três rampas anteriores. Controles sobre cores sólidas usam texto preto/branco por contraste, e tons derivados de links mantêm legibilidade nas superfícies escuras.

## Testes finais

- **Backend em banco descartável com todas as migrações: 513 aprovados, nenhum pulado.** Cinco avisos de depreciação em Starlette/Supabase. `--require-lab` impede aprovação quando houver skips. A bateria inclui RLS real, controles de acesso da paleta, limites concorrentes e helpers de identidade privados.
- **Frontend: build e lint aprovados.** Oito testes Node aprovados, nenhum pulado: quatro de URLs de fotos e quatro de paleta/contraste/troca de tenant.
- `git diff --check` aprovado.
- Migrações aditivas 17 e 18 aplicadas na demo e laboratório, preservando os dados. A reaplicação foi verificada.

A tentativa de `make test` ficou parada na consulta ao registry da imagem Python e foi interrompida. A verificação final utilizou a imagem de dependências já instalada, com o código/testes atuais montados e um Postgres descartável recém-criado:

```sh
docker compose --profile test up -d --wait db-test
docker compose --profile test run --rm --pull never \
  -v "$PWD/portal_fejepe/app:/app/app:ro" \
  -v "$PWD/portal_fejepe/tests:/app/tests:ro" \
  -v "$PWD/infra:/infra:ro" test
```

O banco descartável foi removido após a aprovação. Demo, laboratório, backend e frontend locais permanecem disponíveis para revisão.

## Avaliação real do modelo

Modelo configurado mantido: `nvidia/nemotron-3-super-120b-a12b:free`, via OpenRouter. A primeira avaliação ampliada encontrou uma interpretação indevida de cidade como busca por nome. O backend passou a validar essa intenção e o prompt foi reforçado. A rodada seguinte de 21 perguntas teve zero erros de transporte:

| Medida | Resultado |
|---|---:|
| Ferramenta correta | 21/21 |
| Plano exatamente igual ao gabarito | 17/21 |
| Resposta do catálogo exatamente igual ao gabarito | 20/21 |
| Status do fluxo completo com guardas correto | 21/21 |
| Valores/linhas do fluxo completo corretos | 21/21 |
| IDs retornados autorizados | 21/21 |
| Recusas esperadas | 7/7 |

[Rodada inicial](ia-avaliacao-nexo-2026-10-05-inicial.json) e [rodada após ajuste](ia-avaliacao-nexo-2026-10-05.json). O runner terminou com código 1 porque exige aprovação integral também na igualdade exata do plano e da resposta do catálogo. Essa condição foi preservada; não foi mascarada como execução totalmente aprovada.

As medidas de interpretação, catálogo e fluxo completo são distintas. O corpus foi usado para desenvolvimento, não é um conjunto independente, e não prova interpretação universal. A avaliação reaproveita a mesma interpretação, não faz segunda chamada, e não testa autenticação HTTP. A igualdade de linhas em uma recusa/esclarecimento não mede uma resposta numérica. O limite operacional e a preservação de acentos foram acrescentados após a rodada; seus controles foram verificados pelos testes e pela rota real, sem nova rodada integral de 21 chamadas.

## Verificação de integração e visual

Na sessão de demonstração FEJEPAR, foram verificados prévia/salvamento das três cores, persistência após reload e restauração da paleta original. A verificação visual cobriu desktop e viewport móvel, sem overflow horizontal nos formulários e no diálogo.

No Nexo, a pergunta ambígua com cluster/mês apresentou opções mantendo os filtros. A consulta real pela sigla da própria federação retornou indicadores com fonte/período/cluster, e “e em agosto?” mudou o mês preservando o cluster. A reserva de uso foi confirmada via JWT no PostgREST e na chamada real da API. Valores reais observados não foram copiados para este documento nem para fixtures.

O laboratório inicialmente ocultou uma diferença de privilégios: no Supabase, o schema `auth` pertence ao GoTrue, e o papel novo não recebeu USAGE por um GRANT feito pelo usuário postgres limitado. A integração encontrou 403. Helpers privados que retornam somente uid e tenant corrigiram essa dependência, sem ampliar acesso do limitador a dados estratégicos. O papel do limitador continua NOLOGIN/NOBYPASSRLS, a tabela de usuário é filtrada por RLS e os clientes não podem executar os helpers. Detalhes em [controle operacional](nexo-controle-operacional-2026-10-05.md).

Capturas com dados reais ficaram fora do Git em `../../validacao/portal-2026-10-05/`: `paleta-desktop.jpg`, `paleta-mobile.jpg`, `visao-geral-desktop.jpg`, `nexo-esclarecimento.jpg`, `nexo-indicadores-desktop.jpg`, `nexo-continuacao-desktop.jpg` e `nexo-mobile.jpg`.

## Decisões e limites

- [Paleta e fronteira de escrita](adr-006-paleta-por-federacao.md)
- [Revisão visual](interface-2026-10-05.md)
- [Investigação das fotos](fotos-ejs-2026-10-05.md)
- [Ajustes do Nexo](nexo-ajustes-2026-10-05.md)

Não foi realizada auditoria integral WCAG/leitor de tela, teste de carga ou estimativa de custo. A ausência de fotos nas exportações atuais permanece uma limitação de origem. Os limites por minuto não representam uma franquia mensal ou teto monetário. Antes de uma publicação remota, as migrações 17 e 18 devem ser aplicadas no ambiente de destino; nenhuma alteração remota foi executada nesta tarefa.
