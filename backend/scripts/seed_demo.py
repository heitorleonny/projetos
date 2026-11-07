"""
Cria os usuários de teste do ambiente de DEMONSTRAÇÃO e prova que o hook funciona.

    cd backend
    python -m scripts.seed_demo

Ou, da raiz: `make demo-seed`.

O QUE ELE FAZ, NESTA ORDEM (a ordem importa):

  1. cria os usuários no Supabase Auth (GoTrue), via API de admin;
  2. grava a linha correspondente em `usuario`, com `auth_user_id`,
     `federacao_id` e `papel`;
  3. faz login com cada um e DECODIFICA o access_token, conferindo que
     `federacao_id` e `papel` chegaram nos claims.

O passo 3 não é enfeite. A função `public.custom_access_token_hook` existe
desde `06-usuario.sql`, mas só roda depois do gatilho ligado — aqui, em
`supabase/config.toml`. Token sem esses claims = hook desligado, e todo o
isolamento por federação vira teatro: a RLS não tem contra o que comparar.

E o passo 2 tem que vir antes do 3 porque o hook procura em `usuario`: se a
linha não existir, ele devolve o token intacto, sem tenant.

CONTAS DE REFERÊNCIA:

  um@teste.local   → FEJEPE, a federação de origem. Tudo tem que continuar
                     parecendo o que sempre foi.
  dois@teste.local → FEJEMG, a maior da base. É ela que expõe os limites
                     fixos de 100 EJs da divergência 9.17.
  op@teste.local   → papel `plataforma` (migração 13): abre o painel
                     administrativo com todas as federações.

O script cria ainda uma conta admin `<slug>@teste.local` para cada uma das
outras 25 federações do catálogo. Todos os endereços são exclusivos da demo.

Saída: 0 sucesso; 1 o ambiente respondeu mas algo não bate (inclusive claim
faltando no JWT); 2 uso errado ou stack inacessível.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import subprocess
import sys
from urllib.parse import urlsplit

import httpx
import psycopg

# Contas existentes da demonstração, preservadas para os roteiros de smoke.
# As demais federações são lidas do catálogo do banco por _usuarios_demo.
# `federacao_id` é sempre resolvido pelo slug, nunca inventado pelo script.
USUARIOS = (
    {
        "email": "um@teste.local",
        "nome": "Usuário Um (FEJEPE)",
        "slug_federacao": "fejepe",
        "papel": "admin",
    },
    {
        "email": "dois@teste.local",
        "nome": "Usuário Dois (FEJEMG)",
        "slug_federacao": "fejemg",
        "papel": "admin",
    },
    # O operador da plataforma (papel da migração 13). Vinculado à FEJEPE como
    # qualquer usuário — é o que ele vê no dashboard —, mas NÃO como conta
    # principal: essa é única por federação e já é de um@teste.local.
    {
        "email": "op@teste.local",
        "nome": "Operador da plataforma",
        "slug_federacao": "fejepe",
        "papel": "plataforma",
        "conta_principal": False,
    },
)

SENHA_PADRAO = "demo1234"  # desenvolvimento local; `minimum_password_length = 6`


class ErroDemo(RuntimeError):
    """O ambiente respondeu, mas não do jeito que deveria."""


# ── Descoberta da stack ─────────────────────────────────────────────────────


def _raiz_do_repo() -> pathlib.Path:
    """Onde mora o supabase/config.toml: dois níveis acima deste arquivo."""
    return pathlib.Path(__file__).resolve().parents[2]


def _status_da_cli(_projeto: str) -> dict:
    """Pergunta as URLs e chaves para a própria CLI, em vez de fixá-las aqui.

    As chaves locais mudam entre versões da CLI, e chutar o formato delas é o
    tipo de coisa que funciona hoje e quebra no `brew upgrade`.
    """
    try:
        saida = subprocess.run(
            # --workdir porque este script roda de backend/, e o
            # config.toml (que identifica o projeto) esta na raiz do repo.
            # `status` nao aceita --project-id; quem aceita e `stop`.
            ["supabase", "status", "-o", "json", "--workdir", str(_raiz_do_repo())],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        raise ErroDemo("a CLI do Supabase não está no PATH (brew install supabase/tap/supabase)")
    except subprocess.TimeoutExpired:
        raise ErroDemo("`supabase status` não respondeu em 60s; a stack está no ar?")

    if saida.returncode != 0:
        detalhe = (saida.stderr or saida.stdout).strip()
        raise ErroDemo(f"`supabase status` falhou. A stack está no ar (`make demo`)?\n{detalhe}")

    try:
        return json.loads(saida.stdout)
    except json.JSONDecodeError:
        raise ErroDemo(f"não entendi a saída de `supabase status`:\n{saida.stdout[:400]}")


def _campo(status: dict, *nomes: str) -> str:
    """Primeiro campo presente. A CLI já renomeou chaves entre versões."""
    for nome in nomes:
        valor = status.get(nome)
        if valor:
            return str(valor)
    raise ErroDemo(f"não achei nenhum de {nomes} na saída de `supabase status`; chaves: {sorted(status)}")


# ── Auth (GoTrue) ───────────────────────────────────────────────────────────


def _cabecalhos(chave: str) -> dict[str, str]:
    return {"apikey": chave, "Authorization": f"Bearer {chave}", "Content-Type": "application/json"}


def _procurar_usuario(cliente: httpx.Client, api: str, chave: str, email: str) -> str | None:
    """Devolve o auth_user_id de quem já existe, ou None."""
    resposta = cliente.get(
        f"{api}/auth/v1/admin/users",
        headers=_cabecalhos(chave),
        params={"per_page": 200},
    )
    resposta.raise_for_status()
    for usuario in resposta.json().get("users", []):
        if (usuario.get("email") or "").lower() == email.lower():
            return usuario["id"]
    return None


def _criar_usuario(cliente: httpx.Client, api: str, chave: str, email: str, senha: str) -> tuple[str, bool]:
    """Cria no Auth. Idempotente: se já existe, reaproveita e troca a senha.

    Devolve (auth_user_id, foi_criado_agora).
    """
    resposta = cliente.post(
        f"{api}/auth/v1/admin/users",
        headers=_cabecalhos(chave),
        json={"email": email, "password": senha, "email_confirm": True},
    )
    if resposta.status_code in (200, 201):
        return resposta.json()["id"], True

    # Já cadastrado: encontra e realinha a senha, para o login do passo 3
    # funcionar mesmo num ambiente reaproveitado.
    existente = _procurar_usuario(cliente, api, chave, email)
    if existente is None:
        raise ErroDemo(f"não criei nem encontrei {email}: HTTP {resposta.status_code} {resposta.text[:200]}")

    atualizacao = cliente.put(
        f"{api}/auth/v1/admin/users/{existente}",
        headers=_cabecalhos(chave),
        json={"password": senha, "email_confirm": True},
    )
    atualizacao.raise_for_status()
    return existente, False


def _login(cliente: httpx.Client, api: str, anon: str, email: str, senha: str) -> str:
    resposta = cliente.post(
        f"{api}/auth/v1/token",
        headers=_cabecalhos(anon),
        params={"grant_type": "password"},
        json={"email": email, "password": senha},
    )
    if resposta.status_code != 200:
        raise ErroDemo(f"login de {email} falhou: HTTP {resposta.status_code} {resposta.text[:200]}")
    return resposta.json()["access_token"]


def _claims(token: str) -> dict:
    """Decodifica o payload do JWT SEM validar assinatura.

    Aqui não se está autenticando ninguém — está se conferindo o que o GoTrue
    escreveu no token. Validar assinatura seria responder outra pergunta.
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)  # base64url sem padding
        return json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError) as erro:
        raise ErroDemo(f"não consegui decodificar o access_token: {erro}")


