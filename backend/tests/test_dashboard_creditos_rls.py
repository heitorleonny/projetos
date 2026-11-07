"""Os clientes não conseguem contornar o débito atômico do dashboard."""

import json
from uuid import uuid4

import pytest

from tests.test_rls import DSN_APP, lab

psycopg = pytest.importorskip("psycopg")


def test_reserva_interna_nao_e_executavel_por_usuario_autenticado(lab):
    with psycopg.connect(DSN_APP, connect_timeout=3) as conexao:
        with conexao.cursor() as cur:
            cur.execute(
                "SELECT has_function_privilege(current_user, "
                "'public.reservar_creditos_ia(bigint,uuid,text,integer)', 'EXECUTE')"
            )
            assert cur.fetchone()[0] is False


@pytest.mark.parametrize(
    "comando",
    [
        "INSERT INTO dashboard_evento_ia "
        "(federacao_id,criado_por,evento_id,titulo,plano) "
        "VALUES (1,gen_random_uuid(),'teste','Teste','{}'::jsonb)",
        "UPDATE dashboard_evento_ia SET publico=false",
    ],
)
def test_usuario_autenticado_nao_escreve_diretamente_na_tabela(lab, comando):
    with psycopg.connect(DSN_APP, connect_timeout=3) as conexao:
        with conexao.cursor() as cur:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cur.execute(comando)


def test_persistir_dashboard_consumo_atomico_com_jwt_de_admin(lab):
    federacao_id = 991_901
    usuario_id = uuid4()
    claims = json.dumps({
        "sub": str(usuario_id),
        "federacao_id": federacao_id,
        "papel": "admin",
    })
    plano = {
        "titulo": "Faturamento set-out",
        "metrica": "faturamento_mes",
        "agregacao": "soma",
        "dimensao": "ej",
        "visualizacao": "ranking",
        "ano": 2026,
        "mes_inicio": 9,
        "mes_fim": 10,
        "limite": 10,
    }
    try:
        with lab.cursor() as cur:
            cur.execute(
                "INSERT INTO federacao (id,slug,nome,uf) VALUES (%s,%s,%s,'PE')",
                (federacao_id, f"dashboard-ia-{federacao_id}", "Federação de teste"),
            )
            cur.execute("INSERT INTO auth.users (id,email) VALUES (%s,%s)",
                        (usuario_id, f"{usuario_id}@teste.local"))
            cur.execute(
                "INSERT INTO usuario (federacao_id,nome,email,papel,auth_user_id) "
                "VALUES (%s,'Gestor teste',%s,'admin',%s)",
                (federacao_id, f"{usuario_id}@teste.local", usuario_id),
            )
        lab.commit()

        with psycopg.connect(DSN_APP, connect_timeout=3) as conexao:
            with conexao.cursor() as cur:
                cur.execute("SELECT set_config('request.jwt.claims',%s,true)", (claims,))
                cur.execute(
                    "SELECT id FROM public.persistir_dashboard_evento_ia(%s,%s,%s::jsonb,false,NULL)",
                    ("evento-teste", plano["titulo"], json.dumps(plano)),
                )
                assert cur.fetchone()[0] is not None

        with lab.cursor() as cur:
            cur.execute(
                "SELECT consumidos,reservados,cota FROM ia_creditos_mes WHERE federacao_id=%s",
                (federacao_id,),
            )
            assert cur.fetchone() == (1, 0, 100)
            cur.execute(
                "SELECT estado FROM ia_creditos_reserva WHERE federacao_id=%s",
                (federacao_id,),
            )
            assert cur.fetchone() == ("consumida",)
    finally:
        with lab.cursor() as cur:
            cur.execute("DELETE FROM ia_creditos_reserva WHERE federacao_id=%s", (federacao_id,))
            cur.execute("DELETE FROM ia_creditos_mes WHERE federacao_id=%s", (federacao_id,))
            cur.execute("DELETE FROM usuario WHERE federacao_id=%s", (federacao_id,))
            cur.execute("DELETE FROM auth.users WHERE id=%s", (usuario_id,))
            cur.execute("DELETE FROM federacao WHERE id=%s", (federacao_id,))
        lab.commit()
