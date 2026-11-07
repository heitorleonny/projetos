# Nexo: pesquisa e decisões do assistente de dados

Data: 04/10/2026. Escopo: melhorar o caminho de leitura em linguagem natural do Portal das Federações, preservando seu isolamento e seus cálculos.

## Fontes primárias e decisão

A documentação de [Structured Outputs do OpenRouter](https://openrouter.ai/docs/guides/features/structured-outputs) descreve a geração de objetos conforme JSON Schema para modelos compatíveis. O portal usa um plano limitado e valida novamente com Pydantic: o fornecedor interpreta a pergunta, mas não executa ferramentas nem SQL. O gateway exige suporte aos parâmetros solicitados; todas as propriedades do schema estrito são obrigatórias e os parâmetros opcionais aceitam `null`.

O [guia de RLS do Supabase](https://supabase.com/docs/guides/database/postgres/row-level-security) e a documentação de [chaves de API](https://supabase.com/docs/guides/getting-started/api-keys) explicam a combinação de chave pública com JWT do usuário e o privilégio de bypass das chaves secretas. Por isso, a consulta recebe exclusivamente o cliente autenticado da requisição e o tenant extraído da identidade. Nem o plano nem o contexto possuem campos para tenant, papel, token ou SQL.

A decisão continua sendo catálogo parametrizado. Text-to-SQL livre aumentaria a superfície de execução sem melhorar as garantias necessárias neste recorte. O catálogo reutiliza os services de indicadores, ranking, cluster, ritmo e SDE. Isso impede a criação de fórmulas alternativas pelo modelo. Estas são inferências arquiteturais a partir das fontes, e não resultados experimentais sobre produtividade ou escalabilidade.

## Melhorias implementadas

1. Continuação limitada: o frontend pode enviar o último plano tipado para perguntas como “e em agosto?” ou “e no cluster 2?”. O contexto é tratado como não confiável e só referencia filtros. Não contém conversa bruta nem resultados do banco; não concede autoridade e não altera a federação autenticada.
2. Cluster oficial do ano em todo catálogo; busca literal por trecho de nome apenas para EJs fora do zero. A busca não decide identidade nem aceita curingas. Filtros sem suporte não são silenciosamente ignorados.
3. SDE em três cenários e ritmo mensal por mês, calculados pelos services existentes. Indicadores mostram seis medidas, com unidade por linha, para evitar tratar contagens e CSAT como dinheiro.
4. Recuperação de ausência de dados: a cobertura é verificada para o recorte e o mês solicitado. A resposta informa meses com cobertura completa e sugere retomá-los, sem substituir o período silenciosamente. Nenhum resultado numérico é enviado ao modelo para redigir a resposta.

## Contrato compatível

`POST /api/v1/ia/perguntar` continua aceitando `{pergunta}` e passa a aceitar `contexto` opcional com um `PlanoConsulta`. A resposta preserva os campos antigos e acrescenta `contexto`, `sugestoes` e `linhas[].unidade` opcional. As ferramentas são `fora_do_zero`, `indicadores_rede`, `ranking`, `sde`, `ritmo_mensal`, `recusar`. Os filtros adicionais são `cluster` (1–5) e `busca` (2–80 caracteres).

O frontend mantém o contexto apenas na sessão de conversa atual e deve descartá-lo ao trocar a identidade/federação. O servidor revalida o objeto a cada chamada; o contexto não é um token de autorização.

## Evidência e limites

A bateria determinística de IA possui 69 casos aprovados, sem pulados, incluindo PostgreSQL real e filtros de cluster/busca com a defesa Python removida: modelo hostil nas cinco ferramentas e remoção do filtro Python para verificar a RLS independentemente. Inclui rejeição de identidade/SQL no contexto, filtros inválidos, busca por nome dentro do tenant, cobertura por cluster, recuperação de mês e unidades mistas. Executar na raiz `projetos/portal_fejepe`: `../.venv/bin/python -m pytest tests/test_ia.py tests/test_ia_rls.py -q -rs`.

O corpus de avaliação do modelo real passou de 12 para 19 perguntas, cobrindo cluster, busca, SDE, ritmo, continuidade e instrução hostil em contexto. A execução real e seu resultado são registrados separadamente pela integração. A aprovação dos testes determinísticos não garante a interpretação correta de qualquer frase: modelo e prompt precisam continuar avaliados. O sistema não implementa previsão de risco, séries temporais livres, ranking ascendente ou escrita.
