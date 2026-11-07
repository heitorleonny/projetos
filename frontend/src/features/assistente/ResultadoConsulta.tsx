import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { RespostaRede } from './assistenteService';
import GraficoConsulta from './GraficoConsulta';
import { graficoDaResposta, rotuloDoMes } from './visualizacao';

export type ModoVisualizacao = 'grafico' | 'tabela';

const fontes: Record<string, string> = {
    'rede_service.calcular_indicadores_rede': 'Dados do portal · Indicadores da rede',
    'rede_service.gerar_ranking': 'Dados do portal · Ranking',
    'empresa_service.listar_empresas': 'Dados do portal · EJs',
    'rede_service.calcular_sde_cenarios': 'Dados do portal · Cenários de SDE',
    'rede_service.calcular_ritmo_mensal': 'Dados do portal · Ritmo mensal',
    glossario: 'Glossário do portal · regras nacionais do MEJ',
};

function formatar(valor: number | null, unidade: 'moeda' | 'numero') {
    if (valor === null) return 'Sem coleta';
    return valor.toLocaleString('pt-BR', unidade === 'moeda' ? { style: 'currency', currency: 'BRL' } : { maximumFractionDigits: 2 });
}

function AlternarVisualizacao({ modo, alterar }: { modo: ModoVisualizacao; alterar: (modo: ModoVisualizacao) => void }) {
    const opcoes: [ModoVisualizacao, string][] = [['grafico', 'Gráfico'], ['tabela', 'Tabela']];
    return <div role="group" aria-label="Forma de exibição" className="inline-flex rounded-lg border border-neutral-700 p-0.5 text-xs">
        {opcoes.map(([valor, rotulo]) => <button key={valor} type="button" aria-pressed={modo === valor} onClick={() => alterar(valor)}
            className={`rounded-md px-3 py-1.5 ${modo === valor ? 'bg-primary-500/20 text-primary-100' : 'text-neutral-300 hover:bg-neutral-800'}`}>{rotulo}</button>)}
    </div>;
}

