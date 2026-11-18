import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';
import ts from 'typescript';

const src = fileURLToPath(new URL('../src', import.meta.url));
function carregar(caminho) {
    const exports = {};
    runInNewContext(ts.transpileModule(readFileSync(join(src, caminho), 'utf8'),
        { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText, { exports });
    return exports;
}
const tour = carregar('features/onboarding/passosDoTour.ts');
const logo = carregar('branding/logoUrl.ts');
const arquivo = carregar('features/admin/logoArquivo.ts');

function arquivos(pasta) {
    return readdirSync(pasta).flatMap(nome => {
        const caminho = join(pasta, nome);
        return statSync(caminho).isDirectory() ? arquivos(caminho) : /\.tsx$/.test(nome) ? [caminho] : [];
    });
}

test('todo alvo do roteiro está marcado com data-tour em alguma tela', () => {
    const marcados = new Set(arquivos(src).flatMap(f => [...readFileSync(f, 'utf8').matchAll(/data-tour="([a-z-]+)"/g)].map(m => m[1])));
    for (const passo of tour.PASSOS_DO_TOUR) {
        assert.ok(passo.alvos.some(alvo => marcados.has(alvo)), `${passo.id}: nenhum alvo marcado (${passo.alvos})`);
        for (const alvo of passo.alvos) assert.ok(marcados.has(alvo), `${passo.id}: alvo ${alvo} não existe`);
    }
});

test('roteiro abre telas reais e só mostra Administração para quem administra', () => {
    const rotas = readFileSync(join(src, 'App.tsx'), 'utf8');
    for (const passo of tour.PASSOS_DO_TOUR) assert.match(rotas, new RegExp(`path="${passo.rota}"`), passo.rota);
    const membro = tour.passosVisiveis(false).map(p => p.id);
    const admin = tour.passosVisiveis(true).map(p => p.id);
    assert.ok(!membro.includes('admin') && admin.includes('admin'));
    assert.equal(admin.length, membro.length + 1);
    assert.equal(new Set(admin).size, admin.length);
});

test('parâmetro ?tour só aceita índice existente', () => {
    assert.equal(tour.indiceDoParametro('0', 5), 0);
    assert.equal(tour.indiceDoParametro('4', 5), 4);
    for (const valor of [null, '5', '-1', '1.5', 'abc', '', '999', '1e1']) assert.equal(tour.indiceDoParametro(valor, 5), null, String(valor));
});

const janela = { width: 1280, height: 800 };
const cartao = { width: 360, height: 220 };
test('cartão fica abaixo, acima ou sobreposto, sempre dentro da janela', () => {
    const abaixo = tour.posicionarCartao({ top: 80, left: 100, width: 400, height: 60 }, janela, cartao);
    assert.equal(abaixo.lado, 'abaixo');
    assert.equal(abaixo.top, 80 + 60 + 14);
    const acima = tour.posicionarCartao({ top: 600, left: 100, width: 400, height: 120 }, janela, cartao);
    assert.equal(acima.lado, 'acima');
    const grande = tour.posicionarCartao({ top: 20, left: 0, width: 1280, height: 760 }, janela, cartao);
    assert.equal(grande.lado, 'sobreposto');
    const canto = tour.posicionarCartao({ top: 10, left: 1250, width: 30, height: 30 }, janela, cartao);
    assert.ok(canto.left + cartao.width <= janela.width - 16 && canto.left >= 16);
    const celular = tour.posicionarCartao({ top: 10, left: 300, width: 60, height: 40 }, { width: 390, height: 800 }, { width: 358, height: 240 });
    assert.ok(celular.left >= 16 && celular.left + 358 <= 390);
    assert.equal(tour.posicionarCartao(null, janela, cartao).lado, 'centro');
});

test('destaque ganha folga e não passa da janela', () => {
    assert.deepEqual(JSON.parse(JSON.stringify(tour.recorteDoAlvo({ top: 100, left: 100, width: 50, height: 20 }, janela))),
        { top: 92, left: 92, width: 66, height: 36 });
    const borda = tour.recorteDoAlvo({ top: -50, left: -10, width: 2000, height: 2000 }, janela);
    assert.ok(borda.top >= 4 && borda.left >= 4 && borda.left + borda.width <= 1276 && borda.top + borda.height <= 796);
});

test('logo enviada aponta para a API configurada; URL externa não muda', () => {
    const enviada = '/api/v1/federacao/logo?slug=fejepe&v=0123456789abcdef';
    assert.equal(logo.resolverLogoDaApi(enviada, '/api/v1'), enviada);
    assert.equal(logo.resolverLogoDaApi(enviada, 'http://localhost:8000/api/v1/'), 'http://localhost:8000/api/v1/federacao/logo?slug=fejepe&v=0123456789abcdef');
    assert.equal(logo.resolverLogoDaApi('https://cdn.example.com/logo.png', 'http://x/api/v1'), 'https://cdn.example.com/logo.png');
    assert.equal(logo.resolverLogoDaApi(null, '/api/v1'), null);
    assert.equal(logo.logoFoiEnviada(enviada), true);
    assert.equal(logo.logoFoiEnviada('https://cdn.example.com/logo.png'), false);
    assert.equal(logo.logoFoiEnviada(null), false);
});

test('arquivo de logo: só PNG, JPEG e WebP de até 512 KB', () => {
    for (const type of ['image/png', 'image/jpeg', 'image/webp']) assert.equal(arquivo.problemaDoArquivo({ type, size: 1000 }), null);
    assert.match(arquivo.problemaDoArquivo({ type: 'image/svg+xml', size: 1000 }), /SVG/);
    assert.match(arquivo.problemaDoArquivo({ type: 'image/gif', size: 1000 }), /PNG, JPEG ou WebP/);
    assert.match(arquivo.problemaDoArquivo({ type: 'image/png', size: 512 * 1024 + 1 }), /512 KB/);
    assert.equal(arquivo.problemaDoArquivo({ type: 'image/png', size: 512 * 1024 }), null);
    assert.match(arquivo.problemaDoArquivo({ type: 'image/png', size: 0 }), /vazio/);
});
