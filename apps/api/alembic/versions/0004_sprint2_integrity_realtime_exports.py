"""0004_sprint2_integrity_realtime_exports

Revision ID: 0004_sprint2_p1
Revises: 0003_iter3_voting
Create Date: 2026-11-11 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0004_sprint2_p1'
down_revision: Union[str, None] = '0003_iter3_voting'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'

    # 1. Nuevas columnas en election
    op.add_column('election', sa.Column('registration_mode', sa.String(32), nullable=False, server_default='LINK_ONLY'))
    op.add_column('election', sa.Column('merkle_root', sa.String(64), nullable=True))
    op.add_column('election', sa.Column('votes_chain_head', sa.String(64), nullable=True))

    # 2. Nuevas columnas en voter y soporte de PENDING_APPROVAL
    if is_postgres:
        op.execute("ALTER TYPE voter_status_enum ADD VALUE IF NOT EXISTS 'PENDING_APPROVAL'")

    op.add_column('voter', sa.Column('rejection_reason', sa.Text(), nullable=True))
    op.add_column(
        'voter',
        sa.Column(
            'reviewed_by',
            postgresql.UUID(as_uuid=True) if is_postgres else sa.String(36),
            sa.ForeignKey('user.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )

    # 3. Nuevas columnas en vote
    op.add_column('vote', sa.Column('chain_index', sa.Integer(), nullable=False, server_default='1'))
    op.create_index('ix_vote_election_chain', 'vote', ['election_id', 'chain_index'])

    # 4. Nuevas columnas en audit_log
    op.add_column('audit_log', sa.Column('chain_index', sa.Integer(), nullable=False, server_default='1'))
    op.create_index('ix_audit_log_chain_index', 'audit_log', ['chain_index'])

    # 5. Columna election_id en ai_call_log
    op.add_column(
        'ai_call_log',
        sa.Column(
            'election_id',
            postgresql.UUID(as_uuid=True) if is_postgres else sa.String(36),
            nullable=True,
        ),
    )
    op.create_index('ix_ai_call_log_election_id', 'ai_call_log', ['election_id'])

    # 6. Nueva tabla notification_outbox
    op.create_table(
        'notification_outbox',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True) if is_postgres else sa.String(36),
            primary_key=True,
        ),
        sa.Column(
            'organization_id',
            postgresql.UUID(as_uuid=True) if is_postgres else sa.String(36),
            sa.ForeignKey('organization.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'election_id',
            postgresql.UUID(as_uuid=True) if is_postgres else sa.String(36),
            sa.ForeignKey('election.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'schedule_change_id',
            postgresql.UUID(as_uuid=True) if is_postgres else sa.String(36),
            sa.ForeignKey('schedule_change.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('recipient_email', sa.String(255), nullable=False),
        sa.Column('recipient_name', sa.String(250), nullable=False),
        sa.Column('subject', sa.String(300), nullable=False),
        sa.Column('body_text', sa.Text(), nullable=False),
        sa.Column('delivery_status', sa.String(40), nullable=False, server_default='STORED_DEMO_OUTBOX'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_notification_outbox_election_id', 'notification_outbox', ['election_id'])
    op.create_index('ix_notification_outbox_organization_id', 'notification_outbox', ['organization_id'])
    op.create_index('ix_notification_outbox_created_at', 'notification_outbox', ['created_at'])


def downgrade() -> None:
    op.drop_table('notification_outbox')
    op.drop_index('ix_ai_call_log_election_id', table_name='ai_call_log')
    op.drop_column('ai_call_log', 'election_id')
    op.drop_index('ix_audit_log_chain_index', table_name='audit_log')
    op.drop_column('audit_log', 'chain_index')
    op.drop_index('ix_vote_election_chain', table_name='vote')
    op.drop_column('vote', 'chain_index')
    op.drop_column('voter', 'reviewed_by')
    op.drop_column('voter', 'rejection_reason')
    op.drop_column('election', 'votes_chain_head')
    op.drop_column('election', 'merkle_root')
    op.drop_column('election', 'registration_mode')