# ── Banco ───────────────────────────────────────────────────────────────────


def _gravar_usuario(conexao: psycopg.Connection, dados: dict, auth_user_id: str) -> int:
    """Insere (ou realinha) a linha de `usuario`. É ela que o hook consulta."""
    with conexao.cursor() as cursor:
        cursor.execute("SELECT id FROM federacao WHERE slug = %s", (dados["slug_federacao"],))
        linha = cursor.fetchone()
        if linha is None:
            raise ErroDemo(
                f"federação {dados['slug_federacao']!r} não existe. O schema foi aplicado (`make demo-schema`)?"
            )
        federacao_id = linha[0]

        # ON CONFLICT no e-mail: rodar o seed duas vezes não duplica nem falha.
        cursor.execute(
            """
            INSERT INTO usuario (federacao_id, nome, email, papel, conta_principal, ativo, auth_user_id)
            VALUES (%s, %s, %s, %s, %s, true, %s)
            ON CONFLICT (email) DO UPDATE
               SET federacao_id = EXCLUDED.federacao_id,
                   nome         = EXCLUDED.nome,
                   papel        = EXCLUDED.papel,
                   ativo        = true,
                   auth_user_id = EXCLUDED.auth_user_id,
                   updated_at   = now()
            """,
            (federacao_id, dados["nome"], dados["email"], dados["papel"],
             dados.get("conta_principal", True), auth_user_id),
        )
    return federacao_id


def _contar_ejs(conexao: psycopg.Connection, federacao_id: int) -> int:
    with conexao.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM empresa_junior WHERE federacao_id = %s", (federacao_id,))
        return cursor.fetchone()[0]


