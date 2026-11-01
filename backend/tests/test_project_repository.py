"""Unit and regression tests for ProjectRepository batch ontology loading."""

from datetime import datetime
import json
from pathlib import Path
import sys
import pytest
from sqlalchemy import create_engine, text, event

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.project_repository import ProjectRepository  # noqa: E402


@pytest.fixture
def repo_engine(tmp_path):
    """In-memory SQLite database populated with canonical tables."""
    engine = create_engine(f"sqlite:///{tmp_path / 'test_repo.db'}", future=True)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id VARCHAR(64) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(32) NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                total_text_length INTEGER DEFAULT 0,
                chunk_size INTEGER DEFAULT 500,
                chunk_overlap INTEGER DEFAULT 50,
                analysis_summary TEXT,
                simulation_requirement TEXT,
                graph_id VARCHAR(64),
                graph_build_task_id VARCHAR(64),
                error TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                filename VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(1024) NOT NULL,
                file_size INTEGER NOT NULL,
                content_hash VARCHAR(64) NOT NULL,
                upload_date TIMESTAMP NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE ontologies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                task_id VARCHAR(64),
                status VARCHAR(32) NOT NULL,
                result_json JSON,
                error TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """))
    return engine


def test_batch_load_empty_project_ids(repo_engine):
    """Empty project list returns empty dict with zero queries."""
    query_count = 0
    @event.listens_for(repo_engine, 'before_cursor_execute')
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        nonlocal query_count
        query_count += 1

    with repo_engine.connect() as conn:
        result = ProjectRepository._batch_load_latest_completed_ontologies(conn, [])
        assert result == {}
        assert query_count == 0


def test_batch_load_projects_without_ontologies(repo_engine):
    """Projects without completed ontologies are omitted from the batch mapping."""
    now = datetime.now()
    with repo_engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO projects (project_id, name, status, created_at, updated_at)
            VALUES ('proj_1', 'Project 1', 'created', :now, :now),
                   ('proj_2', 'Project 2', 'created', :now, :now)
        """), {'now': now})
        # Insert a pending (non-completed) ontology for proj_1
        conn.execute(text("""
            INSERT INTO ontologies (project_id, task_id, status, result_json, created_at, updated_at)
            VALUES (1, 'task_pending', 'pending', :res, :now, :now)
        """), {'res': json.dumps({'draft': True}), 'now': now})

    with repo_engine.connect() as conn:
        result = ProjectRepository._batch_load_latest_completed_ontologies(conn, [1, 2])
        assert result == {}


def test_batch_load_multiple_ontologies_and_timestamp_tie(repo_engine):
    """Picks the latest completed ontology by updated_at DESC, then id DESC on tie."""
    now = datetime(2026, 1, 1, 12, 0, 0)
    later = datetime(2026, 1, 2, 12, 0, 0)
    with repo_engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO projects (project_id, name, status, created_at, updated_at)
            VALUES ('proj_1', 'Project 1', 'created', :now, :now),
                   ('proj_2', 'Project 2', 'created', :now, :now)
        """), {'now': now})
        # Project 1: two ontologies, one newer updated_at
        conn.execute(text("""
            INSERT INTO ontologies (id, project_id, status, result_json, created_at, updated_at)
            VALUES (1, 1, 'completed', :res1, :now, :now),
                   (2, 1, 'completed', :res2, :now, :later)
        """), {'res1': json.dumps({'version': 1}), 'res2': json.dumps({'version': 2}), 'now': now, 'later': later})
        # Project 2: two ontologies with exact same updated_at, id=4 should win over id=3
        conn.execute(text("""
            INSERT INTO ontologies (id, project_id, status, result_json, created_at, updated_at)
            VALUES (3, 2, 'completed', :res3, :later, :later),
                   (4, 2, 'completed', :res4, :later, :later)
        """), {'res3': json.dumps({'tie_winner': False}), 'res4': json.dumps({'tie_winner': True}), 'later': later})

    with repo_engine.connect() as conn:
        result = ProjectRepository._batch_load_latest_completed_ontologies(conn, [1, 2])
        assert 1 in result
        assert result[1] == {'version': 2}
        assert 2 in result
        assert result[2] == {'tie_winner': True}


def test_list_projects_executes_single_ontology_query(repo_engine, monkeypatch):
    """Project retrieval issues exactly 1 ontology query regardless of project count."""
    now = datetime.now()
    with repo_engine.begin() as conn:
        for i in range(1, 11):
            conn.execute(text("""
                INSERT INTO projects (project_id, name, status, created_at, updated_at)
                VALUES (:pid, :name, 'created', :now, :now)
            """), {'pid': f'proj_{i}', 'name': f'Project {i}', 'now': now})
            if i % 2 == 0:
                conn.execute(text("""
                    INSERT INTO ontologies (project_id, status, result_json, created_at, updated_at)
                    VALUES (:p_pk, 'completed', :res, :now, :now)
                """), {'p_pk': i, 'res': json.dumps({'project_num': i}), 'now': now})

    query_count = 0
    ontology_queries = 0
    @event.listens_for(repo_engine, 'before_cursor_execute')
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        nonlocal query_count, ontology_queries
        query_count += 1
        if 'ranked_ontologies' in statement or 'ontologies' in statement:
            ontology_queries += 1

    monkeypatch.setattr(ProjectRepository, '_get_engine', lambda: repo_engine)

    projects = ProjectRepository.list_projects(limit=10)
    assert len(projects) == 10
    # Exactly 2 queries total: 1 for projects, 1 for batch ontologies
    assert query_count == 2
    assert ontology_queries == 1

    for p in projects:
        num = int(p.project_id.split('_')[1])
        if num % 2 == 0:
            assert p.ontology == {'project_num': num}
        else:
            assert p.ontology is None


def test_list_projects_empty_table(repo_engine, monkeypatch):
    """list_projects on empty table returns empty list and does not query ontologies."""
    query_count = 0
    @event.listens_for(repo_engine, 'before_cursor_execute')
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        nonlocal query_count
        query_count += 1

    monkeypatch.setattr(ProjectRepository, '_get_engine', lambda: repo_engine)

    projects = ProjectRepository.list_projects(limit=10)
    assert projects == []
    # 1 query for projects table, 0 for ontologies
    assert query_count == 1
