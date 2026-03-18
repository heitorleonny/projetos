import { useQuery } from '@tanstack/react-query';
import { fetchEmpresaPerfil } from './empresaService';

export function useEmpresaPerfil(idEj: number, ano: number) {
    return useQuery({
        queryKey: ['empresa', idEj, ano],
        queryFn: () => fetchEmpresaPerfil(idEj, ano),
        enabled: idEj > 0,
    });
}
