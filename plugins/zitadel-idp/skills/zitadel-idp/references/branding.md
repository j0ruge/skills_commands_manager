# Branding da Login UI v1 (LabelPolicy + assets + custom texts)

A Login UI v1 do Zitadel é hospedada e tem layout fixo, mas **expõe cores, logos, ícone e textos via Management API**. Suficiente pra que `/ui/login/login` apareça na identidade da org (cor primária, logo, fundo, copy em PT-BR) e sem o "Powered by Zitadel" — o usuário final nunca precisa saber qual IdP está por trás.

Este guia foi escrito após hit em **4 pegadinhas distintas** que invalidam tutoriais antigos do Zitadel v1/v2: o caminho parecia óbvio, cada passo individual passava na API, mas o browser continuava mostrando o tema default azul do Zitadel.

## Quando ler este arquivo

- Você quer aplicar identidade visual à tela de login do Zitadel self-hosted (`/ui/login/login`)
- O bootstrap já configura LabelPolicy mas a Login UI continua azul Zitadel default (`#5469d4`)
- Você está em Zitadel v4.x e tutoriais antigos referenciam paths `/assets/v1/orgs/me/...` que retornam 405
- Preciso saber qual subset dos tokens do design system mapeia pros campos do LabelPolicy

**Fora de escopo**: customização da Login UI v2 (Next.js separado, fully styleable — você redesenha do zero); migração v1→v2; e-mails transacionais (endpoint `message_text` é separado).

## A ordem que importa

A pegadinha #1 desta área é que aplicar cores+logo+texto na org **não pinta a tela de login** se o projeto OIDC não tiver o flag certo. A ordem correta:

```
1. POST /management/v1/projects/{p}  com privateLabelingSetting=ENFORCE_PROJECT_RESOURCE_OWNER_POLICY
2. GET  /management/v1/policies/label  (escopado pela org via x-zitadel-orgid)
   ├─ se policy.isDefault === true → POST /management/v1/policies/label  (cria override)
   └─ senão                        → PUT  /management/v1/policies/label  (atualiza)
3. POST /assets/v1/org/policy/label/logo       (multipart, light)
4. POST /assets/v1/org/policy/label/logo/dark  (multipart, dark)
5. POST /assets/v1/org/policy/label/icon       (multipart, favicon)
6. PUT  /management/v1/text/login/pt           (textos PT-BR — só pt curto, pt-BR rejeitado)
7. POST /management/v1/policies/label/_activate
```

Pular o passo 1 ou o passo 7 são os erros mais frequentes — ambos não falham loud, só não pintam a tela.

## Quirk 19 — `privateLabelingSetting` no projeto é o gatilho silencioso

**Sintoma**: Você POST/PUT a label policy na org, ativa, vê `primaryColor: "#xxx"` no GET seguinte. Browser ainda mostra azul Zitadel `#5469d4` em `/ui/login/login`.

**Causa**: Sem o flag explícito no projeto OIDC, o Zitadel renderiza com a label policy **default da instância** — não com a da org dona do projeto. O default `PRIVATE_LABELING_SETTING_UNSPECIFIED` significa "não use private labeling" e cai pro tema da instância.

**Fix**: Setar no payload do POST/PUT do projeto:

```json
{
  "name": "ERP-JRC",
  "projectRoleAssertion": true,
  "projectRoleCheck": false,
  "hasProjectCheck": false,
  "privateLabelingSetting": "PRIVATE_LABELING_SETTING_ENFORCE_PROJECT_RESOURCE_OWNER_POLICY"
}
```

Em re-runs do bootstrap (project já existe), aplicar via `PUT /management/v1/projects/{p}` — silenciosamente sobrescreve. Trata `COMMAND-1m88i "No changes"` como no-op (idempotência).

**Sentinela**: `GET /management/v1/projects/{p}` deve retornar `"privateLabelingSetting": "PRIVATE_LABELING_SETTING_ENFORCE_PROJECT_RESOURCE_OWNER_POLICY"`. Se vier ausente da resposta, o flag não foi aplicado (provavelmente por enum errado no payload).

