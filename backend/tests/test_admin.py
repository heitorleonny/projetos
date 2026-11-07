"""
Testes do router do painel administrativo (`/api/v1/admin`).

Com mock, como o resto da suíte: o que se verifica aqui é o que o ROUTER
decide antes de chegar ao banco — quem entra, que escopo cada papel pode pedir,
que erro volta. O que o banco decide (RLS) está em tests/test_rls_painel_admin.py.

A sessão (papel e federação) vem de `admin_service.usuario_atual`, que em
produção lê `public.usuario_atual()`. É ela que se troca em cada cenário.
"""

import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")

import io
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.dependencies import get_current_user, get_supabase
from app.ingestao.contrato import ErroContrato
from app.ingestao.importacao import Escopo
from app.main import app
from app.services import admin_service, convite_service, importacao_service

FEJEPE, FEJEPAR = 12, 4
AUTH = {"Authorization": "Bearer token-de-teste"}

PLATAFORMA = {"id": 1, "federacao_id": FEJEPE, "papel": "plataforma", "nome": "Op", "email": "op@x.invalid"}
ADMIN = {"id": 2, "federacao_id": FEJEPE, "papel": "admin", "nome": "Adm", "email": "adm@x.invalid"}
MEMBRO = {"id": 3, "federacao_id": FEJEPE, "papel": "membro", "nome": "Mem", "email": "mem@x.invalid"}


def _usuario(id_=10, **extra) -> dict:
    return {
        "id": id_, "federacao_id": FEJEPE, "federacao_nome": "FEJEPE", "nome": "Fulana",
        "email": "fulana@x.invalid", "papel": "membro", "ativo": True, "conta_principal": False,
        "vinculado": True, "ultimo_login": datetime(2026, 9, 28, tzinfo=timezone.utc).isoformat(),
        "criado_em": datetime(2026, 9, 1, tzinfo=timezone.utc).isoformat(), **extra,
    }


@pytest.fixture
def cliente(monkeypatch):
    """Cliente HTTP cuja sessão é trocada por `cliente.como(<linha de usuario>)`."""
    app.dependency_overrides[get_current_user] = lambda: MagicMock()
    app.dependency_overrides[get_supabase] = lambda: MagicMock()
    estado = {"sessao": None}
    monkeypatch.setattr(admin_service, "usuario_atual", lambda sb: estado["sessao"])

    c = TestClient(app)
    c.como = lambda linha: estado.__setitem__("sessao", linha)
    yield c
    app.dependency_overrides.clear()


# ── Sessão e acesso ──────────────────────────────────────────


class TestAcesso:
    def test_sem_token_e_401(self):
        app.dependency_overrides.clear()
        assert TestClient(app).get("/api/v1/admin/sessao").status_code == 401

    def test_sessao_sem_vinculo_nao_administra(self, cliente):
        resposta = cliente.get("/api/v1/admin/sessao", headers=AUTH)
        assert resposta.status_code == 200
        assert resposta.json()["pode_administrar"] is False

    @pytest.mark.parametrize("linha,esperado", [(ADMIN, (True, False)), (PLATAFORMA, (True, True)), (MEMBRO, (False, False))])
    def test_sessao_por_papel(self, cliente, linha, esperado):
        cliente.como(linha)
        corpo = cliente.get("/api/v1/admin/sessao", headers=AUTH).json()
        assert (corpo["pode_administrar"], corpo["eh_plataforma"]) == esperado

    @pytest.mark.parametrize("rota", ["/api/v1/admin/usuarios", "/api/v1/admin/federacoes", "/api/v1/admin/importacoes"])
    def test_membro_nao_entra(self, cliente, rota):
        cliente.como(MEMBRO)
        assert cliente.get(rota, headers=AUTH).status_code == 403

    def test_usuario_sem_vinculo_nao_entra(self, cliente):
        assert cliente.get("/api/v1/admin/usuarios", headers=AUTH).status_code == 403


