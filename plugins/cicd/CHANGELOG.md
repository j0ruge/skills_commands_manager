# Changelog — cicd (Unificada)

Formato: [Semantic Versioning](https://semver.org/)

## [2.0.0] - 2026-03-12

### Adicionado

- Skill unificada backend + frontend com progressive disclosure
- Detecção automática de projeto (Prisma → backend, Vite → frontend)
- Quick troubleshooting table unificada com tags `[B]`/`[F]`/`[S]` (21 entradas)
- Tabela de roteamento para 7 arquivos de referência
- Tabela de lições aprendidas unificada (26 lições com tags)
- `references/troubleshooting-shared.md` — 5 cenários de infra compartilhados
- `references/checklist-shared.md` — 4 seções compartilhadas (runner, GHCR, DNS, rede)
- `references/troubleshooting-backend.md` — exit codes, Zod, Prisma, VIRTUAL_PORT, diagnóstico
- `references/checklist-backend.md` — 7 seções (secrets, Zod CI vars, Docker, lint, Jest, build, rede)
- `references/test-fixes-backend.md` — 8 padrões de correção de testes Jest
- `references/troubleshooting-frontend.md` — Vite, SPA, nginx, Alpine, diagnóstico
- `references/checklist-frontend.md` — 6 seções (VITE_* secrets, Dockerfile, compose, CI, CD, build files)
- Comandos úteis com templates por projeto (compose path difere)
- Tabela de arquivos do pipeline separada por projeto

### Removido

- `references/troubleshooting.md` (conteúdo distribuído em troubleshooting-shared/backend/frontend)
- `references/github-actions-checklist.md` (conteúdo distribuído em checklist-shared/backend/frontend)
- `references/test-fixes.md` (renomeado para test-fixes-backend.md)

### Alterado

- SKILL.md agora é entry point fino (~230 linhas) que roteia para referências on-demand
- Conteúdo duplicado entre backend e frontend eliminado via arquivos shared
- Versão: 1.x.0 (separadas) → 2.0.0 (unificada)

---

## Histórico Pré-Unificação

### Frontend (v1.0.0 → v1.1.0)

- **v1.1.0**: 5 lições do deploy real (healthcheck, vite.config.ts, Vitest E2E, treeshake, GHCR login)
- **v1.0.0**: SKILL.md com 10 lições, troubleshooting (9 cenários), checklist (8 seções)

### Backend (v1.0.0 → v1.6.0)

- **v1.6.0**: ERR_SSL_VERSION_OR_CIPHER_MISMATCH, DNS/SSL troubleshooting
- **v1.5.0**: Port mapping desnecessário com nginx-proxy
- **v1.4.0**: VIRTUAL_PORT obrigatório para nginx-proxy
- **v1.3.0**: Secrets com `z.string().url()` devem incluir `https://`
- **v1.2.0**: Variáveis Zod no Generate .env do CD
- **v1.1.0**: GHCR auth sudo/user, rede nginx-proxy variável, lint pré-push, re-trigger
- **v1.0.0**: SKILL.md com 14 lições, troubleshooting (exit codes + 12 cenários), test-fixes (8 padrões), checklist (10 seções)
