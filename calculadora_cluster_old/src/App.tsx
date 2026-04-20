import { useState, useMemo } from 'react';

// ── Constants ────────────────────────────────────────────────────
const CLUSTER_RANGES: [number, number, number][] = [
  [0, 12_000_000, 1],
  [12_000_000.01, 24_000_000, 2],
  [24_000_000.01, 61_000_000, 3],
  [61_000_000.01, 130_000_000, 4],
  [130_000_000.01, Infinity, 5],
];

const CLUSTER_COLORS: Record<number, { color: string; bg: string; border: string; label: string }> = {
  1: { color: '#64748B', bg: '#64748B15', border: '#64748B30', label: 'Cluster 1' },
  2: { color: '#3B82F6', bg: '#3B82F615', border: '#3B82F630', label: 'Cluster 2' },
  3: { color: '#8B5CF6', bg: '#8B5CF615', border: '#8B5CF630', label: 'Cluster 3' },
  4: { color: '#F59E0B', bg: '#F59E0B15', border: '#F59E0B30', label: 'Cluster 4' },
  5: { color: '#16A34A', bg: '#16A34A15', border: '#16A34A30', label: 'Cluster 5' },
};

const MESES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];

// ── Helpers ──────────────────────────────────────────────────────
function calcularPontos(fat: number, csat: number, engaj: number, colab: number): number {
  return fat * csat * (1 + engaj) * (1 + colab) * 100;
}

function classificarCluster(pontos: number): number {
  for (const [min, max, cluster] of CLUSTER_RANGES) {
    if (pontos >= min && pontos <= max) return cluster;
  }
  return 1;
}

function formatPontos(v: number): string {
  if (v >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(2)}B`;
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}k`;
  return v.toFixed(0);
}

function formatCurrency(v: number): string {
  return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
}

// ── Slider field ─────────────────────────────────────────────────
function SliderField({
  label, hint, value, onChange, min = 0, max, step = 1, formatValue,
}: {
  label: string;
  hint?: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max: number;
  step?: number;
  formatValue: (v: number) => string;
}) {
  const pct = max > min ? ((value - min) / (max - min)) * 100 : 0;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-2">
        <label className="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">
          {label}
          {hint && <span className="ml-1.5 text-neutral-600 normal-case font-normal tracking-normal">{hint}</span>}
        </label>
        <span className="text-sm font-bold text-white tabular-nums shrink-0">{formatValue(value)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ '--range-pct': `${pct}%` } as React.CSSProperties}
      />
      <div className="flex justify-between text-[10px] text-neutral-700">
        <span>{formatValue(min)}</span>
        <span>{formatValue(max)}</span>
      </div>
    </div>
  );
}

// ── Currency input ────────────────────────────────────────────────
function CurrencyField({
  label, hint, value, onChange, placeholder = '0',
}: {
  label: string; hint?: string; value: string; onChange: (v: string) => void; placeholder?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">
        {label}
        {hint && <span className="ml-1.5 text-neutral-600 normal-case font-normal tracking-normal">{hint}</span>}
      </label>
      <div className="flex items-center bg-white/[0.04] border border-white/10 rounded-lg overflow-hidden focus-within:border-primary-500/50 focus-within:ring-1 focus-within:ring-primary-500/20 transition-all">
        <span className="px-3 text-sm text-neutral-500 border-r border-white/10 py-2.5 shrink-0">R$</span>
        <input
          type="number"
          min={0}
          step="any"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="flex-1 bg-transparent px-3 py-2.5 text-sm text-white outline-none placeholder-neutral-700 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
        />
      </div>
    </div>
  );
}

