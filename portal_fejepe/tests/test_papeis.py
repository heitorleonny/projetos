"""
Testes de papel (`admin` / `membro`) e do filtro de tenant no caminho de request.

A regra que estes testes existem para fixar, e que vale mais que todas as
outras deste arquivo:

    PAPEL NUNCA AMPLIA TENANT.

Um admin da federação 12 continua sem alcançar dado da federação 4. A checagem
de papel roda DEPOIS que o tenant já delimitou o conjunto — nunca no lugar dela.
Se um dia alguém "resolver" um chamado de suporte dando admin para alguém ver
dado de outra federação, é aqui que a suíte vai gritar.

Organização, no mesmo padrão de tests/test_seguranca.py:

    TestBugCondition*   comportamento novo que precisa passar a funcionar.
    TestPreservacao*    comportamento antigo que não pode quebrar.

O Supabase é mockado via `app.dependency_overrides[get_supabase]`, como no
resto da suíte: nada aqui fala com a rede.
"""

import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.dependencies import (
    HIERARQUIA_PAPEIS,
    PAPEL_PADRAO,
    get_current_user,
    get_federacao_id,
    get_papel,
    get_supabase,
    require_papel,
)
from app.main import app
from tests.test_seguranca import (
    CLUSTER_HISTORICO,
    EMPRESAS,
    METAS,
    MONITORAMENTOS,
    TOKEN_VALIDO,
    RespostaAuthFake,
    UsuarioFake,
)

FEJEPE = 12
FEJEPAR = 4

AUTH = {"Authorization": f"Bearer {TOKEN_VALIDO}"}


# ── Mock que registra os filtros aplicados ───────────────────


