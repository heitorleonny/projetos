# A5 — preparação de regressão controlada

Implementado `scripts/regressao_api.py`: somente GET em indicadores, SDE, ritmo
mensal e ranking de faturamento (máximo 100),
período obrigatório, tolerância absoluta declarada para escalares (padrão 0,01;
listas estruturadas de SDE/ritmo/ranking exigem igualdade exata), HTTPS obrigatório
fora de loopback e redirects recusados para não repassar JWT. Tokens vêm apenas
de `REGRESSAO_TOKEN_ORIGEM` e `REGRESSAO_TOKEN_DESTINO`. O relatório contém nomes
das métricas e status, sem valores, URLs ou identidades.

Execução após configurar JWTs próprios de leitura no ambiente:

```sh
python3 scripts/regressao_api.py \
  --origem https://API-ORIGEM/api/v1 --destino https://API-DESTINO/api/v1 \
  --ano 2026 --mes 10 --tolerancia 0.01 \
  --saida artifacts/regressao-indicadores.json
```

Saída 0: comparação sem diferenças; 1: diferenças encontradas ou erro. A saída de
erro omite detalhes privados. A API original precisa ser compatível com o contrato
de `/rede/indicadores`; se não for, preparar um adaptador explícito sem alterar
semântica. Confirmar mesma federação, versão de dados e período antes da execução.
O script não verifica a identidade do tenant por conta própria e não compara todas
as telas. Não chamar este subconjunto de regressão integral.

Verificação: sete testes sintéticos passaram, sem falhas ou pulos, com
`python3 -m unittest discover -s scripts -p test_regressao_api.py -v`. Cobrem
tolerância absoluta, ausências/null, valores não finitos, URLs, redirect, período
incompatível e projeção privada de SDE/ranking.

Não foi acessada produção. A5 continua pendente de URLs, contas de leitura e
congelamento equivalente dos dados. Cada divergência deve ser examinada em ambiente
privado e classificada como correção deliberada, diferença da fonte ou defeito. A
tabela acadêmica deve usar exemplos sintéticos ou agregados autorizados; nunca
publicar automaticamente resultados reais individuais.