// ── Result card ───────────────────────────────────────────────────
function ResultCard({
  label, description, pontos, cluster, inputs,
}: {
  label: string; description: string; pontos: number | null; cluster: number | null;
  inputs: { label: string; value: string }[];
}) {
  const [showInputs, setShowInputs] = useState(false);
  const ci = cluster ? CLUSTER_COLORS[cluster] : CLUSTER_COLORS[1];
  const hasValue = pontos != null;

  return (
    <div
      className="rounded-2xl border flex flex-col overflow-hidden transition-all duration-300"
      style={{ backgroundColor: `${ci.color}06`, borderColor: hasValue ? ci.border : 'rgba(255,255,255,0.06)' }}
    >
      <div className="p-6 flex flex-col gap-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-neutral-400">{label}</p>
            <p className="text-[11px] text-neutral-600 mt-0.5">{description}</p>
          </div>
          {hasValue && cluster != null && (
            <span
              className="shrink-0 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide border"
              style={{ color: ci.color, backgroundColor: ci.bg, borderColor: ci.border }}
            >
              {ci.label}
            </span>
          )}
        </div>

        {hasValue ? (
          <div>
            <p className="text-4xl font-bold tabular-nums" style={{ color: ci.color }}>
              {formatPontos(pontos!)}
            </p>
            <p className="text-[10px] text-neutral-600 mt-1 tabular-nums">
              {pontos!.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} pts
            </p>
          </div>
        ) : (
          <p className="text-3xl font-bold text-neutral-700">—</p>
        )}
      </div>

      {hasValue && (
        <>
          <button
            onClick={() => setShowInputs((v) => !v)}
            className="flex items-center justify-center gap-1.5 py-2.5 border-t text-[11px] text-neutral-600 hover:text-neutral-400 hover:bg-white/[0.02] transition-colors"
            style={{ borderColor: `${ci.color}15` }}
          >
            {showInputs ? 'Ocultar valores' : 'Ver valores utilizados'}
            <svg className={`w-3.5 h-3.5 transition-transform ${showInputs ? 'rotate-180' : ''}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {showInputs && (
            <div className="border-t px-5 py-3 space-y-2" style={{ borderColor: `${ci.color}15` }}>
              {inputs.map((inp) => (
                <div key={inp.label} className="flex items-center justify-between">
                  <span className="text-[11px] text-neutral-600">{inp.label}</span>
                  <span className="text-[11px] font-mono text-neutral-400">{inp.value}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────
export default function App() {
  const mesAtual = new Date().getMonth() + 1; // automático

  const [faturamento, setFaturamento] = useState('');
  const [fatColab, setFatColab] = useState(0);      // R$ colaborativo (slider)
  const [csatReal, setCsatReal] = useState(0);      // 0-5
  const [metaCsat, setMetaCsat] = useState(0);      // 0-5
  const [engajReal, setEngajReal] = useState(0);    // 0-100
  const [metaEngaj, setMetaEngaj] = useState(0);    // 0-100

  const fat = parseFloat(faturamento) || 0;
  const cl = fat > 0 ? fatColab / fat : 0;           // taxa colab decimal
  const cr = csatReal;
  const mc = metaCsat;
  const er = engajReal / 100;
  const me = metaEngaj / 100;
  const fatAnual = mesAtual > 0 ? (fat / mesAtual) * 12 : 0;

  // Clamp colab slider when faturamento changes
  const colabMax = fat > 0 ? fat : 100_000;

  const results = useMemo(() => {
    const hasBase = fat > 0;
    const c1 = hasBase && cr > 0 ? calcularPontos(fat, cr, er, cl) : null;
    const c2 = hasBase && mc > 0 ? calcularPontos(fat, mc, er, cl) : null;
    const c3 = hasBase && mc > 0 ? calcularPontos(fatAnual, mc, me, cl) : null;
    return {
      c1: { pontos: c1, cluster: c1 != null ? classificarCluster(c1) : null },
      c2: { pontos: c2, cluster: c2 != null ? classificarCluster(c2) : null },
      c3: { pontos: c3, cluster: c3 != null ? classificarCluster(c3) : null },
    };
  }, [fat, cl, cr, mc, er, me, fatAnual]);

  const hasAnyResult = results.c1.pontos != null || results.c2.pontos != null || results.c3.pontos != null;
  const colabPct = fat > 0 ? (fatColab / fat) * 100 : 0;

  return (
    <div className="min-h-screen bg-grid-pattern relative">
      <div className="fixed top-0 left-0 w-96 h-96 rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(13,110,253,0.06) 0%, transparent 70%)' }} />
      <div className="fixed bottom-0 right-0 w-96 h-96 rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(59,130,246,0.04) 0%, transparent 70%)' }} />

      {/* Navbar */}
      <nav className="glass-nav sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-6 h-14 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: 'linear-gradient(135deg, #0A58CA 0%, #0D6EFD 100%)' }}>
            <img src="/logo_fejepe.svg" alt="FEJEPE" className="w-5 h-5" />
          </div>
          <span className="text-sm font-bold font-heading text-white tracking-wide">FEJEPE</span>
          <span className="text-[11px] text-neutral-400 uppercase tracking-widest hidden sm:inline">
            Calculadora de Cluster
          </span>
          <div className="ml-auto flex items-center gap-1.5 text-[11px] text-neutral-500">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            {MESES[mesAtual - 1]}
          </div>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-10 space-y-8 relative z-10">
        {/* Hero */}
        <div className="text-center space-y-3">
          <h1 className="text-3xl md:text-4xl font-bold font-heading text-gradient">
            Calculadora de Cluster
          </h1>
          <p className="text-neutral-400 text-sm max-w-lg mx-auto">
            Insira os dados da sua EJ e veja seu posicionamento nos três índices de cluster da rede FEJEPE.
          </p>
        </div>

        {/* Inputs */}
        <div className="glass-card rounded-2xl p-6 md:p-8 space-y-8">

          {/* Faturamento */}
          <div>
            <SectionTitle icon="💰" title="Faturamento" />
            <div className="mt-4 space-y-5">
              <CurrencyField
                label="Faturamento acumulado"
                hint="total do ano até agora"
                value={faturamento}
                onChange={setFaturamento}
                placeholder="50000"
              />
              {fat > 0 && (
                <p className="text-[11px] text-neutral-600">
                  Anualizado ({MESES[mesAtual - 1]}):&nbsp;
                  <span className="text-neutral-400 font-mono">{formatCurrency(fatAnual)}</span>
                </p>
              )}

              <SliderField
                label="Faturamento colaborativo"
                hint="valor faturado em projetos colaborativos"
                value={Math.min(fatColab, colabMax)}
                onChange={(v) => setFatColab(Math.min(v, fat > 0 ? fat : v))}
                min={0}
                max={colabMax}
                step={Math.max(1, Math.floor(colabMax / 200))}
                formatValue={(v) => `${formatCurrency(v)}${fat > 0 ? ` (${((v / fat) * 100).toFixed(1)}%)` : ''}`}
              />
            </div>
          </div>

          {/* CSAT */}
          <div>
            <SectionTitle icon="⭐" title="CSAT" />
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-6">
              <SliderField
                label="CSAT real"
                hint="média dos CSATs"
                value={csatReal}
                onChange={setCsatReal}
                min={0}
                max={5}
                step={0.1}
                formatValue={(v) => v.toFixed(1)}
              />
              <SliderField
                label="Meta de CSAT"
                hint="meta anual"
                value={metaCsat}
                onChange={setMetaCsat}
                min={0}
                max={5}
                step={0.1}
                formatValue={(v) => v.toFixed(1)}
              />
            </div>
          </div>

          {/* Engajamento */}
          <div>
            <SectionTitle icon="🤝" title="Engajamento com o MEJ" />
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-6">
              <SliderField
                label="Engajamento real"
                hint="membros engajados ÷ total"
                value={engajReal}
                onChange={setEngajReal}
                min={0}
                max={100}
                step={1}
                formatValue={(v) => `${v}%`}
              />
              <SliderField
                label="Meta de engajamento"
                hint="meta anual"
                value={metaEngaj}
                onChange={setMetaEngaj}
                min={0}
                max={100}
                step={1}
                formatValue={(v) => `${v}%`}
              />
            </div>
          </div>
        </div>

        {/* Results */}
        {hasAnyResult ? (
          <div className="space-y-4">
            <h2 className="text-sm font-bold font-heading uppercase tracking-wider text-neutral-400 px-1">
              Resultados
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <ResultCard
                label="Índice de Cluster"
                description="Snapshot real — valores atuais"
                pontos={results.c1.pontos}
                cluster={results.c1.cluster}
                inputs={[
                  { label: 'Faturamento', value: formatCurrency(fat) },
                  { label: 'CSAT real', value: cr.toFixed(1) },
                  { label: 'Engajamento real', value: `${engajReal}%` },
                  { label: 'Fat. Colaborativo', value: `${formatCurrency(fatColab)} (${colabPct.toFixed(1)}%)` },
                ]}
              />
              <ResultCard
                label="Índice c/ Meta CSAT"
                description="Fat. real × Meta CSAT × Engaj. real"
                pontos={results.c2.pontos}
                cluster={results.c2.cluster}
                inputs={[
                  { label: 'Faturamento', value: formatCurrency(fat) },
                  { label: 'Meta CSAT', value: mc.toFixed(1) },
                  { label: 'Engajamento real', value: `${engajReal}%` },
                  { label: 'Fat. Colaborativo', value: `${formatCurrency(fatColab)} (${colabPct.toFixed(1)}%)` },
                ]}
              />
              <ResultCard
                label="Tracking de Cluster"
                description="Projeção anual × Metas de qualidade"
                pontos={results.c3.pontos}
                cluster={results.c3.cluster}
                inputs={[
                  { label: 'Fat. anualizado', value: formatCurrency(fatAnual) },
                  { label: 'Meta CSAT', value: mc.toFixed(1) },
                  { label: 'Meta Engajamento', value: `${metaEngaj}%` },
                  { label: 'Fat. Colaborativo', value: `${formatCurrency(fatColab)} (${colabPct.toFixed(1)}%)` },
                ]}
              />
            </div>

            {/* Cluster legend */}
            <div className="glass-card rounded-xl px-5 py-4">
              <p className="text-[10px] uppercase tracking-widest text-neutral-600 font-semibold mb-3">
                Faixas de Cluster
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                {CLUSTER_RANGES.map(([min, max, c]) => {
                  const ci = CLUSTER_COLORS[c];
                  const rangeLabel = max === Infinity
                    ? `acima de ${formatPontos(min)}`
                    : `${formatPontos(min)} – ${formatPontos(max)}`;
                  return (
                    <div key={c} className="rounded-lg px-3 py-2 text-center border"
                      style={{ backgroundColor: ci.bg, borderColor: ci.border }}>
                      <p className="text-[10px] font-bold" style={{ color: ci.color }}>{ci.label}</p>
                      <p className="text-[9px] text-neutral-600 mt-0.5">{rangeLabel}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className="glass-card rounded-2xl p-10 text-center text-neutral-600 text-sm">
            Preencha os dados acima para ver os índices de cluster.
          </div>
        )}

        <footer className="text-center text-[11px] text-neutral-700 pb-6">
          FEJEPE — Federação das Empresas Juniores de Pernambuco
        </footer>
      </main>
    </div>
  );
}

function SectionTitle({ icon, title }: { icon: string; title: string }) {
  return (
    <div className="flex items-center gap-2 border-b border-white/5 pb-2">
      <span className="text-base">{icon}</span>
      <h2 className="text-xs font-bold font-heading uppercase tracking-wider text-neutral-300">{title}</h2>
    </div>
  );
}