def _usuarios_demo(conexao: psycopg.Connection) -> list[dict]:
    """Um admin por federação; mantém as duas contas já usadas nos testes."""
    existentes = {u["slug_federacao"] for u in USUARIOS if u["papel"] == "admin"}
    with conexao.cursor() as cursor:
        cursor.execute("SELECT slug, nome FROM federacao ORDER BY slug")
        federacoes = cursor.fetchall()
    if len(federacoes) != 27:
        raise ErroDemo(f"esperava 27 federações no catálogo local; encontrei {len(federacoes)}")
    novos = [
        {"email": f"{slug}@teste.local", "nome": f"Admin de {nome}",
         "slug_federacao": slug, "papel": "admin"}
        for slug, nome in federacoes if slug not in existentes
    ]
    return [*USUARIOS, *novos]


# ── Orquestração ────────────────────────────────────────────────────────────


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.seed_demo",
        description="Cria os usuários de teste do ambiente de demonstração e confere os claims do JWT.",
    )
    parser.add_argument("--projeto", default="portal-fejepe-demo", help="project_id da stack local")
    parser.add_argument("--dsn", default=None, help="conexão Postgres (padrão: DEMO_DSN ou o postgres da stack)")
    parser.add_argument("--senha", default=os.getenv("DEMO_SENHA", SENHA_PADRAO), help="senha dos usuários de teste")
    parser.add_argument(
        "--sem-verificacao",
        action="store_true",
        help="pula o login e a conferência dos claims (não recomendado: é a prova de que o hook está ligado)",
    )
    return parser.parse_args(argv)


def principal(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)

    try:
        status = _status_da_cli(args.projeto)
    except ErroDemo as erro:
        print(f"{erro}", file=sys.stderr)
        return 2

    api = _campo(status, "API_URL")
    destino = urlsplit(api)
    if destino.hostname not in ("localhost", "127.0.0.1") or destino.port != 54421:
        print("O seed de contas de teste só pode rodar na demo local (:54421).", file=sys.stderr)
        return 2
    anon = _campo(status, "ANON_KEY", "PUBLISHABLE_KEY")
    servico = _campo(status, "SERVICE_ROLE_KEY", "SECRET_KEY")
    dsn = args.dsn or os.getenv("DEMO_DSN") or _campo(status, "DB_URL")

    print(f"Stack:  {api}")
    print(f"Banco:  {dsn.rsplit('@', 1)[-1]}")

    falhas: list[str] = []
    try:
        with httpx.Client(timeout=30) as cliente, psycopg.connect(dsn, autocommit=True) as conexao:
            for dados in _usuarios_demo(conexao):
                email = dados["email"]
                auth_user_id, criado = _criar_usuario(cliente, api, servico, email, args.senha)
                federacao_id = _gravar_usuario(conexao, dados, auth_user_id)
                ejs = _contar_ejs(conexao, federacao_id)
                marca = "criado" if criado else "já existia"
                print(
                    f"\n{email}  [{marca}]"
                    f"\n  federacao    : {dados['slug_federacao']} (id {federacao_id}), {ejs} EJs"
                    f"\n  papel        : {dados['papel']}"
                )

                if args.sem_verificacao:
                    continue

                # A prova: o que o GoTrue escreveu no token.
                claims = _claims(_login(cliente, api, anon, email, args.senha))
                no_topo = claims.get("federacao_id")
                no_metadata = (claims.get("app_metadata") or {}).get("federacao_id")
                papel = claims.get("papel") or (claims.get("app_metadata") or {}).get("papel")

                print(
                    f"  JWT          : federacao_id={no_topo!r} (topo), "
                    f"{no_metadata!r} (app_metadata), papel={papel!r}"
                )

                # O hook grava em DOIS lugares, e cada um tem um leitor: o topo
                # é lido pela RLS (07-rls-policies.sql), o app_metadata é lido
                # pelo backend (app/dependencies.py). Faltar um já quebra.
                if no_topo is None or no_metadata is None or papel is None:
                    falhas.append(f"{email}: claim faltando no JWT — o hook está ligado no config.toml?")
                elif int(no_topo) != federacao_id or int(no_metadata) != federacao_id:
                    falhas.append(f"{email}: JWT diz federacao_id {no_topo}/{no_metadata}, banco diz {federacao_id}")
                elif papel != dados["papel"]:
                    falhas.append(f"{email}: JWT diz papel {papel!r}, banco diz {dados['papel']!r}")

    except ErroDemo as erro:
        print(f"\n{erro}", file=sys.stderr)
        return 1
    except psycopg.OperationalError as erro:
        print(f"\nNão consegui conectar no banco da demo. A stack está no ar (`make demo`)?\n{erro}", file=sys.stderr)
        return 2
    except httpx.HTTPError as erro:
        print(f"\nA API da demo não respondeu como esperado: {erro}", file=sys.stderr)
        return 1

    if falhas:
        print("\nO ambiente subiu, mas o JWT não está certo:", file=sys.stderr)
        for falha in falhas:
            print(f"  - {falha}", file=sys.stderr)
        return 1

    if not args.sem_verificacao:
        print("\nHook confirmado: todos os tokens carregam federacao_id e papel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
