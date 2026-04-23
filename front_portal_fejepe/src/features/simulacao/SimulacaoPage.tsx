import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchIndicadoresRede } from '../indicadores/indicadoresService';
import { getClusterInfo } from '../../utils/formatters';

const CLUSTERS = [1, 2, 3, 4, 5] as const;
const PESOS: Record<number, number> = { 1: 0.30, 2: 0.25, 3: 0.15, 4: 0.15, 5: 0.15 };
const ANO_DEFAULT = 2026;

interface ClusterRow {
    total: number;
    subindo: number;
    descendo: number;
}

const INITIAL_STATE: Record<number, ClusterRow> = {
    1: { total: 0, subindo: 0, descendo: 0 },
    2: { total: 0, subindo: 0, descendo: 0 },
    3: { total: 0, subindo: 0, descendo: 0 },
    4: { total: 0, subindo: 0, descendo: 0 },
    5: { total: 0, subindo: 0, descendo: 0 },
};

function calcularSde(rows: Record<number, ClusterRow>): number {
    let sde = 0;
    for (const c of CLUSTERS) {
        // C5 só entra na conta de descendo
        const subidas = c === 5 ? 0 : rows[c].subindo;
        sde += PESOS[c] * (subidas - rows[c].descendo);
    }
    return Math.round(sde * 10000) / 10000;
}

function Spinner({
    value,
    onChange,
    color,
}: {
    value: number;
    onChange: (v: string) => void;
    color: string;
}) {
    return (
        <div className="flex items-center justify-center gap-1.5">
            <button
                onClick={() => onChange(String(Math.max(0, value - 1)))}
                className="w-6 h-6 rounded-md bg-white/5 border border-white/10 text-neutral-400 hover:text-white hover:bg-white/10 transition-colors text-sm leading-none cursor-pointer flex items-center justify-center"
            >
                −
            </button>
            <input
                type="number"
                min={0}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="w-12 text-center text-sm font-semibold bg-white/5 border border-white/10 rounded-md py-1 focus:outline-none tabular-nums [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                style={{ color }}
            />
            <button
                onClick={() => onChange(String(value + 1))}
                className="w-6 h-6 rounded-md bg-white/5 border border-white/10 text-neutral-400 hover:text-white hover:bg-white/10 transition-colors text-sm leading-none cursor-pointer flex items-center justify-center"
            >
                +
            </button>
        </div>
    );
}

