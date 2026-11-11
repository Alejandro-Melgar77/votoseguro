"""0003_sprint1_iteration3_voting_reconciliation

Revision ID: 0003_sprint1_iteration3_voting_reconciliation
Revises: 0002_sprint1_iteration2_reconciliation
Create Date: 2026-11-11 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003_iter3_voting'
down_revision: Union[str, None] = '0002_iter2_reconcile'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Agregar raw_token a registration_link
    op.add_column('registration_link', sa.Column('raw_token', sa.String(128), nullable=True))

    # 2. Agregar raw_token a voting_credential
    op.add_column('voting_credential', sa.Column('raw_token', sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column('voting_credential', 'raw_token')
    op.drop_column('registration_link', 'raw_token')
