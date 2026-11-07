import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';
import ts from 'typescript';

const codigo = ts.transpileModule(
    readFileSync(new URL('../src/utils/fotoUrl.ts', import.meta.url), 'utf8'),
    { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } },
).outputText;
const exports = {};
runInNewContext(codigo, { exports, URL });
const { fotoUrlSegura } = exports;

test('foto HTTPS pública preserva caminho e parâmetros sem download', () => {
    assert.equal(fotoUrlSegura(' https://cdn.example.com/logo.png?v=2 '), 'https://cdn.example.com/logo.png?v=2');
});
test('assets do portal são preservados sem aceitar travessia ou protocolo implícito', () => {
    assert.equal(fotoUrlSegura('/logos/ej.png'), '/logos/ej.png');
    assert.equal(fotoUrlSegura('/assets/ej.svg?v=2'), '/assets/ej.svg?v=2');
    for (const valor of ['logos/ej.png', '//cdn.example.com/a.png', '/%2fcdn.example.com/a.png',
        '/../logo.png', '/logos/%2e%2e/logo.png', '/logos/%5c%5clogo.png', '/logos/%0alogo.png']) {
        assert.equal(fotoUrlSegura(valor), null, valor);
    }
});
test('foto ausente, inválida ou com protocolo inseguro resulta em iniciais', () => {
    for (const valor of [null, undefined, '', '   ',
        'http://cdn.example.com/a.png', 'data:image/svg+xml,logo', 'javascript:alert(1)',
        'https://cdn.example.com/a\nb.png', 'https://cdn.example.com\\logo.png']) {
        assert.equal(fotoUrlSegura(valor), null, String(valor));
    }
});
test('credenciais e endereços locais não são usados como imagem de EJ', () => {
    for (const valor of ['https://usuario:senha@cdn.example.com/logo.png',
        'https://localhost/logo.png', 'https://tenant.local/logo.png',
        'https://tenant.internal/logo.png', 'https://127.0.0.1/logo.png',
        'https://192.168.1.1/logo.png', 'https://[::1]/logo.png']) {
        assert.equal(fotoUrlSegura(valor), null, valor);
    }
});
