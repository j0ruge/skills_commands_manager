# Backend Django (gunicorn) — variante do blueprint para Python

Esta reference cobre o backend **Django/gunicorn** do mesmo blueprint de CD
(build → GHCR → deploy no runner self-hosted) que o lado Node/Prisma. A infra é
idêntica (nginx-proxy + acme-companion, runner conteinerizado, `compose pull`/`up`
escopado, rollback); só o **backend** muda de Node para Python. Use junto com
`troubleshooting-shared.md` (GHCR/SSL/runner) e `self-hosted-runner-docker.md`.

## Quando usar esta reference

- O backend é Django (`manage.py`, `requirements.txt`, `config/settings.py`) — não Node/Prisma.
- Deploy `wait healthy` nunca fica `healthy` e o log do container mostra `GET /healthz/ 400`.
- Admin Django dá 403 CSRF sob HTTPS atrás de nginx-proxy, mas a API (JWT) funciona.
- Estáticos do admin retornam 404 sob gunicorn.
- "Como faço o `prisma migrate deploy` em Django?" / migração one-off no CD.

## §1. `ALLOWED_HOSTS` sem `127.0.0.1` → healthcheck do container responde 400 (nunca fica healthy)

**Sintoma**: `build`/`push`/GHCR `login`/`pull` e a **migração** passam; só o passo
`Aguardar healthy` do CD estoura. `docker logs <backend>` mostra o healthcheck
batendo e levando **400**:

```text
127.0.0.1 - - "GET /healthz/ HTTP/1.1" 400 143 "-" "Python-urllib/3.11"
```

**Causa**: o HEALTHCHECK roda **dentro** do container e bate em
`http://127.0.0.1:8000/healthz/` — Host = `127.0.0.1`. Em produção (`DEBUG=False`)
o Django responde **400 Bad Request** a qualquer `Host` fora de `ALLOWED_HOSTS`.
Se `ALLOWED_HOSTS` só tem o domínio público (`api.exemplo.com`), o healthcheck
interno é rejeitado → o container nunca fica `healthy` → o `wait-healthy` do deploy
estoura. **Isolation key**: tudo antes do wait passa; o tell é o `400` no log com
`Host 127.0.0.1` (ou `Python-urllib`/`curl` como user-agent).

**Fix**: inclua `localhost` e `127.0.0.1` no `ALLOWED_HOSTS` do serviço:

```yaml
# docker-compose (staging/prod)
backend:
  environment:
    ALLOWED_HOSTS: api.exemplo.com,localhost,127.0.0.1   # 127.0.0.1 p/ o healthcheck interno
```

> Alternativa pior: mandar um `Host` válido no healthcheck (`urllib.request.Request(url, headers={'Host': 'api.exemplo.com'})`) — acopla a imagem ao domínio. Preferir liberar `127.0.0.1` no `ALLOWED_HOSTS`.

## §2. Imagem de produção: gunicorn + `collectstatic` em build + WhiteNoise + healthcheck sem curl

Diferenças do `Dockerfile` de dev (que roda `runserver`):

```dockerfile
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# psycopg2-binary/reportlab/openpyxl são wheels — sem toolchain de build.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# collectstatic em BUILD-TIME: exige SECRET_KEY (DEBUG=False) mas NÃO acessa DB.
# Use um SECRET_KEY dummy só neste RUN — não vaza em runtime.
RUN DEBUG=False SECRET_KEY=build-only python manage.py collectstatic --noinput

RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000

# python:slim NÃO tem curl/wget → healthcheck via urllib do próprio Python.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz/')" || exit 1

CMD ["gunicorn","config.wsgi:application","--bind","0.0.0.0:8000","--workers","3","--access-logfile","-","--error-logfile","-"]
```

E um endpoint público de saúde (sem auth, sem DB) em `urls.py`:

```python
from django.http import JsonResponse
def healthz(request):
    """Saúde para healthcheck/smoke — responde rápido, sem DB nem auth."""
    return JsonResponse({'status': 'ok'})
# urlpatterns = [path('healthz/', healthz), ...]
```

**Estáticos do admin sob gunicorn** — gunicorn não serve `/static/`. Use
**WhiteNoise** (servido pelo próprio app), com o storage **comprimido SEM
manifest**:

```python
# settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # logo após o SecurityMiddleware
    # ...
]
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    # CompressedStaticFilesStorage (NÃO CompressedManifest…) — Manifest quebra
    # `{% static %}` em DEBUG=True quando o collectstatic ainda não rodou.
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
```

