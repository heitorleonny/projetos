import { useEffect, useMemo, useState } from 'react';
import EventoSelector from './EventoSelector';
import EventoMetaCard from './EventoMetaCard';
import CirandaMetaCard from './CirandaMetaCard';
import { useEventoDetalhe, useEventos } from './useEventos';
import type { EventoMetaTipo } from '../../types/evento';

export default function EventosPage() {
    const { data: eventos, isLoading: eventosLoading, isError: eventosIsError, error: eventosError } = useEventos();
    const [selectedEventoId, setSelectedEventoId] = useState<string | null>(null);
    const [expandedMetas, setExpandedMetas] = useState<Set<EventoMetaTipo>>(new Set());

    useEffect(() => {
        if (!selectedEventoId && eventos && eventos.length > 0) {
            const eventoAtivo = eventos.find((evento) => evento.ativo) ?? eventos[0];
            setSelectedEventoId(eventoAtivo.id_evento);
        }
    }, [eventos, selectedEventoId]);

    useEffect(() => {
        setExpandedMetas(new Set());
    }, [selectedEventoId]);

    const selectedEvento = useMemo(
        () => eventos?.find((evento) => evento.id_evento === selectedEventoId) ?? null,
        [eventos, selectedEventoId],
    );

    const { data: eventoDetalhe, isLoading: detalheLoading, isError: detalheIsError, error: detalheError } = useEventoDetalhe(selectedEventoId);

    const toggleMeta = (tipo: EventoMetaTipo) => {
        setExpandedMetas((prev) => {
            const next = new Set(prev);
            if (next.has(tipo)) {
                next.delete(tipo);
            } else {
                next.add(tipo);
            }
            return next;
        });
    };

    const eventoAtual = eventoDetalhe?.evento ?? selectedEvento;

    return (
        <div>
            <div className="mb-8">
                <div className="flex items-center gap-3 mb-1">
                    <div className="w-1 h-8 rounded-full bg-gradient-to-b from-primary-400 to-primary-600" />
                    <h1 className="font-heading text-3xl font-bold text-gradient">
                        Eventos
                    </h1>
                </div>
                <p className="text-neutral-400 ml-5 text-sm italic">
                    Monitore as metas do evento do momento e veja quais EJs já contam para cada objetivo.
                </p>
            </div>

            {eventosLoading && !eventos && (
                <div className="glass-card rounded-2xl p-8 animate-pulse space-y-4 mb-6">
                    <div className="h-6 w-1/3 bg-white/10 rounded" />
                    <div className="h-12 w-full bg-white/5 rounded-xl" />
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        <div className="h-64 bg-white/5 rounded-2xl" />
                        <div className="h-64 bg-white/5 rounded-2xl" />
                        <div className="h-64 bg-white/5 rounded-2xl" />
                    </div>
                </div>
            )}

            {eventosIsError && (
                <div className="text-center py-12 glass-card rounded-2xl mb-6">
                    <div className="text-error text-4xl mb-3">⚠</div>
                    <h3 className="font-heading font-semibold text-lg text-white mb-1">
                        Erro ao carregar eventos
                    </h3>
                    <p className="text-neutral-500 text-sm">
                        {(eventosError as Error)?.message ?? 'Tente novamente mais tarde.'}
                    </p>
                </div>
            )}

            {eventos && eventos.length > 0 && (
                <div className="grid gap-4 mb-6">
                    {selectedEvento?.id_evento === 'ciranda-mej-26' ? (
                        <div
                            className="rounded-2xl overflow-hidden relative"
                            style={{ background: 'linear-gradient(135deg, #3D0018 0%, #6B0030 45%, #8B0040 100%)', minHeight: '160px' }}
                        >
                            {/* Glow decorativo */}
                            <div
                                className="absolute bottom-0 right-24 w-48 h-48 rounded-full pointer-events-none"
                                style={{ background: 'radial-gradient(circle, rgba(245,197,0,0.12) 0%, transparent 70%)' }}
                            />
                            <div className="relative z-10 px-7 py-7 flex items-center justify-between gap-6">
                                <div>
                                    <div className="flex items-center gap-2.5 mb-3">
                                        <div className="w-7 h-7 rounded-full border-2 flex items-center justify-center shrink-0" style={{ borderColor: 'rgba(255,255,255,0.5)' }}>
                                            <div className="w-3 h-3 rounded-full border" style={{ borderColor: 'rgba(255,255,255,0.4)' }} />
                                        </div>
                                        <span className="text-[10px] uppercase tracking-[0.35em] font-bold" style={{ color: 'rgba(255,255,255,0.55)' }}>
                                            MEJ&apos;26
                                        </span>
                                    </div>
                                    <h2 className="text-3xl font-black text-white leading-tight">Ciranda</h2>
                                    <p className="text-sm italic mt-1" style={{ color: 'rgba(254,205,211,0.75)' }}>O Que Ecoa Entre Nós?</p>
                                    <div className="flex gap-4 mt-4">
                                        <div>
                                            <p className="text-[10px] uppercase tracking-wider mb-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>EJs ativas</p>
                                            <p className="text-xl font-bold text-white">{eventoDetalhe?.total_ejs ?? '—'}</p>
                                        </div>
                                        <div>
                                            <p className="text-[10px] uppercase tracking-wider mb-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>Recorte</p>
                                            <p className="text-xl font-bold text-white">Maio</p>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex flex-col items-center gap-3 opacity-40 select-none shrink-0">
                                    <span className="text-6xl">🎧</span>
                                    <span className="text-5xl">📣</span>
                                </div>
                            </div>
                        </div>
                    ) : (
                        eventoAtual && (
                            <div className="glass-card rounded-2xl p-5 border border-white/10">
                                <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
                                    <div>
                                        <p className="text-xs uppercase tracking-[0.25em] text-neutral-500 font-semibold mb-2">
                                            {eventoAtual.ativo ? 'Evento atual' : 'Evento planejado'}
                                        </p>
                                        <h2 className="text-2xl font-bold text-white mb-2">{eventoAtual.nome}</h2>
                                        <p className="text-sm text-neutral-400 max-w-3xl leading-relaxed">{eventoAtual.descricao}</p>
                                    </div>
                                    <div className="grid grid-cols-2 gap-3 min-w-[280px]">
                                        <div className="rounded-xl bg-white/5 border border-white/10 p-3">
                                            <p className="text-[10px] uppercase tracking-wider text-neutral-500 mb-1">EJs ativas</p>
                                            <p className="text-xl font-bold text-white">{eventoDetalhe?.total_ejs ?? 0}</p>
                                        </div>
                                        <div className="rounded-xl bg-white/5 border border-white/10 p-3">
                                            <p className="text-[10px] uppercase tracking-wider text-neutral-500 mb-1">Recorte</p>
                                            <p className="text-xl font-bold text-white">
                                                {new Date(2000, (eventoAtual.mes_referencia ?? 1) - 1).toLocaleString('pt-BR', { month: 'long' }).replace(/^\w/, (c) => c.toUpperCase())}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )
                    )}

                    <EventoSelector
                        eventos={eventos}
                        selectedEventoId={selectedEventoId ?? eventos[0].id_evento}
                        onChange={setSelectedEventoId}
                    />
                </div>
            )}

            {detalheIsError && (
                <div className="text-center py-12 glass-card rounded-2xl mb-6">
                    <div className="text-error text-4xl mb-3">⚠</div>
                    <h3 className="font-heading font-semibold text-lg text-white mb-1">
                        Erro ao carregar o evento selecionado
                    </h3>
                    <p className="text-neutral-500 text-sm">
                        {(detalheError as Error)?.message ?? 'Tente novamente mais tarde.'}
                    </p>
                </div>
            )}

            {detalheLoading && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {Array.from({ length: 3 }).map((_, index) => (
                        <div key={index} className="glass-card rounded-2xl p-5 animate-pulse h-72" />
                    ))}
                </div>
            )}

            {eventoDetalhe && (
                selectedEvento?.id_evento === 'ciranda-mej-26' ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {eventoDetalhe.metas.map((meta) => (
                            <CirandaMetaCard
                                key={meta.tipo}
                                meta={meta}
                                expanded={expandedMetas.has(meta.tipo)}
                                onToggle={() => toggleMeta(meta.tipo)}
                            />
                        ))}
                    </div>
                ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        {eventoDetalhe.metas.map((meta) => (
                            <EventoMetaCard
                                key={meta.tipo}
                                meta={meta}
                                expanded={expandedMetas.has(meta.tipo)}
                                onToggle={() => toggleMeta(meta.tipo)}
                            />
                        ))}
                    </div>
                )
            )}
        </div>
    );
}