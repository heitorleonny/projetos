import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

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
