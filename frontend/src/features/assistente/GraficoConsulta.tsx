import { Bar, BarChart, CartesianGrid, LabelList, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Grafico } from './visualizacao';

const COR = 'var(--color-primary-400)';
const GRADE = 'rgba(255,255,255,0.08)';
const EIXO = { fill: '#94A3B8', fontSize: 11 };
const ALTURA_LINHA = 40;

function prefereMenosMovimento() {
    return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
        && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function formatarCompleto(valor: number, unidade: Grafico['unidade']) {
    return valor.toLocaleString('pt-BR', unidade === 'moeda' ? { style: 'currency', currency: 'BRL' } : { maximumFractionDigits: 4 });
}

/** Eixo sem "R$": a unidade vai no título, para caber em largura de celular. */
function formatarEixo(valor: number) {
    return valor.toLocaleString('pt-BR', { notation: 'compact', maximumFractionDigits: 1 });
}

function encurtar(texto: string, limite = 40) {
    return texto.length > limite ? `${texto.slice(0, limite - 1)}…` : texto;
}

/** Rótulo acima da barra, alinhado ao início do gráfico: nomes longos não disputam o eixo. */
function RotuloDaBarra({ y, value }: { y?: unknown; value?: unknown }) {
    return <text x={4} y={Number(y) - 5} fill="#CBD5E1" fontSize={11}>{encurtar(String(value ?? ''))}</text>;
}

/**
 * Visualização da consulta: os mesmos valores da tabela, desenhados no navegador.
 * Todas as barras são horizontais (ranking, ritmo, SDE e faixas de meta), com o
 * nome acima de cada barra; a série do perfil é uma linha.
 */
export default function GraficoConsulta({ grafico }: { grafico: Grafico }) {
    const animar = !prefereMenosMovimento();
    const tooltip = <Tooltip
        formatter={(valor) => [formatarCompleto(Number(valor), grafico.unidade), 'Valor']}
        contentStyle={{ background: '#0F172A', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
        labelStyle={{ color: '#E2E8F0' }} itemStyle={{ color: '#E2E8F0' }} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />;
    const temNegativo = grafico.pontos.some(ponto => ponto.valor < 0);
    const titulo = grafico.unidade === 'moeda' ? `${grafico.titulo} (R$)` : grafico.titulo;
    const altura = grafico.tipo === 'linha' ? 220 : grafico.pontos.length * ALTURA_LINHA + 36;
    const descricao = `${grafico.titulo}. ${grafico.pontos.map(p => `${p.rotulo}: ${formatarCompleto(p.valor, grafico.unidade)}`).join('; ')}.`;

    return <figure data-visualizacao="grafico" data-tipo={grafico.tipo} className="rounded-xl border border-neutral-700/80 bg-neutral-800/30 p-3">
        <figcaption className="mb-2 text-xs text-neutral-300">{titulo}</figcaption>
        <div role="img" aria-label={descricao} className="w-full">
            <ResponsiveContainer width="100%" height={altura}>
                {grafico.tipo === 'linha'
                    ? <LineChart data={grafico.pontos} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke={GRADE} vertical={false} />
                        <XAxis dataKey="rotulo" tick={EIXO} tickLine={false} axisLine={{ stroke: GRADE }} />
                        <YAxis width={44} tick={EIXO} tickLine={false} axisLine={false} tickFormatter={formatarEixo} />
                        {tooltip}
                        <Line type="monotone" dataKey="valor" stroke={COR} strokeWidth={2} dot={{ r: 3, fill: COR }} isAnimationActive={animar} />
                    </LineChart>
                    : <BarChart data={grafico.pontos} layout="vertical" margin={{ top: 16, right: 12, left: 4, bottom: 0 }} barCategoryGap={16}>
                        <CartesianGrid strokeDasharray="3 3" stroke={GRADE} horizontal={false} />
                        <XAxis type="number" tick={EIXO} tickLine={false} axisLine={{ stroke: GRADE }} tickFormatter={formatarEixo} />
                        <YAxis type="category" dataKey="rotulo" hide />
                        {temNegativo && <ReferenceLine x={0} stroke="#64748B" />}
                        {tooltip}
                        <Bar dataKey="valor" fill={COR} radius={4} barSize={12} isAnimationActive={animar}>
                            <LabelList dataKey="rotulo" content={RotuloDaBarra} />
                        </Bar>
                    </BarChart>}
            </ResponsiveContainer>
        </div>
    </figure>;
}