## Quirk 20 — POST vs PUT na primeira label policy + 2 error IDs distintos

**Sintoma A** (criação): `PUT /management/v1/policies/label` com payload completo retorna `404 "Private Label Policy not found (Org-0K9dq)"`. A org não tem override ainda.

**Sintoma B** (re-run idempotente): após criar e aplicar, rodar o bootstrap de novo retorna `400 "Private Label Policy has not been changed (Org-8nfSr)"`. Diferente do `COMMAND-1m88i` genérico que outros endpoints usam.

**Fix**: Heurística baseada no `isDefault` do GET prévio:

```typescript
const current = await api(`/management/v1/policies/label`, { method: 'GET' }, orgId);
if (current.policy?.isDefault) {
  // Org ainda usa default da instância — POST cria override
  await api('/management/v1/policies/label', { method: 'POST', body: JSON.stringify(desired) }, orgId);
} else {
  // Override já existe — PUT atualiza
  await api('/management/v1/policies/label', { method: 'PUT', body: JSON.stringify(desired) }, orgId);
}
```

E tratar **ambos** os error IDs como no-op idempotente:

```typescript
} catch (err) {
  const msg = String(err);
  if (msg.includes('COMMAND-1m88i') || msg.includes('Org-8nfSr')) {
    console.log('[label-policy] no-op');
  } else { throw err; }
}
```

**Verificação após sucesso**: GET deve retornar a policy **sem** `isDefault: true` no topo, com seus valores aplicados. Se `isDefault` permanece, o POST não pegou.

## Quirk 21 — Path de assets em Zitadel v4 mudou para `/assets/v1/org/policy/label/...`

**Sintoma**: `POST /assets/v1/orgs/me/policy/label/logo` (path que aparece em docs/exemplos antigos do Zitadel v1/v2/v3) retorna **HTTP 405 Method Not Allowed** em v4. Confuso porque parece "endpoint existe mas método errado", quando na verdade o endpoint está em outro path.

**Cause**: Em Zitadel v4 o path foi renomeado de `orgs/me` para `org` (singular, sem `me`). O escopo continua sendo via header `x-zitadel-orgid`.

**Endpoints corretos (v4)**:

| Asset | Path | Método |
|---|---|---|
| Logo light | `/assets/v1/org/policy/label/logo` | POST |
| Logo dark | `/assets/v1/org/policy/label/logo/dark` | POST |
| Favicon | `/assets/v1/org/policy/label/icon` | POST |
| Fonte custom | `/assets/v1/org/policy/label/font` | POST |

Multipart com field name `file`:

```bash
curl -sk -X POST \
  -H "Authorization: Bearer $PAT" \
  -H "x-zitadel-orgid: $ORG_ID" \
  -F "file=@./logo-light.png;type=image/png" \
  https://<idp-host>/assets/v1/org/policy/label/logo
```

**Idempotência inerente do endpoint**: o response retorna 200 sem hash/etag — não há como saber se a imagem mudou. Aceite re-upload em todo bootstrap; é barato (poucos KB) e simplifica o código.

**Verificação**: `GET /management/v1/policies/label` após o `_activate` deve mostrar `logoUrl`, `logoUrlDark`, `iconUrl` populados (URLs absolutas para `<idp-host>/assets/v1/<orgId>/policy/label/...`). Se vierem ausentes, o upload pegou mas o `_activate` não rodou.

## Quirk 22 — Custom login text usa `/management/v1/text/login/{lang}` e só aceita códigos curtos

**Sintoma A** (path errado): `PUT /management/v1/policies/custom_login_text/pt` retorna 404. Esse path aparece em alguns specs/changelogs antigos mas não existe em v4.

**Sintoma B** (lang errado): `PUT /management/v1/text/login/pt-BR` retorna `400 "Language is not supported (LANG-lg4DP)"`. Zitadel só aceita códigos ISO 639-1 curtos (`pt`, `en`, `de`, `fr`, ...). A negociação `pt-BR → pt` é feita server-side via Accept-Language.

