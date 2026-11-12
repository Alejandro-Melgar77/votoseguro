"""0005_sprint2_phase2_ai_local

Revision ID: 0005_sprint2_p2
Revises: 0004_sprint2_p1
Create Date: 2026-11-11 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0005_sprint2_p2'
down_revision: Union[str, None] = '0004_sprint2_p1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    uuid_type = postgresql.UUID(as_uuid=True) if is_postgres else sa.String(36)
    json_type = postgresql.JSONB() if is_postgres else sa.JSON()

    # 1. Nuevas columnas en import_issue para la segunda opinión de IA (IA-L2b)
    op.add_column('import_issue', sa.Column('ai_verdict', sa.String(32), nullable=True))
    op.add_column('import_issue', sa.Column('ai_reason', sa.Text(), nullable=True))
    op.add_column('import_issue', sa.Column('ai_model', sa.String(64), nullable=True))
    op.add_column('import_issue', sa.Column('ai_evaluated_at', sa.DateTime(timezone=True), nullable=True))

    # 2. Nueva tabla anomaly_alert (IA-L1)
    op.create_table(
        'anomaly_alert',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organization.id', ondelete='CASCADE'), nullable=False),
        sa.Column('election_id', uuid_type, sa.ForeignKey('election.id', ondelete='CASCADE'), nullable=False),
        sa.Column('group_id', uuid_type, sa.ForeignKey('voter_group.id', ondelete='SET NULL'), nullable=True),
        sa.Column('node_id', uuid_type, sa.ForeignKey('unit_node.id', ondelete='SET NULL'), nullable=True),
        sa.Column('anomaly_type', sa.String(64), nullable=False),
        sa.Column('severity', sa.String(24), nullable=False, server_default='MEDIUM'),
        sa.Column('metric_value', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('baseline_value', sa.Float(), nullable=True),
        sa.Column('metrics_summary', json_type, nullable=False),
        sa.Column('ai_explanation', sa.Text(), nullable=False),
        sa.Column('ai_suggested_checks', json_type, nullable=False),
        sa.Column('ai_source', sa.String(40), nullable=False, server_default='DETERMINISTIC_FALLBACK'),
        sa.Column('status', sa.String(24), nullable=False, server_default='OPEN'),
        sa.Column('reviewed_by', uuid_type, sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_anomaly_alert_election_id', 'anomaly_alert', ['election_id'])
    op.create_index('ix_anomaly_alert_organization_id', 'anomaly_alert', ['organization_id'])
    op.create_index('ix_anomaly_alert_created_at', 'anomaly_alert', ['created_at'])

    # 3. Nueva tabla kb_document_chunk (IA-L5)
    op.create_table(
        'kb_document_chunk',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('doc_slug', sa.String(100), nullable=False),
        sa.Column('section_title', sa.String(200), nullable=False),
        sa.Column('audience', sa.String(32), nullable=False, server_default='VOTER'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('keywords', sa.String(255), nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_kb_document_chunk_doc_slug', 'kb_document_chunk', ['doc_slug'])


def downgrade() -> None:
    op.drop_index('ix_kb_document_chunk_doc_slug', table_name='kb_document_chunk')
    op.drop_table('kb_document_chunk')

    op.drop_index('ix_anomaly_alert_created_at', table_name='anomaly_alert')
    op.drop_index('ix_anomaly_alert_organization_id', table_name='anomaly_alert')
    op.drop_index('ix_anomaly_alert_election_id', table_name='anomaly_alert')
    op.drop_table('anomaly_alert')

    op.drop_column('import_issue', 'ai_evaluated_at')
    op.drop_column('import_issue', 'ai_model')
    op.drop_column('import_issue', 'ai_reason')
    op.drop_column('import_issue', 'ai_verdict')
