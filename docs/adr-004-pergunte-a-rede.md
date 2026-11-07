# ADR-004 — Pergunte à Rede: linguagem natural sob a fronteira de tenant

- Data: 04/10/2026
- Status: implementada no código; avaliação com modelo real pendente de configuração.
- Escopo: perguntas em português (S5–S6). Não altera a monografia nem fórmulas estratégicas.

Registro da versão inicial. Identidade, catálogo e continuidade evoluíram no
[ADR-005 — Nexo](adr-005-nexo.md). A ativação inicial e a validação desta evolução
estão em documentos separados; o estado acima reflete o momento desta decisão.

## Contexto e questões

O botão de conversa exibia apenas o placeholder Lamps, nome interno da FEJEPE.
A funcionalidade acrescenta um caminho de leitura ao Portal das Federações. A
questão de pesquisa exige que esse caminho herde o isolamento: uma interpretação
maliciosa ou incorreta não pode conceder ao agente dados que o gestor não poderia ler.

## Decisões

1. Nome exibido: **Pergunte à Rede**, sem mascote ou referência particular de federação.
2. **Consultas pré-definidas parametrizadas (opção 2)**. O modelo devolve um plano
   JSON com uma ferramenta e seus parâmetros. Pydantic valida ferramenta, ano,
   mês, critério e limite; campos extras são proibidos. Nenhum campo representa
   SQL, federação, papel ou identidade.
3. Catálogo inicial: `fora_do_zero`, `indicadores_rede`, `ranking` e `recusar`.
   As ferramentas usam `empresa_service.listar_empresas`,
   `rede_service.calcular_indicadores_rede` e `rede_service.gerar_ranking`.
   O predicado fora do zero usa faturamento acumulado > 0, conforme o glossário;
   não exige vendas no mês. SDE, cluster e tracking não são reimplementados.
4. O cliente Supabase é o da requisição, com chave pública e JWT validado do usuário.
   O tenant deriva do claim autenticado. A rota de IA exige esse claim mesmo quando
   a compatibilidade das demais rotas permite sua ausência. O papel plataforma não
   amplia o acesso a indicadores de outras federações.
5. As chaves secretas modernas e JWTs cujo papel não seja `anon` são recusados na
   configuração do cliente público. A varredura de chave privilegiada inclui `app/ia/`.
6. O mês omitido é o último mês disponível **na própria federação** e no ano indicado
   (ou `ANO_DEFAULT`). Um mês explícito jamais é substituído. A cobertura precisa
   incluir todas as EJs do cadastro; ausência ou cobertura parcial gera `sem_dados`,
   nunca uma lista de zeros por preenchimento. Essa regra pode recusar agregados se
   uma EJ cadastrada não tiver monitoramento: a UI informa a cobertura.
7. Uma pergunta independente = uma interpretação + no máximo uma ferramenta.
   Limites: pergunta de 1.000 caracteres, saída do modelo configurável (padrão 1.024 tokens, máximo 4.096), timeout
   configurável (padrão 20s, máximo 60s), ranking de no máximo 100 EJs. As leituras
   usam a paginação existente; a listagem fora do zero percorre todas as páginas.
8. A resposta factual é composta pelo backend. Não existe uma segunda chamada ao
   modelo para redigir a resposta: resultados de banco, CNPJ, contatos, JWT e chave
   Supabase não são enviados ao provedor. A pergunta escrita pelo usuário é enviada;
   ela pode conter informação que o próprio usuário digitou. `store` não é usado
   como garantia de retenção: a política efetiva depende do fornecedor [CONFIRMAR].