## §3. HTTPS atrás de nginx-proxy: `CSRF_TRUSTED_ORIGINS` + `SECURE_PROXY_SSL_HEADER`

**Sintoma**: a API (DRF + JWT) funciona, mas o **admin Django** dá 403 CSRF no
POST de login (ou loop de redirect) sob HTTPS.

**Causa**: o TLS termina no nginx-proxy; o gunicorn recebe HTTP interno. Sem dizer
ao Django que a requisição original era HTTPS, o CSRF (que compara o `Origin`
`https://…` com o esquema visto) rejeita.

```python
# settings.py
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')   # nginx-proxy encaminha esse header
CSRF_TRUSTED_ORIGINS = ['https://api.exemplo.com', 'https://app.exemplo.com']
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
```

> A SPA autenticada por **JWT** não usa cookie/CSRF → a API não precisa disto. É só para o admin/sessão. Não confunda os dois sintomas.

## §4. Migração one-off no CD (o `prisma migrate deploy` do Django)

Não migre no boot do container (workers do gunicorn correndo migração em paralelo).
Rode como **one-off** antes do `up`, com os labels do reverse-proxy zerados (não
poluir o upstream pool — `cd-pipeline-pitfalls.md §4`):

```bash
docker compose -f infra/staging/docker-compose.yml --env-file infra/staging/.env run --rm \
  -e VIRTUAL_HOST= -e LETSENCRYPT_HOST= \
  backend python manage.py migrate --noinput
# depois: docker compose ... up -d backend frontend postgres   (escopado, sem o runner)
```

Seed/superuser (rodar **uma vez**, não a cada deploy) — preferir `docker exec` no
container já rodando a `compose run` (ver §6):

```bash
docker exec -e DJANGO_SUPERUSER_PASSWORD jrc-staging-backend \
  python manage.py createsuperuser --noinput --username admin --email it@exemplo.com
```

## §5. Two-origin Django + SPA (frontend e backend em subdomínios distintos)

Frontend em `app.exemplo.com`, backend em `api.exemplo.com` → cada serviço com seu
`VIRTUAL_HOST`/`LETSENCRYPT_HOST` (o backend também precisa `VIRTUAL_PORT=8000`).
A SPA chama o backend **direto** (CORS), não via proxy `/api` do nginx do front:

- **Build-time (front)**: `VITE_API_URL=https://api.exemplo.com/api` entra como
  **build-arg** (embute no bundle — lições 18–20). Imagem é específica do ambiente.
- **Runtime (back)**: `CORS_ALLOWED_ORIGINS=https://app.exemplo.com` (django-cors-headers).
- `CSRF_TRUSTED_ORIGINS` inclui **ambos** os domínios (§3).

> Single-origin (front nginx faz `proxy_pass /api/ → backend:8000`) também funciona e dispensa CORS, mas exige `VITE_API_URL=/api` relativo. Escolha um modelo e seja consistente.

## §6. Gotchas cross-stack que mordem o Django também

- **Owner do GHCR em lowercase**: `github.repository_owner` preserva maiúsculas
  (`ChewieSoft`), mas paths de imagem GHCR têm de ser minúsculos. Lowercale antes:
  `owner=$(echo "${{ github.repository_owner }}" | tr '[:upper:]' '[:lower:]')`.
- **Pacote GHCR privado por padrão**: o deploy puxa porque o **runner** faz
  `docker login`; um `docker compose run`/`pull` **manual no host** (não logado)
  falha com `unauthorized`. Para one-offs (seed, migração ad-hoc, shell) use
  `docker exec` no container **já rodando** (sem re-pull), ou `docker login ghcr.io`
  antes.
- **`paths-ignore` p/ docs**: `on.push.paths-ignore: ['**.md','docs/**']` evita
  redeploy em commit só de doc — mas só pula quando **todos** os arquivos batem.

## Sintomas → seção

| Sintoma | Vai para |
|---------|----------|
| `wait healthy` estoura; log `GET /healthz/ 400` (Host 127.0.0.1) | §1 (ALLOWED_HOSTS) |
| Admin 403 CSRF sob HTTPS; API JWT OK | §3 (CSRF/proxy-SSL) |
| Estáticos do admin 404 sob gunicorn | §2 (WhiteNoise + collectstatic) |
| `python:slim` sem curl pro HEALTHCHECK | §2 (urllib) |
| "Como rodar a migração no CD?" | §4 (one-off `migrate --noinput`) |
| SPA não fala com a API / CORS / VITE_API_URL | §5 (two-origin) |
| GHCR `unauthorized` em one-off manual / org com maiúscula | §6 |
