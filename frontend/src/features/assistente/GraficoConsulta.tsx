import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Grafico } from './visualizacao';

const COR = 'var(--color-primary-400)';
const GRADE = 'rgba(255,255,255,0.08)';
const EIXO = { fill: '#94A3B8', fontSize: 11 };

function prefereMenosMovimento() {
    return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
        && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function formatarCompleto(valor: number, unidade: Grafico['unidade']) {
    return valor.toLocaleString('pt-BR', unidade === 'moeda' ? { style: 'currency', currency: 'BRL' } : { maximumFractionDigits: 4 });
}

function formatarEixo(valor: number, unidade: Grafico['unidade']) {
    const compacto = valor.toLocaleString('pt-BR', { notation: 'compact', maximumFractionDigits: 1 });
    return unidade === 'moeda' ? `R$ ${compacto}` : compacto;
}

function encurtar(texto: string, limite = 16) {
    return texto.length > limite ? `${texto.slice(0, limite - 1)}…` : texto;
}

/** Visualização da consulta: os mesmos valores da tabela, desenhados no navegador. */
export default function GraficoConsulta({ grafico }: { grafico: Grafico }) {
    const animar = !prefereMenosMovimento();
    const tooltip = <Tooltip
        formatter={(valor) => [formatarCompleto(Number(valor), grafico.unidade), 'Valor']}
        contentStyle={{ background: '#0F172A', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
        labelStyle={{ color: '#E2E8F0' }} itemStyle={{ color: '#E2E8F0' }} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />;
    const temNegativo = grafico.pontos.some(ponto => ponto.valor < 0);
    const altura = grafico.tipo === 'barras_horizontais' ? Math.max(160, grafico.pontos.length * 34 + 40) : 220;
    const descricao = `${grafico.titulo}. ${grafico.pontos.map(p => `${p.rotulo}: ${formatarCompleto(p.valor, grafico.unidade)}`).join('; ')}.`;

    return <figure data-visualizacao="grafico" className="rounded-xl border border-neutral-700/80 bg-neutral-800/30 p-3">
        <figcaption className="mb-2 text-xs text-neutral-300">{grafico.titulo}</figcaption>
        <div role="img" aria-label={descricao} className="w-full">
            <ResponsiveContainer width="100%" height={altura}>
                {grafico.tipo === 'linha'
                    ? <LineChart data={grafico.pontos} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke={GRADE} vertical={false} />
                        <XAxis dataKey="rotulo" tick={EIXO} tickLine={false} axisLine={{ stroke: GRADE }} />
                        <YAxis width={64} tick={EIXO} tickLine={false} axisLine={false} tickFormatter={(v: number) => formatarEixo(v, grafico.unidade)} />
                        {tooltip}
                        <Line type="monotone" dataKey="valor" stroke={COR} strokeWidth={2} dot={{ r: 3, fill: COR }} isAnimationActive={animar} />
                    </LineChart>
                    : grafico.tipo === 'barras_horizontais'
                        ? <BarChart data={grafico.pontos} layout="vertical" margin={{ top: 4, right: 12, left: 0, bottom: 4 }} barCategoryGap={8}>
                            <CartesianGrid strokeDasharray="3 3" stroke={GRADE} horizontal={false} />
                            <XAxis type="number" tick={EIXO} tickLine={false} axisLine={{ stroke: GRADE }} tickFormatter={(v: number) => formatarEixo(v, grafico.unidade)} />
                            <YAxis type="category" dataKey="rotulo" width={112} tick={EIXO} tickLine={false} axisLine={false} tickFormatter={(v: string) => encurtar(v)} />
                            {tooltip}
                            <Bar dataKey="valor" fill={COR} radius={[0, 4, 4, 0]} isAnimationActive={animar} />
                        </BarChart>
                        : <BarChart data={grafico.pontos} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke={GRADE} vertical={false} />
                            <XAxis dataKey="rotulo" tick={EIXO} tickLine={false} axisLine={{ stroke: GRADE }} interval={0} tickFormatter={(v: string) => encurtar(v, 14)} />
                            <YAxis width={48} tick={EIXO} tickLine={false} axisLine={false} tickFormatter={(v: number) => formatarEixo(v, grafico.unidade)} />
                            {temNegativo && <ReferenceLine y={0} stroke="#64748B" />}
                            {tooltip}
                            <Bar dataKey="valor" fill={COR} radius={[4, 4, 0, 0]} isAnimationActive={animar} />
                        </BarChart>}
            </ResponsiveContainer>
        </div>
    </figure>;
}
