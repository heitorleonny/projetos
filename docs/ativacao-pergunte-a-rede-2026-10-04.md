# Ativação local — Pergunte à Rede (04/10/2026)

Status: **ativado no backend da demo local**, em `http://127.0.0.1:8000`.
O portal em `http://localhost:5173` consome a rota `/api/v1/ia/perguntar`.
A configuração e a chave permanecem em `portal_fejepe/.env`, ignorado pelo Git.
Nenhuma chave ou token aparece nos relatórios.

## Configuração efetivamente avaliada

```dotenv
IA_PROVEDOR=openrouter
IA_MODELO=nvidia/nemotron-3-super-120b-a12b:free
IA_TIMEOUT_SEGUNDOS=20
IA_MAX_TOKENS_SAIDA=2048
IA_RACIOCINIO=desativado
```

O catálogo do OpenRouter foi consultado durante a ativação e anunciava essa
variante com preços de entrada e saída iguais a zero, `structured_outputs`,
`response_format` e `max_tokens`. Disponibilidade e limites podem mudar:
[catálogo oficial](https://openrouter.ai/api/v1/models).
O desligamento de raciocínio é uma opção do servidor para modelos que permitem
isso; segue o contrato da [documentação do gateway](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).

## Ajustes observados na ativação

O modelo inicial Liquid não interpretou corretamente a pergunta de outubro.
Foi substituído pela variante gratuita acima. A primeira avaliação do novo
modelo preservou isolamento nos 12 casos, mas acertou ferramenta em 10/12 e
parâmetros em 9/12: simplificou uma pergunta com filtro de cluster, assumiu uma
métrica para “melhores EJs” e preencheu o ano omitido na interpretação.

Foram reforçadas as instruções de recusa de filtros fora do catálogo e de
perguntas ambíguas, além de manter `ano=null` quando o período é omitido. O
backend resolve o padrão. O gateway agora recebe o nome canônico `max_tokens`,
compatível com os parâmetros anunciados pelos provedores.

O resultado inicial foi preservado em
`ia-avaliacao-2026-10-04-ativacao-inicial.json`; o resultado após ajuste está em
`ia-avaliacao-2026-10-04-ativacao.json`.

## Resultado medido

- 12/12 casos com ferramenta, parâmetros e resposta corretos; 0 erros.
- Recusas corretas em todos os casos que exigiam recusa; isolamento por IDs em
  todos os casos. 5.829 tokens de entrada e 443 de saída no relatório final.
- Backend reiniciado com a configuração final, sem usar credencial administrativa
  para consultar os dados.
- Quatro chamadas HTTP reais, usando login da demo, JWT do usuário e PostgREST:
  consulta fora do zero e tentativa de consultar todas as federações, tanto para
  FEJEPE quanto para FEJEMG. Consultas retornaram dados do próprio tenant;
  tentativas adversariais foram recusadas. Sem login: HTTP 401.
- Suíte final: **430 testes passaram; 0 falharam; 0 foram pulados**.
  Quatro avisos de depreciação da biblioteca Supabase.

Evidência HTTP, sem dados de EJs: `ia-ativacao-local-2026-10-04.json`.

## Limites da interpretação dos resultados

O conjunto de 12 perguntas foi utilizado para ajustar o prompt: é uma avaliação
de desenvolvimento, não um conjunto independente nem prova de acurácia geral.
A demonstração de isolamento inclui também os testes adversariais em PostgreSQL
real com um provedor hostil roteirizado, inclusive sem o filtro Python. A
avaliação HTTP não constitui teste visual do browser. Não foi acessada produção.
