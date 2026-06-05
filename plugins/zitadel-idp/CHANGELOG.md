# Changelog — zitadel-idp

## [0.9.0] — 2026-05-18

### Added

- Primeiro smoke real-browser do loop SPA↔backend↔Zitadel (sales_quote T150) expôs dois
  pitfalls novos. Quirk 41 — o bootstrap idempotente cria os grants do usuário inicial mas
  NÃO reconcilia os já existentes quando o YAML evolui (um usuário seed pré-existente fica
  com os `roleKeys` do dia-0 e o JWT sai sem o novo papel; um usuário novo pelo mesmo
  bootstrap funciona — a assimetria é o diagnóstico); cura é search-then-PUT (padrão do
  quirk 8). Quirk 42 — a SPA no navegador → Express precisa de CORS, senão todo preflight
  `OPTIONS` cai no `authJwt` e retorna 401 (mimetiza a família 401-storm; `curl` com Bearer
  passa porque não dispara preflight, e testes MSW/supertest não emitem preflight real);
  cura é um middleware CORS mínimo como PRIMEIRO middleware, encurtando `OPTIONS` com 204.
- `spa-recipes.md` — receita "E2E browser tests (Playwright) contra Zitadel self-signed"
  (`ignoreHTTPSErrors`, fill condicional de username em `login_hint`, caveat de
  `storageState` + `InMemoryWebStorage`).

## [0.8.0] — 2026-05-08

### Added

- Três quirks de smoke-e2e em CI (validade_bateria_estoque PR #10). Quirk 38 — bind mount
  de `ZITADEL_FIRSTINSTANCE_PATPATH` com EACCES no runner GHA (uid 1000 vs 1001 + 0755)
  cascateia num `unique_constraints_pkey` enganoso; cura é `mkdir -p && chmod 0777` ANTES
  do `docker compose up`. Quirk 39 — a política de senha padrão exige as 4 classes de
  caractere; `openssl rand -hex` é lowercase-only e falha no AddHumanUser (use prefixo
  estruturado `Aa1!` + cauda alfanumérica). Quirk 40 — `zitadel-login` (Login UI v2)
  precisa de ~90s+ pro primeiro healthcheck em runners pequenos, estourando `up --wait`
  da stack inteira; cura é escopar o `--wait` a `zitadel-db zitadel-init zitadel`.
- Checklist "Smoke-e2e plumbing for GHA".
