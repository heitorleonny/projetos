/* Formatação de datas e números do painel. */

const FORMATO_DATA = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' });

export function dataHora(iso: string | null): string {
    return iso ? FORMATO_DATA.format(new Date(iso)) : '—';
}

/** "há 3 dias", "há 2 h", "agora há pouco" — com a data exata no title. */
export function haQuantoTempo(iso: string, agora = Date.now()): string {
    const minutos = Math.round((agora - new Date(iso).getTime()) / 60_000);
    if (minutos < 2) return 'agora há pouco';
    if (minutos < 60) return `há ${minutos} min`;
    const horas = Math.round(minutos / 60);
    if (horas < 24) return `há ${horas} h`;
    const dias = Math.round(horas / 24);
    if (dias < 30) return `há ${dias} dia${dias > 1 ? 's' : ''}`;
    const meses = Math.round(dias / 30);
    if (meses < 12) return `há ${meses} ${meses > 1 ? 'meses' : 'mês'}`;
    const anos = Math.round(meses / 12);
    return `há ${anos} ano${anos > 1 ? 's' : ''}`;
}

export function numero(n: number | null | undefined): string {
    return n == null ? '—' : n.toLocaleString('pt-BR');
}