# ── Federações ───────────────────────────────────────────────


class TestFederacoes:
    def test_admin_nao_edita_federacao(self, cliente):
        cliente.como(ADMIN)
        resposta = cliente.patch(f"/api/v1/admin/federacoes/{FEJEPE}", json={"status": "inativa"}, headers=AUTH)
        assert resposta.status_code == 403

    def test_plataforma_edita_so_o_que_veio(self, cliente, monkeypatch):
        cliente.como(PLATAFORMA)
        chamada = {}

        def atualizar(sb, federacao_id, dados):
            chamada.update(federacao_id=federacao_id, dados=dados)
            return {"id": federacao_id, "slug": "fejepar", "nome": "FEJEPAR", "uf": "PR", "status": "piloto"}

        monkeypatch.setattr(admin_service, "atualizar_federacao", atualizar)
        resposta = cliente.patch(f"/api/v1/admin/federacoes/{FEJEPAR}", json={"status": "piloto"}, headers=AUTH)
        assert resposta.status_code == 200
        assert chamada == {"federacao_id": FEJEPAR, "dados": {"status": "piloto"}}

    def test_cor_fora_do_formato_e_422(self, cliente):
        cliente.como(PLATAFORMA)
        resposta = cliente.patch(f"/api/v1/admin/federacoes/{FEJEPAR}", json={"cor_primaria": "azul"}, headers=AUTH)
        assert resposta.status_code == 422

    def test_slug_nao_e_editavel(self, cliente, monkeypatch):
        """Campo desconhecido é ignorado pelo schema — e o corpo fica vazio."""
        cliente.como(PLATAFORMA)
        resposta = cliente.patch(f"/api/v1/admin/federacoes/{FEJEPAR}", json={"slug": "outro"}, headers=AUTH)
        assert resposta.status_code == 422

    def test_federacao_invisivel_e_404(self, cliente, monkeypatch):
        cliente.como(PLATAFORMA)
        monkeypatch.setattr(admin_service, "atualizar_federacao", lambda *a: None)
        resposta = cliente.patch("/api/v1/admin/federacoes/999", json={"status": "ativa"}, headers=AUTH)
        assert resposta.status_code == 404


# ── Usuários ─────────────────────────────────────────────────


class TestUsuarios:
    def test_lista_com_ultimo_login(self, cliente, monkeypatch):
        cliente.como(ADMIN)
        monkeypatch.setattr(admin_service, "listar_usuarios", lambda sb, fed: [_usuario()])
        corpo = cliente.get("/api/v1/admin/usuarios", headers=AUTH).json()
        assert corpo[0]["ultimo_login"].startswith("2026-09-28")

    def test_ninguem_muda_o_proprio_papel(self, cliente):
        cliente.como(ADMIN)
        resposta = cliente.patch(f"/api/v1/admin/usuarios/{ADMIN['id']}", json={"papel": "membro"}, headers=AUTH)
        assert resposta.status_code == 422

    def test_pode_mudar_o_proprio_nome(self, cliente, monkeypatch):
        cliente.como(ADMIN)
        monkeypatch.setattr(admin_service, "atualizar_usuario", lambda *a: True)
        monkeypatch.setattr(admin_service, "buscar_usuario", lambda sb, i: _usuario(i, papel="admin"))
        resposta = cliente.patch(f"/api/v1/admin/usuarios/{ADMIN['id']}", json={"nome": "Novo"}, headers=AUTH)
        assert resposta.status_code == 200

    def test_admin_nao_move_de_federacao(self, cliente):
        cliente.como(ADMIN)
        resposta = cliente.patch("/api/v1/admin/usuarios/10", json={"federacao_id": FEJEPAR}, headers=AUTH)
        assert resposta.status_code == 403

    def test_admin_nao_promove_a_plataforma(self, cliente):
        cliente.como(ADMIN)
        resposta = cliente.patch("/api/v1/admin/usuarios/10", json={"papel": "plataforma"}, headers=AUTH)
        assert resposta.status_code == 403

    def test_plataforma_move_de_federacao(self, cliente, monkeypatch):
        cliente.como(PLATAFORMA)
        gravado = {}
        monkeypatch.setattr(admin_service, "atualizar_usuario", lambda sb, i, d: gravado.update(d) or True)
        monkeypatch.setattr(admin_service, "buscar_usuario", lambda sb, i: _usuario(i, federacao_id=FEJEPAR))
        resposta = cliente.patch("/api/v1/admin/usuarios/10", json={"federacao_id": FEJEPAR}, headers=AUTH)
        assert resposta.status_code == 200
        assert gravado == {"federacao_id": FEJEPAR}

    def test_usuario_fora_do_alcance_e_404(self, cliente, monkeypatch):
        cliente.como(ADMIN)
        monkeypatch.setattr(admin_service, "atualizar_usuario", lambda *a: False)
        resposta = cliente.patch("/api/v1/admin/usuarios/10", json={"nome": "x"}, headers=AUTH)
        assert resposta.status_code == 404


