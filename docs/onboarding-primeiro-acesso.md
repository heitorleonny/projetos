# Onboarding de usuários — 04/10/2026

> **Evolução em 06/10/2026:** o guia passou a abrir cada aba real, com orientação
> contextual e personalização opcional de cores/hexadecimal. A navbar foi agrupada.
> Consulte [a atualização de 06/10](onboarding-visita-guiada-2026-10-06.md).
> O conteúdo abaixo registra a primeira implementação.

## Comportamento

O primeiro acesso a uma rota protegida abre `/onboarding`, com três etapas:
sua rede, recursos do portal e primeiras ações. O menu **Primeiros passos**
permite reabrir o guia. Administradores recebem também orientação para usuários
e importação, conforme o papel retornado por `/admin/sessao`.

Concluir salva uma preferência por ID da conta no navegador; adiar vale apenas
na sessão da aba. Não há sincronização entre dispositivos. Armazenamento
bloqueado usa memória, sem impedir a saída do guia. A rota original, seus filtros
e âncora são preservados; destinos externos e rotas que gerariam laços são recusados.

O convite continua direcionando para `/definir-senha`; salvar a senha agora abre
o guia. Os formulários tratam exceções de conexão e liberam os botões para uma
nova tentativa. O menu usa a versão recolhida abaixo de `xl`, com rolagem em telas
baixas. O feedback sem URL configurada oferece uma orientação em vez de abrir `#`.
O assistente fica fora do guia para evitar sobreposição. Seu painel agora aceita
`aberto`, preserva o rascunho ao fechar e só aplica foco quando está visível;
a incompatibilidade entre botão e painel impedia o build na checagem final.

## Bug observado no código e corrigido

O antigo `WelcomeModal` usava uma chave global de localStorage, compartilhada entre
contas, e o login forçava sua abertura por sessionStorage a cada entrada.
Ele também apresentava o simulador como construção futura. Foi substituído pelo
guia. Nenhuma permissão ou fórmula estratégica depende dessas preferências.

## Verificação

- `npm run build`: passou.
- `npm run lint`: passou.
- `node --test scripts/test-onboarding.mjs`: 6 passaram, 0 falharam, 0 pulados.
- `git diff --check`: passou.
- Navegador local em `localhost:5173`, sessão de demonstração FEJEPAR:
  etapas renderizadas, orientação administrativa visível, conclusão retorna ao
  Dashboard, recarregar mantém o Dashboard e reabrir `/onboarding` funciona.
- Inspeção visual da primeira etapa e da navegação recolhida na janela disponível.
- Assistente no Dashboard: abrir mostra o diálogo; fechar remove o diálogo.

O convite completo com alteração de senha e a troca entre contas não foram
executados no navegador. A separação entre contas e a persistência foram verificadas
nos testes automatizados. Não houve escrita em produção.
