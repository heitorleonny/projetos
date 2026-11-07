# Pendências implementadas em 13/10/2026

## Escopo e vínculo com o plano

O calendário disponível está em `CONTEXTO-TCC.md`, seção 10: até aproximadamente
17/10, fechar pendências; desenvolvimento de IA em seguida; congelamento de código
a partir de aproximadamente 10/11. As datas são sugestões ainda sujeitas à decisão
do autor. O estado de 07/10 prevalece sobre as listas históricas de conclusão.

Esta entrega fecha dois problemas concretos do frontend relacionados ao isolamento
e à apresentação dos indicadores. Não resolve as divergências de regras de negócio,
o pacote completo de caracterização, ingestão adicional, avaliação humana nem a
geração de aplicações React descrita na arquitetura de dashboards.

## Isolamento de estado no navegador

Antes: o cache de consultas era apagado apenas pela função explícita de sair.
Eventos de logout em outra aba ou troca de sessão podiam reutilizar consultas
sem identidade na chave. O estado local de componentes, incluindo conversa,
também podia permanecer montado entre contas.

Agora: cada transição de usuário, federação ou papel limpa o cache antes de
atualizar a sessão e remonta a árvore sob o provedor de autenticação. Uma renovação
de token com a mesma identidade e claims preserva o cache. Uma resposta de consulta
antiga não repovoa o cache após a troca, verificado com o QueryClient real. A leitura
dos claims no navegador identifica apenas o escopo local; API e RLS continuam
responsáveis pela autorização. O resultado tardio de getSession não substitui um
evento de autenticação já recebido.

Arquivos: `frontend/src/auth/AuthContext.tsx`, `sessionScope.ts` e
`frontend/scripts/test-session-scope.mjs`.

## Comparação entre anos

Antes: subir de cluster 1 para 3 exibia 200%; ir de 40% para 60% da meta exibia 50%.
Agora: a apresentação mostra dois níveis e 20 pontos percentuais, respectivamente.
Taxa de colaboração passa de fração para pontos percentuais na diferença. Valores
monetários e contagens mantêm a variação relativa; base zero ou ausência não inventa
percentual. Os cartões de resumo seguem as mesmas EJs da busca, preservando as
agregações existentes. Nenhuma fórmula de SDE, cluster ou projeção foi alterada.

Arquivos: `frontend/src/features/comparacao/ComparacaoPage.tsx`, `variacao.ts` e
`frontend/scripts/test-comparacao.mjs`.

## Pesquisa em fontes oficiais

Consultadas em 13/10/2026:

- [Supabase: onAuthStateChange](https://supabase.com/docs/reference/javascript/auth-onauthstatechange),
  fundamento para tratar os eventos da sessão e desinscrever o listener.
- [TanStack: QueryClient](https://tanstack.com/query/latest/docs/framework/react/reference/classes/QueryClient),
  documentação de limpeza dos caches de consultas e mutações.

A decisão de remount é uma aplicação desses mecanismos ao risco observado neste
frontend; as fontes não constituem auditoria do Portal.

## Verificação e limites

Comando: `cd frontend && npm run check`.

- 20 testes passaram; 0 falharam; 0 foram pulados.
- ESLint e compilação TypeScript/Vite aprovados.
- Testes novos cobrem transições de conta/tenant/papel/logout, renovação sem troca,
  resposta tardia e unidades da comparação usando dados sintéticos.

Sem navegação autenticada manual nesta etapa. Nenhum teste de banco foi executado
por este agente; verificação integrada coordenada separadamente. Nenhuma chamada
paga, recurso remoto, alteração em produção, commit ou push foi feita. A evidência
é local e não equivale ao aceite dos participantes ou do ambiente hospedado.