class TestConvite:
    @pytest.fixture
    def convites(self, monkeypatch):
        feitos = []

        def convidar(sb, **kw):
            feitos.append(kw)
            return 77

        monkeypatch.setattr(convite_service, "convidar", convidar)
        monkeypatch.setattr(admin_service, "buscar_usuario", lambda sb, i: _usuario(i))
        return feitos

    def test_admin_convida_na_propria_federacao(self, cliente, convites):
        cliente.como(ADMIN)
        resposta = cliente.post("/api/v1/admin/usuarios", json={"nome": "N", "email": "n@x.com"}, headers=AUTH)
        assert resposta.status_code == 201
        assert convites[0]["federacao_id"] == FEJEPE

    def test_admin_nao_convida_em_outra_federacao(self, cliente, convites):
        cliente.como(ADMIN)
        resposta = cliente.post(
            "/api/v1/admin/usuarios", json={"nome": "N", "email": "n@x.com", "federacao_id": FEJEPAR}, headers=AUTH,
        )
        assert resposta.status_code == 403
        assert convites == []

    def test_admin_nao_convida_operador(self, cliente, convites):
        cliente.como(ADMIN)
        resposta = cliente.post(
            "/api/v1/admin/usuarios", json={"nome": "N", "email": "n@x.com", "papel": "plataforma"}, headers=AUTH,
        )
        assert resposta.status_code == 403

    def test_plataforma_precisa_dizer_a_federacao(self, cliente, convites):
        cliente.como(PLATAFORMA)
        resposta = cliente.post("/api/v1/admin/usuarios", json={"nome": "N", "email": "n@x.com"}, headers=AUTH)
        assert resposta.status_code == 422

    def test_email_ja_cadastrado_no_auth_e_409(self, cliente, monkeypatch):
        cliente.como(ADMIN)

        def falha(sb, **kw):
            raise convite_service.ErroConvite("já tem conta")

        monkeypatch.setattr(convite_service, "convidar", falha)
        resposta = cliente.post("/api/v1/admin/usuarios", json={"nome": "N", "email": "n@x.com"}, headers=AUTH)
        assert resposta.status_code == 409

    def test_convite_nao_configurado_e_503(self, cliente, monkeypatch):
        cliente.como(ADMIN)

        def indisponivel(*args, **kwargs):
            raise convite_service.ConviteIndisponivel("Envio de convites não configurado neste ambiente.")

        monkeypatch.setattr(convite_service, "convidar", indisponivel)
        resposta = cliente.post("/api/v1/admin/usuarios", json={"nome": "N", "email": "n@x.com"}, headers=AUTH)
        assert resposta.status_code == 503


