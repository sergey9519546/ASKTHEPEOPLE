#!/usr/bin/env python
"""
Data Migration Script: JSON to PostgreSQL (NON-FUNCTIONAL DRAFT)

STATUS: This script is a non-working draft. It imports from
`app.db.database` and `app.db.models.*`, which do not exist — only
`app/db/schema.py` defines ORM models today. The migration logic below is
kept as a reference skeleton for the real canonical-persistence migration
that lands with gate 3 (ADR-0012). Until then, running this script fails
fast at import time rather than silently corrupting data.

Do NOT attempt to "fix" the imports by pointing them at app.db.schema: the
schema there (UUIDv7 PKs, organization_id) is a different shape from what
this draft assumes (Integer PKs, no tenant), so the row mappings below would
be wrong. The real migration will be written against the gate-3 schema.
"""

import sys

raise ImportError(
    "migrate_json_to_postgres.py is a non-functional draft pending gate 3 "
    "(ADR-0012 canonical persistence). See module docstring."
)

# The remainder is preserved as reference for the gate-3 migration author.
import asyncio  # noqa: E402
import os  # noqa: E402
import json  # noqa: E402
import argparse  # noqa: E402
from pathlib import Path  # noqa: E402
from datetime import datetime  # noqa: E402

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Config  # noqa: E402
from app.db.database import init_db, get_db_session  # noqa: E402  (gate-3)
from app.db.models.project import ProjectDB  # noqa: E402  (gate-3)
from app.db.models.source import SourceDB  # noqa: E402  (gate-3)
from app.models.project import ProjectManager, Project  # noqa: E402


async def migrate_project(project: Project, session, dry_run: bool = False):
    """
    Migrate a single project from filesystem to database.
    
    Args:
        project: Project object from filesystem
        session: Database session
        dry_run: If True, don't commit changes
    """
    print(f"\n  Migrating project: {project.name} ({project.project_id})")
    
    # Create ProjectDB instance
    project_db = ProjectDB(
        project_id=project.project_id,
        name=project.name,
        decision_text=project.simulation_requirement,
        status=project.status.value if hasattr(project.status, 'value') else str(project.status),
        created_at=datetime.fromisoformat(project.created_at) if project.created_at else datetime.utcnow(),
        updated_at=datetime.fromisoformat(project.updated_at) if project.updated_at else datetime.utcnow(),
        user_id=None,  # No user tracking in current filesystem version
        total_text_length=project.total_text_length,
        chunk_size=project.chunk_size,
        chunk_overlap=project.chunk_overlap,
        analysis_summary=project.analysis_summary,
        simulation_requirement=project.simulation_requirement,
        graph_id=project.graph_id,
        graph_build_task_id=project.graph_build_task_id,
        error=project.error,
    )
    
    if not dry_run:
        session.add(project_db)
        await session.flush()  # Get the project.id for foreign keys
    
    # Migrate source files
    if project.files:
        print(f"    Found {len(project.files)} source files")
        for file_info in project.files:
            source_db = SourceDB(
                project_id=project_db.id if not dry_run else 0,
                filename=file_info.get('saved_filename', file_info.get('filename', 'unknown')),
                original_filename=file_info.get('original_filename', file_info.get('filename', 'unknown')),
                file_path=file_info.get('path', ''),
                file_size=file_info.get('size', 0),
                content_hash=None,  # Could compute hash from file if needed
                upload_date=datetime.utcnow(),
            )
            if not dry_run:
                session.add(source_db)
    
    print(f"    ✓ Project migrated successfully")
    return project_db


async def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description='Migrate project data from JSON to PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Preview migration without committing')
    args = parser.parse_args()
    
    print("=" * 60)
    print("JSON to PostgreSQL Migration Script")
    print("=" * 60)
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be committed\n")
    
    # Initialize database
    try:
        database_url = Config.DATABASE_URL
        print(f"\nDatabase URL: {database_url.split('@')[-1] if '@' in database_url else database_url}")
        init_db(database_url)
        print("✓ Database connection initialized")
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}")
        sys.exit(1)
    
    # Get all projects from filesystem
    try:
        projects = ProjectManager.list_projects(limit=1000)
        print(f"\n✓ Found {len(projects)} projects in filesystem storage")
    except Exception as e:
        print(f"✗ Failed to read filesystem projects: {e}")
        sys.exit(1)
    
    if not projects:
        print("\nNo projects to migrate. Exiting.")
        return
    
    # Migrate each project
    migrated_count = 0
    failed_count = 0
    
    async with get_db_session() as session:
        for project in projects:
            try:
                await migrate_project(project, session, dry_run=args.dry_run)
                migrated_count += 1
            except Exception as e:
                print(f"    ✗ Failed to migrate project {project.project_id}: {e}")
                failed_count += 1
        
        if not args.dry_run:
            await session.commit()
            print(f"\n✓ Changes committed to database")
        else:
            print(f"\n⚠️  Dry run complete - no changes committed")
    
    # Summary
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"  Total projects: {len(projects)}")
    print(f"  Successfully migrated: {migrated_count}")
    print(f"  Failed: {failed_count}")
    
    if args.dry_run:
        print("\n  Run without --dry-run to commit changes to database")
    else:
        print("\n  ✓ Migration complete!")
        print("\n  Note: Filesystem data is preserved. You can safely delete")
        print("  the filesystem storage after verifying the migration.")
    
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
