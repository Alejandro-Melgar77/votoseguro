"""Remove persistent secrets and permit ciphertext-only ballots.

Existing insecure elections must be archived before upgrading; rewriting their
ballots would invalidate the published hash chain and receipts.
"""
from alembic import op
import sqlalchemy as sa

revision = '0008_private_ballots'
down_revision = '0007_sprint3_paillier'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    affected = bind.execute(sa.text("""
        SELECT COUNT(*) FROM vote v JOIN election e ON e.id = v.election_id
        WHERE e.paillier_public_n IS NOT NULL
          AND (v.candidate_id IS NOT NULL OR v.choice_type IS NOT NULL)
    """)).scalar_one()
    if affected:
        raise RuntimeError(
            'Existen votos Paillier antiguos con selección legible. Archive esa base '
            'de demostración y despliegue una base nueva; no se reescriben cadenas publicadas.'
        )
    op.alter_column('vote', 'choice_type', nullable=True)
    op.drop_constraint('ck_vote_candidate_consistency', 'vote', type_='check')
    op.create_check_constraint('ck_vote_candidate_consistency', 'vote',
        "(choice_type IS NULL AND candidate_id IS NULL) OR "
        "(choice_type IS NOT NULL AND ((choice_type = 'CANDIDATE' AND candidate_id IS NOT NULL) OR "
        "(choice_type IN ('BLANK', 'NULL') AND candidate_id IS NULL)))")
    # Do not retain recoverable private key shares, including old demo fragments.
    op.execute("UPDATE electoral_trustee_share SET demo_share_token = NULL")
    op.create_check_constraint('ck_trustee_no_persisted_secret', 'electoral_trustee_share',
        'demo_share_token IS NULL')


def downgrade():
    raise RuntimeError('Downgrade incompatible con votos cifrados sin selección en texto plano.')
