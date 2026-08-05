"""Read-only access to the per-simulation OASIS platform SQLite databases.

These databases (`reddit_simulation.db`, `twitter_simulation.db`) are written
by the simulation runner and read by the `/posts` and `/comments` routes.
The route-responsibility contract (ADR-0011) wants route handlers to
`auth → parse → authorize → dispatch → present`, not to open SQLite, build
cursors, and distinguish locked/corrupt/missing-table errors inline. This
module is the service seam those routes dispatch to.

All access is read-only (`mode=ro` URI), with a bounded busy timeout and
explicit classification of the four failure modes the audit §5 P0 required
correction distinguishes: missing database, missing table, locked database,
and corrupt database.
"""

import os
import sqlite3
from typing import Dict, List, Optional, Tuple

from ..utils.logger import get_logger

logger = get_logger('askthepeople.services.activity_reader')


# Canonical platform→filename map (audit §5 P0 path-escape fix). The platform
# identifier is request-controlled, so callers MUST resolve it through this
# allowlist rather than interpolating request text into a path. This is the
# single source of truth for the /posts read path: the route validates a
# request platform against it, and read_posts indexes it. Defining it once
# here removes a drift trap where the route accepts a platform the service
# cannot resolve (KeyError → 500). Other route modules keep their own copies
# for now; consolidating those is further gate-1 cleanup.
ALLOWED_PLATFORMS = {
    "reddit": "reddit_simulation.db",
    "twitter": "twitter_simulation.db",
}


class DatabaseUnavailable(Exception):
    """The simulation database does not exist or cannot be opened."""


class DatabaseLocked(Exception):
    """The database is locked by a writer; retry later (HTTP 423)."""


class DatabaseCorrupt(Exception):
    """The database file is malformed (HTTP 500)."""


def _classify_operational_error(exc: sqlite3.OperationalError) -> Exception:
    """Map a sqlite3 OperationalError to one of the typed reader exceptions,
    falling back to DatabaseUnavailable for anything unrecognized."""
    msg = str(exc).lower()
    if "database is locked" in msg:
        return DatabaseLocked(str(exc))
    if "database disk image is malformed" in msg:
        return DatabaseCorrupt(str(exc))
    if "no such table" in msg:
        # A missing table is not an error condition — the simulation may not
        # have produced that artifact yet. Callers treat None as "empty".
        return DatabaseUnavailable(str(exc))
    return DatabaseUnavailable(str(exc))


def _open_readonly(db_path: str) -> sqlite3.Connection:
    """Open the database read-only with a bounded busy timeout.

    Raises DatabaseUnavailable / DatabaseLocked / DatabaseCorrupt so callers
    never handle raw sqlite3 errors.
    """
    db_uri = f"file:{db_path}?mode=ro"
    try:
        return sqlite3.connect(db_uri, uri=True, timeout=5.0)
    except sqlite3.OperationalError as exc:
        msg = str(exc).lower()
        if "database disk image is malformed" in msg:
            logger.error("Activity sqlite is corrupt: %s", db_path)
            raise DatabaseCorrupt(str(exc)) from exc
        # "unable to open" / "no such file" — treat as not-present.
        raise DatabaseUnavailable(str(exc)) from exc


def read_posts(
    sim_dir: str, platform: str, limit: int, offset: int
) -> Tuple[List[Dict], int]:
    """Return (posts, total) for the given platform's post table.

    A missing database or missing post table returns ([], 0) — the simulation
    may simply not have run or produced posts yet. Locked/corrupt databases
    raise DatabaseLocked / DatabaseCorrupt for the route to map to 423/500.
    """
    db_file = ALLOWED_PLATFORMS[platform]
    db_path = os.path.join(sim_dir, db_file)
    if not os.path.exists(db_path):
        return [], 0

    try:
        conn = _open_readonly(db_path)
    except DatabaseUnavailable:
        return [], 0

    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        try:
            cursor.execute(
                "SELECT * FROM post ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            posts = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT COUNT(*) FROM post")
            total = cursor.fetchone()[0]
            return posts, total
        except sqlite3.OperationalError as exc:
            raise _classify_operational_error(exc) from exc
    finally:
        try:
            conn.close()
        except Exception:  # pragma: no cover - best-effort close
            pass


def read_comments(
    sim_dir: str,
    limit: int,
    offset: int,
    post_id: Optional[str] = None,
) -> List[Dict]:
    """Return comments (Reddit only).

    A missing database or missing comment table returns [] (the simulation
    may not have run or produced comments yet). A locked or corrupt database
    raises DatabaseLocked / DatabaseCorrupt for the route to map to 423/500.
    """
    db_path = os.path.join(sim_dir, "reddit_simulation.db")
    if not os.path.exists(db_path):
        return []

    try:
        conn = _open_readonly(db_path)
    except DatabaseUnavailable:
        return []

    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        if post_id:
            cursor.execute(
                "SELECT * FROM comment WHERE post_id = ? "
                "ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (post_id, limit, offset),
            )
        else:
            cursor.execute(
                "SELECT * FROM comment ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError as exc:
        # Missing comment table is not an error; locked/corrupt propagate.
        if "no such table" in str(exc).lower():
            return []
        raise _classify_operational_error(exc) from exc
    finally:
        # Guard the close so a close-time error cannot mask a typed reader
        # exception raised above (matches read_posts' discipline).
        try:
            conn.close()
        except Exception:  # pragma: no cover - best-effort close
            pass
