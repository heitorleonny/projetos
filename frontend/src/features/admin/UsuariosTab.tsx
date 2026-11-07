import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { lerErro, type ErroApi, type Federacao, type Papel, type Sessao, type Usuario } from './adminService';
import { useAtualizarUsuario, useConvidarUsuario, useUsuariosAdmin } from './useAdmin';
import {
    AvisoErro, AvisoOk, Cartao, Carregando, Selo, botaoPrimario, botaoSecundario,
    inputClass, labelClass, selectClass,
} from './ui';
import { dataHora, haQuantoTempo } from './formatacao';

const ROTULO_PAPEL: Record<Papel, string> = {
    membro: 'Membro',
    admin: 'Admin',
    plataforma: 'Operador da plataforma',
};

export default function UsuariosTab({ sessao, federacoes, federacaoInicial }: { sessao: Sessao; federacoes: Federacao[]; federacaoInicial?: number }) {
    const usuarios = useUsuariosAdmin();
    const atualizar = useAtualizarUsuario();
    const [convidando, setConvidando] = useState(false);
    const [busca, setBusca] = useState('');
    const [filtroFederacao, setFiltroFederacao] = useState<number | ''>(federacaoInicial ?? '');
    const [erro, setErro] = useState<ErroApi | null>(null);
    // Fixado na montagem: o resumo não precisa andar com o relógio.
    const [agora] = useState(() => Date.now());

    const papeisPermitidos: Papel[] = sessao.eh_plataforma ? ['membro', 'admin', 'plataforma'] : ['membro', 'admin'];

    const visiveis = useMemo(() => {
        const termo = busca.trim().toLowerCase();
        return (usuarios.data ?? []).filter((u) =>
            (!termo || u.nome.toLowerCase().includes(termo) || u.email.toLowerCase().includes(termo))
            && (filtroFederacao === '' || u.federacao_id === filtroFederacao));
    }, [usuarios.data, busca, filtroFederacao]);

    const resumo = useMemo(() => {
        const lista = usuarios.data ?? [];
        const trintaDias = agora - 30 * 86_400_000;
        return {
            total: lista.length,
            ativos: lista.filter((u) => u.ativo).length,
            recentes: lista.filter((u) => u.ultimo_login && new Date(u.ultimo_login).getTime() >= trintaDias).length,
            pendentes: lista.filter((u) => u.vinculado && !u.ultimo_login).length,
        };
    }, [usuarios.data, agora]);

    const salvar = (usuario: Usuario, dados: Partial<Pick<Usuario, 'papel' | 'ativo' | 'federacao_id'>>) => {
        setErro(null);
        atualizar.mutate({ id: usuario.id, dados }, { onError: (e) => setErro(lerErro(e)) });
    };

    return (
        <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                {[
                    { rotulo: 'Usuários', valor: resumo.total },
                    { rotulo: 'Ativos', valor: resumo.ativos },
                    { rotulo: 'Entraram nos últimos 30 dias', valor: resumo.recentes },
                    { rotulo: 'Convites não aceitos', valor: resumo.pendentes },
                ].map((i) => (
                    <div key={i.rotulo} className="glass-card rounded-xl px-4 py-3">
                        <div className="text-[11px] uppercase tracking-wider text-neutral-500">{i.rotulo}</div>
                        <div className="text-2xl font-heading font-semibold text-white tabular-nums">{i.valor}</div>
                    </div>
                ))}
            </div>

            <Cartao
                titulo="Usuários"
                descricao={sessao.eh_plataforma
                    ? 'Todas as federações. Mudanças de papel valem a partir do próximo login da pessoa.'
                    : 'Usuários da sua federação. Mudanças de papel valem a partir do próximo login da pessoa.'}
                acao={
                    <button type="button" onClick={() => setConvidando((v) => !v)} className={convidando ? botaoSecundario : botaoPrimario}>
                        {convidando ? 'Fechar' : 'Convidar usuário'}
                    </button>
                }
            >
                {convidando && (
                    <FormularioConvite
                        sessao={sessao}
                        federacoes={federacoes}
                        papeis={papeisPermitidos}
                        aoConcluir={() => setConvidando(false)}
                    />
                )}

                <div className="flex flex-wrap gap-3 mb-4">
                    <input
                        type="search"
                        value={busca}
                        onChange={(e) => setBusca(e.target.value)}
                        placeholder="Buscar por nome ou e-mail"
                        className={`${inputClass} max-w-xs`}
                        aria-label="Buscar usuário"
                    />
                    {sessao.eh_plataforma && (
                        <select
                            value={filtroFederacao}
                            onChange={(e) => setFiltroFederacao(e.target.value ? Number(e.target.value) : '')}
                            className={selectClass}
                            aria-label="Filtrar por federação"
                        >
                            <option value="">Todas as federações</option>
                            {federacoes.map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}
                        </select>
                    )}
                </div>

                <div className="mb-4"><AvisoErro erro={erro} /></div>

                {usuarios.isLoading ? <Carregando /> : usuarios.isError ? (
                    <AvisoErro erro={lerErro(usuarios.error)} />
                ) : visiveis.length === 0 ? (
                    <p className="text-sm text-neutral-400">Nenhum usuário encontrado.</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-left text-xs uppercase tracking-wider text-neutral-500">
                                    <th className="py-2 pr-4 font-medium">Pessoa</th>
                                    {sessao.eh_plataforma && <th className="py-2 pr-4 font-medium">Federação</th>}
                                    <th className="py-2 pr-4 font-medium">Papel</th>
                                    <th className="py-2 pr-4 font-medium">Último acesso</th>
                                    <th className="py-2 pr-4 font-medium">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {visiveis.map((u) => {
                                    const souEu = u.id === sessao.usuario_id;
                                    const bloqueado = souEu || atualizar.isPending;
                                    return (
                                        <tr key={u.id} className={`border-t border-white/5 ${u.ativo ? '' : 'opacity-60'}`}>
                                            <td className="py-3 pr-4">
                                                <div className="text-white font-medium">
                                                    {u.nome}
                                                    {souEu && <span className="ml-2 text-xs text-primary-300">(você)</span>}
                                                    {u.conta_principal && <span className="ml-2"><Selo tom="azul" titulo="Conta responsável pela federação">principal</Selo></span>}
                                                </div>
                                                <div className="text-xs text-neutral-400">{u.email}</div>
                                            </td>
                                            {sessao.eh_plataforma && (
                                                <td className="py-3 pr-4">
                                                    <select
                                                        value={u.federacao_id}
                                                        disabled={bloqueado}
                                                        onChange={(e) => salvar(u, { federacao_id: Number(e.target.value) })}
                                                        className={`${selectClass} max-w-[180px]`}
                                                        aria-label={`Federação de ${u.nome}`}
                                                    >
                                                        {federacoes.map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}
                                                    </select>
                                                </td>
                                            )}
                                            <td className="py-3 pr-4">
                                                {papeisPermitidos.includes(u.papel) ? (
                                                    <select
                                                        value={u.papel}
                                                        disabled={bloqueado}
                                                        onChange={(e) => salvar(u, { papel: e.target.value as Papel })}
                                                        className={selectClass}
                                                        aria-label={`Papel de ${u.nome}`}
                                                    >
                                                        {papeisPermitidos.map((p) => <option key={p} value={p}>{ROTULO_PAPEL[p]}</option>)}
                                                    </select>
                                                ) : (
                                                    <span className="text-neutral-300">{ROTULO_PAPEL[u.papel]}</span>
                                                )}
                                            </td>
                                            <td className="py-3 pr-4"><UltimoAcesso usuario={u} /></td>
                                            <td className="py-3 pr-4">
                                                <button
                                                    type="button"
                                                    disabled={bloqueado}
                                                    onClick={() => salvar(u, { ativo: !u.ativo })}
                                                    title={souEu ? 'Você não pode desativar a própria conta' : u.ativo ? 'Desativar acesso' : 'Reativar acesso'}
                                                    className="cursor-pointer disabled:cursor-not-allowed"
                                                >
                                                    <Selo tom={u.ativo ? 'verde' : 'cinza'}>{u.ativo ? 'Ativo' : 'Inativo'}</Selo>
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </Cartao>
        </>
    );
}

function UltimoAcesso({ usuario }: { usuario: Usuario }) {
    if (!usuario.vinculado) return <Selo tom="cinza" titulo="Cadastro sem conta no portal">Sem conta</Selo>;
    if (!usuario.ultimo_login) {
        return <Selo tom="amarelo" titulo={`Convidado em ${dataHora(usuario.criado_em)}`}>Nunca entrou</Selo>;
    }
    return (
        <span className="text-neutral-300 whitespace-nowrap" title={dataHora(usuario.ultimo_login)}>
            {haQuantoTempo(usuario.ultimo_login)}
            <span className="block text-xs text-neutral-500">{dataHora(usuario.ultimo_login)}</span>
        </span>
    );
}

function FormularioConvite({ sessao, federacoes, papeis, aoConcluir }: {
    sessao: Sessao;
    federacoes: Federacao[];
    papeis: Papel[];
    aoConcluir: () => void;
}) {
    const convidar = useConvidarUsuario();
    const [nome, setNome] = useState('');
    const [email, setEmail] = useState('');
    const [papel, setPapel] = useState<Papel>('membro');
    const [federacaoId, setFederacaoId] = useState<number | ''>(sessao.federacao_id ?? '');
    const [erro, setErro] = useState<ErroApi | null>(null);
    const [enviadoPara, setEnviadoPara] = useState<string | null>(null);

    const enviar = (e: FormEvent) => {
        e.preventDefault();
        setErro(null);
        convidar.mutate(
            {
                nome: nome.trim(),
                email: email.trim(),
                papel,
                federacao_id: sessao.eh_plataforma && federacaoId !== '' ? federacaoId : undefined,
            },
            {
                onSuccess: (u) => {
                    setEnviadoPara(u.convite_url || 'Link indisponível');
                    setNome('');
                    setEmail('');
                    setPapel('membro');
                },
                onError: (err) => setErro(lerErro(err)),
            },
        );
    };

    return (
        <form onSubmit={enviar} className="rounded-xl border border-white/10 bg-white/[0.02] p-4 mb-6 space-y-4">
            <p className="text-sm text-neutral-300">
                Copie o link gerado e compartilhe com a pessoa por um canal privado. O link expira em 24 horas e só pode ser usado uma vez.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                    <label htmlFor="conv-nome" className={labelClass}>Nome</label>
                    <input id="conv-nome" value={nome} onChange={(e) => setNome(e.target.value)} required maxLength={120} className={inputClass} />
                </div>
                <div>
                    <label htmlFor="conv-email" className={labelClass}>E-mail</label>
                    <input id="conv-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className={inputClass} />
                </div>
                <div>
                    <label htmlFor="conv-papel" className={labelClass}>Papel</label>
                    <select id="conv-papel" value={papel} onChange={(e) => setPapel(e.target.value as Papel)} className={`${selectClass} w-full`}>
                        {papeis.map((p) => <option key={p} value={p}>{ROTULO_PAPEL[p]}</option>)}
                    </select>
                </div>
                {sessao.eh_plataforma && (
                    <div>
                        <label htmlFor="conv-fed" className={labelClass}>Federação</label>
                        <select
                            id="conv-fed"
                            value={federacaoId}
                            onChange={(e) => setFederacaoId(e.target.value ? Number(e.target.value) : '')}
                            required
                            className={`${selectClass} w-full`}
                        >
                            <option value="">Escolha…</option>
                            {federacoes.map((f) => <option key={f.id} value={f.id}>{f.nome}</option>)}
                        </select>
                    </div>
                )}
            </div>
            <AvisoErro erro={erro} />
            {enviadoPara && <AvisoOk>Link de convite: <span className="break-all select-all">{enviadoPara}</span></AvisoOk>}
            <div className="flex gap-3">
                <button type="submit" disabled={convidar.isPending} className={botaoPrimario}>
                    {convidar.isPending ? 'Gerando…' : 'Gerar convite'}
                </button>
                <button type="button" onClick={aoConcluir} className={botaoSecundario}>Cancelar</button>
            </div>
        </form>
    );
}
