# Multiple Zitadel Instances & Moving Users Between Them

Two related situations the rest of this skill assumes away: running **more than one
self-hosted Zitadel** (a production instance and a staging one), and **moving accounts
from one to the other**.

The first is mostly discipline about what must not be shared. The second is asymmetric in
a way that surprises people — the import side is supported and the export side is not, so
the obvious "migrate the users" plan has no supported implementation.

---

## §1. What must differ between instances, and what breaks when it doesn't

Two deployments are two independent worlds. Nothing derived from one is valid in the
other:

| Value | Per-instance? | If you cross them |
| --- | --- | --- |
| `issuer` / external domain | yes | `iss` mismatch → token rejected |
| Signing keys (JWKS) | yes | `JWSSignatureVerificationFailed` |
| `projectId` (= JWT **audience**) | yes | `aud` claim rejected — see `token-validation.md` |
| `clientId` (numeric, per app) | yes | authorize returns an error, not a login page |
| `applicationId` (deterministic UUID from your YAML) | **can be equal** | harmless — it is your handle, not OAuth's (Quirk 29) |
| PAT / service credentials | yes | `401` on every Management API call |
| Masterkey | yes | unrelated instances, never share |

**The failure that wastes the most time** is a token from instance A validated against
instance B. It surfaces as `JWSSignatureVerificationFailed`, which reads exactly like a
key-rotation or JWKS-caching problem (Quirks 12, 13, 36) — so you go looking at the
network path and the key cache, and both are fine. Add the instance to your diagnosis
early: decode the token and compare `iss` against the validator's configured issuer
before anything else.

```bash
# Which instance minted this token?
cut -d. -f2 <<< "$TOKEN" | base64 -d 2>/dev/null | grep -oE '"(iss|aud)":[^,}]+'
```

**Configuration hygiene that prevents it**: keep the audience and client id in
environment-scoped configuration (GitHub Environment secrets, per-environment `.env`),
never at a level shared by both. A repository-level variable holding `ZITADEL_AUDIENCE` is
a landmine: it will silently be correct for one environment and wrong for the other.

**Deployment cadence is a coupling too.** If your staging IdP is also the IdP that some
production system points at — a tempting shortcut when a route or feature only exists on
the staging deployment — then a staging deploy can break production. That may be an
acceptable, documented trade-off, but it must be written down as one; it is invisible in
the configuration itself.

---

## §2. Importing users is supported; extracting them is not

**Import (destination side) — supported.** `AddHumanUser` (API v2,
`/v2/users/human`) accepts a pre-hashed password:

```json
{
  "username": "person@example.com",
  "profile": { "givenName": "Person", "familyName": "Example" },
  "email": { "email": "person@example.com", "isVerified": true },
  "hashedPassword": { "hash": "$2a$10$…" }
}
```

The `hash` field takes standard crypt-format strings (bcrypt, argon2 variants). Zitadel
stores it as-is and verifies against it on first login, so users keep their existing
passwords. This is the documented path for coming *from* another IdP that will hand you
its hashes.

**Export (source side) — not supported.** There is no Management or Auth API that returns
a user's password hash. It is written into the eventstore as
`user.human.password.changed` and never exposed for reading. Extracting it means querying
Zitadel's internal Postgres schema directly, which:

- is not a stable contract and changes between versions (the v2.66 → v4 migration rewrites
  parts of it — see `migration-v2-to-v4.md`);
- means handling raw credential material in your own tooling, with all the exposure that
  implies;
- has no test surface — you find out it broke when logins fail after cutover.

So Zitadel → Zitadel password migration has no supported implementation. Say that out
loud early, because the plan "we'll just move the users over" quietly assumes it exists.

---

## §3. The low-risk path: recreate accounts, let people set passwords

```text
For each user in the source instance:
  1. Read the account via ListUsers (username, email, given/family name) — all readable.
  2. AddHumanUser in the destination WITHOUT hashedPassword, using
     password.changeRequired = true (or no password at all + an invite email).
  3. Re-grant roles: CreateAuthorization in the destination project.
```

Three things to know before you start:

- **Grants do not travel with the user.** Roles are per-project authorizations in the
  destination instance and must be recreated. This is where `ZITADEL_SEED_USER_ROLE`
  (Quirk 46) bites if several apps share the target project.
- **`isVerified: true` on the email** avoids the SMTP dependency — otherwise every user
  sits in `state: initial` waiting for a verification mail (Quirk 6), and if SMTP isn't
  configured in the new instance nobody can log in.
- **`userLoginMustBeDomain`** on the destination org changes the resulting login names
  irreversibly (Quirk 34). Decide before creating anyone; fixing it later means recreating
  every account.

**Measure before choosing an approach.** Count the users in the source first:

```bash
# v2 ListUsers, paginated — the total is what matters
curl -s -X POST "https://<src-idp>/v2/users" \
  -H "Authorization: Bearer $PAT" -H 'Content-Type: application/json' \
  -d '{"query":{"limit":1}}' | grep -oE '"totalResult":"?[0-9]+"?'
```

Below a few dozen accounts, recreating them through the API is less work than *designing*
any extraction scheme, let alone validating one. The eventstore route only starts to look
attractive at a scale where the accounts are also too valuable to risk on unsupported
reads — which is the tension that makes it the wrong answer at both ends.

Also check the Zitadel version on both sides: an older source may not expose the v2 user
APIs at all (see `api-v1-to-v2-mapping.md` for what is v1-only), which changes the read
half of the plan.

---

## Symptoms → section

| Symptom | Section |
| --- | --- |
| `JWSSignatureVerificationFailed` and the keys/network look fine | §1 (token from the other instance) |
| `aud` claim rejected after pointing an app at a second instance | §1 |
| Authorize returns an error instead of the login page in one environment only | §1 (per-instance `clientId`) |
| A staging deploy broke production auth | §1 (shared-instance coupling) |
| "How do we move the users' passwords?" | §2 (import yes, export no) |
| Migrated users are stuck in `state: initial` | §3 (`isVerified`, Quirk 6) |
| Migrated users log in but the API returns `401 role_nao_reconhecida` | §3 (grants don't travel) |
