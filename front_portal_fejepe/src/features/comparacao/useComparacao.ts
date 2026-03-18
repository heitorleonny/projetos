import { useQuery } from '@tanstack/react-query';
import { fetchComparacaoAnos } from './comparacaoService';

export function useComparacao(anos: number[], mes?: number) {
    return useQuery({
        queryKey: ['comparacao', anos, mes],
        queryFn: () => fetchComparacaoAnos(anos, mes),
        enabled: anos.length > 0,
    });
}
