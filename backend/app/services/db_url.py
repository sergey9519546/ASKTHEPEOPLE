"""Database URL normalisation for the synchronous canonical-store engines.

Extracted 2026-10-02 while verifying repository reachability.

`_ensure_psycopg_driver` lived in `services/run_repository.py`. That module's
`RunRepository` class turned out to have no production importer at all, so the
helper was the only reason a live module (`services/source_repository.py`)
imported a file whose main export nothing used. Importing a live code path from
a dead module's private helper is the kind of coupling that makes the dead
module impossible to remove without breaking something real.

The logic is unchanged. It is also not new: `services/project_repository.py`
carries an inline copy of the same normalisation, which is the remaining
duplicate worth collapsing.

Nothing here touches credential handling or connection options. It rewrites a
URL scheme and nothing else.
"""

from __future__ import annotations


def ensure_psycopg_driver(url: str) -> str:
    """Force the psycopg3 driver on a PostgreSQL URL.

    `postgresql://` and `postgres://` are both accepted spellings for a
    PostgreSQL DSN, and SQLAlchemy will not infer the driver for either when
    the scheme carries no ``+driver``. An explicit scheme is left alone, so a
    caller that already chose ``postgresql+psycopg2://`` or a non-PostgreSQL
    URL keeps it.
    """
    if url.startswith("postgresql://") and "+" not in url.split("://", 1)[0]:
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url