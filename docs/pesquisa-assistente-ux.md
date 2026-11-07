# Nexo — pesquisa e decisões de experiência

Data: 04/10/2026. Escopo: assistente de leitura dos dados da federação. Não altera regras de negócio ou fórmulas.

## Fontes primárias consultadas

- [W3C — padrão de diálogo modal](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/): recomenda foco dentro do diálogo, navegação por Tab contida, Escape para fechar e retorno ao acionador; o conteúdo externo deve ficar inerte. Implementação usa `dialog.showModal()` em um portal, com título acessível e botão de fechamento. O título recebe foco ao abrir, preservando a leitura inicial e evitando abrir automaticamente o teclado móvel.
- [W3C — WCAG 2.2, mensagens de status](https://www.w3.org/TR/WCAG22/#status-messages): status deve ser identificável por tecnologia assistiva sem mover foco. Conversa usa `role=log` e região viva educada; andamento usa `role=status`.
- [W3C — WCAG 2.2, relações de informação](https://www.w3.org/TR/WCAG22/#info-and-relationships): tabelas conservam cabeçalhos de linha/coluna e nome acessível; métricas usam listas de descrição (`dl`, `dt`, `dd`).

As escolhas de apresentação abaixo são decisões de produto derivadas dessas restrições e do contexto do portal; não são resultados de avaliação com usuários.

## Decisões implementadas

1. Nexo aparece como um painel responsivo sobre o portal, acionado por botão com nome acessível. A marca da federação continua sendo aplicada pelos tokens runtime.
2. O início oferece três perguntas concretas; sugestões do servidor permitem continuar uma consulta sem exigir vocabulário técnico. O texto explica mês/ano e a possibilidade de continuar com outro período.
3. Respostas mostram resumo, métricas em cards ou EJs em tabela compacta, sem recalcular indicadores. Listas longas têm busca local e expansão; a busca opera apenas nas linhas retornadas e informa esse limite.
4. Fonte e período acompanham o resultado. Unidade pode ser específica por indicador, evitando representar faturamento como simples número ou CSAT como moeda.
5. Interromper cancela a espera no cliente; tentar novamente reutiliza a pergunta e seu contexto; limpar descarta a conversa. Isso não promete cancelar uma requisição já processada no provedor.
6. Fechar preserva histórico/draft somente em memória enquanto o componente estiver montado. A identidade combina usuário e claims de federação/papel, sem usar token completo como chave normal; refresh de token preserva a conversa. Troca de identidade desmonta o histórico e aborta a espera anterior. A partição local não autoriza acesso: JWT e RLS continuam sendo verificados no backend.
7. Contexto enviado ao backend é apenas o plano estruturado retornado pela consulta anterior, sem dados anteriores das EJs. Não há persistência em localStorage/sessionStorage.
8. O mascote é decorativo, usa `aria-hidden` e não ocupa o lugar da fonte ou da resposta. A animação de carregamento respeita redução de movimento.

## Verificação

Build TypeScript/Vite e ESLint executados pelo agente de frontend. Verificação visual e com teclado no navegador coordenada pelo agente principal. Esses checks não equivalem a auditoria WCAG ou à validação empírica do TCC.
