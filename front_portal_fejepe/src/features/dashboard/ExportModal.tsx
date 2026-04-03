import { useState } from 'react';
import type { EmpresaComIndicadores } from '../../types/empresa';

interface ExportField {
    key: keyof EmpresaComIndicadores;
    label: string;
    format?: (value: unknown) => string;
}

const EXPORT_FIELDS: ExportField[] = [
    { key: 'nome', label: 'Nome' },
    { key: 'id_ej', label: 'ID EJ' },
    { key: 'cluster', label: 'Cluster' },
    { key: 'comunidade', label: 'Comunidade' },
    { key: 'cidade', label: 'Cidade' },
    { key: 'universidade', label: 'Universidade' },
    { key: 'status', label: 'Status' },
    { key: 'faturamento_acumulado', label: 'Faturamento Acumulado' },
    { key: 'faturamento_colab_acumulado', label: 'Faturamento Colab. Acumulado' },
    { key: 'faturamento_mes', label: 'Faturamento do Mês' },
    { key: 'projetos_totais', label: 'Projetos Totais' },
    { key: 'projetos_colab_totais', label: 'Projetos Colab. Totais' },
    { key: 'csat_medio', label: 'CSAT Médio' },
    { key: 'percentual_meta', label: '% Meta' },
    { key: 'ritmo', label: 'Ritmo' },
    { key: 'taxa_colaboracao', label: 'Taxa de Colaboração' },
    { key: 'cluster_calculado', label: 'Cluster Calculado' },
    { key: 'tendencia_cluster', label: 'Tendência Cluster' },
];

interface ExportModalProps {
    empresas: EmpresaComIndicadores[];
    onClose: () => void;
}

export default function ExportModal({ empresas, onClose }: ExportModalProps) {
    const [selected, setSelected] = useState<Set<keyof EmpresaComIndicadores>>(
        () => new Set(EXPORT_FIELDS.map((f) => f.key)),
    );

    const toggleField = (key: keyof EmpresaComIndicadores) => {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(key)) {
                next.delete(key);
            } else {
                next.add(key);
            }
            return next;
        });
    };

    const toggleAll = () => {
        if (selected.size === EXPORT_FIELDS.length) {
            setSelected(new Set());
        } else {
            setSelected(new Set(EXPORT_FIELDS.map((f) => f.key)));
        }
    };

    const handleExport = () => {
        const fields = EXPORT_FIELDS.filter((f) => selected.has(f.key));
        if (fields.length === 0) return;

        const header = fields.map((f) => f.label).join(';');
        const rows = empresas.map((ej) =>
            fields
                .map((f) => {
                    const raw = ej[f.key];
                    if (raw == null) return '';
                    const str = String(raw);
                    // Escape fields containing separator or quotes
                    if (str.includes(';') || str.includes('"') || str.includes('\n')) {
                        return `"${str.replace(/"/g, '""')}"`;
                    }
                    return str;
                })
                .join(';'),
        );

        const bom = '\uFEFF';
        const csv = bom + [header, ...rows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `dashboard_ejs_${new Date().toISOString().slice(0, 10)}.csv`;
        link.click();
        URL.revokeObjectURL(url);
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative glass-card rounded-2xl w-full max-w-lg p-6 shadow-2xl border border-white/10 animate-in fade-in zoom-in-95">
                {/* Header */}
                <div className="flex items-center justify-between mb-5">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-primary-500/10 text-primary-400">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                            </svg>
                        </div>
                        <div>
                            <h2 className="font-heading font-semibold text-lg text-white">
                                Exportar CSV
                            </h2>
                            <p className="text-xs text-neutral-500">
                                {empresas.length} EJ{empresas.length !== 1 ? 's' : ''} filtrada{empresas.length !== 1 ? 's' : ''}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-lg text-neutral-500 hover:text-white hover:bg-white/10 transition-all cursor-pointer"
                    >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Select all */}
                <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-neutral-400 uppercase tracking-wider font-semibold">
                        Campos para exportação
                    </span>
                    <button
                        onClick={toggleAll}
                        className="text-xs text-primary-400 hover:text-primary-300 transition-colors cursor-pointer"
                    >
                        {selected.size === EXPORT_FIELDS.length ? 'Desmarcar todos' : 'Selecionar todos'}
                    </button>
                </div>

                {/* Fields list */}
                <div className="grid grid-cols-2 gap-1.5 max-h-72 overflow-y-auto pr-1 custom-scrollbar">
                    {EXPORT_FIELDS.map((field) => {
                        const checked = selected.has(field.key);
                        return (
                            <label
                                key={field.key}
                                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer transition-all text-sm
                                    ${checked
                                        ? 'bg-primary-500/10 text-white border border-primary-500/20'
                                        : 'bg-white/[0.03] text-neutral-500 border border-transparent hover:bg-white/[0.06]'
                                    }`}
                            >
                                <input
                                    type="checkbox"
                                    checked={checked}
                                    onChange={() => toggleField(field.key)}
                                    className="sr-only"
                                />
                                <div
                                    className={`w-4 h-4 rounded flex items-center justify-center shrink-0 border transition-all
                                        ${checked
                                            ? 'bg-primary-500 border-primary-500'
                                            : 'border-neutral-600'
                                        }`}
                                >
                                    {checked && (
                                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                        </svg>
                                    )}
                                </div>
                                <span className="truncate">{field.label}</span>
                            </label>
                        );
                    })}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between mt-5 pt-4 border-t border-white/5">
                    <span className="text-xs text-neutral-500">
                        {selected.size} campo{selected.size !== 1 ? 's' : ''} selecionado{selected.size !== 1 ? 's' : ''}
                    </span>
                    <div className="flex gap-2">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 rounded-lg text-sm text-neutral-400 hover:text-white hover:bg-white/10 transition-all cursor-pointer"
                        >
                            Cancelar
                        </button>
                        <button
                            onClick={handleExport}
                            disabled={selected.size === 0}
                            className="px-5 py-2 rounded-lg text-sm font-medium btn-glow text-white disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                        >
                            Exportar
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
