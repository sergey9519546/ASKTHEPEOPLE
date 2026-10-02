import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# ---------------------------------------------------------------------------
# The ORM metadata is imported LAZILY, and only for autogenerate.
#
# Two measured defects motivated this, both verified on 2026-10-02.
#
# 1. Importing `app.db.schema` executes `app/__init__.py`, which raises
#    `SECRET_KEY must be set in production` at import time. So `alembic
#    upgrade head` could not run at all without production credentials --
#    even against a throwaway SQLite file. A migration tool must not depend
#    on the web app's secrets, and after ADR-0013 it does not need them:
#    `app/db/schema.py` now declares `Base` and no tables.
#
# 2. Because ADR-0013 stripped `app/db/schema.py` to `Base` alone,
#    `Base.metadata` is EMPTY. `alembic revision --autogenerate` therefore
#    diffs an empty target against a live database and reads every one of the
#    16 canonical tables as "removed". Measured on a database migrated to
#    head, it generated a revision whose `upgrade()` was 16 `op.drop_table`
#    and 43 `op.drop_index` calls -- a total schema wipe presented as a
#    routine revision. Autogenerate is refused below rather than left armed.
# ---------------------------------------------------------------------------
def _autogenerate_requested() -> bool:
    return bool(getattr(context.config.cmd_opts, "autogenerate", False))


def _load_target_metadata():
    """Return the ORM metadata for autogenerate, or fail loudly.

    Migrations are the single source of truth under ADR-0013, so a table is
    added by hand-writing a revision -- see ADR-0013 and `AGENTS.md` rule 9.
    Autogenerate cannot be correct in that world, and it fails DESTRUCTIVELY
    rather than obviously, which is the worst combination available.
    """
    # Refuse on the ADR-0013 state before touching the import, so the operator
    # reads the real cause rather than whatever the app's credential gate says
    # first. Importing `app.db.schema` executes `app/__init__.py`, which
    # raises without SECRET_KEY; surfacing that as the headline would point at
    # the wrong problem entirely.
    reason = (
        "alembic revision --autogenerate is disabled on purpose.\n"
        "ADR-0013 removed every table declaration from app/db/schema.py, so the "
        "ORM metadata is empty and autogenerate would diff an empty target "
        "against the live database and emit op.drop_table() for all 16 "
        "canonical tables -- a total schema wipe presented as a routine "
        "revision.\n"
        "To add a table, hand-write a revision. backend/migrations/versions/ is "
        "the single source of truth for schema (ADR-0012, ADR-0013, "
        "AGENTS.md rule 9). To check the current head: alembic heads."
    )

    try:
        from app.db.schema import Base
    except Exception as exc:  # noqa: BLE001 - the import is advisory here
        raise RuntimeError(reason) from exc

    if not Base.metadata.tables:
        raise RuntimeError(reason)
    return Base.metadata


target_metadata = _load_target_metadata() if _autogenerate_requested() else None

# Get DATABASE_URL from environment, with fallback to SQLite
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

database_url = os.environ.get('DATABASE_URL', 'sqlite:///./askthepeople.db')

# Convert postgres:// to postgresql:// for SQLAlchemy (sync mode for migrations)
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
elif database_url.startswith('postgresql+asyncpg://'):
    # For migrations, use psycopg2 (sync) instead of asyncpg
    database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://', 1)
elif database_url.startswith('sqlite+aiosqlite://'):
    # For migrations, use standard sqlite
    database_url = database_url.replace('sqlite+aiosqlite://', 'sqlite:///', 1)

# Set the sqlalchemy.url in config
config.set_main_option('sqlalchemy.url', database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