class TestConviteService:
    """Convites agora são uma transação SQL; integração em test_auth_postgresql."""
    def test_sem_sessao_nao_cria_cadastro(self,monkeypatch):
        op=MagicMock();monkeypatch.setattr(convite_service,"operacao",op)
        with pytest.raises(convite_service.ErroConvite):
            convite_service.convidar(MagicMock(token=None),nome="N",email="n@x.com",papel="membro",federacao_id=FEJEPE)
        op.assert_not_called()

    def test_convite_usa_hashes_e_normaliza_email(self,monkeypatch):
        op=MagicMock(return_value=55);monkeypatch.setattr(convite_service,"operacao",op)
        sb=MagicMock(token="sessao-opaca")
        assert convite_service.convidar(sb,nome="N",email="N@X.com",papel="membro",federacao_id=FEJEPE)==55
        args=op.call_args.args
        assert args[0]=="portal_convidar" and args[1]!="sessao-opaca" and args[5]=="n@x.com"
        assert "#convite=" in sb.convite_url


# ── Importação ───────────────────────────────────────────────


class TestImportacao:
    ARQUIVO = {"arquivo": ("monitoring_acumulated_2026_1220260921-1-x.xlsx", io.BytesIO(b"PK\x03\x04"), "application/octet-stream")}

    @pytest.fixture
    def importacoes(self, monkeypatch):
        feitas = []
        relatorio = MagicMock()
        relatorio.para_json.return_value = {"simulacao": True}

        def importar(conteudo, nome, **kw):
            feitas.append({"nome": nome, **kw})
            return relatorio, "texto"

        monkeypatch.setattr(importacao_service, "importar_upload", importar)
        monkeypatch.setattr(admin_service, "slug_da_federacao", lambda sb, f: "fejepe")
        return feitas

    def _enviar(self, cliente, **dados):
        return cliente.post("/api/v1/admin/importacoes", data={"ano": "2026", **dados}, files=self.ARQUIVO, headers=AUTH)

    def test_admin_importa_a_propria_federacao_e_simula_por_padrao(self, cliente, importacoes):
        cliente.como(ADMIN)
        resposta = self._enviar(cliente)
        assert resposta.status_code == 200
        assert importacoes[0]["escopo"] == Escopo.federacao("fejepe")
        assert importacoes[0]["simular"] is True
        assert importacoes[0]["carregado_por"] == ADMIN["id"]

    def test_admin_nao_importa_outra_federacao(self, cliente, importacoes):
        cliente.como(ADMIN)
        assert self._enviar(cliente, federacao_slug="fejepar").status_code == 403
        assert importacoes == []

    def test_plataforma_sem_slug_e_nacional(self, cliente, importacoes):
        cliente.como(PLATAFORMA)
        assert self._enviar(cliente, simular="false").status_code == 200
        assert importacoes[0]["escopo"] == Escopo.nacional()
        assert importacoes[0]["simular"] is False

    def test_plataforma_recorta_por_federacao(self, cliente, importacoes):
        cliente.como(PLATAFORMA)
        self._enviar(cliente, federacao_slug=" FEJEPAR ")
        assert importacoes[0]["escopo"] == Escopo.federacao("fejepar")

    def test_planilha_fora_do_contrato_devolve_os_problemas(self, cliente, monkeypatch):
        cliente.como(ADMIN)
        monkeypatch.setattr(admin_service, "slug_da_federacao", lambda sb, f: "fejepe")

        def rejeita(*a, **kw):
            raise ErroContrato(["faltam as colunas: CSAT"])

        monkeypatch.setattr(importacao_service, "importar_upload", rejeita)
        resposta = self._enviar(cliente)
        assert resposta.status_code == 422
        assert resposta.json()["detail"]["problemas"] == ["faltam as colunas: CSAT"]

    def test_sem_dsn_e_503(self, cliente, monkeypatch):
        cliente.como(ADMIN)
        monkeypatch.setattr(admin_service, "slug_da_federacao", lambda sb, f: "fejepe")
        monkeypatch.setattr(settings, "INGESTAO_DSN", "")
        assert self._enviar(cliente).status_code == 503

    def test_arquivo_acima_do_limite_e_413(self, cliente, importacoes, monkeypatch):
        cliente.como(ADMIN)
        monkeypatch.setattr(settings, "UPLOAD_MAX_MB", 0)
        assert self._enviar(cliente).status_code == 413


