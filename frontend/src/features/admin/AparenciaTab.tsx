import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '../../services/api';
import type { FederacaoBranding } from '../../services/brandingService';
import { useFederacaoBranding } from '../../branding/useFederacaoBranding';
import { corDeTexto, normalizarHex } from '../../branding/tema';
import { lerErro } from './adminService';
import { AvisoErro, AvisoOk, botaoPrimario, botaoSecundario, Cartao } from './ui';
import FormularioLogo from './FormularioLogo';
import type { ErroApi } from './adminService';

type Paleta = Pick<FederacaoBranding, 'cor_primaria' | 'cor_secundaria' | 'cor_acento'>;
const CAMPOS = [
    { chave: 'cor_primaria', nome: 'Principal', descricao: 'Botões, links e seleção.', padrao: '#0D6EFD' },
    { chave: 'cor_secundaria', nome: 'Secundária', descricao: 'Identidade de apoio e prévia.', padrao: '#1E293B' },
    { chave: 'cor_acento', nome: 'Destaque', descricao: 'Detalhes e marcações visuais.', padrao: '#14B8A6' },
] as const;

export default function AparenciaTab() {
    const { branding } = useFederacaoBranding();
    return <div className="space-y-6">
        <FormularioLogo key={`logo:${branding.slug}`} />
        <FormularioPaleta key={branding.slug} />
    </div>;
}

