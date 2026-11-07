import { useMemo, useState } from 'react';
import { lerErro, type ErroApi, type Federacao, type FederacaoAtualizacao, type StatusFederacao } from './adminService';
import { useAtualizarFederacao } from './useAdmin';
import { AvisoErro, Cartao, Selo, botaoPrimario, botaoSecundario, inputClass, selectClass } from './ui';

const STATUS: Record<StatusFederacao, { rotulo: string; tom: 'verde' | 'amarelo' | 'cinza' }> = {
    ativa: { rotulo: 'Ativa', tom: 'verde' },
    piloto: { rotulo: 'Piloto', tom: 'amarelo' },
    inativa: { rotulo: 'Inativa', tom: 'cinza' },
};

const HEX = /^#[0-9A-Fa-f]{6}$/;

/**
 * Só o operador da plataforma chega aqui. Edita status e branding; id, slug
 * e UF não são editáveis (o slug é o que o deploy usa para achar o tenant).
 */
export default function FederacoesTab({ federacoes }: { federacoes: Federacao[] }) {
    const [busca, setBusca] = useState('');
    const [editando, setEditando] = useState<number | null>(null);

    const visiveis = useMemo(() => {
        const termo = busca.trim().toLowerCase();
        return federacoes.filter((f) => !termo || f.nome.toLowerCase().includes(termo) || f.slug.includes(termo) || f.uf.toLowerCase() === termo);
    }, [federacoes, busca]);

    const contagem = useMemo(() => {
        const c = { ativa: 0, piloto: 0, inativa: 0 };
        federacoes.forEach((f) => { c[f.status] += 1; });
        return c;
    }, [federacoes]);

    return (
        <Cartao
            titulo="Federações"
            descricao={`${federacoes.length} federações: ${contagem.ativa} ativas, ${contagem.piloto} em piloto, ${contagem.inativa} inativas. Federação inativa ou em piloto não mostra a marca na tela de login.`}
        >
            <input
                type="search"
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Buscar por nome, slug ou UF"
                className={`${inputClass} max-w-xs mb-4`}
                aria-label="Buscar federação"
            />
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="text-left text-xs uppercase tracking-wider text-neutral-500">
                            <th className="py-2 pr-4 font-medium">Federação</th>
                            <th className="py-2 pr-4 font-medium">UF</th>
                            <th className="py-2 pr-4 font-medium">Status</th>
                            <th className="py-2 pr-4 font-medium">Marca</th>
                            <th className="py-2 pr-4 font-medium" />
                        </tr>
                    </thead>
                    <tbody>
                        {visiveis.map((f) => editando === f.id ? (
                            <LinhaEdicao key={f.id} federacao={f} aoFechar={() => setEditando(null)} />
                        ) : (
                            <tr key={f.id} className="border-t border-white/5">
                                <td className="py-3 pr-4">
                                    <div className="text-white font-medium">{f.nome}</div>
                                    {f.slogan && <div className="text-xs text-neutral-400 italic max-w-[320px] truncate" title={f.slogan}>{f.slogan}</div>}
                                    <div className="text-xs text-neutral-500 font-mono">{f.slug} · id {f.id}</div>
                                </td>
                                <td className="py-3 pr-4 text-neutral-300">{f.uf}</td>
                                <td className="py-3 pr-4"><Selo tom={STATUS[f.status].tom}>{STATUS[f.status].rotulo}</Selo></td>
                                <td className="py-3 pr-4"><Marca federacao={f} /></td>
                                <td className="py-3 pr-4 text-right">
                                    <button type="button" onClick={() => setEditando(f.id)} className="text-primary-300 hover:text-white text-sm cursor-pointer">
                                        Editar
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </Cartao>
    );
}

function Marca({ federacao, cor, logo }: { federacao: Federacao; cor?: string; logo?: string }) {
    const corFinal = cor ?? federacao.cor_primaria;
    const logoFinal = logo ?? federacao.logo_url;
    return (
        <div className="flex items-center gap-2">
            <div
                className="h-8 w-8 rounded-lg flex items-center justify-center shrink-0 border border-white/10"
                style={{ backgroundColor: corFinal && HEX.test(corFinal) ? corFinal : 'rgba(255,255,255,0.05)' }}
            >
                {logoFinal ? (
                    <img src={logoFinal} alt="" className="h-5 w-5 object-contain" />
                ) : (
                    <span className="text-white text-xs font-bold">{federacao.nome.charAt(0)}</span>
                )}
            </div>
            <span className="text-xs text-neutral-500 font-mono">{corFinal ?? 'sem cor'}</span>
        </div>
    );
}

function LinhaEdicao({ federacao, aoFechar }: { federacao: Federacao; aoFechar: () => void }) {
    const atualizar = useAtualizarFederacao();
    const [nome, setNome] = useState(federacao.nome);
    const [status, setStatus] = useState<StatusFederacao>(federacao.status);
    const [cor, setCor] = useState(federacao.cor_primaria ?? '');
    const [logo, setLogo] = useState(federacao.logo_url ?? '');
    const [slogan, setSlogan] = useState(federacao.slogan ?? '');
    const [erro, setErro] = useState<ErroApi | null>(null);

    const corValida = cor === '' || HEX.test(cor);

    const salvar = () => {
        const dados: FederacaoAtualizacao = {};
        if (nome.trim() !== federacao.nome) dados.nome = nome.trim();
        if (status !== federacao.status) dados.status = status;
        if ((cor || null) !== federacao.cor_primaria) dados.cor_primaria = cor || null;
        if ((logo.trim() || null) !== federacao.logo_url) dados.logo_url = logo.trim() || null;
        if ((slogan.trim() || null) !== federacao.slogan) dados.slogan = slogan.trim() || null;
        if (Object.keys(dados).length === 0) {
            aoFechar();
            return;
        }
        setErro(null);
        atualizar.mutate({ id: federacao.id, dados }, { onSuccess: aoFechar, onError: (e) => setErro(lerErro(e)) });
    };

    return (
        <tr className="border-t border-white/5 bg-white/[0.03]">
            <td className="py-3 pr-4 align-top">
                <input value={nome} onChange={(e) => setNome(e.target.value)} className={inputClass} aria-label="Nome de exibição" />
                <input
                    value={slogan}
                    onChange={(e) => setSlogan(e.target.value)}
                    maxLength={200}
                    placeholder="Slogan (subtítulo do Dashboard)"
                    className={`${inputClass} mt-2`}
                    aria-label="Slogan"
                />
                <div className="text-xs text-neutral-500 font-mono mt-1">{federacao.slug} · id {federacao.id}</div>
            </td>
            <td className="py-3 pr-4 align-top text-neutral-300 pt-5">{federacao.uf}</td>
            <td className="py-3 pr-4 align-top">
                <select value={status} onChange={(e) => setStatus(e.target.value as StatusFederacao)} className={selectClass} aria-label="Status">
                    {(Object.keys(STATUS) as StatusFederacao[]).map((s) => <option key={s} value={s}>{STATUS[s].rotulo}</option>)}
                </select>
            </td>
            <td className="py-3 pr-4 align-top space-y-2 min-w-[220px]">
                <div className="flex items-center gap-2">
                    <input
                        type="color"
                        value={HEX.test(cor) ? cor : '#0D6EFD'}
                        onChange={(e) => setCor(e.target.value.toUpperCase())}
                        className="h-9 w-10 rounded bg-transparent border border-white/10 cursor-pointer"
                        aria-label="Escolher cor"
                    />
                    <input
                        value={cor}
                        onChange={(e) => setCor(e.target.value)}
                        placeholder="#RRGGBB"
                        className={`${inputClass} font-mono ${corValida ? '' : 'border-red-500/60'}`}
                        aria-label="Cor primária"
                    />
                </div>
                <input value={logo} onChange={(e) => setLogo(e.target.value)} placeholder="URL ou caminho do logo" className={inputClass} aria-label="Logo" />
                <Marca federacao={federacao} cor={cor || undefined} logo={logo || undefined} />
                <AvisoErro erro={erro} />
            </td>
            <td className="py-3 pr-4 align-top">
                <div className="flex flex-col gap-2">
                    <button type="button" onClick={salvar} disabled={!corValida || !nome.trim() || atualizar.isPending} className={`${botaoPrimario} py-2`}>
                        {atualizar.isPending ? 'Salvando…' : 'Salvar'}
                    </button>
                    <button type="button" onClick={aoFechar} className={`${botaoSecundario} py-2`}>Cancelar</button>
                </div>
            </td>
        </tr>
    );
}
