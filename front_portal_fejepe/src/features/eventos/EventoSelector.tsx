import type { EventoResumo } from '../../types/evento';

interface EventoSelectorProps {
    eventos: EventoResumo[];
    selectedEventoId: string;
    onChange: (eventoId: string) => void;
}

export default function EventoSelector({ eventos, selectedEventoId, onChange }: EventoSelectorProps) {
    return (
        <div className="glass-card rounded-2xl p-5">
            <label className="text-xs text-neutral-400 uppercase tracking-wider font-semibold mb-2.5 block">
                Selecionar evento
            </label>
            <select
                value={selectedEventoId}
                onChange={(event) => onChange(event.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all cursor-pointer appearance-none"
            >
                {eventos.map((evento) => (
                    <option key={evento.id_evento} value={evento.id_evento} className="bg-neutral-900">
                        {evento.nome} {evento.ativo ? '(atual)' : '(planejado)'}
                    </option>
                ))}
            </select>
            {eventos.find((evento) => evento.id_evento === selectedEventoId)?.descricao && (
                <p className="mt-3 text-xs text-neutral-400 leading-relaxed">
                    {eventos.find((evento) => evento.id_evento === selectedEventoId)?.descricao}
                </p>
            )}
        </div>
    );
}