# Onboarding pelas abas e navegação simplificada — 06/10/2026

## Mudanças

- A primeira etapa oferece **Começar visita guiada** e acesso individual a cada aba. A visita abre as páginas reais: Visão geral, Indicadores, Eventos, Evolução de cluster, Comparação, Simulação e Administração quando autorizada. Um painel de orientação permite experimentar a página, voltar, avançar e encerrar.
- A visita libera a navegação nesta sessão, sem marcar o onboarding como concluído. Ao terminar, retorna à etapa opcional de cores. A conclusão e o adiamento continuam por conta/navegador, com retorno à rota original.
- O painel usa espaço reservado no fim das páginas e rolagem em janelas baixas. O Nexo não se sobrepõe à visita.
- A navbar mostra **Visão geral**, **Indicadores** e **Eventos**. **Análises** agrupa Evolução de cluster, Comparação e Simulação. **Minha conta** reúne Administração, Primeiros passos, sugestão e saída. No celular, as páginas ficam em **Abas**, com as mesmas divisões. Menus fecham por Escape, clique fora e navegação.
- A etapa **Suas cores** reutiliza o formulário de aparência. Administradores podem experimentar até três cores, pelo seletor ou código hexadecimal `#RRGGBB`, com prévia e salvamento explícito para toda a federação. Membros seguem com a paleta vigente e recebem orientação sobre quem pode alterá-la. A personalização não amplia permissões e não é uma preferência pessoal distinta do tema compartilhado.
- Código hexadecimal inválido sinaliza o campo e impede o envio. O formulário também verifica validade/alteração antes de enviar, inclusive por Enter. O controle da etapa permite continuar sem personalizar.
- A troca de abas internas da Administração preserva os parâmetros e o estado do guia.

## Validação realizada

- `npm run build` e `npm run lint`: aprovados.
- `node --test scripts/test-onboarding.mjs scripts/test-paleta.mjs`: **11 aprovados, 0 falhos, 0 pulados**. Inclui o novo teste de códigos hexadecimais válidos/inválidos.
- Navegador local, sessão de demonstração FEJEPAR: todas as sete páginas percorridas pelo guia; visita direta à Administração; troca para Aparência preservou o guia; retorno à etapa de cores.
- Formulário: `#12ZZ99` bloqueou Salvar e apresentou `aria-invalid`; `#2563EB` atualizou o seletor e a prévia e habilitou Salvar. A paleta não foi gravada nesta verificação; o endpoint de salvamento existente foi reutilizado sem mudança no backend.
- Menus: expansão de Análises, acesso aos links, fechamento por Escape e acesso a Primeiros passos em Minha conta.
- Viewport móvel 390×844: navegação agrupada e campos empilhados, sem overflow horizontal na tela conferida. O viewport original foi restaurado.
- `git diff --check`: aprovado.

Não houve mudança de fórmulas, migração, deploy ou gravação da paleta na demo. Não foi feita nova suíte backend, auditoria integral de acessibilidade, validação com participantes ou troca manual para uma conta membro. Esses limites são distintos da verificação funcional acima.
