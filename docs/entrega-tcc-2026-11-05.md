# Mapa de fechamento do Portal — 05/11/2026

Pedido de Heitor: revisar a escrita enquanto o portal é preparado com PostgreSQL
próprio e Docker, sem Supabase. O recorte de 23/10 continua: multi-tenancy,
indicadores, eventos, ingestão e Nexo. Geração de dashboards por IA permanece fora.
Este documento distingue código existente, verificação técnica e avaliação humana.

## Ordem de fechamento

| Prioridade | Frente | Estado observado e próximo critério |
|---|---|---|
| P0 | PostgreSQL + autenticação + Docker | Migração em andamento nesta sessão. Substituir Auth/PostgREST, manter papéis/RLS/filtro independente; subir imagens e verificar login, isolamento e persistência. |
| P0 | Regressão integrada | Docker Desktop voltou a responder nesta sessão. Reexecutar testes sem skips, build/lint e smoke de API; resultados anteriores não validam a nova arquitetura. |
| P0 | Demonstração repetível | Preparar duas federações sintéticas, contas por papel e roteiro de login, branding, indicadores, administração, ingestão e acesso cruzado negado. |
| P0 | Avaliação humana | Não foi encontrada evidência de conclusão das sessões P1–P3 e orientador nos documentos consultados. Executar consentimento, tarefas e análise; fechar capítulo de resultados com fatos coletados. |
| P0 | Coerência do texto | Monografia aberta para o autor. Atualizar arquitetura Supabase → PostgreSQL/autenticação própria depois da validação. Preservar cronologia dos resultados anteriores. |
| P1 | Regras divergentes | Caracterização das cinco funções já existe (`tests/test_caracterizacao.py`); não equivale à aprovação de regras. Resolver apenas divergências que impeçam a demonstração, por decisão do autor, ou explicitar limitações. |
| P1 | Regressão FEJEPE de produção | Scripts/preparação existem; não há prova de execução contra produção nesta sessão. Se a escrita alegar preservação dos números, obter evidência autorizada; caso contrário, restringir a alegação à caracterização sintética/local. |
| P1 | Ingestão núcleo/federação/histórico | Implementação corrente cobre nível EJ. Confirmar necessidade para os objetivos; o schema permitir outros níveis não prova ingestão. Pode permanecer como limitação explícita se fora da demonstração aprovada. |
| P1 | Avaliação do Nexo | Preservar catálogo e isolamento. Separar testes determinísticos de acerto real de interpretação; falta avaliação independente para a alegação mais forte. Não fazer chamadas pagas automaticamente. |
| P1 | Onboarding e decisões arquiteturais | Classificar alterações por categoria e registrar esforço/configuração da segunda federação. Não usar tempo de build como métrica de onboarding. |
| P1 | Versionamento e recuperação | Checkout `feat/painel-admin`, HEAD observado `e84fa5b`, com extensa reorganização não commitada. Preservar. Commit/push e publicação continuam ações separadas. |
| P2 | Hospedagem | Pacote local não prova homologação pública. Se sessões exigirem acesso remoto: escolher destino, configurar HTTPS, backup/restauração e contas; publicar somente quando autorizado. |

P0 é requisito para uma entrega demonstrável; P1 depende das afirmações e do
roteiro final. Não acrescentar funcionalidades comerciais ou geração de dashboards
para fechar o TCC.

## Escrita: pontos que exigem evidência do autor

A leitura dos `.tex` encontrou marcadores relativos a uso atual do portal,
levantamento comparativo do Portal BJ, instrumento de avaliação, sessões P1–P3,
classificação do esforço, regressão de produção e avaliação independente do Nexo.
O código não pode preencher esses resultados por inferência. A monografia não foi
editada nesta tarefa; a revisão está com Heitor.

A data 30/11/2026 consta do contexto local, sem reconfirmação institucional nesta
sessão. Priorizar ambiente/demonstração e avaliação agora, em paralelo à escrita;
congelar novas funcionalidades assim que o roteiro estiver verificável.

## Roteiro mínimo de aceite

