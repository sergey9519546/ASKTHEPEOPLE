# Security Incident — Public Historical Provider Credentials

## Status

**OPEN · CRITICAL · ROTATION REQUIRED**

Do not deploy or use provider-connected environments until containment is
complete.

## What was confirmed

A full-history, value-redacted review found that public commit
`65403183ba37cefbcc73d23d9fdf666750db3ddc` replaced placeholders in
`.env.example` with three credential-shaped provider values for one revision.
That commit is an ancestor of `origin/main`, and the GitHub repository is
public.

Safe exact-value comparisons were performed without printing values:

- The historical Zep credential exactly matched the current local and Railway
  production value at discovery time.
- The historical Brave credential exactly matched the current local and
  Railway production value at discovery time.
- The historical OpenAI-compatible LLM credential did not match the current
  local value. It must still be treated as compromised unless provider-side
  revocation is independently confirmed.

The current `.env` is ignored and was not itself committed. That does not undo
the historical exposure.

## Immediate containment order

1. Revoke the exposed Zep and Brave credentials in their provider consoles.
2. Revoke or confirm prior revocation of the historical LLM credential.
3. Issue new credentials with the narrowest available scopes and limits.
4. Update local secret storage and Railway variables through their secure
   interfaces. Never paste replacements into source, chat, logs, issues, or
   workflow output.
5. Restart/redeploy only after `APP_TOKEN`, exact origins, the replacement
   provider credentials, and the hardened revision are configured.
6. Review provider usage, billing, and audit logs from the first public commit
   date through containment.
7. Run the improved secret scan across all refs and retain the redacted result.
   This verification is complete: the clean-checkout-equivalent tree scan had
   zero findings, while the fully redacted all-ref history scan found exactly
   the three known historical provider credentials and failed closed.

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
testing are **NO-GO** until rotation is independently verified. History cleanup,
usage review, hardened deployment, and live authenticated smoke tests remain
required before the incident can be closed. The corrected CI history gate now
intentionally blocks on this incident; it must not be bypassed or allowlisted.

No credential values, prefixes, suffixes, or hashes are recorded in this
document.
