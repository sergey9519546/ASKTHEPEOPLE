"""Add domain aggregate tables for durable runs and source ingestion

Revision ID: a1b2c3d4e5f6
Revises: 384c98f88d53
Create Date: 2026-08-11 09:00:00.000000

Creates the PostgreSQL tables the pure-domain kernels in
``app/domain/run_attempt.py`` and ``app/domain/source_ingestion.py`` need
to persist state. These tables are the canonical store for the run control
plane (Task 5) and the source-ingestion aggregate (Task 4), per ADR-0012.

Every table carries:
- ``organization_id`` / ``workspace_id`` for tenant isolation (ADR-0009);
- ``version`` for optimistic concurrency;
- ``created_at`` / ``updated_at`` timestamps;
- UUIDv7 primary keys (physical identity per the authority packet).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '384c98f88d53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- Run control plane (Task 5, domain/run_attempt.py) ---- #

    op.create_table('dw_runs',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('public_id', sa.String(64), nullable=False),
        sa.Column('organization_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_config_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_run_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('state', sa.String(32), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('current_stage_code', sa.String(64), nullable=True),
        sa.Column('stop_fence', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('human_respondents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_forecast', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('output_origin', sa.String(32), nullable=False, server_default='synthetic'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_runs_public_id', 'dw_runs', ['public_id'], unique=True)
    op.create_index('ix_runs_org_workspace', 'dw_runs', ['organization_id', 'workspace_id'])
    op.create_index('ix_runs_state', 'dw_runs', ['state'])

    op.create_table('dw_run_stages',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stage_code', sa.String(64), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('state', sa.String(32), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('lease_token', sa.String(128), nullable=True),
        sa.Column('lease_fence', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_run_stages_run', 'dw_run_stages', ['run_id'])
    op.create_index('ix_run_stages_run_stage_attempt', 'dw_run_stages', ['run_id', 'stage_code', 'attempt_number'], unique=True)

    op.create_table('dw_run_events',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('command', sa.String(64), nullable=False),
        sa.Column('from_state', sa.String(32), nullable=False),
        sa.Column('to_state', sa.String(32), nullable=False),
        sa.Column('next_version', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('actor_type', sa.String(32), nullable=False),
        sa.Column('actor_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('idempotency_key', sa.String(128), nullable=False),
        sa.Column('reason_code', sa.String(64), nullable=False),
        sa.Column('guard_payload', sa.JSON(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_run_events_run', 'dw_run_events', ['run_id'])
    op.create_index('ix_run_events_idempotency', 'dw_run_events', ['run_id', 'idempotency_key'], unique=True)

    # ---- Source ingestion (Task 4, domain/source_ingestion.py) ---- #

    op.create_table('dw_sources',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('public_id', sa.String(64), nullable=False),
        sa.Column('organization_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('current_version_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_by_actor_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sources_public_id', 'dw_sources', ['public_id'], unique=True)
    op.create_index('ix_sources_org_workspace_project', 'dw_sources', ['organization_id', 'workspace_id', 'project_id'])

    op.create_table('dw_source_versions',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('public_id', sa.String(64), nullable=False),
        sa.Column('organization_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('state', sa.String(32), nullable=False),
        sa.Column('original_filename_display', sa.String(512), nullable=False),
        sa.Column('declared_media_type', sa.String(128), nullable=False),
        sa.Column('detected_media_type', sa.String(128), nullable=True),
        sa.Column('raw_object_ref', sa.String(512), nullable=True),
        sa.Column('processed_object_ref', sa.String(512), nullable=True),
        sa.Column('raw_byte_length', sa.Integer(), nullable=True),
        sa.Column('normalized_byte_length', sa.Integer(), nullable=True),
        sa.Column('normalized_token_count', sa.Integer(), nullable=True),
        sa.Column('scanner_name', sa.String(128), nullable=True),
        sa.Column('scanner_version', sa.String(64), nullable=True),
        sa.Column('scanner_definitions_version', sa.String(64), nullable=True),
        sa.Column('parser_name', sa.String(128), nullable=True),
        sa.Column('parser_version', sa.String(64), nullable=True),
        sa.Column('processing_fence', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('deletion_fence', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_by_actor_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_source_versions_public_id', 'dw_source_versions', ['public_id'], unique=True)
    op.create_index('ix_source_versions_source', 'dw_source_versions', ['source_id'])
    op.create_index('ix_source_versions_state', 'dw_source_versions', ['state'])

    op.create_table('dw_source_segments',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('public_id', sa.String(64), nullable=False),
        sa.Column('organization_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_version_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ordinal', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('char_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_source_segments_version', 'dw_source_segments', ['source_version_id'])

    op.create_table('dw_source_candidates',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('public_id', sa.String(64), nullable=False),
        sa.Column('organization_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_version_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('segment_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('condition_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('disposition', sa.String(32), nullable=False, server_default='PENDING'),
        sa.Column('extracted_statement', sa.Text(), nullable=True),
        sa.Column('accepted_statement', sa.Text(), nullable=True),
        sa.Column('revised_statement', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_source_candidates_version', 'dw_source_candidates', ['source_version_id'])
    op.create_index('ix_source_candidates_disposition', 'dw_source_candidates', ['disposition'])


def downgrade() -> None:
    op.drop_table('dw_source_candidates')
    op.drop_table('dw_source_segments')
    op.drop_table('dw_source_versions')
    op.drop_table('dw_sources')
    op.drop_table('dw_run_events')
    op.drop_table('dw_run_stages')
    op.drop_table('dw_runs')
