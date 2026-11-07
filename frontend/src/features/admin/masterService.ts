import { api } from '../../services/api';
import type { StatusFederacao } from './adminService';
export interface FederacaoMaster {
    id: number; nome: string; uf: string; status: StatusFederacao; plano_id: number | null;
    usuarios_total: number; usuarios_ativos: number; administradores: number; usuarios_sem_vinculo: number;
}
export interface PlanoDados {
    nome: string; limite_usuarios: number | null; limite_creditos_ia_mes: number | null; preco_mensal: number | null;
}
export interface Plano extends PlanoDados { id: number }
export async function fetchResumoMaster() { return (await api.get<FederacaoMaster[]>('/admin/master/federacoes')).data; }
export async function fetchPlanosMaster() { return (await api.get<Plano[]>('/admin/master/planos')).data; }
export async function salvarPlano(id: number | null, dados: PlanoDados) {
    return id === null ? (await api.post<Plano>('/admin/master/planos', dados)).data : (await api.put<Plano>(`/admin/master/planos/${id}`, dados)).data;
}
export async function vincularPlano(id: number, plano_id: number | null) { await api.put(`/admin/master/federacoes/${id}/plano`, { plano_id }); }
