const LOGO_FILES = [
    'Inova Tech.png.jpg',
    'LOGO A.C.E.png',
    'LOGO ACETEC.png',
    'LOGO AGRESTE.png',
    'LOGO AQUA.png',
    'LOGO ARCO.png',
    'LOGO BENS.png',
    'LOGO BEVILAQUA.png',
    'LOGO BIOTECH.png',
    'LOGO CICLO.png',
    'LOGO CITI.png',
    'LOGO DAMAS.png',
    'LOGO DELTA.png',
    'LOGO DIPOLUM.png',
    'LOGO EIXO.png',
    'LOGO EJ UNICAP.png',
    'LOGO ELEMENTUS.png',
    'LOGO ETHOS.png',
    'LOGO FASUP JR_.png',
    'LOGO FCAP JR_.png',
    'LOGO FLORAR.png',
    'LOGO FORMULAR.png',
    'LOGO FUSÃO.png',
    'LOGO FUTURUP.png',
    'LOGO GINGA.png',
    'LOGO INOVAGRO.png',
    'LOGO INTEGRAR.png',
    'LOGO LIGA.png',
    'LOGO LÍDER.png',
    'LOGO MINERA.png',
    'LOGO NUINOVA.png',
    'LOGO POLI_ PJ.png',
    'LOGO POTENCIALIZE.png',
    'LOGO PRESERVE.png',
    'LOGO PRISMA.png',
    'LOGO PROJETOS JR.png',
    'LOGO PÓRTIS.png',
    'LOGO SEED.png',
    'LOGO VOLTS.png',
    'LOGO WATT.png',
    'LOGO ÂMBAR.png',
    'ParaSer.png',
    'Prospere.png',
] as const;

function canonicalize(value: string): string {
    return value
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '');
}

function logoPath(fileName: string): string {
    return `/${encodeURIComponent(fileName)}`;
}

function logoKeyFromFileName(fileName: string): string {
    const withoutExt = fileName.replace(/\.(png|jpg|jpeg)$/i, '');
    const withoutPrefix = withoutExt.replace(/^LOGO\s*/i, '');
    return canonicalize(withoutPrefix);
}

const AUTO_LOGO_MAP = new Map<string, string>(
    LOGO_FILES.map((fileName) => [logoKeyFromFileName(fileName), logoPath(fileName)]),
);

const MANUAL_LOGO_MAP: Record<string, string> = {
    ace: logoPath('LOGO A.C.E.png'),
    acetec: logoPath('LOGO ACETEC.png'),
    agreste: logoPath('LOGO AGRESTE.png'),
    aqua: logoPath('LOGO AQUA.png'),
    arco: logoPath('LOGO ARCO.png'),
    bens: logoPath('LOGO BENS.png'),
    bevilaqua: logoPath('LOGO BEVILAQUA.png'),
    biotech: logoPath('LOGO BIOTECH.png'),
    ciclo: logoPath('LOGO CICLO.png'),
    citi: logoPath('LOGO CITI.png'),
    damas: logoPath('LOGO DAMAS.png'),
    delta: logoPath('LOGO DELTA.png'),
    dipolum: logoPath('LOGO DIPOLUM.png'),
    eixo: logoPath('LOGO EIXO.png'),
    ejunicap: logoPath('LOGO EJ UNICAP.png'),
    elementus: logoPath('LOGO ELEMENTUS.png'),
    ethos: logoPath('LOGO ETHOS.png'),
    fasupjr: logoPath('LOGO FASUP JR_.png'),
    fcapjr: logoPath('LOGO FCAP JR_.png'),
    florar: logoPath('LOGO FLORAR.png'),
    formular: logoPath('LOGO FORMULAR.png'),
    fusao: logoPath('LOGO FUSÃO.png'),
    futurup: logoPath('LOGO FUTURUP.png'),
    ginga: logoPath('LOGO GINGA.png'),
    inovagro: logoPath('LOGO INOVAGRO.png'),
    integrar: logoPath('LOGO INTEGRAR.png'),
    liga: logoPath('LOGO LIGA.png'),
    lider: logoPath('LOGO LÍDER.png'),
    minera: logoPath('LOGO MINERA.png'),
    nuinova: logoPath('LOGO NUINOVA.png'),
    polipj: logoPath('LOGO POLI_ PJ.png'),
    potencialize: logoPath('LOGO POTENCIALIZE.png'),
    preserve: logoPath('LOGO PRESERVE.png'),
    prisma: logoPath('LOGO PRISMA.png'),
    projetosjr: logoPath('LOGO PROJETOS JR.png'),
    portis: logoPath('LOGO PÓRTIS.png'),
    seed: logoPath('LOGO SEED.png'),
    volts: logoPath('LOGO VOLTS.png'),
    watt: logoPath('LOGO WATT.png'),
    ambar: logoPath('LOGO ÂMBAR.png'),
    inovatech: logoPath('Inova Tech.png.jpg'),
    inova: logoPath('Inova Tech.png.jpg'),
    paraser: logoPath('ParaSer.png'),
    prospere: logoPath('Prospere.png'),
};

const ALIAS_TO_LOGO_KEY: Record<string, string> = {
    // Variacoes comuns de nomes institucionais e siglas
    ejunicapconsultoria: 'ejunicap',
    poli: 'polipj',
    poliprojetos: 'polipj',
    poliempresajunior: 'polipj',
    portisconsultoria: 'portis',
    projetosej: 'projetosjr',
    projetosjunior: 'projetosjr',
    inova: 'inovatech',
    inovatechjr: 'inovatech',
    paraeser: 'paraser',
};

function normalizeCompanyName(empresaNome: string): string {
    const normalized = canonicalize(empresaNome);
    return normalized.replace(
        /(empresajunior|junior|jr|consultoria|engenharia|assessoria|projetos|tecnologia|solucoes|solucao|ej)$/g,
        '',
    );
}

const SEARCH_KEYS = [
    ...Object.keys(MANUAL_LOGO_MAP),
    ...Array.from(AUTO_LOGO_MAP.keys()).filter((key) => key.length >= 4),
].sort((a, b) => b.length - a.length);

export function resolveEjLogoPath(empresaNome: string): string | null {
    const normalizedName = canonicalize(empresaNome);
    if (!normalizedName) return null;

    const normalizedCompany = normalizeCompanyName(empresaNome);

    if (MANUAL_LOGO_MAP[normalizedName]) {
        return MANUAL_LOGO_MAP[normalizedName];
    }

    if (MANUAL_LOGO_MAP[normalizedCompany]) {
        return MANUAL_LOGO_MAP[normalizedCompany];
    }

    const aliasKey = ALIAS_TO_LOGO_KEY[normalizedName] ?? ALIAS_TO_LOGO_KEY[normalizedCompany];
    if (aliasKey && MANUAL_LOGO_MAP[aliasKey]) {
        return MANUAL_LOGO_MAP[aliasKey];
    }

    const autoExact = AUTO_LOGO_MAP.get(normalizedName);
    if (autoExact) {
        return autoExact;
    }

    const autoNormalized = AUTO_LOGO_MAP.get(normalizedCompany);
    if (autoNormalized) {
        return autoNormalized;
    }

    for (const key of SEARCH_KEYS) {
        if (normalizedName.includes(key) || normalizedCompany.includes(key)) {
            return MANUAL_LOGO_MAP[key] ?? AUTO_LOGO_MAP.get(key) ?? null;
        }
    }

    return null;
}
