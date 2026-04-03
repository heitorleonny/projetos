import {
    Bar,
    BarChart,
    CartesianGrid,
    Legend,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts';
import type { EmpresaComIndicadores } from '../../types/empresa';
import { formatCurrency } from '../../utils/formatters';

interface ComparacaoChartRow {
    id_ej: number;
    nome: string;
    porAno: Record<number, EmpresaComIndicadores | undefined>;
}

interface ComparacaoFaturamentoChartProps {
    rows: ComparacaoChartRow[];
    anosSelecionados: number[];
    anoColors: Record<number, string>;
}

export default function ComparacaoFaturamentoChart({
    rows,
    anosSelecionados,
    anoColors,
}: ComparacaoFaturamentoChartProps) {
    const anosOrdenados = [...anosSelecionados].sort((a, b) => a - b);
    const anoBase = anosOrdenados[anosOrdenados.length - 1] ?? anosOrdenados[0];

    const chartData = [...rows]
        .sort((a, b) => {
            const aFat = a.porAno[anoBase]?.faturamento_acumulado ?? 0;
            const bFat = b.porAno[anoBase]?.faturamento_acumulado ?? 0;
            return bFat - aFat;
        })
        .map((row) => {
            const base: Record<string, number | string> = {
                nome: row.nome,
            };

            for (const ano of anosOrdenados) {
                base[String(ano)] = row.porAno[ano]?.faturamento_acumulado ?? 0;
            }

            return base;
        });

    const chartHeight = Math.min(Math.max(chartData.length * 42, 300), 900);

    return (
        <div className="glass-card rounded-2xl p-5 mb-8">
            <div className="flex items-center justify-between gap-3 mb-4">
                <h3 className="text-sm font-heading font-semibold text-white uppercase tracking-wider">
                    Faturamento por EJ e Ano
                </h3>
                <span className="text-xs text-neutral-500">
                    Base: acumulado{anoBase ? ` ate ${anoBase}` : ''}
                </span>
            </div>

            <div className="max-h-[920px] overflow-y-auto pr-2 custom-scrollbar">
                <ResponsiveContainer width="100%" height={chartHeight}>
                    <BarChart
                        data={chartData}
                        layout="vertical"
                        margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
                        barCategoryGap={10}
                    >
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
                        <XAxis
                            type="number"
                            tick={{ fill: '#94A3B8', fontSize: 11 }}
                            axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
                            tickLine={false}
                            tickFormatter={(value: number) =>
                                value >= 1000 ? `R$ ${(value / 1000).toFixed(0)}k` : `R$ ${value}`
                            }
                        />
                        <YAxis
                            dataKey="nome"
                            type="category"
                            width={180}
                            tick={{ fill: '#CBD5E1', fontSize: 11 }}
                            axisLine={false}
                            tickLine={false}
                        />
                        <Tooltip
                            cursor={{ fill: 'rgba(13,110,253,0.08)' }}
                            contentStyle={{
                                background: 'rgba(2, 6, 23, 0.95)',
                                border: '1px solid rgba(148, 163, 184, 0.18)',
                                borderRadius: '12px',
                                color: '#E2E8F0',
                            }}
                            formatter={(value: number | undefined, name: string | undefined) => [formatCurrency(value ?? 0), name ?? '']}
                        />
                        <Legend wrapperStyle={{ fontSize: '12px', color: '#94A3B8' }} />

                        {anosOrdenados.map((ano) => (
                            <Bar
                                key={ano}
                                dataKey={String(ano)}
                                name={String(ano)}
                                fill={anoColors[ano] ?? '#0D6EFD'}
                                radius={[0, 4, 4, 0]}
                                maxBarSize={16}
                            />
                        ))}
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
