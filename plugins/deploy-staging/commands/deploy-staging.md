---
description: Sincroniza main com develop, mergeia o branch atual em develop e faz push para triggar o pipeline CD Staging.
metadata:
  version: 1.2.0
---

## Deploy to Staging

Fluxo automatizado para enviar o branch atual para o ambiente de staging via CD pipeline.
Detecta automaticamente se o usuario esta em `develop` ou num feature branch e ajusta o fluxo.

### Pre-requisitos

- Branch atual deve ter todos os commits e mudancas commitadas (working tree limpo)
- `origin/develop` deve estar acessivel
- Acesso push a `origin/main` e `origin/develop`

### Workflow

1. **Verificar working tree**

```bash
git status --short
```

Se houver mudancas nao commitadas, abortar e informar o usuario.

2. **Pre-flight: lint + typecheck + testes**

Rodar as mesmas verificacoes que o CI executa para evitar falhas no pipeline:

```bash
npx eslint . --max-warnings 0
npx tsc --noEmit
yarn vitest run src/test/
```

Se qualquer comando falhar, abortar e informar o usuario. Nao prosseguir com push.

3. **Fetch remotes**

```bash
git fetch origin
```

4. **Detectar branch atual**

```bash
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
```

5. **Detectar cenario (develop vs feature branch)**

Se o branch atual for `develop`, seguir o **fluxo simplificado** (step 5a).
Caso contrario, seguir o **fluxo completo** (steps 6-8).

#### 5a. Fluxo develop — sincronizar main e push

Quando ja estamos em `develop`, nao ha merge de feature branch. Apenas sincronizamos
`main` com o que ja esta no remote de develop e depois pushamos os commits locais.

```bash
git checkout main
git merge origin/develop --ff-only
git push origin main
git checkout develop
git push origin develop
```

Se o merge ff-only falhar, avisar o usuario que ha divergencia em main e abortar.

Apos o push, pular diretamente para o step 9 (verificar pipeline).

---

6. **Sincronizar main com develop** (fluxo feature branch)

```bash
git checkout main
git merge origin/develop --ff-only
git push origin main
```

Se o merge falhar (non-fast-forward), avisar o usuario que ha divergencia e abortar.

7. **Merge feature branch em develop**

```bash
git checkout develop
git pull origin develop
git merge $CURRENT_BRANCH
```

Se houver conflitos, abortar e informar o usuario.

8. **Push develop para triggar CD staging**

```bash
git push origin develop
```

8a. **Voltar ao branch de trabalho**

```bash
git checkout $CURRENT_BRANCH
```

---

9. **Verificar pipeline**

```bash
gh run list --branch develop --limit 3
```

Exibir status do run mais recente ao usuario.

### Notas

- O push em `develop` trigga o workflow `cd-staging.yml` automaticamente
- A imagem Docker e buildada com tag `:staging` e pushada para GHCR
- O deploy e feito no self-hosted runner com label `staging`
- Para monitorar: `gh run watch <run-id>` ou verificar no GitHub Actions
