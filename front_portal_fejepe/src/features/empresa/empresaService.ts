import { api } from '../../services/api';
import type { EmpresaPerfilCompleto } from '../../types/empresa';

export async function fetchEmpresaPerfil(
    idEj: number,
    ano: number = 2026,
    mes?: number,
): Promise<EmpresaPerfilCompleto> {
    const response = await api.get<EmpresaPerfilCompleto>(`/empresas/${idEj}`, {
        params: { ano, ...(mes != null ? { mes } : {}) },
    });
    return response.data;
}
