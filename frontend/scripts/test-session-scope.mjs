import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';
import ts from 'typescript';
import { QueryClient } from '@tanstack/react-query';

const exports = {};
runInNewContext(ts.transpileModule(
    readFileSync(new URL('../src/auth/sessionScope.ts', import.meta.url), 'utf8'),
    { compilerOptions: { module: ts.ModuleKind.CommonJS } },
).outputText, { exports, atob });
const session = (id, tenant, papel = 'membro', exp = 100) => ({
    user: { id, app_metadata: { federacao_id: tenant, papel } }, access_token: `header.${Buffer.from(JSON.stringify({ federacao_id: tenant, papel, exp })).toString('base64url')}.signature`,
});

test('logout externo, troca de conta, tenant e papel removem resultados privados', () => {
    const client = new QueryClient();
    const apply = exports.createSessionBoundary(() => client.clear());
    for (const next of [session('a', 1), session('b', 2), session('b', 3), session('b', 3, 'admin'), null]) {
        client.setQueryData(['empresas'], ['privado']);
        apply(next);
        assert.equal(client.getQueryData(['empresas']), undefined);
    }
});

test('renovação do token com mesmo escopo mantém o cache', () => {
    const client = new QueryClient();
    const apply = exports.createSessionBoundary(() => client.clear());
    apply(session('a', 1));
    client.setQueryData(['empresas'], ['mesma conta']);
    apply(session('a', 1, 'membro', 200));
    assert.deepEqual(client.getQueryData(['empresas']), ['mesma conta']);
});

test('resposta tardia da conta anterior não repovoa cache após troca', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const apply = exports.createSessionBoundary(() => client.clear());
    apply(session('a', 1));
    let resolve;
    const pending = client.fetchQuery({ queryKey: ['empresas'], queryFn: () => new Promise((done) => { resolve = done; }) });
    const settled = pending.catch(() => undefined);
    apply(session('b', 2));
    resolve(['privado da conta a']);
    await settled;
    assert.equal(client.getQueryData(['empresas']), undefined);
});