**Fix**: usar o path correto + lang curto:

```bash
curl -sk -X PUT \
  -H "Authorization: Bearer $PAT" \
  -H "x-zitadel-orgid: $ORG_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "loginText": {
      "title": "Entrar",
      "loginNameLabel": "E-mail corporativo",
      "nextButtonText": "Continuar"
    },
    "passwordText": {
      "title": "Senha",
      "passwordLabel": "Senha",
      "resetLinkText": "Esqueci minha senha",
      "nextButtonText": "Entrar"
    }
  }' \
  https://<idp-host>/management/v1/text/login/pt
```

**PUT é mergeable, não replace.** Campos não enviados preservam o default i18n do Zitadel — você pode aplicar incrementalmente sem zerar `mfaInitText`, `passwordResetText`, etc. que ainda não customizou. Isso também significa que pra "resetar" um campo você manda string vazia explicitamente.

**Estrutura do GET prévio** (útil pra ver quais campos existem):

```bash
curl -sk -H "Authorization: Bearer $PAT" -H "x-zitadel-orgid: $ORG_ID" \
  https://<idp-host>/management/v1/text/login/pt
# retorna { customText: { selectAccountText: {}, loginText: {}, passwordText: {},
#                          initPasswordText: {}, mfaInitText: {}, ... } }
```

## Tom dos textos — princípio geral

Erros de login devem ser **genéricos por princípio de segurança** — não revelar se foi user, senha, ou bloqueio (footprinting). E nunca expor nomes de fornecedores na superfície do produto (vendor-agnostic):

- ❌ "Erro ao consultar Zitadel" / "Token JWT inválido"
- ✅ "Não foi possível entrar. Verifique e tente novamente."

Tom direto, sem emojis nem cordialidade performática — login não é uma boas-vindas, é um portão.

## Tipografia custom (Inter, Roboto, etc.) — não suba

A LabelPolicy aceita upload de fonte (`POST /assets/v1/org/policy/label/font`). **Em Zitadel v4 a fonte custom só aplica em alguns slots** (botões, alguns headings). Inputs e labels caem no fallback do navegador. Resultado: tela com 2 famílias diferentes, pior do que ter 1 só.

A tela de login é vista ~10s por sessão. ROI da paridade tipográfica perfeita é baixo. Cor + logo carregam 90% da continuidade de marca. Se o produto exigir paridade 100% com a SPA, o caminho correto é **migrar para Login UI v2 (Next.js custom)**, não upload de fonte na v1.

## Verificação end-to-end

1. `GET /management/v1/projects/{p}` → `privateLabelingSetting` presente
2. `GET /management/v1/policies/label` (com `x-zitadel-orgid`) → seus `primaryColor`, `disableWatermark: true`, `logoUrl` populados, **sem** `isDefault: true`
3. `GET /management/v1/text/login/pt` → seus textos no `loginText`/`passwordText`
4. Browser em `/oauth/v2/authorize?client_id=...` redireciona pra `/ui/login/login` e renderiza:
   - Logo da org no topo
   - Botão primário na cor configurada
   - **Sem** "Powered by Zitadel" no rodapé (`disableWatermark: true`)
   - Textos PT-BR

Se 1-3 estão verdes mas 4 mostra azul Zitadel, **muito provavelmente** é quirk 19 (privateLabelingSetting ausente no projeto). Se 1+2 verdes mas o logo não aparece, é o `_activate` faltando após o upload de assets.

## Bootstrap completo (referência operacional)

Veja `packages/idp/scripts/bootstrap-zitadel.ts` no projeto JRC — funções `ensureLabelPolicy`, `ensureLabelAssets`, `ensureCustomTexts`, e `ensureProject` com sync do `privateLabelingSetting`. Idempotente, trata os 2 error IDs do quirk 20, faz o `_activate` no fim de cada mutação.