export default function ResultadoConsulta({ resposta, fechar, escolher, enviando, modoInicial = 'grafico' }: { resposta: RespostaRede; fechar: () => void; escolher: (pergunta: string) => void; enviando: boolean; modoInicial?: ModoVisualizacao }) {
    const [modo, setModo] = useState<ModoVisualizacao>(modoInicial);
    const grafico = graficoDaResposta(resposta);
    const exibirGrafico = grafico !== null && modo === 'grafico';
    // Com série mensal, a alternância vale para a série; as linhas ficam sempre visíveis.
    const serie = resposta.serie?.length ? resposta.serie : null;
    const [busca, setBusca] = useState('');
    const [expandido, setExpandido] = useState(false);
    const empresas = resposta.linhas.some(linha => linha.id_ej !== null);
    const filtradas = resposta.linhas.filter(linha => linha.nome.toLocaleLowerCase('pt-BR').includes(busca.toLocaleLowerCase('pt-BR')));
    const visiveis = expandido ? filtradas : filtradas.slice(0, 8);
    const mes = resposta.mes ?? resposta.contexto?.mes;
    const ano = resposta.ano ?? resposta.contexto?.ano;
    const periodo = mes && ano
        ? new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(Date.UTC(ano, mes - 1)))
        : ano ? String(ano) : null;

    return <div className="space-y-4">
        <p className="whitespace-pre-line text-sm leading-relaxed text-neutral-100">{resposta.resposta}</p>
        {resposta.esclarecimento && <div className="flex flex-wrap gap-2" role="group" aria-label="Escolha como consultar">
            {resposta.esclarecimento.opcoes.map(opcao => <button key={opcao.pergunta} type="button" disabled={enviando} onClick={() => escolher(opcao.pergunta)} className="rounded-lg border border-primary-400/40 bg-primary-500/10 px-3 py-2 text-sm text-primary-200 hover:bg-primary-500/20 disabled:opacity-40">{opcao.rotulo}</button>)}
        </div>}
        {resposta.contexto && <div aria-label="Filtros desta consulta" className="flex flex-wrap gap-2 text-[11px] text-neutral-300">
            <span className="rounded-full border border-neutral-700 px-2 py-1">Sua federação</span>
            {periodo && <span className="rounded-full border border-neutral-700 px-2 py-1">{periodo}</span>}
            {resposta.contexto.cluster && <span className="rounded-full border border-neutral-700 px-2 py-1">Cluster oficial {resposta.contexto.cluster}</span>}
            {resposta.contexto.busca && <span className="rounded-full border border-neutral-700 px-2 py-1">Nome: {resposta.contexto.busca}</span>}
            {resposta.contexto.ferramenta === 'ranking' && resposta.contexto.criterio && <span className="rounded-full border border-neutral-700 px-2 py-1">Critério: {resposta.contexto.criterio}</span>}
            {resposta.contexto.ferramenta === 'ranking' && resposta.contexto.ordem === 'asc' && <span className="rounded-full border border-neutral-700 px-2 py-1">Menores valores</span>}
        </div>}
        {grafico && <AlternarVisualizacao modo={modo} alterar={setModo} />}
        {exibirGrafico && <GraficoConsulta grafico={grafico} />}
        {serie && !exibirGrafico && <table className="w-full overflow-hidden rounded-xl border border-neutral-700/80 text-sm">
            <caption className="sr-only">Faturamento por mês</caption>
            <thead className="bg-neutral-800/70 text-xs text-neutral-400"><tr><th scope="col" className="px-3 py-2 text-left font-medium">Mês</th><th scope="col" className="px-3 py-2 text-right font-medium">Faturamento do mês</th></tr></thead>
            <tbody>{serie.map(ponto => <tr key={ponto.mes} className="border-t border-neutral-700/50"><td className="px-3 py-2">{rotuloDoMes(ponto.mes)}</td><td className="px-3 py-2 text-right tabular-nums text-neutral-200">{formatar(ponto.valor, 'moeda')}</td></tr>)}</tbody>
        </table>}
        {(serie || !exibirGrafico) && resposta.linhas.length > 0 && (empresas ? <div className="overflow-hidden rounded-xl border border-neutral-700/80">
            <div className="flex items-center justify-between gap-3 bg-neutral-800/70 px-3 py-2.5">
                <span className="text-xs text-neutral-300">{resposta.linhas.length} EJs na resposta{resposta.total > resposta.linhas.length ? ` · ${resposta.total} no total` : ''}</span>
            </div>
            {resposta.linhas.length > 8 && <div className="px-3 pt-3">
                <input aria-label="Buscar entre as EJs desta resposta" value={busca} onChange={evento => setBusca(evento.target.value)} placeholder="Buscar nesta resposta…" className="w-full rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-primary-300" />
            </div>}
            <table className="w-full text-sm">
                <caption className="sr-only">Empresas juniores e valores consultados</caption>
                <thead className="text-xs text-neutral-400"><tr><th scope="col" className="px-3 py-2 text-left font-medium">Empresa júnior</th><th scope="col" className="px-3 py-2 text-right font-medium">{resposta.unidade === 'moeda' ? 'Faturamento' : 'Valor'}</th></tr></thead>
                <tbody>{visiveis.map((linha, indice) => <tr key={`${linha.id_ej}-${indice}`} className="border-t border-neutral-700/50">
                    <td className="px-3 py-3">{linha.id_ej !== null ? <Link className="text-primary-200 underline-offset-4 hover:underline" to={`/empresas/${linha.id_ej}`} onClick={fechar}>{linha.nome}</Link> : linha.nome}</td>
                    <td className="px-3 py-3 text-right tabular-nums text-neutral-200">{formatar(linha.valor, linha.unidade ?? resposta.unidade)}</td>
                </tr>)}</tbody>
            </table>
            {filtradas.length === 0 && <p className="p-4 text-sm text-neutral-400">Nenhuma EJ com esse nome nesta resposta.</p>}
            {filtradas.length > 8 && <button type="button" onClick={() => setExpandido(!expandido)} aria-expanded={expandido} className="w-full border-t border-neutral-700 px-3 py-3 text-sm text-primary-200 hover:bg-neutral-800">{expandido ? 'Mostrar menos' : `Ver todas as ${filtradas.length} EJs`}</button>}
        </div> : <dl className="grid grid-cols-1 gap-2 min-[400px]:grid-cols-2">
            {resposta.linhas.map((linha, indice) => <div key={indice} className="rounded-xl border border-neutral-700/70 bg-neutral-800/50 p-3"><dt className="text-xs leading-relaxed text-neutral-400">{linha.nome}</dt><dd className="mt-1 text-lg font-semibold tabular-nums text-neutral-100">{formatar(linha.valor, linha.unidade ?? resposta.unidade)}</dd></div>)}
        </dl>)}
        {resposta.fonte && <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-neutral-700/70 pt-3 text-[11px] text-neutral-400">
            <span>Fonte: {fontes[resposta.fonte] ?? 'Dados do portal'}</span>{periodo && <span className="rounded-full bg-neutral-800 px-2 py-1">{periodo}</span>}
        </div>}
    </div>;
}
