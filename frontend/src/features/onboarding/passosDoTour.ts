/**
 * Roteiro do tour guiado. Cada passo abre uma tela e destaca um elemento
 * marcado com `data-tour`. `alvos` lista alternativas na ordem de preferência:
 * a primeira visível vence (ex.: menu de abas no celular). Sem nenhum alvo
 * visível, o passo aparece centralizado, sem destaque, e o tour continua.
 */
export interface PassoTour {
    id: string;
    rota: string;
    alvos: string[];
    titulo: string;
    texto: string;
    somenteAdmin?: boolean;
}

export const PASSOS_DO_TOUR: PassoTour[] = [
    {
        id: 'navegacao', rota: '/dashboard', alvos: ['nav-abas', 'nav-abas-movel'],
        titulo: 'As abas do portal',
        texto: 'Visão geral e Indicadores ficam aqui. Em Análises estão Evolução de cluster, Comparação, Simulação e Métricas. Vamos passar por cada uma.',
    },
    {
        id: 'dashboard-filtros', rota: '/dashboard', alvos: ['dashboard-filtros'],
        titulo: 'Encontre uma empresa júnior',
        texto: 'Busque pelo nome e filtre por cidade, universidade, cluster, ritmo, ano e mês. A ordenação ajuda a ver quem fatura mais ou está mais perto da meta.',
    },
    {
        id: 'dashboard-ejs', rota: '/dashboard', alvos: ['dashboard-ejs'],
        titulo: 'Cada cartão é uma EJ',
        texto: 'O cartão resume faturamento, meta, ritmo e cluster. Clique nele para abrir o perfil completo, com a evolução mês a mês.',
    },
    {
        id: 'indicadores-filtros', rota: '/indicadores', alvos: ['indicadores-filtros'],
        titulo: 'Indicadores da rede',
        texto: 'Escolha o ano e o cluster e marque quais gráficos quer ver. Os números consideram só as EJs da sua federação.',
    },
    {
        id: 'indicadores-sde', rota: '/indicadores', alvos: ['indicadores-sde', 'indicadores-filtros'],
        titulo: 'SDE — Saldo de Evolução da Rede',
        texto: 'Mostra se a rede, no conjunto, tende a subir ou descer de cluster, em três cenários. Abra a lista para ver quais EJs sobem e quais descem.',
    },
    {
        id: 'cluster', rota: '/cluster-track', alvos: ['cluster-filtros'],
        titulo: 'Evolução de cluster',
        texto: 'Compare o cluster oficial de cada EJ com o tracking, a estimativa de onde ela termina o ano, e veja quanto falta para o próximo cluster.',
    },
    {
        id: 'comparacao', rota: '/comparacao', alvos: ['comparacao-filtros'],
        titulo: 'Comparação entre anos',
        texto: 'Escolha os anos, o mês e o indicador para comparar as EJs lado a lado. Períodos sem dados aparecem identificados.',
    },
    {
        id: 'simulacao', rota: '/simulacao', alvos: ['simulacao-resultado'],
        titulo: 'Simule cenários',
        texto: 'Ajuste quantas EJs sobem ou descem em cada cluster e veja o SDE simulado. Nada é gravado: é um espaço para testar hipóteses.',
    },
    {
        id: 'metricas', rota: '/metricas', alvos: ['metricas-painel'],
        titulo: 'Métricas da federação',
        texto: 'Um painel com métricas criadas pela própria federação, como o top 10 em faturamento de um período ou uma fórmula combinando faturamento, CSAT e projetos. Administradores criam por texto ou pelo construtor e tiram do painel pelo menu de cada cartão. Não substituem os indicadores oficiais.',
    },
    {
        id: 'admin', rota: '/admin', alvos: ['admin-abas'], somenteAdmin: true,
        titulo: 'Administração',
        texto: 'Aqui você convida usuários, importa a planilha do Portal BJ e muda a logo e as cores da federação. Na importação, comece pela simulação.',
    },
    {
        id: 'nexo', rota: '/dashboard', alvos: ['nexo'],
        titulo: 'Pergunte ao Lamps',
        texto: 'Escreva perguntas em português, como "quais EJs estão fora do zero?" ou "o que é SDE?". O Lamps consulta só os dados da sua federação.',
    },
    {
        id: 'conta', rota: '/dashboard', alvos: ['menu-conta'],
        titulo: 'Minha conta',
        texto: 'Por aqui você reabre este guia em Primeiros passos, envia sugestões e sai do portal. Agora, vamos deixar o portal com a cara da sua rede.',
    },
];

export function passosVisiveis(podeAdministrar: boolean): PassoTour[] {
    return PASSOS_DO_TOUR.filter(passo => !passo.somenteAdmin || podeAdministrar);
}

/** `?tour=3` → 3, só quando é um índice existente. */
export function indiceDoParametro(valor: string | null, total: number): number | null {
    if (valor === null || !/^\d{1,2}$/.test(valor)) return null;
    const indice = Number(valor);
    return indice < total ? indice : null;
}

export interface Retangulo { top: number; left: number; width: number; height: number }
export interface Tamanho { width: number; height: number }
export type Lado = 'abaixo' | 'acima' | 'sobreposto' | 'centro';

const MARGEM = 16;
const DISTANCIA = 14;

/** Área destacada: o alvo com uma folga, sem passar das bordas da janela. */
export function recorteDoAlvo(alvo: Retangulo, janela: Tamanho, folga = 8): Retangulo {
    const top = Math.max(4, alvo.top - folga);
    const left = Math.max(4, alvo.left - folga);
    const bottom = Math.min(janela.height - 4, alvo.top + alvo.height + folga);
    const right = Math.min(janela.width - 4, alvo.left + alvo.width + folga);
    return { top, left, width: Math.max(0, right - left), height: Math.max(0, bottom - top) };
}

/**
 * Onde o cartão fica: abaixo do destaque, acima se não couber, e sobreposto
 * na base da tela quando o alvo ocupa quase toda a altura. Sem alvo, centralizado.
 */
export function posicionarCartao(alvo: Retangulo | null, janela: Tamanho, cartao: Tamanho): { top: number; left: number; lado: Lado } {
    const centroHorizontal = (janela.width - cartao.width) / 2;
    if (!alvo) {
        return { top: Math.max(MARGEM, (janela.height - cartao.height) / 2), left: Math.max(MARGEM, centroHorizontal), lado: 'centro' };
    }
    const maximoLeft = janela.width - cartao.width - MARGEM;
    const left = Math.min(Math.max(MARGEM, alvo.left + alvo.width / 2 - cartao.width / 2), Math.max(MARGEM, maximoLeft));
    const abaixo = alvo.top + alvo.height + DISTANCIA;
    if (abaixo + cartao.height <= janela.height - MARGEM) return { top: abaixo, left, lado: 'abaixo' };
    const acima = alvo.top - DISTANCIA - cartao.height;
    if (acima >= MARGEM) return { top: acima, left, lado: 'acima' };
    return { top: Math.max(MARGEM, janela.height - cartao.height - MARGEM), left: Math.max(MARGEM, centroHorizontal), lado: 'sobreposto' };
}
