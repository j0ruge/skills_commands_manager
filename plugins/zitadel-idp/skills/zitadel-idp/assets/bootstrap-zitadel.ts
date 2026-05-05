/**
 * Bootstrap declarativo do Zitadel — cria Org "JRC", Project "ERP-JRC",
 * roles `battery.operator`/`battery.admin` e Application OIDC
 * `battery-lifecycle-web` (SPA, PKCE) via Management API REST.
 *
 * Idempotente: para cada recurso, busca antes de criar; se já existe, segue.
 *
 * Pré-requisitos:
 *   - Zitadel rodando e healthy (docker compose up)
 *   - PAT do service account IAM_OWNER em ZITADEL_PAT_FILE
 *   - ZITADEL_API_URL aponta ao Zitadel
 *
 * Saída: imprime IDs no stdout e gera `infra/docker/zitadel/local/bootstrap.json`
 * com `orgId`, `projectId`, `clientId` para preenchimento do `.env`.
 *
 * Referência: docs/zitadel-reference.md, contracts/zitadel-config.yaml.
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

interface BootstrapResult {
  orgId: string;
  orgName: string;
  projectId: string;
  projectName: string;
  appId: string;
  clientId: string;
  clientType: 'OIDC';
  redirectUris: string[];
  roles: string[];
}

const ZITADEL_API_URL = process.env.ZITADEL_API_URL ?? 'http://127.0.0.1.sslip.io:8080';
const PAT_FILE =
  process.env.ZITADEL_PAT_FILE ?? resolve(__dirname, '../../../infra/docker/zitadel/local/admin.pat');

const ORG_NAME = 'JRC';
const PROJECT_NAME = 'ERP-JRC';
const APP_NAME = 'battery-lifecycle-web';
const ROLES = [
  { key: 'battery.operator', displayName: 'Operador Battery Lifecycle', group: 'battery' },
  { key: 'battery.admin', displayName: 'Administrador Battery Lifecycle', group: 'battery' },
];
// IMPORTANTE: incluir o silent-renew URI por default. Sem ele, todo
// `automaticSilentRenew` na SPA retorna 400 e a UI fica em loop "verifying
// session..." → ver references/troubleshooting.md.
//
// QUIRK 23 — Multi-app refactor caveat: este asset é single-app. Se você
// evolui ele para ler `applications[].redirectUris` de um YAML declarativo
// (multi-sistema), preserve a precedência **env > YAML > hardcoded**: o
// `dev.sh` em LAN HTTPS popula `OIDC_REDIRECT_URIS` com hosts dinâmicos
// (`https://<ip>.sslip.io:5443/...`) que NUNCA aparecem em YAML estático.
// Se YAML wins, o callback do dev bate em "redirect_uri missing in client
// configuration" silenciosamente. Em prod o env é unset e YAML ganha. →
// references/troubleshooting.md §"redirect_uri missing — multi-app refactor".
const REDIRECT_URIS = (
  process.env.OIDC_REDIRECT_URIS ??
  'http://localhost:5173/auth/callback,http://localhost:5173/silent-renew'
)
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);
const POST_LOGOUT_URIS = (
  process.env.OIDC_POST_LOGOUT_URIS ?? 'http://localhost:5173/login,http://localhost:5173/'
)
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);

// TODO (out of scope deste script): seed do primeiro usuário humano + grant
// no project. Ver references/api-cheatsheet.md §"Seed an admin user" para o
// combo `POST /v2/users/human` + `POST /management/v1/users/{id}/grants`.

if (!existsSync(PAT_FILE)) {
  console.error(`PAT não encontrado em ${PAT_FILE}`);
  process.exit(1);
}
const PAT = readFileSync(PAT_FILE, 'utf8').trim();

async function api<T = unknown>(path: string, init: RequestInit = {}, orgId?: string): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${PAT}`,
    'Content-Type': 'application/json',
    ...((init.headers as Record<string, string>) ?? {}),
  };
  if (orgId) headers['x-zitadel-orgid'] = orgId;

  const res = await fetch(`${ZITADEL_API_URL}${path}`, { ...init, headers });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(`Zitadel ${res.status} ${path}: ${text}`);
  }
  return text ? (JSON.parse(text) as T) : ({} as T);
}

async function findOrg(name: string): Promise<{ id: string; name: string } | null> {
  const res = await api<{ result?: Array<{ id: string; name: string }> }>('/admin/v1/orgs/_search', {
    method: 'POST',
    body: JSON.stringify({
      queries: [{ nameQuery: { name, method: 'TEXT_QUERY_METHOD_EQUALS' } }],
    }),
  });
  return res.result?.[0] ?? null;
}

async function ensureOrg(): Promise<string> {
  const existing = await findOrg(ORG_NAME);
  if (existing) {
    console.log(`[org] reusing "${ORG_NAME}" id=${existing.id}`);
    return existing.id;
  }
  // V2 Connect protocol — POST /zitadel.org.v2.OrganizationService/AddOrganization.
  // Diferente de _setup, não exige admin human; admin-sa (IAM_OWNER instance) cobre.
  const created = await api<{ organizationId: string }>(
    '/zitadel.org.v2.OrganizationService/AddOrganization',
    { method: 'POST', body: JSON.stringify({ name: ORG_NAME }) },
  );
  console.log(`[org] created "${ORG_NAME}" id=${created.organizationId}`);
  return created.organizationId;
}

async function findProject(orgId: string, name: string): Promise<{ id: string } | null> {
  const res = await api<{ result?: Array<{ id: string; name: string }> }>(
    '/management/v1/projects/_search',
    {
      method: 'POST',
      body: JSON.stringify({
        queries: [{ nameQuery: { name, method: 'PROJECT_NAME_QUERY_METHOD_EQUALS' } }],
      }),
    },
    orgId,
  );
  return res.result?.[0] ?? null;
}

async function ensureProject(orgId: string): Promise<string> {
  const existing = await findProject(orgId, PROJECT_NAME);
  if (existing) {
    console.log(`[project] reusing "${PROJECT_NAME}" id=${existing.id}`);
    return existing.id;
  }
  const created = await api<{ id: string }>(
    '/management/v1/projects',
    {
      method: 'POST',
      body: JSON.stringify({
        name: PROJECT_NAME,
        projectRoleAssertion: true,
        projectRoleCheck: false,
        hasProjectCheck: false,
      }),
    },
    orgId,
  );
  console.log(`[project] created "${PROJECT_NAME}" id=${created.id}`);
  return created.id;
}

async function ensureRoles(orgId: string, projectId: string): Promise<void> {
  const existing = await api<{ result?: Array<{ key: string }> }>(
    `/management/v1/projects/${projectId}/roles/_search`,
    { method: 'POST', body: JSON.stringify({}) },
    orgId,
  );
  const have = new Set((existing.result ?? []).map((r) => r.key));
  for (const role of ROLES) {
    if (have.has(role.key)) {
      console.log(`[role] reuse ${role.key}`);
      continue;
    }
    await api(
      `/management/v1/projects/${projectId}/roles`,
      {
        method: 'POST',
        body: JSON.stringify({
          roleKey: role.key,
          displayName: role.displayName,
          group: role.group,
        }),
      },
      orgId,
    );
    console.log(`[role] created ${role.key}`);
  }
}

async function findApp(
  orgId: string,
  projectId: string,
  name: string,
): Promise<{ id: string; oidcConfig?: { clientId?: string } } | null> {
  const res = await api<{
    result?: Array<{ id: string; name: string; oidcConfig?: { clientId?: string } }>;
  }>(
    `/management/v1/projects/${projectId}/apps/_search`,
    {
      method: 'POST',
      body: JSON.stringify({
        queries: [{ nameQuery: { name, method: 'APP_NAME_QUERY_METHOD_EQUALS' } }],
      }),
    },
    orgId,
  );
  return res.result?.[0] ?? null;
}

async function ensureApp(
  orgId: string,
  projectId: string,
): Promise<{ appId: string; clientId: string }> {
  const existing = await findApp(orgId, projectId, APP_NAME);
  if (existing) {
    console.log(`[app] reuse "${APP_NAME}" id=${existing.id}`);
    if (existing.oidcConfig?.clientId) {
      return { appId: existing.id, clientId: existing.oidcConfig.clientId };
    }
    const detail = await api<{ app: { oidcConfig?: { clientId?: string } } }>(
      `/management/v1/projects/${projectId}/apps/${existing.id}`,
      { method: 'GET' },
      orgId,
    );
    return { appId: existing.id, clientId: detail.app.oidcConfig?.clientId ?? '' };
  }
  const created = await api<{ appId: string; clientId: string }>(
    `/management/v1/projects/${projectId}/apps/oidc`,
    {
      method: 'POST',
      body: JSON.stringify({
        name: APP_NAME,
        redirectUris: REDIRECT_URIS,
        responseTypes: ['OIDC_RESPONSE_TYPE_CODE'],
        grantTypes: ['OIDC_GRANT_TYPE_AUTHORIZATION_CODE', 'OIDC_GRANT_TYPE_REFRESH_TOKEN'],
        appType: 'OIDC_APP_TYPE_USER_AGENT',
        authMethodType: 'OIDC_AUTH_METHOD_TYPE_NONE',
        postLogoutRedirectUris: POST_LOGOUT_URIS,
        version: 'OIDC_VERSION_1_0',
        devMode: true,
        accessTokenType: 'OIDC_TOKEN_TYPE_JWT',
        accessTokenRoleAssertion: true,
        idTokenRoleAssertion: true,
        idTokenUserinfoAssertion: true,
        clockSkew: '5s',
        // Pin the OIDC client to Login UI v1. Sozinho NÃO supera o instance
        // feature flag `loginV2.required` — este precisa ser desativado via
        // `PUT /v2/features/instance` quando v2 não estiver deployada.
        // Ver references/troubleshooting.md §"Hosted UI returns 404".
        loginVersion: { loginV1: {} },
      }),
    },
    orgId,
  );
  console.log(`[app] created "${APP_NAME}" appId=${created.appId} clientId=${created.clientId}`);
  return { appId: created.appId, clientId: created.clientId };
}

async function main(): Promise<void> {
  console.log(`[bootstrap] Zitadel API: ${ZITADEL_API_URL}`);

  const orgId = await ensureOrg();
  const projectId = await ensureProject(orgId);
  await ensureRoles(orgId, projectId);
  const { appId, clientId } = await ensureApp(orgId, projectId);

  const result: BootstrapResult = {
    orgId,
    orgName: ORG_NAME,
    projectId,
    projectName: PROJECT_NAME,
    appId,
    clientId,
    clientType: 'OIDC',
    redirectUris: REDIRECT_URIS,
    roles: ROLES.map((r) => r.key),
  };

  const outFile = resolve(__dirname, '../../../infra/docker/zitadel/local/bootstrap.json');
  writeFileSync(outFile, JSON.stringify(result, null, 2));
  console.log(`\n[bootstrap] OK → ${outFile}`);
  console.log(JSON.stringify(result, null, 2));
  console.log('\nAtualize packages/idp/.env com:');
  console.log(`  ZITADEL_PROJECT_ID=${projectId}`);
  console.log(`  OIDC_AUDIENCE=${projectId}`);
  console.log(`  OIDC_ISSUER=http://127.0.0.1.sslip.io:8080`);
}

main().catch((err: unknown) => {
  console.error('[bootstrap] FALHOU:', err instanceof Error ? err.message : err);
  process.exit(1);
});