class ConsultaEspia:
    """
    Query builder falso que ANOTA cada filtro aplicado.

    Serve para verificar não só o resultado, mas o caminho: queremos saber que
    a consulta saiu com `federacao_id = <tenant do token>`, e não apenas que os
    dados mockados voltaram.
    """

    def __init__(self, dados: list[dict], registro: list[tuple]):
        self._dados = dados
        self.registro = registro

    def select(self, *args, **kwargs):
        return self

    def eq(self, campo=None, valor=None, *args, **kwargs):
        self.registro.append(("eq", campo, valor))
        return self

    def in_(self, campo=None, valores=None, *args, **kwargs):
        self.registro.append(("in_", campo, tuple(valores or ())))
        return self

    def ilike(self, *args, **kwargs):
        return self

    def lte(self, *args, **kwargs):
        return self

    def lt(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        resposta = MagicMock()
        resposta.data = self._dados
        return resposta


def _mock_supabase(usuario: UsuarioFake) -> tuple[MagicMock, list[tuple]]:
    """Cliente Supabase mockado que autentica `usuario` e registra os filtros."""
    registro: list[tuple] = []
    dados = {
        "empresa_junior": EMPRESAS,
        "monitoramento": MONITORAMENTOS,
        "metas": METAS,
        "cluster_historico": CLUSTER_HISTORICO,
    }

    mock_sb = MagicMock()
    mock_sb.table = lambda nome: ConsultaEspia(dados.get(nome, []), registro)

    def get_user(token: str | None = None):
        if token != TOKEN_VALIDO:
            raise Exception("Invalid JWT")
        return RespostaAuthFake(usuario)

    mock_sb.auth.get_user = get_user
    return mock_sb, registro


@pytest.fixture
def cliente_para():
    """
    Fábrica de TestClient autenticado como um usuário com papel/tenant dados.

    Devolve `(client, registro_de_filtros)`.
    """
    criados = []

    def _criar(federacao_id: int | None = FEJEPE, papel: str | None = "membro"):
        mock_sb, registro = _mock_supabase(UsuarioFake(federacao_id=federacao_id, papel=papel))
        app.dependency_overrides[get_supabase] = lambda: mock_sb
        client = TestClient(app)
        criados.append(client)
        return client, registro

    yield _criar
    app.dependency_overrides.clear()


def _app_com_rotas_de_papel(mock_sb) -> FastAPI:
    """
    App mínima com uma rota por papel mínimo.

    Os routers de hoje são todos de leitura, então `require_papel("admin")` não
    tem onde ser exercido no app real. Estas rotas existem para testar a
    dependência agora, antes de a primeira rota de escrita ser escrita.
    """
    app_teste = FastAPI()

    @app_teste.get("/so-membro", dependencies=[Depends(require_papel("membro"))])
    def _so_membro():
        return {"ok": True}

    @app_teste.get("/so-admin", dependencies=[Depends(require_papel("admin"))])
    def _so_admin():
        return {"ok": True}

    app_teste.dependency_overrides[get_supabase] = lambda: mock_sb
    return app_teste


# ══════════════════════════════════════════════════════════════
# EXPLORAÇÃO — Property 1: papel não amplia tenant
# ══════════════════════════════════════════════════════════════


class TestBugConditionPapelNaoAmpliaTenant:
    """Property 1 — o tenant do token delimita, o papel não mexe nisso."""

    @pytest.mark.parametrize("papel", ["membro", "admin"])
    def test_consulta_sai_filtrada_pelo_tenant_do_token(self, cliente_para, papel):
        """A consulta a `empresa_junior` carrega o federacao_id de quem pediu."""
        client, registro = cliente_para(federacao_id=FEJEPE, papel=papel)
        assert client.get("/api/v1/empresas", headers=AUTH).status_code == 200
        assert ("eq", "federacao_id", FEJEPE) in registro, (
            f"papel {papel!r}: a consulta saiu sem o filtro de tenant"
        )

    @pytest.mark.parametrize("papel", ["membro", "admin"])
    def test_nenhum_papel_consulta_outro_tenant(self, cliente_para, papel):
        """Nenhum filtro jamais aponta para a federação de outro."""
        client, registro = cliente_para(federacao_id=FEJEPE, papel=papel)
        client.get("/api/v1/empresas", headers=AUTH)
        client.get("/api/v1/rede/indicadores", headers=AUTH)
        client.get("/api/v1/empresas/101", headers=AUTH)

        tenants_consultados = {valor for verbo, campo, valor in registro if campo == "federacao_id"}
        assert tenants_consultados == {FEJEPE}, (
            f"papel {papel!r} consultou tenants {tenants_consultados}"
        )

    def test_admin_de_outro_tenant_consulta_o_proprio(self, cliente_para):
        """Trocando o tenant do token, o filtro acompanha — sem vazar o anterior."""
        client, registro = cliente_para(federacao_id=FEJEPAR, papel="admin")
        client.get("/api/v1/empresas", headers=AUTH)
        assert ("eq", "federacao_id", FEJEPAR) in registro
        assert ("eq", "federacao_id", FEJEPE) not in registro

    def test_o_tenant_vem_do_token_e_nao_da_query_string(self, cliente_para):
        """Tentar passar `federacao_id` na URL não muda o tenant consultado."""
        client, registro = cliente_para(federacao_id=FEJEPE, papel="admin")
        client.get("/api/v1/empresas?federacao_id=4", headers=AUTH)
        tenants = {valor for _, campo, valor in registro if campo == "federacao_id"}
        assert tenants == {FEJEPE}

    @pytest.mark.parametrize("rota", ["/api/v1/rede/ranking", "/api/v1/rede/sde", "/api/v1/rede/ritmo-mensal"])
    def test_rotas_da_rede_tambem_filtram(self, cliente_para, rota):
        """O recorte de tenant vale para os agregados, não só para a listagem."""
        client, registro = cliente_para(federacao_id=FEJEPE, papel="membro")
        assert client.get(rota, headers=AUTH).status_code == 200
        assert ("eq", "federacao_id", FEJEPE) in registro


# ══════════════════════════════════════════════════════════════
# EXPLORAÇÃO — Property 2: require_papel separa os dois papéis
# ══════════════════════════════════════════════════════════════


class TestBugConditionRequirePapel:
    """Property 2 — `admin` alcança o que é de admin; `membro`, não."""

    def _client(self, papel):
        mock_sb, _ = _mock_supabase(UsuarioFake(federacao_id=FEJEPE, papel=papel))
        return TestClient(_app_com_rotas_de_papel(mock_sb))

    def test_admin_alcanca_rota_de_admin(self):
        assert self._client("admin").get("/so-admin", headers=AUTH).status_code == 200

    def test_membro_nao_alcanca_rota_de_admin(self):
        resposta = self._client("membro").get("/so-admin", headers=AUTH)
        assert resposta.status_code == 403
        assert "admin" in resposta.json()["detail"]

    @pytest.mark.parametrize("papel", ["membro", "admin"])
    def test_os_dois_papeis_alcancam_rota_de_membro(self, papel):
        assert self._client(papel).get("/so-membro", headers=AUTH).status_code == 200

    def test_token_sem_papel_vale_como_membro(self):
        """
        Enquanto o hook de access token não for ativado no Supabase, NENHUM
        token traz papel. O default precisa ser o papel fraco: lê, não escreve.
        """
        client = self._client(None)
        assert client.get("/so-membro", headers=AUTH).status_code == 200
        assert client.get("/so-admin", headers=AUTH).status_code == 403

    def test_papel_desconhecido_nao_vira_admin(self):
        """Nome antigo ou errado (`gestor`, `visualizador`) cai no papel fraco."""
        for papel in ("gestor", "visualizador", "admin_federacao", "superadmin", ""):
            client = self._client(papel)
            assert client.get("/so-admin", headers=AUTH).status_code == 403, papel
            assert client.get("/so-membro", headers=AUTH).status_code == 200, papel

    def test_sem_token_e_401_e_nao_403(self):
        """Autenticação vem antes de autorização: sem token, 401."""
        assert self._client("admin").get("/so-admin").status_code == 401

    def test_token_invalido_e_401_e_nao_403(self):
        client = self._client("admin")
        resposta = client.get("/so-admin", headers={"Authorization": "Bearer token.errado"})
        assert resposta.status_code == 401

    def test_papel_minimo_desconhecido_falha_na_montagem(self):
        """Erro de digitação em `require_papel` estoura no import, não em produção."""
        with pytest.raises(ValueError):
            require_papel("gestor")


# ══════════════════════════════════════════════════════════════
# EXPLORAÇÃO — Property 3: leitura do claim de tenant
# ══════════════════════════════════════════════════════════════


class TestBugConditionClaimDeTenant:
    """Property 3 — `get_federacao_id` lê o claim, e só o claim."""

    def test_le_o_claim_como_inteiro(self):
        assert get_federacao_id(UsuarioFake(federacao_id=FEJEPE)) == FEJEPE

    def test_aceita_claim_em_texto(self):
        """O hook pode gravar o valor como string; o tipo não pode importar."""
        usuario = UsuarioFake()
        usuario.app_metadata["federacao_id"] = "12"
        assert get_federacao_id(usuario) == 12

    def test_sem_claim_devolve_none(self, monkeypatch):
        monkeypatch.setattr(settings, "TENANT_CLAIM_OBRIGATORIO", False)
        assert get_federacao_id(UsuarioFake(federacao_id=None)) is None

    def test_sem_claim_com_flag_ligada_e_403(self, monkeypatch):
        """Depois que o hook for ativado, token sem tenant deixa de ser tolerado."""
        from fastapi import HTTPException

        monkeypatch.setattr(settings, "TENANT_CLAIM_OBRIGATORIO", True)
        with pytest.raises(HTTPException) as erro:
            get_federacao_id(UsuarioFake(federacao_id=None))
        assert erro.value.status_code == 403

    def test_claim_ilegivel_e_sempre_403(self, monkeypatch):
        """Claim presente mas torto é recusado mesmo com a flag desligada."""
        from fastapi import HTTPException

        monkeypatch.setattr(settings, "TENANT_CLAIM_OBRIGATORIO", False)
        usuario = UsuarioFake()
        usuario.app_metadata["federacao_id"] = "doze"
        with pytest.raises(HTTPException) as erro:
            get_federacao_id(usuario)
        assert erro.value.status_code == 403

    def test_usuario_sem_app_metadata_nao_estoura(self, monkeypatch):
        """Usuário vindo de um token antigo, sem `app_metadata`, não quebra a API."""
        monkeypatch.setattr(settings, "TENANT_CLAIM_OBRIGATORIO", False)

        class UsuarioAntigo:
            id = "sem-metadata"

        assert get_federacao_id(UsuarioAntigo()) is None
        assert get_papel(UsuarioAntigo()) == PAPEL_PADRAO


# ══════════════════════════════════════════════════════════════
# EXPLORAÇÃO — Property 4: a service key não entra no request
# ══════════════════════════════════════════════════════════════


class TestBugConditionServiceKeyForaDoRequest:
    """
    Property 4 — a chave que ignora RLS não aparece no caminho de requisição.

    Este é um teste de código-fonte, não de comportamento, e é de propósito: o
    estrago de usar a service key num router não aparece em teste funcional
    nenhum — tudo continua respondendo 200. O que muda é que as políticas
    param de filtrar, silenciosamente.
    """

    PROIBIDOS = ("SUPABASE_SERVICE_KEY", "get_supabase_admin", "service_role")

    def _arquivos_do_caminho_de_request(self):
        raiz = Path(__file__).resolve().parent.parent / "app"
        return sorted((raiz / "routers").rglob("*.py")) + sorted((raiz / "services").rglob("*.py"))

    def test_nenhum_router_ou_service_usa_a_service_key(self):
        ofensores = []
        for arquivo in self._arquivos_do_caminho_de_request():
            conteudo = arquivo.read_text(encoding="utf-8")
            for linha_num, linha in enumerate(conteudo.splitlines(), start=1):
                if linha.lstrip().startswith("#"):
                    continue  # comentário explicando a regra não é uso
                if any(proibido in linha for proibido in self.PROIBIDOS):
                    ofensores.append(f"{arquivo.name}:{linha_num}: {linha.strip()}")
        assert ofensores == [], "service key no caminho de request:\n" + "\n".join(ofensores)

    def test_a_chave_anonima_e_a_usada_na_criacao_do_cliente(self):
        """`get_supabase` constrói com a anônima — nunca com a de serviço."""
        import inspect

        from app import dependencies

        fonte = inspect.getsource(dependencies.get_supabase)
        assert "SUPABASE_ANON_KEY" in fonte
        assert "SUPABASE_SERVICE_KEY" not in fonte


# ══════════════════════════════════════════════════════════════
# PRESERVAÇÃO — o que não pode ter quebrado
# ══════════════════════════════════════════════════════════════


class TestPreservacaoLeituraAutenticada:
    """Property 5 — o usuário legítimo continua lendo o que lia."""

    ROTAS_DE_LEITURA = [
        "/api/v1/empresas",
        "/api/v1/empresas/101",
        "/api/v1/empresas/comparar?ids=101&ids=102",
        "/api/v1/rede/indicadores",
        "/api/v1/rede/ritmo-mensal",
        "/api/v1/rede/sde",
        "/api/v1/rede/ranking",
        "/api/v1/eventos",
    ]

    @pytest.mark.parametrize("rota", ROTAS_DE_LEITURA)
    @pytest.mark.parametrize("papel", ["membro", "admin"])
    def test_leitura_exige_apenas_membro(self, cliente_para, rota, papel):
        """GET pede `membro`: exigir `admin` para ler seria regressão."""
        client, _ = cliente_para(federacao_id=FEJEPE, papel=papel)
        resposta = client.get(rota, headers=AUTH)
        assert resposta.status_code == 200, f"{rota} com papel {papel!r} → {resposta.status_code}"

    @pytest.mark.parametrize("rota", ROTAS_DE_LEITURA)
    def test_leitura_segue_funcionando_sem_claim_nenhum(self, cliente_para, rota, monkeypatch):
        """
        Enquanto o hook não é ativado, os tokens reais não têm nem tenant nem
        papel. A API não pode trancar todo mundo para fora nesse meio-tempo.
        """
        monkeypatch.setattr(settings, "TENANT_CLAIM_OBRIGATORIO", False)
        client, registro = cliente_para(federacao_id=None, papel=None)
        assert client.get(rota, headers=AUTH).status_code == 200
        assert [r for r in registro if r[1] == "federacao_id"] == []

    def test_valores_do_baseline_preservados(self, cliente_para):
        """Os números da listagem não mudaram com a entrada do filtro de tenant."""
        client, _ = cliente_para(federacao_id=FEJEPE, papel="admin")
        dados = client.get("/api/v1/empresas", headers=AUTH).json()
        assert dados["meta"]["total"] == 2
        alpha = dados["data"][0]
        assert alpha["faturamento_acumulado"] == 20_000.0
        assert alpha["csat_medio"] == 4.65
        assert alpha["percentual_meta"] == 16.67
        assert alpha["cluster_calculado"] == 4

    def test_health_continua_publico(self, cliente_para):
        client, _ = cliente_para()
        assert client.get("/health").status_code == 200


class TestPreservacaoContratoDosPapeis:
    """Property 6 — o vocabulário de papéis não pode escorregar."""

    def test_existem_exatamente_dois_papeis(self):
        assert sorted(HIERARQUIA_PAPEIS) == ["admin", "membro"]

    def test_admin_e_mais_forte_que_membro(self):
        assert HIERARQUIA_PAPEIS["admin"] > HIERARQUIA_PAPEIS["membro"]

    def test_o_papel_padrao_e_o_mais_fraco(self):
        assert PAPEL_PADRAO == min(HIERARQUIA_PAPEIS, key=HIERARQUIA_PAPEIS.get)

    def test_nomes_antigos_nao_voltaram_ao_codigo(self):
        """`gestor`, `visualizador` e `admin_federacao` saíram de circulação."""
        raiz = Path(__file__).resolve().parent.parent / "app"
        ofensores = []
        for arquivo in sorted(raiz.rglob("*.py")):
            for num, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), start=1):
                if linha.lstrip().startswith("#"):
                    continue  # o comentário que proíbe os nomes precisa citá-los
                if any(antigo in linha for antigo in ("admin_federacao", "'gestor'", '"gestor"', "visualizador")):
                    ofensores.append(f"{arquivo.name}:{num}")
        assert ofensores == [], f"papel de vocabulário antigo em {ofensores}"