export function FormularioPaleta() {
    const { branding, nome, atualizarBranding } = useFederacaoBranding();
    const qc = useQueryClient();
    const [cores, setCores] = useState<Paleta>({ cor_primaria: branding.cor_primaria, cor_secundaria: branding.cor_secundaria, cor_acento: branding.cor_acento });
    const [salvando, setSalvando] = useState(false);
    const [erro, setErro] = useState<ErroApi | null>(null);
    const [sucesso, setSucesso] = useState(false);
    const alterado = CAMPOS.some(c => normalizarHex(cores[c.chave]) !== normalizarHex(branding[c.chave]));
    const invalido = CAMPOS.some(c => cores[c.chave] !== null && !normalizarHex(cores[c.chave]));

    function mudar(chave: keyof Paleta, valor: string | null) {
        setCores(atuais => ({ ...atuais, [chave]: valor })); setSucesso(false); setErro(null);
    }
    async function salvar() {
        if (salvando || invalido || !alterado) return;
        setSalvando(true); setErro(null); setSucesso(false);
        try {
            const normalizadas = Object.fromEntries(CAMPOS.map(c => [c.chave, normalizarHex(cores[c.chave])]));
            const { data } = await api.put<FederacaoBranding>('/federacao/minha/paleta', normalizadas);
            atualizarBranding(data, branding.slug);
            setCores({ cor_primaria: data.cor_primaria, cor_secundaria: data.cor_secundaria, cor_acento: data.cor_acento });
            void qc.invalidateQueries({ queryKey: ['admin', 'federacoes'] });
            setSucesso(true);
        } catch (e) { setErro(lerErro(e)); }
        finally { setSalvando(false); }
    }
    const principal = normalizarHex(cores.cor_primaria) ?? '#0D6EFD';
    const secundaria = normalizarHex(cores.cor_secundaria) ?? '#1E293B';
    const acento = normalizarHex(cores.cor_acento) ?? '#14B8A6';
    return <Cartao titulo={`Aparência de ${nome}`} descricao="Escolha até três cores. A paleta salva vale para todos os usuários desta federação.">
        <form onSubmit={e => { e.preventDefault(); void salvar(); }} className="space-y-6">
            <section className="grid gap-6 lg:grid-cols-[1fr_1.3fr]">
                <div><p className="text-xs uppercase tracking-[.2em] text-primary-300">Identidade da rede</p><h2 className="mt-3 text-3xl font-heading text-white">Uma marca que acompanha sua federação.</h2><p className="mt-3 text-sm leading-relaxed text-neutral-400">Comece por uma combinação e ajuste as cores abaixo. Veja o resultado antes de publicar para toda a equipe.</p></div>
                <div className="grid grid-cols-2 gap-3">{[
                    { nome: 'Atlântico', cores: ['#0284C7','#0C2340','#2DD4BF'] },
                    { nome: 'Terracota', cores: ['#C65D3B','#292524','#FBBF24'] },
                    { nome: 'Floresta', cores: ['#16836B','#102C27','#D4E157'] },
                    { nome: 'Essencial', cores: ['#64748B','#111827','#E2E8F0'] },
                ].map(p => <button key={p.nome} type="button" disabled={salvando} onClick={() => { setCores({ cor_primaria:p.cores[0],cor_secundaria:p.cores[1],cor_acento:p.cores[2] });setSucesso(false);setErro(null); }} className="rounded-xl border border-white/10 bg-white/[.03] p-4 text-left transition hover:border-white/30 focus-visible:outline-2 focus-visible:outline-primary-400"><span className="mb-3 flex overflow-hidden rounded-full">{p.cores.map(c => <span key={c} className="h-5 flex-1" style={{backgroundColor:c}} />)}</span><span className="text-sm text-white">{p.nome}</span></button>)}</div>
            </section>
            <div className="grid gap-4 md:grid-cols-3">
                {CAMPOS.map(c => <fieldset key={c.chave} disabled={salvando} className="rounded-lg border border-neutral-700 p-4">
                    <legend className="px-1 text-sm font-medium text-neutral-100">{c.nome}</legend>
                    <p className="mb-3 text-xs text-neutral-400">{c.descricao}</p>
                    <label className="mb-3 flex items-center gap-2 text-sm text-neutral-300"><input type="checkbox" checked={cores[c.chave] !== null} onChange={e => mudar(c.chave, e.target.checked ? c.padrao : null)} />Personalizar {c.nome.toLowerCase()}</label>
                    <label className="mb-1 block text-xs text-neutral-400">Seletor ou código hexadecimal (#RRGGBB)</label>
                    <div className="flex items-center gap-2">
                        <input type="color" aria-label={`Selecionar cor ${c.nome.toLowerCase()}`} disabled={cores[c.chave] === null} value={normalizarHex(cores[c.chave]) ?? c.padrao} onChange={e => mudar(c.chave, e.target.value)} className="h-10 w-12 cursor-pointer rounded border border-neutral-600 bg-neutral-800 disabled:opacity-40" />
                        <input aria-label={`Cor ${c.nome.toLowerCase()} em hexadecimal`} aria-invalid={cores[c.chave] !== null && !normalizarHex(cores[c.chave])} type="text" maxLength={7} placeholder="#RRGGBB" autoComplete="off" spellCheck={false} disabled={cores[c.chave] === null} value={cores[c.chave] ?? ''} onChange={e => mudar(c.chave, e.target.value)} className="min-w-0 w-full rounded border border-neutral-600 bg-neutral-800 px-2 py-2 text-sm uppercase text-neutral-100 disabled:opacity-40" />
                    </div>
                    {cores[c.chave] !== null && !normalizarHex(cores[c.chave]) && <p className="mt-2 text-xs text-red-300">Digite um hexadecimal válido, como #2563EB (seis dígitos após #).</p>}
                </fieldset>)}
            </div>
            <section aria-label="Prévia da paleta" className="overflow-hidden rounded-lg border border-neutral-700">
                <div className="flex items-center justify-between px-4 py-3" style={{ backgroundColor: secundaria, color: corDeTexto(secundaria) }}><span className="font-medium">{nome}</span><span className="text-xs">Prévia</span></div>
                <div className="grid gap-4 bg-neutral-950 p-6 sm:grid-cols-3">{['Visão da rede','Metas do ano','Evolução mensal'].map((titulo,i) => <div key={titulo} className="rounded-xl border border-white/10 bg-white/[.03] p-4"><p className="text-xs text-neutral-400">{titulo}</p><p className="mt-3 text-2xl font-heading text-white">{['Sua federação','68%','+12%'][i]}</p><div className="mt-4 flex h-12 items-end gap-1" aria-hidden="true">{[35,60,45,80,65,95,75].map((h,j) => <span key={j} className="flex-1 rounded-t" style={{height:`${h}%`,backgroundColor:j===5?acento:principal,opacity:.4+j*.08}} />)}</div></div>)}<p className="text-xs text-neutral-500 sm:col-span-3">Dados ilustrativos para visualizar as cores.</p></div>
                <div className="flex flex-wrap items-center justify-between gap-4 bg-neutral-900 p-4"><span className="text-sm text-neutral-300">Indicadores da rede <span className="ml-2 inline-block h-2 w-2 rounded-full" style={{ backgroundColor: acento }} /></span><span className="rounded-md px-4 py-2 text-sm font-medium" style={{ backgroundColor: principal, color: corDeTexto(principal) }}>Ação principal</span></div>
            </section>
            <p className="text-xs leading-relaxed text-neutral-400">A prévia não altera o portal até você salvar. Cores de erro e alerta permanecem padronizadas. Outras sessões recebem a paleta ao abrir o portal ou em até um minuto.</p>
            <AvisoErro erro={erro} />
            {sucesso && <div role="status"><AvisoOk>Paleta salva para todos os usuários de {nome}.</AvisoOk></div>}
            <div className="flex flex-wrap gap-3"><button type="submit" disabled={salvando || !alterado || invalido} className={botaoPrimario}>{salvando ? 'Salvando…' : 'Salvar paleta'}</button><button type="button" disabled={salvando} className={botaoSecundario} onClick={() => { setCores({ cor_primaria: null, cor_secundaria: null, cor_acento: null }); setSucesso(false); }}>Usar padrão</button></div>
        </form>
    </Cartao>;
}
