import { useQuery } from '@tanstack/react-query';
import { fetchComparacaoAnos } from './comparacaoService';

export function useComparacao(
    anos: number[],
    mes?: number,
    comunidade?: string,
) {
    return useQuery({
        queryKey: ['comparacao', anos, mes, comunidade],
        queryFn: () => fetchComparacaoAnos(anos, mes, comunidade),
        enabled: anos.length > 0,
    });
}