class TestPreservacaoClienteSupabase:
    """Property 7 — o cliente deixou de ser singleton, e carrega o token."""

    def test_cada_requisicao_recebe_um_cliente_novo(self):
        """
        Dois clientes compartilhados carregariam o token de quem chegou antes —
        com RLS ligada, isso é vazamento entre federações.
        """
        from app.dependencies import _bearer_scheme  # noqa: F401  (documenta a origem)

        credenciais_a = MagicMock(scheme="Bearer", credentials="token-a")
        credenciais_b = MagicMock(scheme="Bearer", credentials="token-b")

        primeiro = get_supabase(credenciais_a)
        segundo = get_supabase(credenciais_b)
        assert primeiro is not segundo

    def test_o_token_do_usuario_e_aplicado_ao_postgrest(self, monkeypatch):
        """Sem `postgrest.auth(token)`, as políticas não recebem claim nenhum."""
        import app.dependencies as dependencies

        cliente_falso = MagicMock()
        monkeypatch.setattr(dependencies, "create_client", lambda url, key: cliente_falso)

        credenciais = MagicMock(scheme="Bearer", credentials="token-do-usuario")
        dependencies.get_supabase(credenciais)

        cliente_falso.postgrest.auth.assert_called_once_with("token-do-usuario")

    def test_sem_credenciais_nao_aplica_token(self, monkeypatch):
        import app.dependencies as dependencies

        cliente_falso = MagicMock()
        monkeypatch.setattr(dependencies, "create_client", lambda url, key: cliente_falso)

        dependencies.get_supabase(None)
        cliente_falso.postgrest.auth.assert_not_called()
