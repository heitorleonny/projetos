/**
 * Listas de anos derivadas do ano de referência, em vez de escritas à mão.
 *
 * O PROBLEMA
 *
 * As telas traziam `[2022, 2023, 2024, 2025, 2026]`, `[2023, 2024, 2025, 2026]`
 * e `useState(2026)` cada uma por conta própria. É o mesmo defeito que as
 * colunas `cluster_20XX` tinham no banco: alguém precisa lembrar de editar
 * isso todo começo de ano, em vários arquivos, e nada avisa quando esquece.
 *
 * A fonte do ano de referência é `settings.ANO_DEFAULT` no backend, que chega
 * junto com o branding (`useFederacaoBranding().anoDefault`). Daqui para trás,
 * o resto é contagem.
 */

/**
 * Os `quantidade` últimos anos terminando em `anoDefault`, em ordem crescente.
 *
 * Quem chama escolhe a quantidade porque as telas têm janelas diferentes, e
 * essa diferença é intencional: a comparação olha cinco anos, o perfil da EJ e
 * os indicadores quatro, o acompanhamento de cluster dois. Unificar mudaria o
 * que cada tela oferece hoje, o que é outra discussão — esta função só tira o
 * ano fixo do caminho.
 *
 * Uma alternativa mais fiel seria perguntar ao banco quais anos existem de
 * fato por EJ (`cluster_historico` tem isso desde a migração 08). Fica para
 * quando a API expuser: exigiria uma chamada a mais em cada tela, e hoje o
 * número de anos com dado é exatamente o que estas janelas já mostravam.
 */
export function ultimosAnos(anoDefault: number, quantidade: number): number[] {
    return Array.from({ length: quantidade }, (_, i) => anoDefault - quantidade + 1 + i);
}

/** Os mesmos anos, do mais recente para o mais antigo. */
export function ultimosAnosDecrescente(anoDefault: number, quantidade: number): number[] {
    return ultimosAnos(anoDefault, quantidade).reverse();
}

/**
 * Cor de cada ano nos gráficos e nas legendas.
 *
 * Continua sendo um mapa fixo — a cor não vem da federação, é só um jeito de
 * distinguir séries. O que mudou é a chave: era `{ 2022: ..., 2026: ... }`,
 * com anos literais, e agora é o índice `ano % 5`.
 *
 * O resto da paleta está na ordem em que reproduz exatamente as cores que
 * 2022–2026 já tinham. Como a conta é sobre o próprio ano, e não sobre a
 * posição na lista, 2025 continua azul em 2030 — as cores não escorregam
 * quando a janela de anos anda.
 */
const PALETA_POR_ANO = ['#0D6EFD', '#16A34A', '#06B6D4', '#8B5CF6', '#F59E0B'];

export function corDoAno(ano: number): string {
    return PALETA_POR_ANO[((ano % PALETA_POR_ANO.length) + PALETA_POR_ANO.length) % PALETA_POR_ANO.length];
}
