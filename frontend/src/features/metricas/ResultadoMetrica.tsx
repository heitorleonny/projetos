import { Link } from 'react-router-dom';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatarCompacto, formatarValor, MESES, textoPeriodo, type ResultadoMetrica, type Visual } from './metricasService';

function Ranking({ resultado }: { resultado: ResultadoMetrica }) {
    const maior = Math.max(...resultado.linhas.map(l => Math.abs(l.valor)), 0) || 1;
    return (
        <ol className="space-y-2" aria-label="Ranking de EJs">
            {resultado.linhas.map(linha => (
                <li key={linha.id_ej} className="grid grid-cols-[2rem_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 text-sm">
                    <span className="text-right font-heading font-semibold text-neutral-400">{linha.posicao}º</span>
                    <Link to={`/empresas/${linha.id_ej}?ano=${resultado.ano}`} className="truncate text-white no-underline hover:text-accent-300">
                        {linha.nome}
                        {linha.cluster !== null && <span className="ml-2 text-xs text-neutral-500">C{linha.cluster}</span>}
                    </Link>
                    <span className="font-semibold tabular-nums text-neutral-100">{formatarValor(linha.valor, resultado.unidade)}</span>
                    <span aria-hidden="true" className="col-start-2 col-span-2 h-1.5 overflow-hidden rounded-full bg-white/5">
                        <span className="block h-full rounded-full bg-primary-500" style={{ width: `${Math.max(2, (Math.abs(linha.valor) / maior) * 100)}%` }} />
                    </span>
                </li>
            ))}
        </ol>
    );
}

function Valor({ resultado }: { resultado: ResultadoMetrica }) {
    return (
        <div className="py-4">
            <p className="font-heading text-4xl font-bold text-white tabular-nums break-words">{formatarValor(resultado.valor_rede, resultado.unidade)}</p>
            <p className="mt-2 text-sm text-neutral-400">
                {resultado.agregacao_rede === 'soma' ? 'Soma' : 'Média'} de {resultado.avaliadas} EJs da rede
            </p>
        </div>
    );
}

function Serie({ resultado }: { resultado: ResultadoMetrica }) {
    const dados = resultado.serie.map(p => ({ ...p, rotulo: MESES[p.mes - 1].slice(0, 3) }));
    return (
        <div className="h-64" role="img" aria-label={`Evolução mensal: ${dados.map(p => `${p.rotulo} ${p.valor === null ? 'sem valor' : formatarValor(p.valor, resultado.unidade)}`).join(', ')}`}>
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dados} margin={{ top: 10, right: 16, left: 4, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="rotulo" tick={{ fill: '#94A3B8', fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis width={84} tick={{ fill: '#94A3B8', fontSize: 12 }} axisLine={false} tickLine={false}
                        tickFormatter={(v: number) => formatarCompacto(v, resultado.unidade)} />
                    <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                        formatter={(v, _nome, item) => [formatarValor(typeof v === 'number' ? v : null, resultado.unidade),
                            `${resultado.agregacao_rede === 'soma' ? 'Soma' : 'Média'} de ${(item?.payload as { ejs?: number } | undefined)?.ejs ?? 0} EJs`]} />
                    <Line type="monotone" dataKey="valor" stroke="var(--color-primary-400)" strokeWidth={2.5} connectNulls={false}
                        dot={{ fill: 'var(--color-primary-400)', strokeWidth: 0, r: 4 }} />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}

export default function ResultadoView({ resultado, visual }: { resultado: ResultadoMetrica; visual: Visual }) {
    const vazio = resultado.status === 'sem_dados' || (visual === 'ranking' && resultado.linhas.length === 0);
    return (
        <div>
            <p className="mb-3 text-xs text-neutral-400">
                {textoPeriodo(resultado.ano, resultado.mes_inicio, resultado.mes_fim)}
                {visual === 'ranking' && (resultado.ordem === 'asc' ? ' · menores valores' : ' · maiores valores')}
            </p>
            {vazio
                ? <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-200">{resultado.mensagem}</p>
                : visual === 'ranking' ? <Ranking resultado={resultado} />
                    : visual === 'valor' ? <Valor resultado={resultado} /> : <Serie resultado={resultado} />}
            {!vazio && <p className="mt-3 text-xs text-neutral-500">{resultado.mensagem}</p>}
            <details className="mt-3 text-xs text-neutral-400">
                <summary className="cursor-pointer text-neutral-300 hover:text-white">Como é calculado</summary>
                <p className="mt-2 font-medium text-neutral-200">{resultado.formula_legivel}</p>
                <ul className="mt-1 list-disc space-y-1 pl-5">
                    {resultado.explicacao.map(item => <li key={item}>{item}</li>)}
                </ul>
            </details>
        </div>
    );
}
