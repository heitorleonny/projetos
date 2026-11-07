import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';
import { build } from 'esbuild';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import ts from 'typescript';

const src = fileURLToPath(new URL('../src', import.meta.url));
function arquivos(pasta) {
    return readdirSync(pasta).flatMap(nome => {
        const caminho = join(pasta, nome);
        return statSync(caminho).isDirectory() ? arquivos(caminho) : /\.(ts|tsx)$/.test(nome) ? [caminho] : [];
    });
}

test('SDE aparece com o nome oficial: Saldo de Evolução da Rede', () => {
    const lista = arquivos(src);
    assert.ok(lista.length > 0);
    for (const arquivo of lista) assert.ok(!readFileSync(arquivo, 'utf8').includes('Desenvolvimento Estratégico'), arquivo);
    assert.ok(readFileSync(join(src, 'features/indicadores/IndicadoresPage.tsx'), 'utf8').includes('SDE — Saldo de Evolução da Rede'));
});

// ── Visualização da consulta ─────────────────────────────────────────────

const visualizacao = {};
runInNewContext(ts.transpileModule(readFileSync(join(src, 'features/assistente/visualizacao.ts'), 'utf8'),
    { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText, { exports: visualizacao });
const { graficoDaResposta } = visualizacao;

const linha = (nome, valor, id_ej = null) => ({ id_ej, nome, valor });
const resposta = (fonte, linhas, extra = {}) => ({
    status: 'respondida', resposta: 'Resposta sintética.', fonte, ano: 2026, mes: 9, total: linhas.length, linhas,
    unidade: 'numero', modelo: null, contexto: null, sugestoes: [], esclarecimento: null, ...extra,
});
const ranking = resposta('rede_service.gerar_ranking', Array.from({ length: 14 }, (_, i) => linha(`EJ Sintética ${i}`, 1000 - i, i + 1)), { unidade: 'moeda' });
const indicadores = resposta('rede_service.calcular_indicadores_rede', [linha('Faturamento acumulado', 10), linha('Total de EJs', 2)]);
const foraDoZero = resposta('empresa_service.listar_empresas', [linha('EJ Sintética A', 10, 1), linha('EJ Sintética B', 20, 2)], { unidade: 'moeda' });
const ritmo = resposta('rede_service.calcular_ritmo_mensal', [linha('Sem vendas', 3), linha('Ritmo mínimo', 2), linha('Ritmo significativo', 1)]);
const sde = resposta('rede_service.calcular_sde_cenarios', [linha('Índice de Cluster', -0.45), linha('Índice c/ Meta CSAT', 0), linha('Tracking de Cluster', 0.3)]);

test('ranking vira barras horizontais com no máximo 10 EJs', () => {
    const grafico = graficoDaResposta(ranking);
    assert.equal(grafico.tipo, 'barras_horizontais');
    assert.equal(grafico.pontos.length, 10);
    assert.equal(grafico.unidade, 'moeda');
});
test('ritmo e SDE viram barras com as mesmas categorias da resposta', () => {
    assert.deepEqual(graficoDaResposta(ritmo).pontos.map(p => p.rotulo), ['Sem vendas', 'Ritmo mínimo', 'Ritmo significativo']);
    assert.deepEqual(graficoDaResposta(sde).pontos.map(p => p.valor), [-0.45, 0, 0.3]);
});
test('indicadores da rede, fora do zero, glossário e respostas vazias não têm gráfico', () => {
    for (const r of [indicadores, foraDoZero, resposta('glossario', []), resposta('rede_service.gerar_ranking', []), resposta(null, [])]) {
        assert.equal(graficoDaResposta(r), null);
    }
});
test('perfil usa a série do backend e distribuição de metas usa as faixas', () => {
    const perfil = resposta('empresa_service.buscar_empresa', [linha('EJ Sintética', null, 7)], { serie: [{ mes: 1, valor: 10 }, { mes: 2, valor: 30 }] });
    assert.deepEqual(JSON.parse(JSON.stringify(graficoDaResposta(perfil).pontos)), [{ rotulo: 'jan', valor: 10 }, { rotulo: 'fev', valor: 30 }]);
    assert.equal(graficoDaResposta(perfil).tipo, 'linha');
    const metas = resposta('calculo_service.calcular_percentual_meta', [linha('Meta atingida', 2), linha('Sem meta cadastrada', 1)]);
    assert.equal(graficoDaResposta(metas).tipo, 'barras');
    const faixa = resposta('calculo_service.calcular_percentual_meta', [linha('EJ Sintética', 20, 3)]);
    assert.equal(graficoDaResposta(faixa), null);
});

const pastaBundle = fileURLToPath(new URL('../node_modules/.cache/nexo-test/', import.meta.url));
await build({
    entryPoints: [join(src, 'features/assistente/ResultadoConsulta.tsx')], bundle: true, format: 'esm', platform: 'node',
    jsx: 'automatic', outfile: join(pastaBundle, 'ResultadoConsulta.mjs'), logLevel: 'error',
    external: ['react', 'react/*', 'react-dom', 'react-dom/*', 'react-router-dom', 'recharts'],
});
const { default: ResultadoConsulta } = await import(new URL('../node_modules/.cache/nexo-test/ResultadoConsulta.mjs', import.meta.url));
function renderizar(r, modoInicial) {
    const avisos = console.warn;
    console.warn = () => {}; // ResponsiveContainer avisa que não tem medida no servidor.
    try {
        return renderToStaticMarkup(createElement(MemoryRouter, null, createElement(ResultadoConsulta, {
            resposta: r, fechar: () => {}, escolher: () => {}, enviando: false, ...(modoInicial ? { modoInicial } : {}),
        })));
    } finally { console.warn = avisos; }
}

test('componente: ranking abre no gráfico, com alternância para a tabela preservada', () => {
    const html = renderizar(ranking);
    assert.match(html, /role="group" aria-label="Forma de exibição"/);
    assert.match(html, /aria-pressed="true"[^>]*>Gráfico</);
    assert.match(html, /aria-pressed="false"[^>]*>Tabela</);
    assert.match(html, /data-visualizacao="grafico"/);
    assert.doesNotMatch(html, /<table/);
});
test('componente: modo tabela mostra a mesma tabela de antes, sem o gráfico', () => {
    const html = renderizar(ranking, 'tabela');
    assert.match(html, /aria-pressed="true"[^>]*>Tabela</);
    assert.match(html, /<table/);
    assert.match(html, /EJ Sintética 0/);
    assert.doesNotMatch(html, /data-visualizacao="grafico"/);
});
test('componente: indicadores da rede e fora do zero não oferecem gráfico', () => {
    const cartoes = renderizar(indicadores);
    assert.doesNotMatch(cartoes, /Forma de exibição|data-visualizacao/);
    assert.match(cartoes, /<dl/);
    const tabela = renderizar(foraDoZero);
    assert.doesNotMatch(tabela, /Forma de exibição|data-visualizacao/);
    assert.match(tabela, /<table/);
});
test('componente: gráfico de SDE e ritmo traz descrição textual acessível', () => {
    const html = renderizar(sde);
    assert.match(html, /role="img" aria-label="SDE por cenário\. Índice de Cluster: -0,45/);
});

const perfil = resposta('empresa_service.buscar_empresa', [
    linha('EJ Sintética PE', null, 101), { id_ej: null, nome: 'Faturamento acumulado', valor: 6000, unidade: 'moeda' },
    { id_ej: null, nome: 'Projeção anual', valor: null, unidade: 'moeda' },
], { serie: [{ mes: 1, valor: 1000 }, { mes: 2, valor: 2000 }], total: 1 });

test('componente: perfil mostra link, indicadores e a série com alternância', () => {
    const grafico = renderizar(perfil);
    assert.match(grafico, /href="\/empresas\/101"[^>]*>Abrir o perfil completo de EJ Sintética PE</);
    assert.match(grafico, /Faturamento acumulado/);
    assert.match(grafico, /Não disponível/);
    assert.match(grafico, /data-visualizacao="grafico"/);
    assert.match(grafico, /Faturamento por mês\. jan: R\$\s1\.000,00/);
    const tabela = renderizar(perfil, 'tabela');
    assert.match(tabela, /<caption class="sr-only">Faturamento por mês<\/caption>/);
    assert.match(tabela, /Faturamento acumulado/); // indicadores continuam visíveis
    assert.doesNotMatch(tabela, /data-visualizacao="grafico"/);
});
test('componente: esclarecimento de EJ sem opções não desenha grupo vazio', () => {
    const html = renderizar({ ...resposta(null, []), status: 'esclarecimento', esclarecimento: { pergunta: 'Qual EJ?', opcoes: [] } });
    assert.doesNotMatch(html, /Escolha como consultar/);
});

test('componente: distribuição de metas em gráfico e lista de uma faixa em tabela com "% da meta"', () => {
    const distribuicao = resposta('calculo_service.calcular_percentual_meta', [linha('100% ou mais da meta', 1), linha('Sem meta cadastrada', 2)]);
    assert.match(renderizar(distribuicao), /data-visualizacao="grafico"/);
    const faixa = resposta('calculo_service.calcular_percentual_meta', [linha('EJ Sintética A', 12.5, 1), linha('EJ Sintética B', null, 2)]);
    const html = renderizar(faixa);
    assert.doesNotMatch(html, /Forma de exibição/);
    assert.match(html, />% da meta</);
    assert.match(html, />Sem meta</);
});
