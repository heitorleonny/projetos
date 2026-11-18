import { useEffect, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { lerErro } from '../admin/adminService';
import { AvisoErro, botaoPrimario, botaoSecundario, inputClass, labelClass, selectClass } from '../admin/ui';
import ResultadoView from './ResultadoMetrica';
import { fetchPrevia, MESES, type Catalogo, type DefinicaoMetrica, type MetricaEntrada, type Visual } from './metricasService';
import { useSalvarMetrica } from './useMetricas';

interface Props {
    catalogo: Catalogo;
    inicial: MetricaEntrada;
    id?: number;
    fechar: () => void;
}

const VISUAIS: [Visual, string, string][] = [
    ['ranking', 'Ranking de EJs', 'Lista as EJs da maior para a menor (ou o contrário).'],
    ['valor', 'Valor da rede', 'Um número: soma ou média das EJs.'],
    ['serie', 'Série mensal', 'Evolução mês a mês da rede.'],
];
const OPERADORES = [['+', '+'], ['−', '-'], ['×', '*'], ['÷', '/'], ['(', '('], [')', ')']];

export default function ConstrutorMetrica({ catalogo, inicial, id, fechar }: Props) {
    const dialogo = useRef<HTMLDialogElement>(null);
    const formula = useRef<HTMLTextAreaElement>(null);
    const [dados, setDados] = useState<MetricaEntrada>(inicial);
    const salvar = useSalvarMetrica();
    const previa = useMutation({ mutationFn: fetchPrevia });
    const def = dados.definicao;

    // Sem close() na limpeza: ele dispararia `onClose` (e fecharia o construtor
    // na montagem dupla do modo estrito). Desmontar já remove o diálogo.
    useEffect(() => {
        const atual = dialogo.current;
        if (atual && !atual.open) atual.showModal();
    }, []);

    function alterarDef(parcial: Partial<DefinicaoMetrica>) {
        setDados(d => ({ ...d, definicao: { ...d.definicao, ...parcial } }));
    }

    function inserir(trecho: string) {
        const campo = formula.current;
        const texto = def.expressao;
        const inicio = campo?.selectionStart ?? texto.length;
        const fim = campo?.selectionEnd ?? texto.length;
        const antes = texto.slice(0, inicio);
        const separador = antes && !antes.endsWith(' ') ? ' ' : '';
        const novo = `${antes}${separador}${trecho} ${texto.slice(fim)}`;
        alterarDef({ expressao: novo.slice(0, 300) });
        requestAnimationFrame(() => {
            const pos = antes.length + separador.length + trecho.length + 1;
            campo?.focus();
            campo?.setSelectionRange(pos, pos);
        });
    }

    async function enviar(evento: React.FormEvent) {
        evento.preventDefault();
        try {
            await salvar.mutateAsync({ id, dados: { ...dados, descricao: dados.descricao?.trim() || null } });
            fechar();
        } catch { /* erro mostrado abaixo */ }
    }

    const erro = salvar.isError ? lerErro(salvar.error) : previa.isError ? lerErro(previa.error) : null;

    return (
        <dialog ref={dialogo} onClose={fechar} aria-labelledby="construtor-titulo"
            className="m-auto w-[calc(100%-1.5rem)] max-w-3xl rounded-2xl border border-neutral-700 bg-neutral-900 p-0 text-white shadow-2xl backdrop:bg-black/60">
            <form onSubmit={enviar} className="max-h-[calc(100dvh-2rem)] overflow-y-auto p-5 sm:p-6">
                <div className="mb-5 flex items-start justify-between gap-3">
                    <div>
                        <h2 id="construtor-titulo" className="font-heading text-lg font-semibold">{id === undefined ? 'Nova métrica' : 'Editar métrica'}</h2>
                        <p className="mt-1 text-sm text-neutral-400">Combine variáveis do catálogo. O portal calcula com os dados da sua federação em {catalogo.ano}.</p>
                    </div>
                    <button type="button" onClick={fechar} aria-label="Fechar" className="rounded-lg px-2 py-1 text-neutral-400 hover:bg-white/5 hover:text-white">✕</button>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                    <label className="block">
                        <span className={labelClass}>Nome</span>
                        <input required minLength={3} maxLength={80} className={inputClass} value={dados.nome}
                            onChange={e => setDados(d => ({ ...d, nome: e.target.value }))} placeholder="Ex.: Impacto comercial" />
                    </label>
                    <label className="block">
                        <span className={labelClass}>Descrição (opcional)</span>
                        <input maxLength={300} className={inputClass} value={dados.descricao ?? ''}
                            onChange={e => setDados(d => ({ ...d, descricao: e.target.value }))} placeholder="Para que serve esta métrica" />
                    </label>
                </div>

                <fieldset className="mt-4">
                    <legend className={labelClass}>Fórmula</legend>
                    <textarea ref={formula} required maxLength={300} rows={2} className={`${inputClass} font-mono`} value={def.expressao}
                        onChange={e => alterarDef({ expressao: e.target.value })} placeholder="faturamento * csat * projetos_vendidos"
                        aria-describedby="formula-ajuda" spellCheck={false} />
                    <p id="formula-ajuda" className="mt-1 text-xs text-neutral-500">Clique numa variável ou operador para inserir. Use números com vírgula ou ponto.</p>
                    <div className="mt-2 flex flex-wrap gap-1.5" role="group" aria-label="Operadores">
                        {OPERADORES.map(([rotulo, valor]) => (
                            <button key={valor} type="button" onClick={() => inserir(valor)} aria-label={`Inserir ${rotulo}`}
                                className="min-w-9 rounded-lg border border-white/10 bg-white/5 px-2.5 py-1 font-mono text-sm hover:bg-white/10">{rotulo}</button>
                        ))}
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5" role="group" aria-label="Variáveis do catálogo">
                        {catalogo.variaveis.map(v => (
                            <button key={v.nome} type="button" onClick={() => inserir(v.nome)} title={v.descricao}
                                className="rounded-full border border-primary-500/30 bg-primary-500/10 px-3 py-1 text-xs text-primary-200 hover:bg-primary-500/20">
                                {v.rotulo}
                            </button>
                        ))}
                    </div>
                </fieldset>

                <div className="mt-4 grid gap-4 sm:grid-cols-3">
                    <label className="block">
                        <span className={labelClass}>De</span>
                        <select className={`${selectClass} w-full`} value={def.mes_inicio}
                            onChange={e => {
                                const mes = Number(e.target.value);
                                alterarDef({ mes_inicio: mes, mes_fim: def.mes_fim !== null && def.mes_fim < mes ? mes : def.mes_fim });
                            }}>
                            {MESES.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
                        </select>
                    </label>
                    <label className="block">
                        <span className={labelClass}>Até</span>
                        <select className={`${selectClass} w-full`} value={def.mes_fim ?? ''}
                            onChange={e => alterarDef({ mes_fim: e.target.value === '' ? null : Number(e.target.value) })}>
                            <option value="">Último mês com dados</option>
                            {MESES.map((m, i) => i + 1 >= def.mes_inicio && <option key={m} value={i + 1}>{m}</option>)}
                        </select>
                    </label>
                    <label className="block">
                        <span className={labelClass}>Cluster oficial</span>
                        <select className={`${selectClass} w-full`} value={def.cluster ?? ''}
                            onChange={e => alterarDef({ cluster: e.target.value === '' ? null : Number(e.target.value) })}>
                            <option value="">Todos</option>
                            {[1, 2, 3, 4, 5].map(c => <option key={c} value={c}>Cluster {c}</option>)}
                        </select>
                    </label>
                </div>

                <fieldset className="mt-4">
                    <legend className={labelClass}>Visualização</legend>
                    <div className="grid gap-2 sm:grid-cols-3">
                        {VISUAIS.map(([valor, rotulo, ajuda]) => (
                            <label key={valor} className={`cursor-pointer rounded-xl border p-3 text-sm ${dados.visual === valor ? 'border-primary-500/60 bg-primary-500/10' : 'border-white/10 hover:bg-white/5'}`}>
                                <input type="radio" name="visual" value={valor} checked={dados.visual === valor} className="sr-only"
                                    onChange={() => setDados(d => ({ ...d, visual: valor }))} />
                                <span className="block font-medium">{rotulo}</span>
                                <span className="mt-0.5 block text-xs text-neutral-400">{ajuda}</span>
                            </label>
                        ))}
                    </div>
                </fieldset>

                <div className="mt-4 grid gap-4 sm:grid-cols-3">
                    {dados.visual === 'ranking' ? <>
                        <label className="block">
                            <span className={labelClass}>Ordem</span>
                            <select className={`${selectClass} w-full`} value={def.ordem} onChange={e => alterarDef({ ordem: e.target.value as 'desc' | 'asc' })}>
                                <option value="desc">Maiores primeiro</option>
                                <option value="asc">Menores primeiro</option>
                            </select>
                        </label>
                        <label className="block">
                            <span className={labelClass}>Quantas EJs</span>
                            <input type="number" min={1} max={50} className={inputClass} value={def.limite}
                                onChange={e => alterarDef({ limite: Math.min(50, Math.max(1, Number(e.target.value) || 1)) })} />
                        </label>
                    </> : (
                        <label className="block">
                            <span className={labelClass}>Agregar a rede por</span>
                            <select className={`${selectClass} w-full`} value={def.agregacao_rede} onChange={e => alterarDef({ agregacao_rede: e.target.value as 'soma' | 'media' })}>
                                <option value="soma">Soma</option>
                                <option value="media">Média</option>
                            </select>
                        </label>
                    )}
                    <label className="block">
                        <span className={labelClass}>Unidade</span>
                        <select className={`${selectClass} w-full`} value={def.unidade} onChange={e => alterarDef({ unidade: e.target.value as 'moeda' | 'numero' })}>
                            <option value="moeda">Reais (R$)</option>
                            <option value="numero">Número</option>
                        </select>
                    </label>
                </div>

                <label className="mt-4 flex items-center gap-2 text-sm text-neutral-300">
                    <input type="checkbox" checked={dados.no_painel} onChange={e => setDados(d => ({ ...d, no_painel: e.target.checked }))} />
                    Mostrar no painel
                </label>

                {erro && <div className="mt-4"><AvisoErro erro={erro} /></div>}

                {previa.data && !previa.isError && (
                    <section aria-label="Prévia" className="mt-5 rounded-xl border border-white/10 bg-white/[0.03] p-4">
                        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-neutral-400">Prévia com os dados atuais</p>
                        <ResultadoView resultado={previa.data} visual={dados.visual} />
                    </section>
                )}

                <div className="mt-6 flex flex-wrap justify-end gap-2">
                    <button type="button" className={botaoSecundario} onClick={fechar}>Cancelar</button>
                    <button type="button" className={botaoSecundario} disabled={!def.expressao.trim() || previa.isPending}
                        onClick={() => { salvar.reset(); previa.mutate(def); }}>
                        {previa.isPending ? 'Calculando…' : 'Ver prévia'}
                    </button>
                    <button type="submit" className={botaoPrimario} disabled={salvar.isPending}>
                        {salvar.isPending ? 'Salvando…' : 'Salvar métrica'}
                    </button>
                </div>
            </form>
        </dialog>
    );
}
