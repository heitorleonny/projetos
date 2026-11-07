import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';
import ts from 'typescript';

const codigo = ts.transpileModule(
    readFileSync(new URL('../src/features/onboarding/onboardingStorage.ts', import.meta.url), 'utf8'),
    { compilerOptions: { module: ts.ModuleKind.CommonJS } },
).outputText;
const armazenamento = () => {
    const itens = new Map();
    return { getItem: (id) => itens.get(id) ?? null, setItem: (id, valor) => itens.set(id, valor) };
};
function carregar(localStorage = armazenamento(), sessionStorage = armazenamento()) {
    const exports = {};
    runInNewContext(codigo, { exports, localStorage, sessionStorage });
    return exports;
}

test('primeiro acesso é independente por conta e ignora o aviso legado', () => {
    const local = armazenamento();
    local.setItem('portal-fejepe-welcome-v1.0', '1');
    const guia = carregar(local);
    assert.equal(guia.onboardingVisto('conta-a'), false);
    guia.registrarOnboarding('conta-a', true);
    assert.equal(guia.onboardingVisto('conta-a'), true);
    assert.equal(guia.onboardingVisto('conta-b'), false);
});
test('conclusão persiste depois de recarregar e numa nova sessão', () => {
    const local = armazenamento();
    carregar(local).registrarOnboarding('conta-a', true);
    assert.equal(carregar(local).onboardingVisto('conta-a'), true);
});
test('adiar só vale na sessão atual', () => {
    const local = armazenamento();
    const sessao = armazenamento();
    carregar(local, sessao).registrarOnboarding('conta-a', false);
    assert.equal(carregar(local, sessao).onboardingVisto('conta-a'), true);
    assert.equal(carregar(local).onboardingVisto('conta-a'), false);
});
test('armazenamento bloqueado não impede sair do guia', () => {
    const bloqueado = { getItem() { throw new Error('Bloqueado'); }, setItem() { throw new Error('Bloqueado'); } };
    const guia = carregar(bloqueado, bloqueado);
    assert.equal(guia.onboardingVisto('conta-a'), false);
    guia.registrarOnboarding('conta-a', true);
    assert.equal(guia.onboardingVisto('conta-a'), true);
    assert.equal(guia.onboardingVisto('conta-b'), false);
});
test('retorno preserva filtros e âncoras de rotas internas', () => {
    assert.equal(carregar().destinoDoOnboarding('/admin?aba=usuarios#lista'), '/admin?aba=usuarios#lista');
});
test('retorno recusa URLs externas e laços de autenticação ou onboarding', () => {
    const guia = carregar();
    for (const destino of [null, 123, 'https://exemplo.com', '//exemplo.com', '/\\exemplo.com', '/onboarding', '/onboarding?etapa=2', '/login#erro', '/definir-senha']) {
        assert.equal(guia.destinoDoOnboarding(destino), '/dashboard');
    }
});
