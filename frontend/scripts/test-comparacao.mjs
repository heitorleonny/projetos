import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';
import ts from 'typescript';

const exports = {};
runInNewContext(ts.transpileModule(
    readFileSync(new URL('../src/features/comparacao/variacao.ts', import.meta.url), 'utf8'),
    { compilerOptions: { module: ts.ModuleKind.CommonJS } },
).outputText, { exports });

test('cluster não apresenta percentual e percentuais usam pontos percentuais', () => {
    const variacao = exports.variacaoComparacao;
    assert.equal(variacao('cluster', 1, 3), 2);
    assert.equal(variacao('percentual_meta', 40, 60), 20);
    assert.equal(variacao('taxa_colab', 0.1, 0.3).toFixed(1), '20.0');
    assert.equal(variacao('percentual_meta', 0, 10), 10);
});

test('valores monetários preservam variação relativa; base zero/ausente não inventa percentual', () => {
    assert.equal(exports.variacaoComparacao('faturamento', 100, 150), 50);
    assert.equal(exports.variacaoComparacao('faturamento', 0, 100), null);
    assert.equal(exports.variacaoComparacao('cluster', null, 3), null);
});
