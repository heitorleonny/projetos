import { useEffect, useId, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '../../services/api';
import type { FederacaoBranding } from '../../services/brandingService';
import { useFederacaoBranding } from '../../branding/useFederacaoBranding';
import { logoFoiEnviada } from '../../branding/logoUrl';
import { lerErro } from './adminService';
import type { ErroApi } from './adminService';
import { AvisoErro, AvisoOk, botaoPrimario, botaoSecundario, Cartao } from './ui';
import { problemaDoArquivo, TIPOS_DE_LOGO } from './logoArquivo';

function Previa({ src, nome }: { src: string | null; nome: string }) {
    return <div className="flex items-center gap-4" aria-hidden="true">
        {/* Como aparece no topo do portal e num círculo, sobre o fundo escuro. */}
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-secondary-500">
            {src ? <img src={src} alt="" className="h-9 w-9 object-contain" /> : <span className="font-heading text-lg font-bold">{nome.charAt(0).toUpperCase()}</span>}
        </div>
        <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-full border border-white/10 bg-white">
            {src ? <img src={src} alt="" className="h-full w-full object-contain" /> : <span className="font-heading text-xl font-bold text-neutral-800">{nome.charAt(0).toUpperCase()}</span>}
        </div>
    </div>;
}

export default function FormularioLogo() {
    const { branding, nome, atualizarBranding } = useFederacaoBranding();
    const qc = useQueryClient();
    const campo = useRef<HTMLInputElement>(null);
    const idCampo = useId();
    const [arquivo, setArquivo] = useState<File | null>(null);
    const [previa, setPrevia] = useState<string | null>(null);
    const [aviso, setAviso] = useState<string | null>(null);
    const [erro, setErro] = useState<ErroApi | null>(null);
    const [sucesso, setSucesso] = useState<string | null>(null);
    const [enviando, setEnviando] = useState(false);

    // A prévia local é liberada ao trocar de arquivo ou sair da tela.
    useEffect(() => () => { if (previa) URL.revokeObjectURL(previa); }, [previa]);

    function escolher(selecionado: File | null) {
        setErro(null); setSucesso(null);
        setArquivo(null); setPrevia(null);
        if (!selecionado) { setAviso(null); return; }
        const problema = problemaDoArquivo(selecionado);
        setAviso(problema);
        if (problema) return;
        setArquivo(selecionado);
        setPrevia(URL.createObjectURL(selecionado));
    }
    function limparCampo() {
        setArquivo(null); setPrevia(null);
        if (campo.current) campo.current.value = '';
    }
    async function enviar() {
        if (!arquivo || enviando) return;
        setEnviando(true); setErro(null); setSucesso(null);
        try {
            const corpo = new FormData();
            corpo.append('arquivo', arquivo);
            // Sem declarar multipart, o cliente padrão (JSON) converteria o FormData.
            const { data } = await api.put<FederacaoBranding>('/federacao/minha/logo', corpo, { headers: { 'Content-Type': 'multipart/form-data' } });
            atualizarBranding(data, branding.slug);
            void qc.invalidateQueries({ queryKey: ['admin', 'federacoes'] });
            limparCampo();
            setSucesso(`Logo salva para todos os usuários de ${nome}.`);
        } catch (e) { setErro(lerErro(e)); }
        finally { setEnviando(false); }
    }
    async function remover() {
        if (enviando) return;
        setEnviando(true); setErro(null); setSucesso(null);
        try {
            const { data } = await api.delete<FederacaoBranding>('/federacao/minha/logo');
            atualizarBranding(data, branding.slug);
            void qc.invalidateQueries({ queryKey: ['admin', 'federacoes'] });
            limparCampo();
            setSucesso('Logo removida. O portal volta a mostrar a inicial da federação.');
        } catch (e) { setErro(lerErro(e)); }
        finally { setEnviando(false); }
    }

    return <Cartao titulo="Logo da federação" descricao="Aparece no topo do portal, na aba do navegador e na tela de entrada. Vale para todos os usuários desta federação.">
        <div className="grid gap-6 md:grid-cols-[auto_1fr] md:items-center">
            <div className="space-y-2">
                <p className="text-xs text-neutral-400">{previa ? 'Prévia do arquivo escolhido' : 'Logo atual'}</p>
                <Previa src={previa ?? branding.logo_url} nome={nome} />
            </div>
            <div className="space-y-3">
                <label htmlFor={idCampo} className="block text-sm font-medium text-neutral-100">Escolher imagem</label>
                <input ref={campo} id={idCampo} type="file" accept={TIPOS_DE_LOGO.join(',')} disabled={enviando}
                    aria-describedby={`${idCampo}-ajuda`}
                    onChange={e => escolher(e.target.files?.[0] ?? null)}
                    className="block w-full text-sm text-neutral-300 file:mr-3 file:cursor-pointer file:rounded-lg file:border-0 file:bg-primary-600 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-primary-500" />
                <p id={`${idCampo}-ajuda`} className="text-xs leading-relaxed text-neutral-400">PNG, JPEG ou WebP de até 512 KB. Prefira uma imagem quadrada; PNG com fundo transparente aparece sobre fundo branco nos círculos.</p>
                {aviso && <p role="alert" className="text-xs text-red-300">{aviso}</p>}
            </div>
        </div>
        <div className="mt-5 space-y-3">
            <AvisoErro erro={erro} />
            {sucesso && <div role="status"><AvisoOk>{sucesso}</AvisoOk></div>}
            <div className="flex flex-wrap gap-3">
                <button type="button" disabled={!arquivo || enviando} onClick={() => void enviar()} className={botaoPrimario}>{enviando ? 'Salvando…' : 'Salvar logo'}</button>
                {arquivo && <button type="button" disabled={enviando} onClick={limparCampo} className={botaoSecundario}>Cancelar</button>}
                {!arquivo && logoFoiEnviada(branding.logo_url) && <button type="button" disabled={enviando} onClick={() => void remover()} className={botaoSecundario}>Remover logo</button>}
            </div>
        </div>
    </Cartao>;
}
