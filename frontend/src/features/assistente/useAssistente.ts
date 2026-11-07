import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { perguntarRede } from './assistenteService';
import type { ContextoConsulta, RespostaRede } from './assistenteService';

export interface MensagemRede {
    id: string;
    pergunta: string;
    resposta?: RespostaRede;
    erro?: string;
    interrompida?: boolean;
    contexto?: ContextoConsulta | null;
}

/** Histórico efêmero: não vai para storage, nem acompanha troca de identidade. */
export function useAssistente() {
    const [mensagens, setMensagens] = useState<MensagemRede[]>([]);
    const [enviando, setEnviando] = useState(false);
    const requisicao = useRef<AbortController | null>(null);
    const mensagemAtiva = useRef<string | null>(null);
    useEffect(() => () => requisicao.current?.abort(), []);

    function interromper() {
        const idAtivo = mensagemAtiva.current;
        requisicao.current?.abort();
        requisicao.current = null;
        setEnviando(false);
        setMensagens(atuais => atuais.map(mensagem => mensagem.id === idAtivo
            ? { ...mensagem, interrompida: true } : mensagem));
    }

    function limpar() {
        interromper();
        setMensagens([]);
    }

    async function enviar(pergunta: string, substituirId?: string) {
        if (requisicao.current || pergunta.trim().length < 3) return;
        const controller = new AbortController();
        const id = substituirId ?? crypto.randomUUID();
        requisicao.current = controller;
        mensagemAtiva.current = id;
        const anterior = substituirId ? mensagens.find(mensagem => mensagem.id === id)?.contexto : [...mensagens].reverse().find(mensagem => mensagem.resposta?.contexto)?.resposta?.contexto;
        setEnviando(true);
        setMensagens(atuais => substituirId
            ? atuais.map(mensagem => mensagem.id === id ? { id, pergunta, contexto: anterior } : mensagem)
            : [...atuais.slice(-19), { id, pergunta, contexto: anterior }]);
        try {
            const resposta = await perguntarRede(pergunta, controller.signal, anterior);
            if (!controller.signal.aborted) setMensagens(atuais => atuais.map(mensagem => mensagem.id === id ? { id, pergunta, contexto: anterior, resposta } : mensagem));
        } catch (erro) {
            if (controller.signal.aborted) return;
            const detalhe = axios.isAxiosError(erro) ? erro.response?.data?.detail : null;
            const texto = typeof detalhe === 'string' ? detalhe : 'Não consegui consultar os dados agora. Tente novamente em instantes.';
            setMensagens(atuais => atuais.map(mensagem => mensagem.id === id ? { id, pergunta, contexto: anterior, erro: texto } : mensagem));
        } finally {
            // Uma resposta cancelada não pode alterar o estado de uma consulta nova.
            if (requisicao.current === controller) {
                setEnviando(false);
                requisicao.current = null;
            }
        }
    }

    return { mensagens, enviando, enviar, interromper, limpar };
}
