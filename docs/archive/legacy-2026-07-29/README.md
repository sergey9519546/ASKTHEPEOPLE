# Legacy documentation archive (2026-07-29)

**Status:** Superseded. Retained for audit only.
**Archived during:** Documentation authority migration to `docs/` per
[`INTEGRATION_GUIDE.md`](../../INTEGRATION_GUIDE.md).
**Repository baseline at archive time:** commit `8b616dc7fa02eeed5ada8c51998d8b197be28f8d` on `main`.

This directory contains pre-authority documentation that lived at the top of
`docs/` before the production documentation system was adopted. The new
authority is the modular document set under [`../../README.md`](../../README.md)
(Normative status, 12 ADRs, 48 modular docs, see
[`../../SOURCES.md`](../../SOURCES.md)).

These documents are kept so that:

- prior engineering, security, and design decisions can still be referenced
  by commit hash;
- the original MiroFish → ASKTHEPEOPLE provenance trail remains intact;
- historical audits and incident reports are not silently lost.

**Do not link new work to anything in this archive.** New citations MUST point
to the corresponding normative document under `docs/`. If you need to cite a
specific fact that only exists here, cite it as "legacy archive, `…`" and open
a follow-up to either restore that fact to the live authority or formally
reject it.

The structural validator (`tools/validate_docs.py`) intentionally excludes this
directory. The archive is not subject to the same front-matter, heading,
footnote, and link rules as the live authority.

## Reconciliation map

| Archived document | Disposition | Current authority |
|---|---|---|
| `APPROPRIATE_USE.md` | superseded | [`docs/product/USE_POLICY.md`](../../product/USE_POLICY.md) |
| `AUDIT-2026-07-28.md` | superseded by the integrated build plan + 12 ADRs | [`docs/architecture/index.md`](../../architecture/index.md), [`ASKTHEPEOPLE_GODMODE_BUILDPLAN.md`](../../../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md) |
| `AUDIT-security-2026-07-28.md` | superseded | [`docs/security/THREAT_MODEL.md`](../../security/THREAT_MODEL.md), [`docs/security/SOURCE_INGESTION.md`](../../security/SOURCE_INGESTION.md) |
| `DEPLOYMENT.md` | superseded | [`docs/release/RUNBOOK.md`](../../release/RUNBOOK.md) |
| `DESIGN-DIRECTION-C.md` | superseded | [`docs/design/DIRECTION_C.md`](../../design/DIRECTION_C.md) |
| `METHODOLOGY.md` | superseded | [`docs/product/METHODOLOGY.md`](../../product/METHODOLOGY.md) |
| `PROVENANCE.md` | preserved at root (project lineage) | (relocated to repo root, no longer archived) |
| `SECURITY-INCIDENT-2026-07-29.md` | superseded | [`docs/security/INCIDENT_RESPONSE.md`](../../security/INCIDENT_RESPONSE.md) |
| `THIRD_PARTY_NOTICES.md` | preserved at root (license attributions) | (relocated to repo root, no longer archived) |
| `VALIDATE_WITH_PEOPLE.md` | superseded | [`docs/product/METHODOLOGY.md`](../../product/METHODOLOGY.md) §"Human-validation handoff" |
| `plans/2026-03-23-hardening-plan.md` | superseded | [`docs/exec-plans/`](../../exec-plans/README.md) (8 plans, 00–07) |
| `superpowers/specs/2026-03-24-production-crash-remediation-design.md` | superseded | [`docs/release/ACCEPTANCE.md`](../../release/ACCEPTANCE.md), [`docs/release/RUNBOOK.md`](../../release/RUNBOOK.md) |

## Divergences recorded at archive time

Per `INTEGRATION_GUIDE.md` §2, the documentation system was authored against
repository commit `c33a6a9127fa0705cfff426053f54815f58b4755`. The
documentation-system target state is the contract; the current implementation
baseline is `8b616dc7fa02eeed5ada8c51998d8b197be28f8d`. Recorded divergences
between the two include (non-exhaustive, full census pending
[`docs/exec-plans/00-repository-census-and-governance.md`](../../exec-plans/00-repository-census-and-governance.md)):

- 30+ commits between the two baselines; the working tree included new
  data fixtures, agent profile JSON, and entity type registries at
  archive time.
- The current implementation has not yet adopted the
  authoritative state machines, the durable orchestration layer, the
  PostgreSQL canonical store, the object-storage artifact layer, the
  multi-tenant authorization model, or the prompt registry referenced by
  the new docs. Those remain target-state requirements, not current
  capabilities.
- The `backend/app/api/simulation.py` controller was not yet decomposed
  per the audit. The release blockers identified in
  [`ASKTHEPEOPLE_GODMODE_BUILDPLAN.md`](../../../ASKTHEPEOPLE_GODMODE_BUILDPLAN.md)
  still apply.

A complete divergence report is required from
[`docs/exec-plans/00-repository-census-and-governance.md`](../../exec-plans/00-repository-census-and-governance.md)
before any release claim citing the new authority is made.
