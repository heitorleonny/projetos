import { api } from '../../services/api';
import type { EmpresaPerfilCompleto } from '../../types/empresa';

// `ano` sem default de propósito: quem chama sabe qual e', e um default
// aqui seria mais uma copia do ano corrente escondida numa camada de servico.
export async function fetchEmpresaPerfil(
    idEj: number,
    ano: number,
    mes?: number,
): Promise<EmpresaPerfilCompleto> {
    const response = await api.get<EmpresaPerfilCompleto>(`/empresas/${idEj}`, {
        params: { ano, ...(mes != null ? { mes } : {}) },
    });
    return response.data;
}
