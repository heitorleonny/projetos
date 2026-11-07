/**
 * Configuração de runtime — PLACEHOLDER de desenvolvimento.
 *
 * Em produção este arquivo é SOBRESCRITO no start do container pelo
 * docker-entrypoint.sh, que o gera a partir das variáveis de ambiente reais.
 * É o que permite uma imagem única servir ambientes e federações diferentes
 * sem rebuild.
 *
 * Aqui ele existe só para que `npm run dev` e `npm run preview` não peçam um
 * arquivo inexistente. Deixar `window.__ENV__` sem definir é proposital: sem
 * ele, src/config/env.ts cai no `.env` lido em build time, que é exatamente o
 * que o desenvolvimento local espera.
 *
 * Para simular um deploy localmente, descomente e edite:
 *
 * window.__ENV__ = {
 *     API_BASE_URL: 'http://127.0.0.1:8000/api/v1',
 *     TENANT_SLUG: 'fejepe',
 * };
 */