9. **OpenRouter como provedor inicial**, escolhido para trocar modelos pagos e gratuitos
   por configuração (`IA_MODELO`). `IA_PROVEDOR=openai` usa a API direta;
   `compativel` permite outro endpoint. Interface `Provedor` substituível e
   primeiro adaptador HTTP compatível com Chat
   Completions e JSON Schema estrito. Modelo, endpoint e chave são configuração do
   servidor (`IA_*`). O contrato de saída estruturada segue a
   [documentação oficial OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs).
   No OpenRouter, a requisição exige `provider.require_parameters=true`, conforme
   [documentação de saídas estruturadas](https://openrouter.ai/docs/guides/features/structured-outputs),
   para não encaminhar a um endpoint que ignore os parâmetros. Modelos com
   variante gratuita listada usam o sufixo `:free`, conforme
   [documentação de variantes gratuitas](https://openrouter.ai/docs/guides/routing/model-variants/free).
   A disponibilidade e compatibilidade devem ser verificadas a cada troca.
   Outros protocolos exigem adaptador novo; endpoint compatível precisa suportar
   o schema e `max_completion_tokens`. Nenhum modelo fica fixo no código.
10. Registro de execução em log: identidade, tenant, modelo, ferramenta, status,
    tokens e duração, sem pergunta nem dados financeiros. Os logs dependem da
    configuração de logging do servidor. Persistência de uso com RLS e créditos
    mensais continua pendente; esta versão não afirma aplicar limites de plano.

## Alternativas rejeitadas

| Alternativa | Benefício | Motivo para não adotar agora |
|---|---|---|
| Text-to-SQL livre | Maior flexibilidade | Acrescenta executor SQL, controle de views, transação read-only, timeout e possibilidade de duplicar fórmulas; amplia a superfície a verificar |
| Híbrida (catálogo + SQL) | Responde perguntas além do catálogo | Mantém os riscos e o custo de verificação do executor SQL, sem evidência de que o catálogo seja insuficiente |
| Modelo redige a resposta após receber os dados | Texto mais flexível | Exige nova chamada, expõe mais dados e dificulta comprovar que números e nomes exibidos vieram dos services |

A contrapartida da opção escolhida é explícita: perguntas por cidade, cluster,
EJ específica, comparação, SDE, previsão ou escrita são fora do catálogo. Não há
memória conversacional: cada pergunta deve conter os parâmetros necessários.
A recusa semântica depende da interpretação, enquanto o isolamento independe dela.
Um modelo que interprete mal uma injeção pode consultar os dados do próprio tenant;
mesmo assim não pode escolher outra identidade nem devolver uma resposta textual livre.

## Consequências e avaliação

A contribuição investigada é a preservação da fronteira de tenant em uma leitura
mediada por IA. A correção semântica do modelo e o isolamento são métricas distintas.
Testes sem rede roteirizam inclusive um modelo hostil; testes em PostgreSQL real
verificam dados e agregados com e sem o filtro em Python. Não simulam a política RLS.

A avaliação com modelo real usa 12 perguntas-ouro em
`app/ia/avaliacao/perguntas.json`, incluindo ausência de período, ambiguidade,
filtro não suportado e injeções. O runner calcula o gabarito pelo catálogo usando o
plano-ouro, registra acerto de ferramenta, parâmetros, resposta, recusa, tokens e
latência; falha se houver erro ou divergência. Não grava nomes, números financeiros
ou tokens de autenticação. A métrica de IDs do runner complementa os testes de
agregados em PostgreSQL; não prova isoladamente ausência de vazamento em agregados.
Custo monetário não é estimado, porque modelo e tarifa ainda não foram definidos.

### Trecho sugerido para a monografia (adaptar por Heitor)

> Para a consulta em linguagem natural, adotou-se um catálogo de operações de
> leitura parametrizadas. O modelo interpreta a intenção e o período, mas não
> produz comandos SQL nem determina o contexto de federação. A execução reutiliza
> os serviços de cálculo existentes e o cliente autenticado da requisição, mantendo
> a política de Row Level Security e o filtro explícito por tenant como camadas
> independentes. Essa escolha restringe a variedade de perguntas respondidas em
> troca de um contrato verificável de acesso e de uma única fonte de verdade para
> as regras estratégicas. A avaliação distingue a interpretação correta da pergunta
> da preservação do isolamento, incluindo tentativas adversariais em que o modelo
> aceita instruções maliciosas. [CITAR: isolamento multi-tenant e ameaças de prompt injection]

Não apresentar resultados com modelo real enquanto o runner não tiver sido executado.
