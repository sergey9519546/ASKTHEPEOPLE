# Security Incident — Public Historical Provider Credentials

## Status

**OPEN · CRITICAL · ROTATION REQUIRED**

Do not deploy or use provider-connected environments until containment is
complete.

## What was confirmed

A full-history, value-redacted review found that public commit
`65403183ba37cefbcc73d23d9fdf666750db3ddc` replaced placeholders in
`.env.example` with credential-shaped provider values for one revision.
That commit is an ancestor of `origin/main`, and the GitHub repository is
public.

Safe boolean-only comparisons were performed without displaying credential
material. The affected configured-variable set is:

- `ZEP_API_KEY`;
- `LLM_API_KEY`;
- `LLM_BOOST_API_KEY`; and
- `BRAVE_SEARCH_API_KEY`.

At the latest audit, each configured local value matched credential material
present in public history. All four values MUST be treated as compromised.
This comparison does not prove provider-side revocation, replacement, or
deployment state.

The current `.env` is ignored and was not itself committed. That does not undo
the historical exposure.

## Public legacy deployment observation — 2026-08-11

An anonymous read-only probe of the previously documented Railway origin found
that it was still publicly reachable. `/health` returned HTTP 200 with
`status=degraded`, `revision=unknown`, and a degraded database component;
`/health/readiness` returned HTTP 503 with the database component in error.
`/health/revision` served the frontend HTML shell rather than an immutable
revision response. This proves a stale, unhealthy public deployment remains;
it does not reveal which provider credentials or service variables that
deployment holds. Repository sentinels cannot disable an already-connected
provider dashboard. The Railway project and every legacy Vercel/Render
integration MUST be disabled by an authorized operator and the public origin
must be independently rechecked before containment can close.

## Current containment — UNCOMMITTED / NOT RELEASED

The current working tree redacts known provider-shaped literals and tightens
the scanner policy so documentation, examples, and deployment guides cannot
silently bypass provider-secret detection. This containment is uncommitted and
has not been released or deployed. Public Git history still contains the
exposed credential material. A clean current-tree scan is necessary evidence,
but it cannot close the historical exposure or establish provider-side
containment.

## Immediate containment order

1. Revoke every affected Zep, primary-LLM, boost-LLM, and search credential in
   its provider console.
2. Issue replacement credentials with the narrowest available scopes and
   limits.
3. Update local secret storage and deployment variables through their secure
   interfaces. Never paste replacements into source, chat, logs, issues, or
   workflow output.
4. Independently verify provider-side revocation and rotation for all four
   variables before enabling provider-connected testing.
5. Restart/redeploy both web and worker services only after `APP_TOKEN`, exact
   origins, replacement provider credentials, and the hardened immutable
   revision are configured.
6. Review provider usage, billing, and audit logs from the first public commit
   date through the later of the web-service and worker-service restarts that
   removed the exposed credentials. Preserve the review as restricted incident
   evidence.
7. Run the improved secret scan across all refs and retain only its redacted
   result.
   This verification is complete: the clean-checkout-equivalent tree scan had
   zero findings, while the fully redacted all-ref history scan found exactly
   the known historical provider credentials and failed closed.
8. After rotation evidence and immutable deployment identity are independently
   verified, run the protected harmless Zep canary defined in the release
   runbook. The canary MUST create an isolated graph, register the approved
   PascalCase ontology, ingest only the harmless fixture, verify nodes and
   edges, and delete the graph. A failed or incomplete cleanup is an incident,
   not permission to retry blindly.

Rotation comes before history rewriting. Rewriting Git history cannot make a
published credential secret again.

## History remediation

After rotation, coordinate a public-history rewrite that removes the secret
values from every affected object and ref. This is destructive and requires an
operator-approved maintenance window because it changes commit IDs, requires a
force push, invalidates existing clones and open work, and may require GitHub
cache/support follow-up.

Do not perform a history rewrite until:

- replacement credentials are active and the old values are revoked;
- all collaborators and deployment integrations are ready to re-clone or
  rebase;
- the current uncommitted hardening work is preserved in a reviewed patch or
  other restricted backup that has passed a current-tree secret scan;
- the intended protected-branch and environment policy is documented,
  including the named operator and exact time window for the one required
  force-push exception; and
- a verified backup of the pre-rewrite repository exists in restricted
  storage.

During the maintenance window, pause merges and deployments, grant the
time-bounded force-push exception only to the named operator, rewrite and push
every affected ref, then immediately remove the exception. Verify branch
protection, tag protection, collaborator re-clones, GitHub caches, and a clean
all-ref history scan before resuming normal work.

## Release gate

Public production, staging with provider access, and provider-connected local
testing are **NO-GO** until all four affected credentials are revoked and
rotated, usage is reviewed through the later web/worker restart, rotation and
deployment identity are independently verified, and the protected harmless
canary passes with cleanup confirmed. History cleanup, hardened deployment,
and live authenticated smoke tests remain required before the incident can be
closed. The corrected CI history gate now intentionally blocks on this
incident; it must not be bypassed or allowlisted.

No credential values, prefixes, suffixes, or hashes are recorded in this
document.