export default function SimulacaoPage() {
    const [rows, setRows] = useState<Record<number, ClusterRow>>(INITIAL_STATE);

    const { data: indicadores } = useQuery({
        queryKey: ['indicadores-rede', { ano: ANO_DEFAULT }],
        queryFn: () => fetchIndicadoresRede({ ano: ANO_DEFAULT }),
    });

    // Preenche totais com os dados reais quando a API responde
    useEffect(() => {
        if (!indicadores?.distribuicao_clusters) return;
        setRows((prev) => {
            const next = { ...prev };
            for (const c of CLUSTERS) {
                const total = indicadores.distribuicao_clusters[String(c)] ?? 0;
                next[c] = { ...next[c], total };
            }
            return next;
        });
    }, [indicadores]);

    const sde = calcularSde(rows);
    const totalEjs = CLUSTERS.reduce((acc, c) => acc + rows[c].total, 0);

    const sdeColor = sde > 0 ? '#16A34A' : sde < 0 ? '#DC2626' : '#F59E0B';
    const sdeLabel = sde > 0 ? `+${sde.toFixed(4)}` : sde.toFixed(4);

    function handleChange(cluster: number, field: keyof ClusterRow, raw: string) {
        const parsed = parseInt(raw, 10);
        const value = isNaN(parsed) || parsed < 0 ? 0 : parsed;
        setRows((prev) => ({ ...prev, [cluster]: { ...prev[cluster], [field]: value } }));
    }

    function reset() {
        setRows((prev) => {
            const next = { ...prev };
            for (const c of CLUSTERS) next[c] = { ...next[c], subindo: 0, descendo: 0 };
            return next;
        });
    }

    return (
        <div className="flex flex-col items-center">
            <div className="w-full max-w-2xl">
                <div className="mb-8 text-center">
                    <h1 className="font-heading text-3xl font-bold text-gradient mb-1">
                        Simulador de Cenários
                    </h1>
                    <p className="text-neutral-400 text-sm italic">
                        Simule o número de EJs subindo e descendo por cluster e veja o impacto no SDE.
                    </p>
                </div>

                {/* Resultado */}
                <div className="glass-card rounded-2xl p-6 mb-6 flex items-center justify-between">
                    <div>
                        <p className="text-xs text-neutral-500 uppercase tracking-wider font-semibold mb-1">
                            SDE Simulado
                        </p>
                        <p className="text-4xl font-bold tabular-nums" style={{ color: sdeColor }}>
                            {sdeLabel}
                        </p>
                    </div>
                    <div className="flex items-center gap-4">
                        <div className="text-right">
                            <p className="text-xs text-neutral-500 uppercase tracking-wider font-semibold mb-1">
                                Total de EJs
                            </p>
                            <p className="text-4xl font-bold tabular-nums text-white">
                                {totalEjs}
                            </p>
                        </div>
                        <button
                            onClick={reset}
                            className="text-xs font-semibold px-4 py-2 rounded-lg border border-white/10 bg-white/5 text-neutral-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
                        >
                            Resetar
                        </button>
                    </div>
                </div>

                {/* Tabela por cluster */}
                <div className="glass-card rounded-2xl overflow-hidden w-full">
                    {/* Header */}
                    <div className="grid grid-cols-[1fr_80px_1fr_1fr_80px] gap-3 px-5 py-3 border-b border-white/5">
                        <span className="text-[11px] uppercase tracking-wider text-neutral-500 font-semibold">Cluster</span>
                        <span className="text-[11px] uppercase tracking-wider text-neutral-500 font-semibold text-center">Total EJs</span>
                        <span className="text-[11px] uppercase tracking-wider text-green-600 font-semibold text-center">Subindo</span>
                        <span className="text-[11px] uppercase tracking-wider text-red-600 font-semibold text-center">Descendo</span>
                        <span className="text-[11px] uppercase tracking-wider text-neutral-500 font-semibold text-right">Contribuição</span>
                    </div>

                    {CLUSTERS.map((c, idx) => {
                        const info = getClusterInfo(c);
                        const row = rows[c];
                        const subidas = c === 5 ? 0 : row.subindo;
                        const contribuicao = PESOS[c] * (subidas - row.descendo);
                        const contribColor = contribuicao > 0 ? '#16A34A' : contribuicao < 0 ? '#DC2626' : '#64748B';
                        const contribLabel = contribuicao > 0
                            ? `+${contribuicao.toFixed(4)}`
                            : contribuicao.toFixed(4);

                        return (
                            <div
                                key={c}
                                className={`grid grid-cols-[1fr_80px_1fr_1fr_80px] gap-3 items-center px-5 py-4 ${idx < CLUSTERS.length - 1 ? 'border-b border-white/5' : ''}`}
                            >
                                {/* Cluster */}
                                <div className="flex items-center gap-2">
                                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: info.color }} />
                                    <div>
                                        <span className="text-sm font-semibold text-white">{info.label}</span>
                                        <span className="text-[10px] text-neutral-600 ml-1.5 tabular-nums">
                                            peso {PESOS[c].toFixed(2)}
                                        </span>
                                    </div>
                                </div>

                                {/* Total EJs */}
                                <div className="flex items-center justify-center">
                                    <Spinner
                                        value={row.total}
                                        onChange={(v) => handleChange(c, 'total', v)}
                                        color="#E2E8F0"
                                    />
                                </div>

                                {/* Subindo — desabilitado para C5 */}
                                <div className="flex items-center justify-center">
                                    {c === 5 ? (
                                        <span className="text-xs text-neutral-700 italic">—</span>
                                    ) : (
                                        <Spinner
                                            value={row.subindo}
                                            onChange={(v) => handleChange(c, 'subindo', v)}
                                            color="#4ade80"
                                        />
                                    )}
                                </div>

                                {/* Descendo */}
                                <div className="flex items-center justify-center">
                                    <Spinner
                                        value={row.descendo}
                                        onChange={(v) => handleChange(c, 'descendo', v)}
                                        color="#f87171"
                                    />
                                </div>

                                {/* Contribuição */}
                                <span
                                    className="text-xs font-semibold tabular-nums text-right"
                                    style={{ color: contribColor }}
                                >
                                    {contribLabel}
                                </span>
                            </div>
                        );
                    })}

                    {/* Footer */}
                    <div className="px-5 py-3 border-t border-white/5 bg-white/[0.02]">
                        <p className="text-[10px] text-neutral-600">
                            SDE = Σ peso<sub>i</sub> × (subidas<sub>i</sub> − descidas<sub>i</sub>) &nbsp;|&nbsp;
                            Pesos: C1=0,30 · C2=0,25 · C3–C5=0,15 &nbsp;|&nbsp; C5 não computa subidas
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
