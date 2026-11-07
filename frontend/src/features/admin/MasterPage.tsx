import { useState, type FormEvent } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../auth/useAuth';
import { lerErro, type Sessao } from './adminService';
import { useFederacoesAdmin, useSessaoAdmin } from './useAdmin';
import { fetchPlanosMaster, fetchResumoMaster, salvarPlano, vincularPlano, type Plano, type PlanoDados, type FederacaoMaster } from './masterService';
import { AvisoErro, AvisoOk, Carregando, Cartao, inputClass, selectClass, botaoPrimario, botaoSecundario } from './ui';
import FederacoesTab from './FederacoesTab';
import UsuariosTab from './UsuariosTab';
import ImportacaoTab from './ImportacaoTab';

const abas = [['visao', 'Visão da plataforma'], ['planos', 'Planos'], ['federacoes', 'Federações'], ['usuarios', 'Usuários'], ['importacao', 'Importações']];
const moeda = (valor: number | null) => valor === null ? 'A definir' : valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
export default function MasterPage() {
    const sessao = useSessaoAdmin();
    if (sessao.isLoading) return <Carregando />;
    if (sessao.isError) return <AvisoErro erro={lerErro(sessao.error)} />;
    if (!sessao.data?.eh_plataforma) return <Navigate to="/dashboard" replace />;
    return <PainelMaster sessao={sessao.data} />;
}
function PainelMaster({ sessao }: { sessao: Sessao }) {
    const { user } = useAuth();
    const qc = useQueryClient();
    const [params, setParams] = useSearchParams();
    const [busca, setBusca] = useState('');
    const [status, setStatus] = useState('');
    const resumo = useQuery({ queryKey: ['master', user?.id, 'resumo'], queryFn: fetchResumoMaster });
    const planos = useQuery({ queryKey: ['master', user?.id, 'planos'], queryFn: fetchPlanosMaster });
    const federacoes = useFederacoesAdmin();
    const aba = abas.some(([id]) => id === params.get('aba')) ? params.get('aba') : 'visao';
    const lista = resumo.data ?? [];
    const visiveis = lista.filter(f => (!status || f.status === status) && `${f.nome} ${f.uf}`.toLowerCase().includes(busca.toLowerCase().trim()));
    const erro = resumo.error || planos.error || federacoes.error;
    return <div>
        <div className="mb-6"><p className="text-xs uppercase tracking-widest text-primary-300">Portal das Federações</p><h1 className="text-2xl font-semibold text-white mt-2">Administração master</h1><p className="text-sm text-neutral-400 mt-2">Visão de todas as federações, seus acessos e planos.</p></div>
        <nav aria-label="Administração master" className="flex flex-wrap gap-2 mb-6">{abas.map(([id, titulo]) => <button type="button" key={id} aria-current={aba === id ? 'page' : undefined} className={aba === id ? botaoPrimario : botaoSecundario} onClick={() => setParams({ aba: id })}>{titulo}</button>)}</nav>
        {erro ? <AvisoErro erro={lerErro(erro)} /> : resumo.isLoading || planos.isLoading || federacoes.isLoading ? <Carregando /> : <>
            {aba === 'visao' && <>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">{[[lista.length, 'Federações cadastradas'], [lista.filter(f => f.status === 'ativa').length, 'Federações ativas'], [lista.reduce((n, f) => n + f.usuarios_total, 0), 'Usuários cadastrados'], [lista.reduce((n, f) => n + f.usuarios_ativos, 0), 'Usuários ativos']].map(([valor, rotulo]) => <div key={rotulo} className="glass-card rounded-xl p-4"><p className="text-xs text-neutral-400">{rotulo}</p><p className="text-3xl text-white font-semibold mt-2">{valor}</p></div>)}</div>
                <Cartao titulo="Federações e acessos" descricao="Totais de cadastros, incluindo usuários inativos. Trocar o plano não gera cobrança.">
                    <div className="flex flex-wrap gap-3 mb-5"><input type="search" aria-label="Buscar federação" placeholder="Buscar federação ou UF" value={busca} onChange={e => setBusca(e.target.value)} className={`${inputClass} max-w-sm`} /><select aria-label="Filtrar status" className={selectClass} value={status} onChange={e => setStatus(e.target.value)}><option value="">Todos os status</option><option value="ativa">Ativa</option><option value="piloto">Piloto</option><option value="inativa">Inativa</option></select><button type="button" className={botaoSecundario} onClick={() => void qc.invalidateQueries({ queryKey: ['master'] })}>Atualizar</button></div>
                    <div className="overflow-x-auto"><table className="w-full text-sm text-left"><thead className="text-neutral-400"><tr>{['Federação', 'Status', 'Usuários', 'Administradores ativos', 'Plano', 'Ações'].map(t => <th key={t} className="p-3">{t}</th>)}</tr></thead><tbody>{visiveis.map(f => <tr key={f.id} className="border-t border-white/10"><td className="p-3 text-white font-medium">{f.nome}<span className="block text-xs text-neutral-500">{f.uf}</span></td><td className="p-3 text-neutral-300 capitalize">{f.status}</td><td className="p-3 text-white">{f.usuarios_total} no total<span className="block text-xs text-neutral-400">{f.usuarios_ativos} ativos · {f.usuarios_total - f.usuarios_ativos} inativos</span></td><td className="p-3 text-neutral-300">{f.administradores}</td><td className="p-3"><Vinculo key={`${f.id}-${f.plano_id}`} federacao={f} planos={planos.data ?? []} /></td><td className="p-3"><button type="button" className="text-primary-300 hover:text-white" onClick={() => setParams({ aba: 'usuarios', federacao: String(f.id) })}>Ver usuários</button></td></tr>)}</tbody></table></div>
                    {!visiveis.length && <p className="text-neutral-400 py-5">Nenhuma federação encontrada.</p>}
                </Cartao>
            </>}
            {aba === 'planos' && <Planos planos={planos.data ?? []} />}
            {aba === 'federacoes' && <FederacoesTab federacoes={federacoes.data ?? []} />}
            {aba === 'usuarios' && <UsuariosTab key={params.get('federacao')} federacaoInicial={Number(params.get('federacao')) || undefined} sessao={sessao} federacoes={federacoes.data ?? []} />}
            {aba === 'importacao' && <ImportacaoTab sessao={sessao} federacoes={federacoes.data ?? []} />}
        </>}
    </div>;
}
function Vinculo({ federacao, planos }: { federacao: FederacaoMaster; planos: Plano[] }) {
    const qc = useQueryClient();
    const [id, setId] = useState(String(federacao.plano_id ?? ''));
    const salvar = useMutation({ mutationFn: () => vincularPlano(federacao.id, id ? Number(id) : null), onSuccess: () => qc.invalidateQueries({ queryKey: ['master'] }) });
    return <div className="min-w-48"><select aria-label={`Plano de ${federacao.nome}`} className={`${selectClass} w-full`} disabled={salvar.isPending} value={id} onChange={e => { setId(e.target.value); salvar.reset(); }}><option value="">Sem plano definido</option>{planos.map(p => <option key={p.id} value={p.id}>{p.nome}</option>)}</select>{id !== String(federacao.plano_id ?? '') && <button type="button" className={`${botaoPrimario} mt-2`} disabled={salvar.isPending} onClick={() => salvar.mutate()}>{salvar.isPending ? 'Salvando…' : 'Salvar plano'}</button>}{salvar.isError && <AvisoErro erro={lerErro(salvar.error)} />}{salvar.isSuccess && <p role="status" className="text-emerald-300 text-xs mt-1">Plano atualizado.</p>}</div>;
}
function Planos({ planos }: { planos: Plano[] }) {
    const [edicao, setEdicao] = useState<Plano | null | undefined>(undefined);
    const [sucesso, setSucesso] = useState(false);
    return <Cartao titulo="Catálogo de planos" descricao="Os valores iniciais são provisórios. O preço é cadastral e não gera cobrança. O limite de usuários é informativo." acao={<button type="button" className={botaoPrimario} onClick={() => { setEdicao(null); setSucesso(false); }}>Criar plano</button>}>
        {sucesso && <AvisoOk>Plano salvo.</AvisoOk>}{edicao !== undefined && <FormularioPlano key={edicao?.id ?? 'novo'} plano={edicao} fechar={() => setEdicao(undefined)} concluido={() => { setEdicao(undefined); setSucesso(true); }} />}
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4 mt-4">{planos.map(p => <div className="border border-white/10 rounded-xl p-5" key={p.id}><h3 className="text-white font-semibold">{p.nome}</h3><p className="text-2xl text-white mt-3">{moeda(p.preco_mensal)}<span className="text-sm text-neutral-400"> / mês</span></p><p className="text-sm text-neutral-400 mt-3">Usuários: {p.limite_usuarios ?? 'Sem limite definido'}</p><button type="button" className={`${botaoSecundario} mt-4`} onClick={() => { setEdicao(p); setSucesso(false); }}>Editar {p.nome}</button></div>)}</div>
    </Cartao>;
}
function FormularioPlano({ plano, fechar, concluido }: { plano: Plano | null; fechar: () => void; concluido: () => void }) {
    const qc = useQueryClient();
    const [nome, setNome] = useState(plano?.nome ?? '');
    const [usuarios, setUsuarios] = useState(String(plano?.limite_usuarios ?? ''));
    const [preco, setPreco] = useState(String(plano?.preco_mensal ?? ''));
    const gravar = useMutation({ mutationFn: (dados: PlanoDados) => salvarPlano(plano?.id ?? null, dados), onSuccess: async () => { await qc.invalidateQueries({ queryKey: ['master'] }); concluido(); } });
    const enviar = (e: FormEvent) => { e.preventDefault(); gravar.mutate({ nome: nome.trim(), limite_usuarios: usuarios === '' ? null : Number(usuarios), limite_creditos_ia_mes: plano?.limite_creditos_ia_mes ?? null, preco_mensal: preco === '' ? null : Number(preco) }); };
    const campos = [{ valor: usuarios, alterar: setUsuarios, rotulo: 'Limite de usuários (opcional)', passo: '1' }, { valor: preco, alterar: setPreco, rotulo: 'Preço mensal em R$ (opcional)', passo: '0.01' }];
    return <form onSubmit={enviar} className="border border-primary-500/30 rounded-xl p-5 mt-4"><p className="text-white font-semibold mb-4">{plano ? `Editar ${plano.nome}` : 'Novo plano'}</p><div className="grid sm:grid-cols-2 gap-4"><label className="text-sm text-neutral-300">Nome<input required maxLength={120} value={nome} onChange={e => setNome(e.target.value)} className={`${inputClass} mt-1`} /></label>{campos.map(c => <label key={c.rotulo} className="text-sm text-neutral-300">{c.rotulo}<input type="number" min="0" max="1000000" step={c.passo} value={c.valor} onChange={e => c.alterar(e.target.value)} className={`${inputClass} mt-1`} /></label>)}</div>{plano && <p className="text-xs text-amber-300 mt-3">A edição altera o catálogo para todas as federações vinculadas a este plano.</p>}{gravar.isError && <AvisoErro erro={lerErro(gravar.error)} />}<div className="flex gap-3 mt-4"><button type="submit" disabled={!nome.trim() || gravar.isPending} className={botaoPrimario}>{gravar.isPending ? 'Salvando…' : 'Salvar plano'}</button><button type="button" disabled={gravar.isPending} className={botaoSecundario} onClick={fechar}>Cancelar</button></div></form>;
}
