"""Verificação HTTP com Auth e PostgREST reais da demo; não imprime dados de EJs."""

import os
from urllib.parse import urlsplit

import httpx
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def conferir(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise RuntimeError(mensagem)


def main() -> None:
    url = urlsplit(settings.SUPABASE_URL)
    conferir(url.hostname in ("localhost", "127.0.0.1") and url.port == 54421,
             "Este script só roda na demo local (:54421).")
    tokens = {}
    for slug, email in (("fejepe", "um@teste.local"), ("fejemg", "dois@teste.local"), ("operador", "op@teste.local")):
        resposta = httpx.post(
            f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={"apikey": settings.SUPABASE_ANON_KEY},
            json={"email": email, "password": os.getenv("DEMO_SENHA", "demo1234")}, timeout=15,
        )
        conferir(resposta.status_code == 200, f"Login de {slug} falhou; confira `make demo-seed` e DEMO_SENHA.")
        tokens[slug] = {"Authorization": f"Bearer {resposta.json()['access_token']}"}

    with TestClient(app, raise_server_exceptions=False) as cliente:
        def get(caminho, slug=None, esperado=200, **kwargs):
            resposta = cliente.get(caminho, headers=tokens.get(slug, {}), **kwargs)
            conferir(resposta.status_code == esperado, f"{slug or 'anônimo'}: {caminho.split('?')[0]} retornou {resposta.status_code}, esperado {esperado}.")
            return resposta.json()

        get("/health")
        get("/api/v1/empresas", esperado=401)
        get("/api/v1/admin/usuarios", esperado=401)
        conjuntos = {}
        for slug in ("fejepe", "fejemg", "operador"):
            marca = "fejepe" if slug == "operador" else slug
            branding = get("/api/v1/federacao/minha", slug)
            conferir(branding["slug"] == marca, f"Branding incorreto para {slug}.")
            ids = set()
            primeira = get("/api/v1/empresas?page_size=100", slug)
            for pagina in range(1, primeira["meta"]["total_pages"] + 1):
                dados = primeira if pagina == 1 else get(f"/api/v1/empresas?page_size=100&page={pagina}", slug)
                ids.update(ej["id_ej"] for ej in dados["data"])
            conferir(len(ids) == primeira["meta"]["total"] and len(ids) > 1, f"Paginação incompleta ou demo sem dados para {slug}.")
            conjuntos[slug] = ids
            indicadores = get("/api/v1/rede/indicadores", slug)
            conferir(indicadores["total_ejs"] == len(ids), f"Total dos indicadores diverge da listagem para {slug}.")
            for rota in ("rede/ritmo-mensal", "rede/sde", "rede/ranking", "eventos", "admin/sessao", "admin/federacoes", "admin/usuarios", "admin/importacoes"):
                get(f"/api/v1/{rota}", slug)
            selecionadas = sorted(ids)[:2]
            get(f"/api/v1/empresas/{selecionadas[0]}", slug)
            get("/api/v1/empresas/comparar", slug, params=[("ids", i) for i in selecionadas])
            print(f"OK: {slug} — login, branding, paginação completa e endpoints das telas.")

        conferir(conjuntos["fejepe"].isdisjoint(conjuntos["fejemg"]), "A listagem misturou tenants.")
        conferir(conjuntos["operador"] == conjuntos["fejepe"], "Operador ampliou o alcance dos dados de EJ.")
        for origem, destino in (("fejepe", "fejemg"), ("fejemg", "fejepe"), ("operador", "fejemg")):
            get(f"/api/v1/empresas/{min(conjuntos[destino])}", origem, esperado=404)
        print("OK: consultas cruzadas recusadas e operador restrito ao próprio tenant nos dados de EJ.")

        federacoes = get("/api/v1/admin/federacoes", "operador")
        conferir(len(federacoes) == 27, "O catálogo não contém as 27 federações.")
        resumo_master = get("/api/v1/admin/master/federacoes", "operador")
        planos_master = get("/api/v1/admin/master/planos", "operador")
        conferir(len(resumo_master) == len(federacoes), "Resumo master omitiu federações.")
        conferir(bool(planos_master), "Catálogo master vazio.")
        get("/api/v1/admin/master/federacoes", "fejepe", esperado=403)
        get("/api/v1/admin/master/planos", "fejemg", esperado=403)
        get("/api/v1/admin/master/federacoes", esperado=401)
        usuarios = get("/api/v1/admin/usuarios", "operador")
        for f in resumo_master:
            cadastros = [u for u in usuarios if u["federacao_id"] == f["id"]]
            conferir(f["usuarios_total"] == len(cadastros), "Total master diverge do cadastro.")
            conferir(f["usuarios_ativos"] == sum(u["ativo"] for u in cadastros), "Ativos master divergem do cadastro.")
        print("OK: master — agregados por federação conferidos, catálogo visível e admins comuns recusados.")
        ids_admin = {u["federacao_id"] for u in usuarios if u["papel"] == "admin" and u["ativo"] and u["vinculado"]}
        conferir(ids_admin == {f["id"] for f in federacoes}, "Falta admin ativo e vinculado em alguma federação.")
        totais = {}
        for federacao in federacoes:
            slug = federacao["slug"]
            if slug not in tokens:
                email = f"{slug}@teste.local"
                resposta = httpx.post(
                    f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
                    headers={"apikey": settings.SUPABASE_ANON_KEY},
                    json={"email": email, "password": os.getenv("DEMO_SENHA", "demo1234")}, timeout=15,
                )
                conferir(resposta.status_code == 200, f"Login de {slug} falhou.")
                tokens[slug] = {"Authorization": f"Bearer {resposta.json()['access_token']}"}
            sessao = get("/api/v1/admin/sessao", slug)
            conferir(sessao["papel"] == "admin" and sessao["federacao_id"] == federacao["id"],
                     f"Conta de {slug} sem vínculo administrativo correto.")
            conferir(get("/api/v1/federacao/minha", slug)["slug"] == slug, f"Marca incorreta para {slug}.")
            pagina = get("/api/v1/empresas?page_size=1", slug)
            totais[slug] = pagina["meta"]["total"]
            conferir(totais[slug] > 0, f"{slug} não tem EJs visíveis.")
        conferir(sum(totais.values()) == 1507, "Total nacional por tenant difere das 1.507 EJs da planilha.")
        print("OK: 27 contas admin autenticadas, vinculadas e com dados de sua federação; 1.507 EJs no total.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, httpx.HTTPError) as exc:
        raise SystemExit(f"Falha na verificação da demo: {exc}") from None
