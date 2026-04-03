import { useMemo, useState } from 'react';

export interface ComparacaoExportField {
    key: string;
    label: string;
    scope: 'base' | 'ano';
    defaultSelected?: boolean;
}

interface ComparacaoExportModalProps {
    fields: ComparacaoExportField[];
    initialSelectedKeys?: string[];
    onClose: () => void;
    onConfirm: (selectedKeys: string[]) => void;
}

export default function ComparacaoExportModal({
    fields,
    initialSelectedKeys,
    onClose,
    onConfirm,
}: ComparacaoExportModalProps) {
    const defaultSelected = useMemo(() => {
        if (initialSelectedKeys && initialSelectedKeys.length > 0) {
            return new Set(initialSelectedKeys);
        }
        return new Set(fields.filter((f) => f.defaultSelected).map((f) => f.key));
    }, [fields, initialSelectedKeys]);

    const [selected, setSelected] = useState<Set<string>>(defaultSelected);

    const baseFields = fields.filter((field) => field.scope === 'base');
    const anoFields = fields.filter((field) => field.scope === 'ano');

    const toggleField = (key: string) => {
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
        if (selected.size === fields.length) {
            setSelected(new Set());
            return;
        }
        setSelected(new Set(fields.map((f) => f.key)));
    };

    const handleConfirm = () => {
        if (selected.size === 0) return;
        onConfirm(Array.from(selected));
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

            <div className="relative glass-card rounded-2xl w-full max-w-2xl p-6 shadow-2xl border border-white/10 animate-in fade-in zoom-in-95">
                <div className="flex items-center justify-between mb-5">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-primary-500/10 text-primary-400">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                            </svg>
                        </div>
                        <div>
                            <h2 className="font-heading font-semibold text-lg text-white">Exportar Planilha</h2>
                            <p className="text-xs text-neutral-500">Escolha os campos que vao para o CSV.</p>
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

                <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-neutral-400 uppercase tracking-wider font-semibold">Campos</span>
                    <button
                        onClick={toggleAll}
                        className="text-xs text-primary-400 hover:text-primary-300 transition-colors cursor-pointer"
                    >
                        {selected.size === fields.length ? 'Desmarcar todos' : 'Selecionar todos'}
                    </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-[420px] overflow-y-auto pr-1 custom-scrollbar">
                    <FieldBlock
                        title="Dados Cadastrais"
                        fields={baseFields}
                        selected={selected}
                        onToggle={toggleField}
                    />
                    <FieldBlock
                        title="Indicadores por Ano"
                        fields={anoFields}
                        selected={selected}
                        onToggle={toggleField}
                    />
                </div>

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
                            onClick={handleConfirm}
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

function FieldBlock({
    title,
    fields,
    selected,
    onToggle,
}: {
    title: string;
    fields: ComparacaoExportField[];
    selected: Set<string>;
    onToggle: (key: string) => void;
}) {
    return (
        <div>
            <p className="text-[11px] text-neutral-500 uppercase tracking-wider font-semibold mb-2">{title}</p>
            <div className="space-y-1.5">
                {fields.map((field) => {
                    const checked = selected.has(field.key);
                    return (
                        <label
                            key={field.key}
                            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer transition-all text-sm ${checked
                                ? 'bg-primary-500/10 text-white border border-primary-500/20'
                                : 'bg-white/[0.03] text-neutral-500 border border-transparent hover:bg-white/[0.06]'
                                }`}
                        >
                            <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => onToggle(field.key)}
                                className="sr-only"
                            />
                            <div
                                className={`w-4 h-4 rounded flex items-center justify-center shrink-0 border transition-all ${checked
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
        </div>
    );
}
