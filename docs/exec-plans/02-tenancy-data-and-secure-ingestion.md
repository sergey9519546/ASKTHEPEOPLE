---
title: "Execution Plan 02 — Tenancy, Data, and Secure Ingestion"
status: "Operational"
version: "1.0.0"
owner: "Platform + Security + Privacy"
last_reviewed: "2026-07-29"
review_cycle: "Quarterly"
research_cutoff: "2026-07-29"
---

# Execution Plan 02 — tenancy, data, and secure ingestion

## Objective

Create the production tenant boundary, transactional data model, object-storage
separation, and zero-trust source pipeline.

## Dependencies

- Plan 00 baseline.
- Product truth enums and domain validation from Plan 01.
- Approved identity/provider choices before production.

## Workstreams

### A. Organization and authorization model

Implement organizations, users, memberships, roles, invitations, projects, and
capability checks. Authorization lives in domain/application services and is
tested at every object boundary.

### B. PostgreSQL migration

- add versioned migrations;
- use UUIDv7 domain IDs;
- introduce organization scope;
- create append-only audit events;
- implement RLS defense in depth;
- configure production roles so ordinary application roles cannot bypass RLS;
- migrate SQLite/JSONL data with reconciliation;
- preserve read-only rollback snapshot during migration window.

### C. Object storage

Create separate quarantine, processed, and export prefixes/buckets with scoped
credentials, lifecycle rules, encryption, audit logs, and tenant key structure.

### D. Upload coordinator

Implement rights attestation, quota reservation, presigned upload, generated
safe filenames, state machine, content-length constraints, and safe status APIs.

### E. Isolated parsing

Build a worker image and sandbox:

- no network;
- non-root/read-only;
- file, memory, CPU, time, and process limits;
- parser allowlist;
- malware/CDR integration;
- OCR only when required;
- exact location and hash preservation;
- destroy ephemeral workspace.

### F. Injection and sensitive-content review

Add deterministic/heuristic flags and an adversarial model classifier only as
supplemental triage. Build a review interface. Source content remains
untrusted after passing detection.

### G. Candidate extraction

Implement Stage S02 with structured outputs and exact source segment IDs.
Candidate conditions enter review; they do not become path evidence.

### H. Retention/deletion

Apply quarantine and source retention classes. Implement deletion across
primary stores, provider calls, indexes, caches, exports, and backup ledger.

## Security corpus

Include:

- extension/MIME/signature mismatch;
- polyglot files;
- malformed PDF/DOCX;
- macro and embedded object;
- zip/decompression bomb;
- huge page/object count;
- parser timeout;
- hidden/low-contrast instruction;
- image/OCR injection;
- encoded and multilingual injection;
- payload split across files;
- credentials and sensitive identifiers;
- path traversal filenames;
- cross-tenant object IDs.

## Acceptance evidence

- no cross-tenant data access in API, DB, object, worker, or export tests;
- PostgreSQL migration reconciles counts/hashes and can restore safely;
- sandbox has no network/secrets and survives malicious corpus;
- every approved condition resolves to source location;
- flagged content requires review;
- source instructions cannot invoke tools or change stage policy;
- deletion completes truthfully across stores;
- data map and subprocessor register match actual egress;
- security/privacy owners approve production enablement.

## Rollback

During dual-read migration, the legacy store remains read-only after cutover.
Rollback restores traffic to the reconciled snapshot and replays accepted
writes if designed and tested. Uploaded files remain quarantined until the new
pipeline is proven; never fall back to unsandboxed parsing.
