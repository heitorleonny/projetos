import { useQuery } from '@tanstack/react-query';
import { fetchEmpresaPerfil } from './empresaService';

export function useEmpresaPerfil(idEj: number, ano: number, mes?: number) {
    return useQuery({
        queryKey: ['empresa', idEj, ano, mes],
        queryFn: () => fetchEmpresaPerfil(idEj, ano, mes),
        enabled: idEj > 0,
    });
}
