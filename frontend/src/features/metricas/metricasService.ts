import { api } from '../../services/api';

/* Contratos de /api/v1/metricas. A API decide quem pode editar; a tela só esconde. */

export type Unidade = 'moeda' | 'numero';
export type Visual = 'ranking' | 'valor' | 'serie';

export interface DefinicaoMetrica {
    expressao: string;
    unidade: Unidade;
    ano: number;
    mes_inicio: number;
    mes_fim: number | null;
    cluster: number | null;
    ordem: 'desc' | 'asc';
    limite: number;
    agregacao_rede: 'soma' | 'media';
}

export interface MetricaEntrada {
    nome: string;
    descricao: string | null;
    visual: Visual;
    no_painel: boolean;
    definicao: DefinicaoMetrica;
}

export interface Metrica extends MetricaEntrada {
    id: number;
    ordem: number;
    versao: number;
    arquivada: boolean;
    formula_legivel: string;
    criado_em: string;
    atualizado_em: string;
}

export interface VariavelCatalogo {
    nome: string;
    rotulo: string;
    descricao: string;
    unidade: Unidade;
}

export interface Catalogo {
    pode_editar: boolean;
    ano: number;
    variaveis: VariavelCatalogo[];
    texto_livre_disponivel: boolean;
}

export interface LinhaMetrica {
    posicao: number;
    id_ej: number;
    nome: string;
    cluster: number | null;
    valor: number;
}

export interface PontoMetrica {
    mes: number;
    valor: number | null;
    ejs: number;
}

export interface ResultadoMetrica {
    status: 'ok' | 'sem_dados';
    mensagem: string;
    ano: number;
    mes_inicio: number;
    mes_fim: number | null;
    unidade: Unidade;
    formula: string;
    formula_legivel: string;
    explicacao: string[];
    agregacao_rede: 'soma' | 'media';
    ordem: 'desc' | 'asc';
    linhas: LinhaMetrica[];
    total_ejs: number;
    avaliadas: number;
    sem_cobertura: number;
    sem_valor: number;
    valor_rede: number | null;
    serie: PontoMetrica[];
}

export interface PropostaMetrica {
    status: 'pronta' | 'esclarecimento' | 'fora_do_catalogo';
    mensagem: string;
    opcoes: { rotulo: string; texto: string }[];
    metrica: MetricaEntrada | null;
    formula_legivel: string | null;
    resultado: ResultadoMetrica | null;
    modelo: string | null;
}

const base = '/metricas';

export const fetchCatalogo = async () => (await api.get<Catalogo>(`${base}/catalogo`)).data;
export const fetchMetricas = async (arquivadas = false) =>
    (await api.get<Metrica[]>(base, { params: { arquivadas } })).data;
export const fetchResultado = async (id: number) => (await api.get<ResultadoMetrica>(`${base}/${id}/resultado`)).data;
export const fetchPrevia = async (definicao: DefinicaoMetrica) =>
    (await api.post<ResultadoMetrica>(`${base}/previa`, { definicao })).data;
export const interpretar = async (texto: string) =>
    (await api.post<PropostaMetrica>(`${base}/interpretar`, { texto })).data;
export const criarMetrica = async (dados: MetricaEntrada) => (await api.post<Metrica>(base, dados)).data;
export const atualizarMetrica = async (id: number, dados: MetricaEntrada) =>
    (await api.put<Metrica>(`${base}/${id}`, dados)).data;
export const definirPainel = async (id: number, noPainel: boolean) =>
    (await api.post<Metrica>(`${base}/${id}/painel`, { no_painel: noPainel })).data;
export const arquivarMetrica = async (id: number) => (await api.post<Metrica>(`${base}/${id}/arquivar`)).data;
export const restaurarMetrica = async (id: number) => (await api.post<Metrica>(`${base}/${id}/restaurar`)).data;
export const excluirMetrica = async (id: number) => { await api.delete(`${base}/${id}`); };
export const reordenarMetricas = async (ids: number[]) => (await api.put<Metrica[]>(`${base}/ordem`, { ids })).data;

export const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro',
    'Outubro', 'Novembro', 'Dezembro'];

export function textoPeriodo(ano: number, inicio: number, fim: number | null): string {
    if (fim === null) return `${MESES[inicio - 1]} até o último mês com dados de ${ano}`;
    if (inicio === fim) return `${MESES[inicio - 1]} de ${ano}`;
    return `${MESES[inicio - 1]} a ${MESES[fim - 1].toLowerCase()} de ${ano}`;
}

export function formatarValor(valor: number | null, unidade: Unidade): string {
    if (valor === null) return 'Sem valor';
    return unidade === 'moeda'
        ? valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
        : valor.toLocaleString('pt-BR', { maximumFractionDigits: Math.abs(valor) >= 1000 ? 0 : 2 });
}

export function formatarCompacto(valor: number, unidade: Unidade): string {
    const texto = Math.abs(valor) >= 1000
        ? valor.toLocaleString('pt-BR', { notation: 'compact', maximumFractionDigits: 1 })
        : valor.toLocaleString('pt-BR', { maximumFractionDigits: 2 });
    return unidade === 'moeda' ? `R$ ${texto}` : texto;
}

export function definicaoPadrao(ano: number): DefinicaoMetrica {
    return { expressao: '', unidade: 'numero', ano, mes_inicio: 1, mes_fim: null, cluster: null, ordem: 'desc',
        limite: 10, agregacao_rede: 'soma' };
}