1. Subir em volume vazio, aplicar a cadeia de migrações e criar operador sem senha padrão.
2. Criar federações A/B sintéticas e contas admin/membro; autenticar separadamente.
3. Conferir branding e indicadores; solicitar diretamente ID da outra federação e provar bloqueio, também sem o filtro de aplicação no teste de RLS.
4. Importar fixture sintética nacional como admin A; provar que B não muda e que repetir não duplica. Membro não importa.
5. Mudar papel/desativar conta; sessão antiga não conserva privilégios. Sair revoga a sessão.
6. Nexo com provedor falso preserva recorte e rejeita pedido de dados de B. Modelo real é avaliação separada.
7. Reiniciar containers sem apagar volume; contas e cadastros persistem.
8. Registrar ambiente, comandos, passes/falhas/skips e limitações. Realizar sessões humanas separadamente.

## Fontes locais

- `CONTEXTO-TCC.md`, especialmente invariantes e método.
- `ESTADO-PORTAL-PARA-TCC.md`, com estados históricos preservados.
- `docs/retomada-escopo-reduzido-2026-10-23.md`.
- `docs/caracterizacao-2026-10-13.md` e testes correspondentes.
- `docs/pendencias-implementacao-2026-10-13.md`.
- `docs/preparacao-vps-2026-10-13.md`: direção Supabase agora superada pelo pedido.

Resultados desta sessão serão acrescentados após execução; nenhuma tabela de
pendências acima é declaração de aceite humano ou publicação.

## Verificação da base antes da substituição

- Backend em imagem Python 3.12 e PostgreSQL 16 descartável: **580 passaram,
  0 falharam, 0 pulados**, 7 avisos (SDK antigo e cache de pytest).
- Frontend anterior: **20 passaram, 0 falharam, 0 pulados**; lint e build aprovados.
- Calculadora auxiliar: build aprovado.
- Banco novo `portal-federacoes`, separado dos volumes anteriores: migrações 01–23
  aplicadas pelo executor com ledger, após shim 00; segunda execução não reaplicou
  arquivos. Login de laboratório `app_authenticated` desabilitado; `app_ingestao`
  sem superuser/BYPASSRLS e com senha privada.

Esses resultados precedem a troca de autenticação e persistência. Não são os
resultados finais da migração. Logs de trabalho privados em `/tmp/tcc-2026-11-05`.

## Conta inicial

Depois de subir a stack, crie seu operador com senha individual (mínimo 12
caracteres), digitada de forma oculta no terminal:

```sh
docker compose --env-file .env.docker run --rm -it migrate \
  python -m scripts.criar_operador_postgres \
  --email SEU-EMAIL --nome 'Seu nome' --federacao 12
```

O identificador 12 corresponde à FEJEPE no cadastro inicial. Não há conta ou
senha padrão. Convites da administração geram link privado de uso único, válido
por 24 horas; o portal não envia e-mail automaticamente. Trocar a senha revoga
as sessões existentes. Contas antigas do Supabase não são copiadas.

## Participação do Claude

Foi tentada colaboração via bridge seguro, sem resposta ou alteração após cerca
de dez minutos. A chamada foi interrompida; implementação e validação ficaram
com Codex. Não houve revisão concluída pelo Claude.

## Verificação da migração em 05/11/2026

Runtime local substituído por PostgreSQL direto (psycopg), autenticação própria
com PBKDF2, sessões opacas armazenadas por hash, expiração/revogação e convite
local de uso único. SDK Supabase removido do frontend e dependências runtime;
PostgREST permanece somente como biblioteca de tipo de erro compatível, sem
serviço HTTP. API usa login restrito e SET LOCAL ROLE/claims por transação;
credencial de proprietário somente em migração/bootstrap.

`make check`: **582 backend passaram, 0 falhas, 0 pulados**, 3 avisos;
**20 frontend passaram, 0 falhas, 0 pulados**, lint/build e calculadora aprovados.
Inclui integração real de login/logout, expiração, papel atual, desativação,
convite único, troca de senha e RLS sem filtro Python. Stack Docker local subiu;
portal via nginx retornou 200 e rota protegida sem sessão retornou 401.
Não houve navegação autenticada manual, avaliação humana, publicação remota ou
migração de dados/contas antigas. Conta inicial deve ser criada pelo autor pelo
comando documentado em `docs/entrega-tcc-2026-11-05.md`. Monografia preservada.

Pacote: `artifacts/portal-das-federacoes-src.tar.gz`, 351 arquivos de código,
sem configuração privada/dados reais segundo o empacotador. Claude foi tentado,
interrompido sem resultado; implementação e verificação por Codex.
