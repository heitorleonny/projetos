# Operação local — PostgreSQL próprio

Configuração vigente a partir de 05/11/2026. O comando de entrada fica na raiz:

```sh
python3 scripts/configurar_docker.py
docker compose --env-file .env.docker up --build -d
docker compose --env-file .env.docker ps
```

O arquivo `.env.docker` contém senhas privadas e não é incluído no pacote de
fontes. O gerador não o sobrescreve. Preserve esse arquivo junto de backups
protegidos; não cole seu conteúdo em relatórios.

O banco é `postgres:16-alpine`, sem porta publicada. API e frontend têm imagens
separadas; nginx encaminha `/api/` à API. A porta local é 8080. Para outra porta,
altere `FRONTEND_PORT`, `CONVITE_REDIRECT_URL` e `CORS_ORIGINS` juntos.

## Dados e migrações

O volume `portal_postgres` pertence à nova stack. `docker compose down` conserva
o volume. Não use `down -v`, `make clean` ou os resets da demo antiga para validar.

O proprietário conecta apenas no serviço `migrate`, que aplica os SQL canônicos
com checksum/ledger e falha diante de banco legado sem controle. A API recebe
contas restritas. O login de laboratório com senha conhecida é desabilitado neste
ambiente. Migrações novas recebem arquivo numerado; não edite as antigas.

A nova instalação não copia dados/contas do Supabase. Importações reais exigem
arquivo autorizado e tenant explícito. Não reutilize senhas de demonstração.

## Backup

Exemplo local; o dump contém dados privados e deve ficar fora do repositório:

```sh
umask 077
docker compose --env-file .env.docker exec -T postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > /CAMINHO-PRIVADO/portal.dump
```

Valide restauração em banco separado antes de depender do backup. Não restaure
sobre o volume corrente como teste. Retenção, criptografia e cópia fora da máquina
são responsabilidades do operador quando houver dados reais.

## Hospedagem

O binding padrão é somente `127.0.0.1`; o pacote não publica um site na internet.
Para servidor remoto, definir HTTPS/reverse proxy, domínio, política de backup,
contas individuais e acesso de rede; verificar novamente cookies/tokens, convites,
login, RLS e importação no destino. Não presumir que o smoke local substitui isso.
Os antigos manifestos Supabase são histórico e não são o comando desta entrega.
