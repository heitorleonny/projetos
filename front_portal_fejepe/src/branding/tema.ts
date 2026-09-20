/**
 * Aplicação da cor da federação sobre a paleta compilada.
 *
 * COMO ISTO FUNCIONA
 *
 * O Tailwind v4 não cola a cor dentro de cada utilitário: ele declara
 * `--color-primary-500` em `:root` e faz os utilitários apontarem para a
 * variável (`.text-primary-400{color:var(--color-primary-400)}`). Redefinir a
 * variável em `document.documentElement` depois do CSS carregado restila tudo
 * que a referencia, sem rebuild. Foi conferido no CSS gerado, não suposto.
 *
 * POR QUE A PALETA INTEIRA, E NÃO SÓ O TOM 500
 *
 * A interface usa os nove tons: hover em 400, borda em 500/30, texto em 300,
 * gradiente de 400 a 600. Trocar só o 500 deixaria uma federação verde com
 * hover azul e texto azul — pior do que não trocar nada. Os outros oito tons
 * são derivados da cor principal misturando com branco (tons claros) e com
 * preto (tons escuros).
 *
 * As proporções abaixo foram escolhidas para reproduzir a *forma* da rampa
 * que já existe em src/index.css. Uma derivação nunca vai reproduzir uma
 * rampa feita à mão tom a tom — e é por isso que existe a regra de parada
 * logo abaixo.
 */

/** Quanto de BRANCO entra em cada tom mais claro que o principal. */
const TONS_CLAROS: Record<number, number> = {
    50: 0.9,
    100: 0.8,
    200: 0.6,
    300: 0.4,
    400: 0.2,
};

/** Quanto de PRETO entra em cada tom mais escuro que o principal. */
const TONS_ESCUROS: Record<number, number> = {
    600: 0.12,
    700: 0.3,
    800: 0.5,
    900: 0.72,
};

const VARIAVEL_PRINCIPAL = '--color-primary-500';

type Rgb = [number, number, number];

/** Devolve o hexadecimal em minúsculas, ou null se não for `#RRGGBB`. */
export function normalizarHex(valor: string | null | undefined): string | null {
    const limpo = valor?.trim().toLowerCase();
    if (!limpo || !/^#[0-9a-f]{6}$/.test(limpo)) return null;
    return limpo;
}

function paraRgb(hex: string): Rgb {
    return [
        parseInt(hex.slice(1, 3), 16),
        parseInt(hex.slice(3, 5), 16),
        parseInt(hex.slice(5, 7), 16),
    ];
}

function paraHex([r, g, b]: Rgb): string {
    return `#${[r, g, b].map((c) => c.toString(16).padStart(2, '0')).join('')}`;
}

function misturar(cor: Rgb, alvo: Rgb, proporcao: number): Rgb {
    return cor.map((canal, i) => Math.round(canal + (alvo[i] - canal) * proporcao)) as Rgb;
}

/** Monta os nove tons a partir da cor principal. */
export function derivarPaleta(hex: string): Record<string, string> {
    const base = paraRgb(hex);
    const paleta: Record<string, string> = { [VARIAVEL_PRINCIPAL]: hex };

    for (const [tom, proporcao] of Object.entries(TONS_CLAROS)) {
        paleta[`--color-primary-${tom}`] = paraHex(misturar(base, [255, 255, 255], proporcao));
    }
    for (const [tom, proporcao] of Object.entries(TONS_ESCUROS)) {
        paleta[`--color-primary-${tom}`] = paraHex(misturar(base, [0, 0, 0], proporcao));
    }

    return paleta;
}

/**
 * Aplica a cor da federação em `:root`. Devolve `true` quando mexeu em algo.
 *
 * A REGRA DE PARADA, que é o detalhe importante daqui:
 *
 * quando a cor pedida já é a cor compilada no CSS, esta função não escreve
 * nada. Não é otimização — é o que garante que a federação cujo tema foi
 * desenhado à mão continue com a rampa exata que alguém escolheu, em vez de
 * uma aproximação gerada por mistura. Para qualquer outra cor, a derivação
 * é melhor do que a rampa errada que estaria lá.
 *
 * Valor inválido também não escreve nada: a paleta compilada continua valendo.
 * O banco já barra formato torto (CHECK em 09-federacao-branding.sql); aqui é
 * a segunda barreira, porque o valor vai direto para uma propriedade de CSS.
 */
export function aplicarCorPrimaria(cor: string | null | undefined): boolean {
    const hex = normalizarHex(cor);
    if (!hex) return false;

    const raiz = document.documentElement;
    const compilada = normalizarHex(
        getComputedStyle(raiz).getPropertyValue(VARIAVEL_PRINCIPAL),
    );
    if (compilada === hex) return false;

    for (const [variavel, valor] of Object.entries(derivarPaleta(hex))) {
        raiz.style.setProperty(variavel, valor);
    }
    return true;
}

/**
 * Troca o favicon em runtime.
 *
 * O ícone não pode vir só do HTML estático: ele muda por federação, e o
 * index.html é o mesmo para todas. Ver o comentário no próprio index.html.
 */
export function aplicarFavicon(url: string | null | undefined): void {
    if (!url?.trim()) return;

    let link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (!link) {
        link = document.createElement('link');
        link.rel = 'icon';
        document.head.appendChild(link);
    }
    link.href = url.trim();
}