class TestNomeSeguro:
    def test_preserva_a_data_da_exportacao(self):
        nome = "monitoring_acumulated_2026_1220260921-1-9ldcm9.xlsx"
        assert importacao_service.nome_seguro(nome) == nome

    def test_tira_diretorio(self):
        assert importacao_service.nome_seguro("../../etc/planilha.xlsx") == "planilha.xlsx"

    def test_recusa_o_que_nao_e_xlsx(self):
        with pytest.raises(importacao_service.ArquivoInvalido):
            importacao_service.nome_seguro("planilha.csv")


class TestMaster:
    @pytest.mark.parametrize('sessao', [ADMIN, MEMBRO, None])
    @pytest.mark.parametrize('metodo,caminho,corpo', [
        ('get', '/master/federacoes', None), ('get', '/master/planos', None),
        ('post', '/master/planos', {'nome': 'Plano'}),
        ('put', '/master/planos/1', {'nome': 'Plano'}),
        ('put', '/master/federacoes/12/plano', {'plano_id': 1}),
    ])
    def test_so_master_acessa(self, cliente, sessao, metodo, caminho, corpo):
        cliente.como(sessao)
        kwargs = {'headers': AUTH}
        if corpo is not None:
            kwargs['json'] = corpo
        assert getattr(cliente, metodo)('/api/v1/admin' + caminho, **kwargs).status_code == 403

    def test_resumo(self, cliente, monkeypatch):
        cliente.como(PLATAFORMA)
        linha = {'id': 12, 'nome': 'FEJEPE', 'uf': 'PE', 'status': 'ativa', 'plano_id': None,
                 'usuarios_total': 1500, 'usuarios_ativos': 1300, 'administradores': 2, 'usuarios_sem_vinculo': 1}
        monkeypatch.setattr(admin_service, 'resumo_master', lambda sb: [linha])
        assert cliente.get('/api/v1/admin/master/federacoes', headers=AUTH).json() == [linha]

    @pytest.mark.parametrize('campo,valor', [('limite_usuarios', -1), ('limite_creditos_ia_mes', 1000001), ('preco_mensal', -0.01), ('nome', '')])
    def test_valores_invalidos(self, cliente, campo, valor):
        cliente.como(PLATAFORMA)
        assert cliente.post('/api/v1/admin/master/planos', json={'nome': 'Teste', campo: valor}, headers=AUTH).status_code == 422

    def test_criar_editar_e_desvincular(self, cliente, monkeypatch):
        cliente.como(PLATAFORMA)
        salvar = MagicMock(side_effect=lambda sb, id, dados: {'id': id or 4, **dados})
        vincular = MagicMock()
        monkeypatch.setattr(admin_service, 'salvar_plano', salvar)
        monkeypatch.setattr(admin_service, 'vincular_plano', vincular)
        dados = {'nome': 'Teste', 'limite_usuarios': None, 'limite_creditos_ia_mes': 0, 'preco_mensal': 99}
        assert cliente.post('/api/v1/admin/master/planos', json=dados, headers=AUTH).status_code == 201
        assert cliente.put('/api/v1/admin/master/planos/4', json=dados, headers=AUTH).json()['id'] == 4
        assert cliente.put('/api/v1/admin/master/federacoes/12/plano', json={'plano_id': None}, headers=AUTH).status_code == 204
        assert vincular.call_args.args[1:] == (12, None)
