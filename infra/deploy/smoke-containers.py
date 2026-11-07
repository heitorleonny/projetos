#!/usr/bin/env python3
"""Smoke isolado com config sintética, sem publicar portas ou usar dados reais."""
import argparse
import subprocess
import time
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--api-image', default='portal-api:beta')
parser.add_argument('--web-image', default='portal-web:beta')
args = parser.parse_args()
nome = 'portal-infra-smoke-' + uuid.uuid4().hex[:8]
containers = []


def docker(*comando):
    return subprocess.check_output(['docker', *comando], text=True, stderr=subprocess.PIPE).strip()


def aguardar(container, url):
    for _ in range(30):
        try:
            assert docker('exec', container, 'python', '-c',
                          f'import urllib.request;assert urllib.request.urlopen({url!r},timeout=3).status==200') == ''
            return
        except subprocess.CalledProcessError:
            time.sleep(1)
    raise RuntimeError('Serviço sintético não ficou pronto em 30 tentativas.')


def iniciar_api(porta):
    api = nome + '-api'
    containers.append(api)
    docker('run', '-d', '--name', api, '--network', nome, '--network-alias', 'backend',
           '-e', 'SUPABASE_URL=https://fixture.supabase.co',
           '-e', 'SUPABASE_ANON_KEY=sb_publishable_fixture', '-e', 'DOCS_ENABLED=false',
           '-e', f'PORT={porta}', args.api_image)
    aguardar(api, f'http://127.0.0.1:{porta}/health')
    return api


try:
    docker('network', 'create', nome)
    api = iniciar_api(18000)
    assert docker('exec', api, 'id', '-u') == '10001'
    docker('exec', api, 'python', '-c',
           'import importlib.util;assert importlib.util.find_spec("pytest") is None')
    docker('rm', '-f', api)
    containers.remove(api)
    api = iniciar_api(8000)
    web = nome + '-web'
    containers.append(web)
    docker('run', '-d', '--name', web, '--network', nome, '--network-alias', 'frontend',
           '-e', 'SUPABASE_URL=https://fixture.supabase.co',
           '-e', 'SUPABASE_ANON_KEY=sb_publishable_fixture', '-e', 'API_BASE_URL=/api/v1',
           '-e', 'USE_MOCK=false', args.web_image)
    aguardar(api, 'http://frontend/definir-senha')
    docker('exec', api, 'python', '-c', '''import urllib.request,urllib.error
r=urllib.request.urlopen('http://frontend/env-config.js')
assert r.status==200 and r.headers['Cache-Control']=='no-store'
t=r.read().decode();assert 'sb_publishable_fixture' in t and 'SERVICE_KEY' not in t
assert urllib.request.urlopen('http://frontend/healthz').status==200
try:urllib.request.urlopen('http://frontend/api/v1/admin/usuarios')
except urllib.error.HTTPError as e:assert e.code==401,e.code
else:raise AssertionError('Endpoint protegido liberado')
try:urllib.request.urlopen('http://127.0.0.1:8000/docs')
except urllib.error.HTTPError as e:assert e.code==404
else:raise AssertionError('Docs habilitadas')
''')
    print('Smoke Docker passou: PORT, UID sem privilégios, runtime sem pytest, SPA, env sem cache, proxy 401 e docs 404.')
finally:
    for container in reversed(containers):
        subprocess.run(['docker', 'rm', '-f', container], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['docker', 'network', 'rm', nome], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
