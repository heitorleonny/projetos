# ADR-005 — Nexo: conversa delimitada e identidade do assistente

Data: 04/10/2026. Status: implementado localmente; validação registrada separadamente.

## Problema e decisão

O primeiro assistente respondia perguntas isoladas com um catálogo pequeno e uma lista extensa num painel estreito. A evolução precisa ajudar o gestor a explorar os dados sem conceder ao modelo uma nova fronteira de acesso. O nome de produto passa a ser **Nexo**, com o descritor **Pergunte à sua rede** e um **vaga-lume** como mascote. O SVG nativo segue as cores da federação e tem uma cauda com um nó de rede; é decorativo e o controle fornece seu nome acessível.

Mantemos consultas pré-definidas parametrizadas, conforme ADR-004. O modelo escolhe um plano fechado; os services executam e compõem os valores. O catálogo passa a incluir EJs fora do zero, indicadores, ranking, SDE e ritmo mensal, com cluster oficial do ano. Busca literal por nome é suportada nas EJs fora do zero. Requisitos fora do catálogo precisam ser recusados; não podem ser descartados para produzir uma resposta aparentemente correta.

Continuações recebem somente o último plano tipado, com período, ferramenta e filtros limitados. O plano é revalidado e tratado como entrada não confiável. Ele não contém JWT, tenant, SQL nem resultados do banco. Perguntas novas prevalecem sobre o contexto; o backend resolve ano e mês omitidos usando a configuração e os dados autorizados. Um mês sem cobertura completa permanece sem resposta numérica; sugestões de meses completos auxiliam a recuperação sem substituição silenciosa.

## Experiência de uso

O painel apresenta a identidade, exemplos, fontes, período e recorte consultado. Agregados aparecem em cartões e EJs em tabela com busca visual e expansão. O usuário pode interromper a espera, repetir uma falha e limpar a conversa. O histórico fica apenas na memória da página, persiste ao fechar e é descartado na troca de identidade, federação ou papel. O diálogo nativo mantém o fundo inerte e gerencia foco e Escape.

A pergunta e o plano de continuação são enviados ao fornecedor configurado. Os resultados do banco não são enviados ao modelo; as respostas factuais continuam determinísticas. Interromper no navegador cancela a espera local, mas não garante cancelamento do processamento já iniciado no fornecedor.

## Fronteira de segurança e limites

O tenant é obtido da identidade validada pelo backend. O cliente Supabase da requisição usa chave pública e JWT do usuário; o catálogo não aceita seleção de federação, SQL ou escrita. RLS deve continuar isolando consultas mesmo quando a interpretação for hostil ou os filtros Python forem removidos nos testes. Recusa textual e JSON Schema são controles complementares, não prova de isolamento nem de fidelidade semântica.

Este fluxo é uma interpretação seguida de uma consulta, sem ciclo de execução autônomo. Isso reduz a superfície de ferramentas e permite avaliar interpretação, valores e isolamento separadamente. A troca de modelo continua configurável por provedor compatível, mas exige repetir a avaliação: suporte a schema não assegura equivalência de comportamento.

Não há previsão de risco, alteração de dados, consulta por cidade, série temporal livre ou resposta aberta sobre qualquer assunto. Não foi realizada pesquisa comercial de marca ou avaliação com usuários. A evidência local não demonstra robustez universal, desempenho sob carga ou custo operacional ilimitado.

## Fundamentação e texto para o artigo

A revisão paralela está em [pesquisa-identidade-assistente.md](pesquisa-identidade-assistente.md), [pesquisa-assistente-backend.md](pesquisa-assistente-backend.md) e [pesquisa-assistente-ux.md](pesquisa-assistente-ux.md), com fontes primárias da Anthropic, OWASP, Supabase, OpenRouter e W3C. A evidência final está em [verificacao-nexo-2026-10-04.md](verificacao-nexo-2026-10-04.md).

> O Nexo utiliza um modelo de linguagem como intérprete de consultas parametrizadas, sem acesso direto ao banco. A saída estruturada identifica uma ferramenta do catálogo e seus argumentos, que são validados e executados pelos services sob a identidade autenticada do usuário. Continuidade conversacional é representada por um plano limitado, e não por resultados recuperados ou credenciais. A federação permanece uma propriedade da autorização, independente da pergunta ou da interpretação do modelo. Assim, a IA constitui um caminho adicional de leitura submetido à mesma fronteira multi-tenant, cuja eficácia é verificada por tentativas adversariais e testes com RLS real.

## Adendo de 07/11/2026 — nome Lamps e prompt reorganizado

Por decisão de Heitor, o assistente passa a se chamar **Lamps** em todo o portal:
prompt, botão, painel, tour e mensagens de limite. O descritor "Pergunte à sua rede" e o
mascote vaga-lume continuam. Documentos anteriores mantêm "Nexo" como registro da época;
identificadores internos (`NexoMascot`, `data-tour="nexo"`, `docs/nexo-*`) não mudaram.

Trade-off registrado: "Lamps" era o nome interno da FEJEPE (ADR-004, decisão 1). Em
outras federações o assistente aparece com esse nome. Se isso pesar, o nome pode virar
configuração por federação, como logo e cores; não foi feito agora.

O prompt de sistema saiu de `adaptadores/compativel.py` para `app/ia/prompt.py`, de modo
que qualquer adaptador reaproveite o mesmo texto. Foi reorganizado em seções (formato,
regras prioritárias em ordem, catálogo com exemplos, campos e contexto) e passou a cobrir:
- limite pedido ("top 5");
- mês sem ano;
- "faturamento colaborativo" → `colab`;
- datas relativas → `esclarecer` com `periodo`, porque o modelo não sabe a data de hoje;
- pergunta e contexto como dado, nunca instrução.

O contrato `PlanoConsulta` não mudou. `tests/test_ia_prompt.py` exige que todo valor
aceito pelo schema apareça no prompt. A exceção é `ordem="desc"`: o prompt pede `null`
para os maiores valores. **A mudança de prompt exige nova avaliação com modelo real**;
nenhum resultado anterior vale para este texto.
