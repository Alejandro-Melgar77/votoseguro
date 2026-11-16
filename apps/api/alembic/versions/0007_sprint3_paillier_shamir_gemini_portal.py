"""0007_sprint3_paillier_shamir_gemini_portal

Revision ID: 0007_sprint3_paillier
Revises: 0006_sprint2_tunnel
Create Date: 2026-11-16 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0007_sprint3_paillier'
down_revision: Union[str, None] = '0006_sprint2_tunnel'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    uuid_type = postgresql.UUID(as_uuid=True) if is_postgres else sa.String(36)
    jsonb_type = postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON()

    # 1. Agregar columnas criptográficas y de seguridad a election
    op.add_column('election', sa.Column('encryption_scheme', sa.String(32), nullable=False, server_default='PAILLIER_HOMOMORPHIC'))
    op.add_column('election', sa.Column('paillier_public_n', sa.Text(), nullable=True))
    op.add_column('election', sa.Column('paillier_public_key', sa.Text(), nullable=True))
    op.add_column('election', sa.Column('paillier_key_size', sa.Integer(), nullable=False, server_default='1024'))
    op.add_column('election', sa.Column('shamir_threshold_k', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('election', sa.Column('shamir_total_n', sa.Integer(), nullable=False, server_default='5'))
    op.add_column('election', sa.Column('shamir_prime_modulus', sa.Text(), nullable=True))
    op.add_column('election', sa.Column('key_ceremony_hash', sa.String(64), nullable=True))
    op.add_column('election', sa.Column('tally_ceremony_hash', sa.String(64), nullable=True))
    op.add_column('election', sa.Column('biometric_verification_mode', sa.String(24), nullable=False, server_default='OPTIONAL'))

    # 2. Crear tabla electoral_trustee_share (S3-02)
    op.create_table(
        'electoral_trustee_share',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organization.id', ondelete='CASCADE'), nullable=False),
        sa.Column('election_id', uuid_type, sa.ForeignKey('election.id', ondelete='CASCADE'), nullable=False),
        sa.Column('share_index', sa.Integer(), nullable=False),
        sa.Column('trustee_name', sa.String(150), nullable=False),
        sa.Column('trustee_email', sa.String(255), nullable=False),
        sa.Column('commitment_hash', sa.String(64), nullable=False),
        sa.Column('demo_share_token', sa.Text(), nullable=True),
        sa.Column('submitted_for_tally', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('election_id', 'share_index', name='uq_trustee_share_election_index'),
    )
    op.create_index('ix_trustee_share_org', 'electoral_trustee_share', ['organization_id'])
    op.create_index('ix_trustee_share_election', 'electoral_trustee_share', ['election_id'])

    # 3. Crear tabla homomorphic_tally_cell (S3-01)
    op.create_table(
        'homomorphic_tally_cell',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organization.id', ondelete='CASCADE'), nullable=False),
        sa.Column('election_id', uuid_type, sa.ForeignKey('election.id', ondelete='CASCADE'), nullable=False),
        sa.Column('contest_id', uuid_type, sa.ForeignKey('contest.id', ondelete='CASCADE'), nullable=False),
        sa.Column('constituency_id', uuid_type, sa.ForeignKey('constituency.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cell_scope_type', sa.String(24), nullable=False),
        sa.Column('breakdown_id', uuid_type, sa.ForeignKey('contest_breakdown.id', ondelete='CASCADE'), nullable=True),
        sa.Column('cell_key', sa.String(512), nullable=False),
        sa.Column('cell_label', sa.String(250), nullable=False),
        sa.Column('ballots_aggregated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('option_order_keys', jsonb_type, nullable=False),
        sa.Column('aggregated_ciphertexts', jsonb_type, nullable=False),
        sa.Column('decrypted_counts', jsonb_type, nullable=True),
        sa.Column('suppressed_by_k_anonymity', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('cell_proof_hash', sa.String(64), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('constituency_id', 'cell_scope_type', 'cell_key', name='uq_tally_cell_constituency_scope_key'),
    )
    op.create_index('ix_tally_cell_org', 'homomorphic_tally_cell', ['organization_id'])
    op.create_index('ix_tally_cell_election', 'homomorphic_tally_cell', ['election_id'])

    # 4. Crear tabla executive_report (IA-E1)
    op.create_table(
        'executive_report',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organization.id', ondelete='CASCADE'), nullable=False),
        sa.Column('election_id', uuid_type, sa.ForeignKey('election.id', ondelete='CASCADE'), nullable=False),
        sa.Column('generated_by', uuid_type, sa.ForeignKey('user.id'), nullable=False),
        sa.Column('language', sa.String(16), nullable=False, server_default='es'),
        sa.Column('model_used', sa.String(80), nullable=False),
        sa.Column('ai_source', sa.String(40), nullable=False),
        sa.Column('aggregated_input_payload', jsonb_type, nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('summary_markdown', sa.Text(), nullable=False),
        sa.Column('key_highlights', jsonb_type, nullable=False, server_default='[]'),
        sa.Column('integrity_certification', sa.Text(), nullable=False),
        sa.Column('recommendations', jsonb_type, nullable=False, server_default='[]'),
        sa.Column('report_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_exec_report_org', 'executive_report', ['organization_id'])
    op.create_index('ix_exec_report_election', 'executive_report', ['election_id'])

    # 5. Crear tabla biometric_verification_audit (IA-E3)
    op.create_table(
        'biometric_verification_audit',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('organization_id', uuid_type, sa.ForeignKey('organization.id', ondelete='CASCADE'), nullable=False),
        sa.Column('election_id', uuid_type, sa.ForeignKey('election.id', ondelete='CASCADE'), nullable=False),
        sa.Column('voter_id', uuid_type, sa.ForeignKey('voter.id', ondelete='SET NULL'), nullable=True),
        sa.Column('document_id', sa.String(64), nullable=False),
        sa.Column('explicit_consent_given', sa.Boolean(), nullable=False),
        sa.Column('verification_channel', sa.String(32), nullable=False),
        sa.Column('verdict', sa.String(32), nullable=False),
        sa.Column('confidence_band', sa.String(24), nullable=False),
        sa.Column('explanation_es', sa.Text(), nullable=False),
        sa.Column('images_persisted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('ai_source', sa.String(40), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('images_persisted = false', name='chk_zero_biometric_image_persistence'),
    )
    op.create_index('ix_bio_audit_org', 'biometric_verification_audit', ['organization_id'])
    op.create_index('ix_bio_audit_election', 'biometric_verification_audit', ['election_id'])


def downgrade() -> None:
    op.drop_table('biometric_verification_audit')
    op.drop_table('executive_report')
    op.drop_table('homomorphic_tally_cell')
    op.drop_table('electoral_trustee_share')
    op.drop_column('election', 'biometric_verification_mode')
    op.drop_column('election', 'tally_ceremony_hash')
    op.drop_column('election', 'key_ceremony_hash')
    op.drop_column('election', 'shamir_prime_modulus')
    op.drop_column('election', 'shamir_total_n')
    op.drop_column('election', 'shamir_threshold_k')
    op.drop_column('election', 'paillier_key_size')
    op.drop_column('election', 'paillier_public_key')
    op.drop_column('election', 'paillier_public_n')
    op.drop_column('election', 'encryption_scheme')
