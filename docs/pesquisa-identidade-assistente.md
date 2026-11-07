# Identidade e revisão independente do assistente de dados

Data: 04/10/2026. Natureza: recomendações para a evolução local do portal, baseadas no CONTEXTO-TCC.md, leitura do código e fontes primárias consultadas. Não é avaliação com usuários nem prova universal de segurança.

## Identidade recomendada

**Nexo**, assistente de dados da sua federação. A palavra comunica conexão entre a pergunta, a rede e a evidência. É curta, pronunciável em português e não pertence ao vocabulário de uma federação específica. Esta escolha é uma decisão de produto; não foi feita pesquisa de marca ou disponibilidade comercial.

Mascote: **um vaga-lume geométrico**, com corpo arredondado, antenas discretas e cauda luminosa formada por um pequeno nó de rede. A luz representa encontrar um dado verificável. Expressão cordial e calma; evitar aparência de autoridade onisciente. O texto de apresentação pode ser: “Sou o Nexo. Vamos entender os dados da sua rede?”

Alternativas de nome:

| Nome | Sentido | Limitação |
|---|---|---|
| Nexo | Relação entre dados e rede | Palavra relativamente comum |
| Elo | Vínculo entre empresas e federação | Pode parecer nome de organização |
| Lume | Clareza na leitura de indicadores | Pode lembrar a metáfora anterior de Lamps |

Alternativas de espécie:

| Mascote | Coerência | Limitação |
|---|---|---|
| Vaga-lume | Orientação discreta por uma luz; recomendação | Precisa preservar leitura em tamanho pequeno |
| Pássaro tecelão | Redes, construção coletiva, acompanhamento | Mais detalhes para um ícone pequeno |
| Polvo | Conecta diversos indicadores | Pode sugerir ações/autonomia que o assistente não possui |

Recomenda-se um componente SVG nativo, com cores do tema por tenant. É leve, nítido em botão e painel, fácil de ajustar e de animar com respeito a `prefers-reduced-motion`. Usar `aria-hidden` quando decorativo e texto acessível no botão. Uma ilustração raster gerada pode enriquecer uma tela futura, mas acrescenta manutenção, peso e variantes de tema sem melhorar a interação principal. A implementação visual não precisa de um modelo gerador de imagem.

## Arquitetura a preservar

A implementação observada separa interpretação probabilística e execução determinística: pergunta → `PlanoConsulta` fechado → ferramenta do catálogo → services existentes → resposta factual. O adaptador recebe a pergunta e instruções; não recebe resultados de banco ou JWT. O catálogo não aceita SQL, tenant ou papel como parâmetros. `get_supabase` cria cliente por requisição e propaga o JWT para o PostgREST; o router exige tenant antes de executar. Esses controles são coerentes com a recomendação da OWASP de manter autorização e privilégio mínimo fora do modelo. [OWASP, prevenção de prompt injection](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html).

Manter consultas parametrizadas em vez de SQL livre. Ampliar capacidade por ferramentas com finalidade clara, parâmetros limitados e cálculo nos services. Fluxos previsíveis permitem avaliar a interpretação separadamente da correção dos dados; não há necessidade demonstrada de uma orquestração autônoma para o catálogo atual. [Anthropic, Building effective agents](https://www.anthropic.com/engineering/building-effective-agents).

RLS continua sendo a fronteira independente. Uma recusa do modelo é comportamento útil, mas não substitui isolamento. Controles por tenant e verificações devem permanecer mesmo quando o modelo interprete um pedido hostil como consulta válida. Chaves privilegiadas podem contornar RLS, conforme a documentação do Supabase. [Supabase, Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security).

## Melhorias priorizadas

1. **Período e contexto visíveis.** Mostrar federação atual, ano/mês efetivamente consultados, definição da métrica e cobertura. Se mês omitido, declarar que foi usado o último disponível; mês solicitado sem dados nunca deve virar outro silenciosamente. No código observado, MAX(mês) pode escolher um mês com cobertura incompleta; oferecer meses disponíveis ajuda a recuperação sem falsificar completude.
2. **Consultas úteis com limite claro.** Expandir filtros de cluster, situação de faturamento e ritmo a partir dos services, com parâmetros validados localmente. Não aceitar filtros que o catálogo ignora. Perguntas como “melhores EJs” devem pedir uma métrica em vez de assumir faturamento.
3. **Resultados legíveis.** Separar resumo, valores, definição e links para EJs. Listas grandes precisam de expansão/paginação visual; não despejar centenas de linhas num painel estreito. Exemplos de pergunta devem usar períodos disponíveis do tenant, evitando um exemplo de outubro quando só existe setembro.
4. **Conversa honesta.** Histórico visual não é memória conversacional. Se acrescentar continuação, transportar apenas contexto estruturado do plano anterior, validado novamente e sem tenant escolhido pelo modelo. Explicitar até onde perguntas anteriores influenciam a próxima.
5. **Acessibilidade e recuperação.** O painel atual tem backdrop, Escape e foco retornando ao acionador. Contudo, `aria-modal=true` exige fundo inerte para todos os usuários. Usar modal nativo ou tornar o fundo inerte; confirmar teclado, leitor de tela e viewport pequeno. [W3C WAI, Modal Dialog Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).
6. **Avaliação ao mudar catálogo/modelo.** Ampliar perguntas-ouro com ambiguidades, sinônimos, “sem vender no mês” versus “fora do zero no acumulado”, cobertura parcial e tentativa de ampliar tenant. Separar acerto da interpretação, correção numérica e isolamento. Registrar latência/tokens e limites observados; não concluir robustez geral de uma amostra de 12 perguntas. A Anthropic recomenda avaliações realistas, resultados verificáveis e métricas de chamadas, erros e consumo. [Anthropic, Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents).

## Riscos concretos e limites desta revisão

- O modelo pode continuar escolhendo uma ferramenta válida para a intenção errada. O schema assegura forma, não fidelidade semântica. Testes de perguntas fora do catálogo precisam permanecer.
- A pergunta enviada ao provedor pode conter informação sensível digitada pelo usuário, mesmo sem resultados do banco. Manter aviso curto e não registrar perguntas/respostas desnecessariamente.
- O histórico do painel observado remonta a cada mudança de `access_token`, inclusive refresh normal. Uma chave de identidade e tenant evita perder histórico em refresh; deve continuar limpando dados ao mudar sessão/tenant.
- Metadados de erro ficam genéricos ao usuário, mas falhas do banco/catálogo precisam de observabilidade interna sem segredos para serem diagnosticadas.
- Consulta só de leitura reduz impacto sobre o banco, mas chamadas ao provedor podem gerar consumo. Limites por usuário/tenant devem ser uma evolução operacional, sem prometer custos ilimitados.
- Revisão estática feita antes da conclusão das alterações paralelas. Recomendações precisam ser confrontadas com o diff final e os testes; nenhum resultado de teste novo é afirmado neste documento.
