-- Autenticação própria. Funções privadas não são expostas pela API de consultas.
CREATE ROLE portal_app NOLOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS;
GRANT anon, authenticated TO portal_app;
CREATE ROLE portal_auth NOLOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS;
GRANT USAGE ON SCHEMA auth TO portal_auth;
ALTER TABLE auth.users ADD COLUMN password_hash text;
CREATE UNIQUE INDEX auth_users_email_portal ON auth.users(lower(email));
CREATE TABLE auth.portal_sessao (
 token_hash text PRIMARY KEY, user_id uuid NOT NULL REFERENCES auth.users(id),
 expira_em timestamptz NOT NULL DEFAULT now()+interval '8 hours'
);
CREATE INDEX portal_sessao_user ON auth.portal_sessao(user_id);
CREATE TABLE auth.portal_convite (
 token_hash text PRIMARY KEY, user_id uuid NOT NULL REFERENCES auth.users(id),
 expira_em timestamptz NOT NULL DEFAULT now()+interval '24 hours'
);
CREATE TABLE auth.portal_tentativa (
 email text PRIMARY KEY, inicio timestamptz NOT NULL, total integer NOT NULL
);
REVOKE ALL ON auth.portal_sessao,auth.portal_convite,auth.portal_tentativa FROM PUBLIC,anon,authenticated,portal_app,portal_auth;

CREATE FUNCTION auth.portal_conta(p_email text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,auth AS $$
DECLARE tent integer; conta jsonb;
BEGIN
 INSERT INTO auth.portal_tentativa VALUES(lower(p_email),now(),1)
 ON CONFLICT(email) DO UPDATE SET
 total=CASE WHEN portal_tentativa.inicio < now()-interval '15 minutes' THEN 1 ELSE portal_tentativa.total+1 END,
 inicio=CASE WHEN portal_tentativa.inicio < now()-interval '15 minutes' THEN now() ELSE portal_tentativa.inicio END
 RETURNING total INTO tent;
 IF tent>15 THEN RETURN NULL; END IF;
 SELECT jsonb_build_object('id',a.id,'password_hash',a.password_hash) INTO conta
 FROM auth.users a JOIN public.usuario u ON u.auth_user_id=a.id
 WHERE lower(a.email)=lower(p_email) AND u.ativo;
 RETURN conta;
END $$;

CREATE FUNCTION auth.portal_criar_sessao(p_id uuid,p_hash text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,auth AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.usuario WHERE auth_user_id=p_id AND ativo) THEN RAISE EXCEPTION 'Conta indisponível' USING ERRCODE='42501'; END IF;
 INSERT INTO auth.portal_sessao(token_hash,user_id) VALUES(p_hash,p_id);
 UPDATE auth.users SET last_sign_in_at=now() WHERE id=p_id;
 DELETE FROM auth.portal_tentativa WHERE email=(SELECT lower(email) FROM auth.users WHERE id=p_id);
END $$;

CREATE FUNCTION auth.portal_sessao_atual(p_hash text) RETURNS jsonb
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,public,auth AS $$
 SELECT jsonb_build_object('id',a.id,'email',a.email,'nome',u.nome,'federacao_id',u.federacao_id,'papel',u.papel)
 FROM auth.portal_sessao s JOIN auth.users a ON a.id=s.user_id
 JOIN public.usuario u ON u.auth_user_id=a.id
 WHERE s.token_hash=p_hash AND s.expira_em>now() AND u.ativo
$$;

CREATE FUNCTION auth.portal_sair(p_hash text) RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,public,auth AS $$
 DELETE FROM auth.portal_sessao WHERE token_hash=p_hash
$$;

CREATE FUNCTION auth.portal_senha(p_hash text,p_senha text,p_convite boolean) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,auth AS $$
DECLARE alvo uuid;
BEGIN
 IF p_convite THEN
  DELETE FROM auth.portal_convite WHERE token_hash=p_hash AND expira_em>now() RETURNING user_id INTO alvo;
 ELSE
  SELECT user_id INTO alvo FROM auth.portal_sessao WHERE token_hash=p_hash AND expira_em>now() FOR UPDATE;
 END IF;
 IF alvo IS NULL OR NOT EXISTS(SELECT 1 FROM public.usuario WHERE auth_user_id=alvo AND ativo) THEN RETURN false; END IF;
 UPDATE auth.users SET password_hash=p_senha WHERE id=alvo;
 DELETE FROM auth.portal_sessao WHERE user_id=alvo;
 DELETE FROM auth.portal_convite WHERE user_id=alvo;
 RETURN true;
END $$;

CREATE FUNCTION auth.portal_convidar(p_ator text,p_id uuid,p_hash text,p_nome text,p_email text,p_papel text,p_federacao bigint) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public,auth AS $$
DECLARE ator jsonb; novo bigint;
BEGIN
 ator:=auth.portal_sessao_atual(p_ator);
 IF ator IS NULL OR (ator->>'papel') NOT IN ('admin','plataforma') THEN RAISE EXCEPTION 'Acesso negado' USING ERRCODE='42501'; END IF;
 IF ator->>'papel'<>'plataforma' AND (p_federacao<>(ator->>'federacao_id')::bigint OR p_papel='plataforma') THEN RAISE EXCEPTION 'Acesso negado' USING ERRCODE='42501'; END IF;
 IF p_papel NOT IN ('membro','admin','plataforma') THEN RAISE EXCEPTION 'Papel inválido' USING ERRCODE='22023'; END IF;
 INSERT INTO auth.users(id,email) VALUES(p_id,lower(p_email));
 INSERT INTO public.usuario(nome,email,papel,federacao_id,auth_user_id) VALUES(p_nome,lower(p_email),p_papel,p_federacao,p_id) RETURNING id INTO novo;
 INSERT INTO auth.portal_convite(token_hash,user_id) VALUES(p_hash,p_id);
 RETURN novo;
END $$;

REVOKE ALL ON FUNCTION auth.portal_conta(text), auth.portal_criar_sessao(uuid,text), auth.portal_sessao_atual(text), auth.portal_sair(text), auth.portal_senha(text,text,boolean), auth.portal_convidar(text,uuid,text,text,text,text,bigint) FROM PUBLIC,anon,authenticated,portal_app;
GRANT EXECUTE ON FUNCTION auth.portal_conta(text), auth.portal_criar_sessao(uuid,text), auth.portal_sessao_atual(text), auth.portal_sair(text), auth.portal_senha(text,text,boolean), auth.portal_convidar(text,uuid,text,text,text,text,bigint) TO portal_auth;
