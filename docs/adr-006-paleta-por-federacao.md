# ADR-006 — Paleta compartilhada com gestão pelo administrador

Data: 05/10/2026. Status: implementado localmente.

## Contexto

O portal já armazenava `cor_primaria`, mas sua edição estava restrita ao operador da plataforma. O usuário solicitou que cada administrador pudesse escolher até três cores, salvas para todos os usuários da própria federação. A interface também precisava reduzir efeitos decorativos e assumir uma apresentação de ferramenta de gestão.

## Decisão

A migração aditiva17 inclui `cor_secundaria` e `cor_acento`, com validação hexadecimal. O branding público continua limitado às colunas de apresentação das federações ativas; os dados estratégicos permanecem autenticados. O endpoint `/federacao/minha/paleta` não aceita identidade no corpo. Ele executa uma RPC que deriva o vínculo pelo `auth.uid()`, exige papel admin/plataforma ativo atual no banco e coincidência com o tenant do JWT. A escrita contém exclusivamente as três cores e o timestamp.

Não adicionamos uma política UPDATE de federação para o admin: o role comum `authenticated` já possui privilégios de coluna para o operador, incluindo status/nome. Uma política ampla de UPDATE poderia habilitar essas colunas para o admin também. A RPC limitada evita essa ampliação e permite revogação de permissão no banco sem depender de expiração do token.

As três cores geram rampas em variáveis CSS, preservando a rampa padrão quando corresponde à marca padrão. Cor principal identifica ações/links, secundária a marca de apoio e acento a seleção de navegação. Superfícies e feedback de erro/alerta continuam neutros ou semânticos. O texto de controles sobre cores sólidas escolhe preto ou branco por contraste relativo; os tons derivados destinados a links são clareados até contraste mínimo 4,5 contra a superfície escura. Antes de aplicar um tenant, as três rampas anteriores são removidas; valores nulos restauram o padrão, evitando tema residual na troca de federação.

A aba **Administração → Aparência** fornece prévia local, até três cores opcionais, salvamento e restauração. Somente o salvamento altera o tema compartilhado. O administrador recebe a mudança imediatamente; outras sessões recarregam os metadados ao focar, entrar ou a cada minuto. Essa atualização usa somente branding, sem reconsultar os dados estratégicos.

## Alternativas e consequências

- Preferência em localStorage foi descartada: não seria compartilhada com a federação.
- Corpo com id de federação foi descartado: o recurso trata exclusivamente a própria identidade autenticada.
- UPDATE direto com nova política admin foi descartado pelo privilégio compartilhado do role `authenticated`.
- Tema completamente arbitrário de superfícies/estados foi descartado: erros, alertas e estrutura de leitura precisam manter significado consistente.

É necessária a aplicação da migração17 no ambiente de destino antes de publicar a nova API. Migrações anteriores não foram alteradas. Não se afirma conformidade integral WCAG apenas pela escolha de cor de texto; validação com usuários e leitor de tela permanecem separadas. Os limites operacionais de IA são tratados em uma migração própria, sem alterar planos/créditos comerciais.

## Evidências

Testes de API e PostgreSQL verificam administrador, membro, operador, usuário rebaixado, claim divergente, ausência de tenant, coluna pública de branding e ausência de UPDATE amplo. Um teste alterna usuários na mesma transação para verificar que membro da própria federação lê as cores salvas e a outra federação permanece com sua paleta. Testes de tema verificam restauração/troca de tenant e texto em fundos claros/escuros. A verificação visual confirmou prévia, salvamento e persistência após reload; as cores temporárias da demo foram restauradas após o teste.
