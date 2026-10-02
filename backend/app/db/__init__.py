import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.schema import Base

def get_engine(database_url: str = None):
    """
    Get SQLAlchemy engine. Uses SQLite for local dev if not specified.
    Supports PostgreSQL for production.
    """
    if database_url is None:
        database_url = os.environ.get("DATABASE_URL", "sqlite:///./local_dev.db")
        
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        
    engine = create_engine(database_url, connect_args=connect_args)
    return engine

def get_session_factory(engine):
    """Get SQLAlchemy session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db(engine):
    """REFUSED. Schema creation is Alembic-only.

    This used to call ``Base.metadata.create_all`` at application boot. ADR-0012
    forbids that ("web and worker startup never call ``create_all``") and
    ADR-0013 makes ``backend/migrations/versions/`` the single source of truth.

    It was also actively harmful rather than merely redundant: the ORM stub's
    ``projects`` table lacks the ``project_id`` column that
    ``services/project_repository.py`` queries, so a database built by this
    function could not serve the one repository that targets the canonical
    store.

    To create the schema, run ``alembic upgrade head`` as an explicit deploy
    step. This function raises so that any surviving caller fails loudly at
    import-and-call time rather than silently reintroducing the old behaviour.
    """
    raise RuntimeError(
        "init_db() is removed: schema creation is Alembic-only (ADR-0012, "
        "ADR-0013). Run 'alembic upgrade head' as an explicit deploy step. "
        "This function used to call Base.metadata.create_all at boot, which "
        "built a projects table missing the project_id column that "
        "services/project_repository.py requires."
    )

def drop_db(engine):
    """Drop all tables, mostly for test cleanup."""
    Base.metadata.drop_all(bind=engine)


class CanonicalSchemaMissing(RuntimeError):
    """The canonical store is reachable but its tables are not present.

    Raised when a repository is asked to query a table that no migration
    created. This is the loud failure exec-plan T6 asks for. Previously the
    same condition surfaced as a raw driver ``UndefinedTable`` at the first
    query, which named a SQL fragment rather than the missing table and gave
    no indication that a migration had not been run.
    """


def missing_tables(engine, expected) -> set:
    """Return the subset of ``expected`` that is absent from the database.

    ``expected`` is an iterable of table names. Presence is read from
    ``information_schema`` on PostgreSQL and from ``sqlite_master`` elsewhere,
    so this works against the SQLite databases used by tests without pretending
    to be a migration check.
    """
    from sqlalchemy import inspect

    present = set(inspect(engine).get_table_names())
    return set(expected) - present


def require_tables(engine, expected) -> None:
    """Fail loudly, naming the missing tables and the remediation.

    Call this from a repository's engine accessor. The failure is deliberately
    explicit about the next action, because the operator who hits it is usually
    looking at a database that exists and is reachable.
    """
    missing = missing_tables(engine, expected)
    if not missing:
        return
    raise CanonicalSchemaMissing(
        "canonical store is missing {count} table(s): {tables}. The database "
        "is reachable but was never migrated. Schema is created only by "
        "Alembic (ADR-0012, ADR-0013); run 'alembic upgrade head' as an "
        "explicit deploy step, or unset the feature flag that enabled the "
        "canonical store to fall back to filesystem persistence. Startup does "
        "not create schema by design.".format(
            count=len(missing),
            tables=", ".join(sorted(missing)),
        )
    )
