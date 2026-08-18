"""Add path aggregate tables for first-class paths and path-set reviews

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-11 10:30:00.000000

Creates the PostgreSQL tables the pure-domain kernel in
``app/domain/possible_path.py`` needs to persist path sets, individual paths,
and path-set reviews. Follows the same pattern as ``a1b2c3d4e5f6`` (Task 5/4
domain aggregates): UUID PKs, org/workspace scoping, optimistic-concurrency
version columns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('dw_path_sets',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('public_id', sa.String(64), nullable=False),
        sa.Column('organization_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('content_sha256', sa.String(64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_dw_path_sets_public_id', 'dw_path_sets', ['public_id'], unique=True)
    op.create_index('ix_dw_path_sets_run', 'dw_path_sets', ['run_id'])

    op.create_table('dw_paths',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('public_id', sa.String(64), nullable=False),
        sa.Column('semantic_id', sa.String(64), nullable=False),
        sa.Column('organization_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('run_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('path_set_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('display_code', sa.String(8), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('branch_trigger', sa.Text(), nullable=False),
        sa.Column('bounded_rationale', sa.Text(), nullable=False),
        sa.Column('scenario_frame', sa.Text(), nullable=False),
        sa.Column('content_json', sa.JSON(), nullable=False),
        sa.Column('content_sha256', sa.String(64), nullable=False),
        sa.Column('distinctness_sha256', sa.String(64), nullable=False),
        sa.Column('origin', sa.String(32), nullable=False, server_default='GENERATED_GENERATED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_dw_paths_public_id', 'dw_paths', ['public_id'], unique=True)
    op.create_index('ix_dw_paths_path_set', 'dw_paths', ['path_set_id'])
    op.create_index('ix_dw_paths_content_hash', 'dw_paths', ['content_sha256'])

    op.create_table('dw_path_set_reviews',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('path_set_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reviewer_actor_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('items_json', sa.JSON(), nullable=False),
        sa.Column('content_sha256', sa.String(64), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_dw_path_set_reviews_set', 'dw_path_set_reviews', ['path_set_id'])


def downgrade() -> None:
    op.drop_table('dw_path_set_reviews')
    op.drop_table('dw_paths')
    op.drop_table('dw_path_sets')
