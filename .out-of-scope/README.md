# Out-of-scope knowledge base

One file per **concept** that has been considered and rejected. When an issue
arrives asking for something that resembles an entry here, read the entry and
surface the prior decision to the maintainer rather than re-litigating it from
scratch.

This directory exists so that rejections are institutional memory rather than
something a future contributor has to rediscover by reading a closed issue.
An enhancement rejected as `wontfix` gets a file here; a bug never does.

## Format

Each file is a short design note, not a database row. It should read sensibly to
someone who has never seen the issue it came from.

```markdown
# Concept Name

One-sentence statement of what is not supported.

## Why this is out of scope

Substantive reasoning: what supporting it would require, which architecture or
decision it conflicts with, and why that conflict is worth keeping. Refer to the
ADR, decision, or constraint that settles it so the reason is checkable rather
than folklore.

## Prior requests

- #NN — "the request as filed"
```

## Rules

- **One file per concept, not per issue.** Several requests for the same idea are
  appended to the same file.
- **Reasons must be durable.** "We are too busy" is a deferral, not a
  rejection, and belongs in an issue backlog rather than here.
- **Cite the constraint.** Prefer naming the ADR or decision that settles the
  question over asserting a preference.
- **Archived material is not a source.** `docs/archive/` records what was once
  believed; it cannot overrule a live ADR.
- If the maintainer changes their mind, **delete the file**. Closed issues are
  historical record and are not reopened.