"""Consultas PostgreSQL do portal: parâmetros vinculados e RLS por transação."""
from types import SimpleNamespace
from datetime import date, datetime
from decimal import Decimal
import json
import re
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from postgrest.exceptions import APIError

TABELAS = {'empresa_junior', 'metas', 'monitoramento', 'cluster_historico', 'federacao', 'nucleo', 'plano', 'usuario', 'ingestao_carga', 'dashboard_evento_ia'}
RPCS = {'usuario_atual', 'admin_listar_usuarios', 'master_resumo_federacoes', 'master_salvar_plano', 'master_vincular_plano', 'definir_paleta_da_federacao', 'reservar_consulta_ia', 'consultar_creditos_dashboard_ia', 'persistir_dashboard_evento_ia', 'atualizar_publicacao_dashboard_evento_ia', 'dashboard_evento_publico'}
ESCALARES = {'reservar_consulta_ia', 'persistir_dashboard_evento_ia', 'master_vincular_plano'}


def identificador(nome):
    if not re.fullmatch(r'[a-z_][a-z_0-9]*', nome):
        raise ValueError('Identificador SQL inválido')
    return sql.Identifier(nome)


def normalizar_resultado(valor):
    """Preserva o contrato numérico JSON consumido pelos services existentes."""
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, dict):
        return {chave: normalizar_resultado(item) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [normalizar_resultado(item) for item in valor]
    return valor


class Client:
    def __init__(self, token=None):
        self.token = token
        self.auth = SimpleNamespace(get_user=self.get_user)
        self.postgrest = SimpleNamespace(auth=self.set_token)

    def set_token(self, token):
        self.token = token

    def get_user(self, token):
        from app.auth_native import autenticar
        return SimpleNamespace(user=autenticar(token))

    def table(self, nome):
        if nome not in TABELAS:
            raise ValueError('Tabela não permitida')
        return Consulta(self, nome)

    def rpc(self, nome, params=None):
        if nome not in RPCS:
            raise ValueError('Operação não permitida')
        return Consulta(self, nome, params or {})

    def executar(self, consulta):
        from app.config import settings
        claims = {}
        if self.token:
            user = self.get_user(self.token).user
            claims = {'sub': user.id, **user.app_metadata}
        try:
            with psycopg.connect(settings.DATABASE_DSN, row_factory=dict_row, connect_timeout=5) as conn:
                role = conn.execute('SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
                dono = conn.execute("SELECT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname='public' AND tableowner=current_user) AS dono").fetchone()['dono']
                if role['rolsuper'] or role['rolbypassrls'] or dono:
                    raise RuntimeError('A API exige papel sem privilégios de proprietário/BYPASSRLS')
                conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier('authenticated' if claims else 'anon')))
                conn.execute("SELECT set_config('request.jwt.claims', %s, true)", (json.dumps(claims),))
                conn.execute("SET LOCAL statement_timeout = '15s'")
                return consulta.executar_sql(conn)
        except psycopg.Error as exc:
            raise APIError({'code': exc.sqlstate or '08000', 'message': 'Operação de banco recusada ou indisponível.', 'details': None, 'hint': None}) from exc


