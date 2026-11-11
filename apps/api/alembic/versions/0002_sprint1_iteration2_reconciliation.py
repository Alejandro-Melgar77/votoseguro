"""0002_sprint1_iteration2_reconciliation

Revision ID: 0002_sprint1_iteration2_reconciliation
Revises: 0001_initial_sprint1_schema
Create Date: 2026-11-11 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002_iter2_reconcile'
down_revision: Union[str, None] = '0001_initial_sprint1_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Ensanchar columna version_num si es PostgreSQL
    try:
        op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)")
    except Exception:
        pass

    # 1. Agregar description a contest si no existe
    op.add_column('contest', sa.Column('description', sa.Text(), nullable=True))

    # 2. Agregar organization_id a import_batch
    op.add_column(
        'import_batch',
        sa.Column(
            'organization_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('organization.id', ondelete='CASCADE'),
            nullable=True,
        ),
    )
    op.create_index('ix_import_batch_organization_id', 'import_batch', ['organization_id'])

    # 3. Agregar campos de duplicados a import_issue
    op.add_column(
        'import_issue',
        sa.Column(
            'candidate_voter_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('voter.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )
    op.add_column('import_issue', sa.Column('edit_distance', sa.Integer(), nullable=True))
    op.add_column(
        'import_issue',
        sa.Column(
            'resolved_by',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('user.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )
    op.add_column('import_issue', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_import_issue_candidate_voter_id', 'import_issue', ['candidate_voter_id'])


def downgrade() -> None:
    op.drop_index('ix_import_issue_candidate_voter_id', table_name='import_issue')
    op.drop_column('import_issue', 'resolved_at')
    op.drop_column('import_issue', 'resolved_by')
    op.drop_column('import_issue', 'edit_distance')
    op.drop_column('import_issue', 'candidate_voter_id')

    op.drop_index('ix_import_batch_organization_id', table_name='import_batch')
    op.drop_column('import_batch', 'organization_id')

    op.drop_column('contest', 'description')
