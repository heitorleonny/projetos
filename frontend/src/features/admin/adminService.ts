import axios from 'axios';
import { api } from '../../services/api';

/* Tipos espelham backend/app/models/admin.py. */

export type Papel = 'membro' | 'admin' | 'plataforma';
export type StatusFederacao = 'ativa' | 'inativa' | 'piloto';

export interface Sessao {
    usuario_id: number | null;
    nome: string | null;
    papel: Papel | null;
    federacao_id: number | null;
    pode_administrar: boolean;
    eh_plataforma: boolean;
}

export interface Federacao {
    id: number;
    slug: string;
    nome: string;
    uf: string;
    status: StatusFederacao;
    logo_url: string | null;
    cor_primaria: string | null;
    slogan: string | null;
}

export type FederacaoAtualizacao = Partial<Pick<Federacao, 'nome' | 'status' | 'logo_url' | 'cor_primaria' | 'slogan'>>;

export interface Usuario {
    convite_url?: string | null;
    id: number;
    federacao_id: number;
    federacao_nome: string;
    nome: string;
    email: string;
    papel: Papel;
    ativo: boolean;
    conta_principal: boolean;
    vinculado: boolean;
    ultimo_login: string | null;
    criado_em: string;
}

export type UsuarioAtualizacao = Partial<Pick<Usuario, 'nome' | 'papel' | 'ativo' | 'federacao_id'>>;

export interface Convite {
    nome: string;
    email: string;
    papel: Papel;
    federacao_id?: number;
}

export interface Carga {
    id: number;
    arquivo_nome: string;
    ano: number;
    exportado_em: string | null;
    carregado_em: string;
    carregado_por: number | null;
    origem: string;
    escopo: 'nacional' | 'federacao';
    federacao_id: number | null;
    status: 'sucesso' | 'erro' | 'rejeitada';
    linhas_lidas: number | null;
    linhas_aplicadas: number | null;
    linhas_ignoradas: number | null;
    mensagem_erro: string | null;
    reenvio_de: number | null;
}

export interface ContagemTabela {
    enviadas: number;
    novas: number;
    atualizadas: number;
    inalteradas: number;
}

/** Subconjunto do `Relatorio` de app/ingestao/importacao.py que a tela usa. */
export interface RelatorioImportacao {
    simulacao: boolean;
    carga_id: number | null;
    reenvio_de: number | null;
    arquivo_nome: string;
    exportado_em: string | null;
    escopo: 'nacional' | 'federacao';
    federacao: string | null;
    linhas_lidas: number;
    linhas_aplicadas: number;
    linhas_ignoradas: number;
    federacoes: string[];
    ejs: number;
    meses: number[];
    tabelas: Record<string, ContagemTabela>;
    avisos: string[];
    nucleos_criados: string[];
    duracao_s: number;
}

export interface ResultadoImportacao {
    relatorio: RelatorioImportacao;
    texto: string;
}

export interface PedidoImportacao {
    arquivo: File;
    ano: number;
    federacaoSlug?: string;
    simular: boolean;
}

/* ── Chamadas ── */

export async function fetchSessao(): Promise<Sessao> {
    return (await api.get<Sessao>('/admin/sessao')).data;
}

export async function fetchFederacoes(): Promise<Federacao[]> {
    return (await api.get<Federacao[]>('/admin/federacoes')).data;
}

export async function atualizarFederacao(id: number, dados: FederacaoAtualizacao): Promise<Federacao> {
    return (await api.patch<Federacao>(`/admin/federacoes/${id}`, dados)).data;
}

export async function fetchUsuarios(): Promise<Usuario[]> {
    return (await api.get<Usuario[]>('/admin/usuarios')).data;
}

export async function atualizarUsuario(id: number, dados: UsuarioAtualizacao): Promise<Usuario> {
    return (await api.patch<Usuario>(`/admin/usuarios/${id}`, dados)).data;
}

export async function convidarUsuario(convite: Convite): Promise<Usuario> {
    return (await api.post<Usuario>('/admin/usuarios', convite)).data;
}

export async function fetchCargas(): Promise<Carga[]> {
    return (await api.get<Carga[]>('/admin/importacoes')).data;
}

export async function importarPlanilha(pedido: PedidoImportacao): Promise<ResultadoImportacao> {
    const corpo = new FormData();
    corpo.append('arquivo', pedido.arquivo);
    corpo.append('ano', String(pedido.ano));
    corpo.append('simular', pedido.simular ? 'true' : 'false');
    if (pedido.federacaoSlug) corpo.append('federacao_slug', pedido.federacaoSlug);

    // O Content-Type padrão da instância é JSON, e com ele o axios converteria
    // o FormData em JSON. Declarando multipart, o navegador monta o boundary.
    const resposta = await api.post<ResultadoImportacao>('/admin/importacoes', corpo, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120_000,
    });
    return resposta.data;
}

/* ── Erros ── */

export interface ErroApi {
    mensagem: string;
    problemas: string[];
}

/**
 * O `detail` da API vem em três formas: texto, o objeto da importação
 * ({ mensagem, problemas }) ou a lista de validação do FastAPI.
 */
export function lerErro(erro: unknown): ErroApi {
    if (!axios.isAxiosError(erro)) return { mensagem: 'Erro inesperado.', problemas: [] };
    const detalhe = erro.response?.data?.detail;
    if (typeof detalhe === 'string') return { mensagem: detalhe, problemas: [] };
    if (Array.isArray(detalhe)) {
        return {
            mensagem: 'Dados inválidos.',
            problemas: detalhe.map((d: { loc?: unknown[]; msg?: string }) =>
                `${(d.loc ?? []).slice(1).join('.')}: ${d.msg ?? ''}`),
        };
    }
    if (detalhe && typeof detalhe === 'object') {
        return { mensagem: detalhe.mensagem ?? 'Operação recusada.', problemas: detalhe.problemas ?? [] };
    }
    if (!erro.response) return { mensagem: 'Sem resposta da API. Verifique a conexão.', problemas: [] };
    return { mensagem: `Erro ${erro.response.status}.`, problemas: [] };
}