class Consulta:
    def __init__(self, client, nome, params=None):
        self.client, self.nome, self.params = client, nome, params
        self.colunas, self.contagem = '*', None
        self.filtros, self.ordens = [], []
        self.inicio, self.quantidade, self.unica = 0, None, False
        self.operacao, self.dados = 'select', None

    def select(self, colunas='*', count=None):
        self.colunas, self.contagem = colunas, count
        return self

    def _filtro(self, coluna, operador, valor):
        self.filtros.append((coluna, operador, valor)); return self

    def eq(self, c, v): return self._filtro(c, '=', v)
    def neq(self, c, v): return self._filtro(c, '<>', v)
    def lte(self, c, v): return self._filtro(c, '<=', v)
    def gte(self, c, v): return self._filtro(c, '>=', v)
    def ilike(self, c, v): return self._filtro(c, 'ILIKE', v)
    def in_(self, c, v): return self._filtro(c, 'IN', list(v))
    def is_(self, c, v): return self._filtro(c, 'IS', v)
    def order(self, c, desc=False): self.ordens.append((c, desc)); return self
    def range(self, inicio, fim): self.inicio, self.quantidade = inicio, fim-inicio+1; return self
    def limit(self, n): self.quantidade = n; return self
    def maybe_single(self): self.unica = True; return self
    def single(self): self.unica = True; return self
    def insert(self, dados): self.operacao, self.dados = 'insert', dados; return self
    def update(self, dados): self.operacao, self.dados = 'update', dados; return self
    def delete(self): self.operacao = 'delete'; return self
    def execute(self): return self.client.executar(self)

    def executar_sql(self, conn):
        valores, partes = [], []
        for coluna, op, valor in self.filtros:
            c = identificador(coluna)
            if op == 'IN':
                partes.append(sql.SQL('{} = ANY(%s)').format(c)); valores.append(valor)
            elif op == 'IS':
                if valor not in (None, 'null', True, False): raise ValueError('Filtro inválido')
                partes.append(sql.SQL('{} IS {}').format(c, sql.SQL('NULL' if valor in (None, 'null') else str(valor).upper())))
            else:
                partes.append(sql.SQL('{} {} %s').format(c, sql.SQL(op))); valores.append(valor)
        where = sql.SQL(' WHERE ') + sql.SQL(' AND ').join(partes) if partes else sql.SQL('')
        cols = sql.SQL('*') if self.colunas == '*' else sql.SQL(',').join(identificador(c.strip()) for c in self.colunas.split(','))
        origem = sql.SQL('public.{}').format(identificador(self.nome))
        prefixo = []
        if self.params is not None:
            args = []
            for k, v in self.params.items():
                args.append(sql.SQL('{} => %s').format(identificador(k)))
                prefixo.append(Jsonb(v) if isinstance(v, (dict,list)) else v)
            origem += sql.SQL('({})').format(sql.SQL(',').join(args))
        if self.operacao == 'select':
            total = None
            if self.contagem:
                total = conn.execute(sql.SQL('SELECT count(*) AS n FROM {}').format(origem)+where, prefixo+valores).fetchone()['n']
            query = sql.SQL('SELECT {} FROM {}').format(cols, origem)+where
            if self.ordens:
                query += sql.SQL(' ORDER BY ')+sql.SQL(',').join(sql.SQL('{} {}').format(identificador(c),sql.SQL('DESC' if desc else 'ASC')) for c,desc in self.ordens)
            if self.quantidade is not None:
                query += sql.SQL(' LIMIT %s OFFSET %s'); valores += [self.quantidade,self.inicio]
            linhas = conn.execute(query,prefixo+valores).fetchall()
            if self.nome in ESCALARES:
                data = next(iter(linhas[0].values())) if linhas else None
            else:
                data = (linhas[0] if linhas else None) if self.unica else linhas
            return SimpleNamespace(data=normalizar_resultado(data),count=total)
        if self.params is not None: raise ValueError('RPC não aceita mutação encadeada')
        if self.operacao == 'insert':
            dados = self.dados
            if not isinstance(dados,dict): raise ValueError('Inserção exige objeto')
            query = sql.SQL('INSERT INTO {} ({}) VALUES ({}) RETURNING *').format(origem,sql.SQL(',').join(map(identificador,dados)),sql.SQL(',').join(sql.Placeholder() for _ in dados))
            valores = [Jsonb(v) if isinstance(v,(dict,list)) else v for v in dados.values()]
        elif self.operacao == 'update':
            if not partes: raise ValueError('Atualização exige filtro')
            query = sql.SQL('UPDATE {} SET ').format(origem)+sql.SQL(',').join(sql.SQL('{}=%s').format(identificador(k)) for k in self.dados)+where+sql.SQL(' RETURNING *')
            valores = list(self.dados.values())+valores
        else:
            if not partes: raise ValueError('Exclusão exige filtro')
            query = sql.SQL('DELETE FROM {}').format(origem)+where+sql.SQL(' RETURNING *')
        return SimpleNamespace(data=normalizar_resultado(conn.execute(query,valores).fetchall()),count=None)
