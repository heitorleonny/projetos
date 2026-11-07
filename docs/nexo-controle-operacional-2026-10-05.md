# Controle operacional de chamadas do Nexo

Data: 05/10/2026. Defaults: **6 chamadas por usuário e 30 chamadas por federação, em janela fixa de um minuto**. É uma política operacional para conter bursts e concorrência, independente dos créditos mensais ou do plano comercial. Não impõe teto mensal de gasto do fornecedor.

## Caminho de execução

A rota envolve o provedor em `ProvedorComLimite`. A reserva ocorre imediatamente antes de `interpretar`: recusas e esclarecimentos resolvidos localmente não consomem uma chamada. Tentativas aceitas de interpretar contam mesmo se o fornecedor falhar; devolver a reserva permitiria contornar o limite com repetição de erros. Falha do RPC ou reserva sem booleano válido impede a chamada ao modelo.

O RPC `reservar_consulta_ia()` não recebe argumentos. Ele usa `auth.uid()` e o tenant do JWT, confirma `usuario.ativo` e o vínculo atual no banco e ignora o claim de papel. Identidade sem vínculo atual gera 403. Esgotamento da janela do portal gera 429 com `Retry-After: 60`; indisponibilidade ou quota do fornecedor continua sendo 503 e mensagem distinta.

As reservas de uma federação são serializadas por um lock de transação. O incremento dos dois contadores usa UPSERT na mesma transação. Assim, múltiplos processos do backend e chamadas simultâneas compartilham o mesmo limite. Uma federação não consome o contador da outra. Cada usuário usa um registro da janela atual e compartilha o registro da federação; os registros são reutilizados a cada minuto. Não são armazenados prompt, resposta, resultados ou histórico de janelas.

## Privilégios

A migração 18 cria `ia_limitador`: papel dedicado sem login, superuser, bypass de RLS, criação de banco/roles, replicação ou herança. O RPC é SECURITY DEFINER desse papel, com search path fixo e nomes qualificados. Ele pode ler somente o próprio registro de usuário, ler configuração operacional e atualizar os contadores; não pode ler dados de monitoramento da rede. Como o schema `auth` pertence ao GoTrue na demo, dois helpers privados SECURITY DEFINER do administrador devolvem apenas UUID do usuário e tenant textual. O papel limitador não depende de USAGE no schema `auth`. Os helpers não devolvem o JWT e não podem ser executados por `anon` ou `authenticated`.

As tabelas de controle têm RLS e FORCE RLS. `anon` e `authenticated` não têm leitura/escrita direta; somente `authenticated` pode executar o RPC. Os valores e a identidade não podem ser substituídos por parâmetros. A migração concede membership temporária ao administrador para atribuir o owner da função em PostgreSQL sem superuser, e a retira ao final. O administrador do banco possui políticas explícitas para operar as tabelas mesmo sob FORCE RLS. Nenhuma service key é usada no caminho de request.

## Ajustar os defaults

Somente um administrador SQL autorizado pode executar, por exemplo:

```sql
UPDATE public.ia_controle_config
SET limite_usuario = 6, limite_federacao = 30
WHERE singleton;
```

O RPC lê a configuração a cada reserva, sem reiniciar o backend. Os defaults devem ser reavaliados com uso real e os limites do modelo escolhido. Uma janela fixa permite duas rajadas próximas à virada do minuto; não é uma janela móvel. A política não altera fórmulas de negócio nem créditos comerciais. A migração é aditiva e idempotente, preservando configurações existentes no seed.

## Evidência

26 testes de controle passaram com PostgreSQL real, incluindo 24 chamadas concorrentes do mesmo usuário (somente 6 aceitas), 42 chamadas distribuídas entre sete usuários (somente 30 aceitas), isolamento de federação, usuário inativo, vínculo alterado, identidade ausente, papel privilegiado no claim sem ampliação, reuso da janela, ajuste SQL protegido e bloqueio de leitura/escrita direta do cliente. Testes HTTP comprovam 429 distinto do fornecedor e ausência de consumo nas respostas locais. A bateria de IA/RLS/controle completa passou em 113 casos, sem pulados.

Comando: `../.venv/bin/python -m pytest tests/test_ia.py tests/test_ia_rls.py tests/test_ia_limites.py -q -rs --require-lab`, a partir de `projetos/portal_fejepe`.

## Compatibilidade do schema auth do GoTrue

A validação live da demo identificou que o administrador PostgreSQL não é dono do schema `auth`; tentar conceder USAGE ao limitador não produzia a autorização necessária. A migração deixou de alterar privilégios de `auth` e passou a usar os dois helpers mínimos em `public`. Testes adicionais verificam EXECUTE negado ao cliente e reserva funcional com USAGE de `auth` explicitamente removido do limitador no laboratório. Após aplicar a migração no laboratório e na demo, a integração confirmou HTTP 200 com reserva `true` no RPC via JWT de usuário da FEJEPAR no Supabase real. A bateria final de IA/RLS/controle passou em 113 casos, nenhum pulado, incluindo os testes sem USAGE em auth e de helpers privados.
