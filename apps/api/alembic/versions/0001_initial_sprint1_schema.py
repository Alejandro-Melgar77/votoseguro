"""0001_initial_sprint1_schema

Revision ID: 0001_initial_sprint1_schema
Revises: 
Create Date: 2026-11-11 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001_initial_sprint1_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Habilitar extensiones obligatorias de PostgreSQL
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "fuzzystrmatch";')

    # 2. Tipos ENUM
    org_type_enum = sa.Enum('UNIVERSITY', 'MUNICIPALITY', 'NATIONAL', 'CORPORATE', 'COOPERATIVE', 'OTHER', name='org_type_enum')
    org_status_enum = sa.Enum('PENDING', 'ACTIVE', 'SUSPENDED', name='org_status_enum')
    election_request_org_type_enum = sa.Enum('UNIVERSITY', 'MUNICIPALITY', 'NATIONAL', 'CORPORATE', 'COOPERATIVE', 'OTHER', name='election_request_org_type_enum')
    election_request_status_enum = sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='election_request_status_enum')
    user_role_enum = sa.Enum('PLATFORM_ADMIN', 'ADMIN_GENERAL', 'ADMIN_SEGMENT', 'OBSERVER', name='user_role_enum')
    user_status_enum = sa.Enum('ACTIVE', 'LOCKED', 'DISABLED', name='user_status_enum')
    election_status_enum = sa.Enum('DRAFT', 'SCHEDULED', 'REGISTRATION_OPEN', 'REGISTRATION_CLOSED', 'VOTING_OPEN', 'VOTING_CLOSED', 'TALLIED', 'CANCELLED', name='election_status_enum')
    breakdown_kind_enum = sa.Enum('LEVEL', 'FILTER', name='breakdown_kind_enum')
    voter_status_enum = sa.Enum('IMPORTED', 'INVITED', 'ACTIVE', 'BLOCKED', name='voter_status_enum')
    link_status_enum = sa.Enum('ACTIVE', 'EXPIRED', 'REVOKED', name='link_status_enum')
    vote_choice_type_enum = sa.Enum('CANDIDATE', 'BLANK', 'NULL', name='vote_choice_type_enum')

    # 3. Tablas
    # organization
    op.create_table(
        'organization',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('org_type', org_type_enum, nullable=False),
        sa.Column('status', org_status_enum, nullable=False, server_default='ACTIVE'),
        sa.Column('contact_email', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )
    op.create_index('ix_organization_slug', 'organization', ['slug'])

    # user
    op.create_table(
        'user',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organization.id', ondelete='CASCADE'), nullable=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('full_name', sa.String(200), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', user_role_enum, nullable=False),
        sa.Column('status', user_status_enum, nullable=False, server_default='ACTIVE'),
        sa.Column('failed_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(role = 'PLATFORM_ADMIN' AND organization_id IS NULL) OR (role != 'PLATFORM_ADMIN' AND organization_id IS NOT NULL)",
            name='ck_user_org_role'
        )
    )
    op.create_index('ix_user_email', 'user', ['email'])
    op.create_index('ix_user_organization_id', 'user', ['organization_id'])

    # election_request
    op.create_table(
        'election_request',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_name', sa.String(200), nullable=False),
        sa.Column('org_type', election_request_org_type_enum, nullable=False),
        sa.Column('requester_name', sa.String(150), nullable=False),
        sa.Column('contact_email', sa.String(255), nullable=False),
        sa.Column('contact_phone', sa.String(50), nullable=True),
        sa.Column('desired_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', election_request_status_enum, nullable=False, server_default='PENDING'),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('approved_organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organization.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )

    # election
    op.create_table(
        'election',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organization.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(250), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('timezone', sa.String(64), nullable=False, server_default='America/La_Paz'),
        sa.Column('registration_opens_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('registration_closes_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('voting_opens_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('voting_closes_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', election_status_enum, nullable=False, server_default='DRAFT'),
        sa.Column('k_anonymity', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('config_hash', sa.String(64), nullable=True),
        sa.Column('roll_hash', sa.String(64), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('registration_frozen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('voting_closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "registration_opens_at < registration_closes_at AND registration_closes_at <= voting_opens_at AND voting_opens_at < voting_closes_at",
            name='ck_election_schedule_order'
        ),
        sa.CheckConstraint("k_anonymity >= 0", name='ck_election_k_non_negative')
    )
    op.create_index('ix_election_organization_id', 'election', ['organization_id'])

    # schedule_change
    op.create_table(
        'schedule_change',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organization.id', ondelete='CASCADE'), nullable=False),
        sa.Column('election_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('election.id', ondelete='CASCADE'), nullable=False),
        sa.Column('field_name', sa.String(64), nullable=False),
        sa.Column('old_value', sa.DateTime(timezone=True), nullable=False),
        sa.Column('new_value', sa.DateTime(timezone=True), nullable=False),
        sa.Column('election_status_at_change', sa.String(40), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('changed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )
    op.create_index('ix_schedule_change_election_id', 'schedule_change', ['election_id'])
    op.create_index('ix_schedule_change_organization_id', 'schedule_change', ['organization_id'])

    # voter_group
    op.create_table(
        'voter_group',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organization.id', ondelete='CASCADE'), nullable=False),
        sa.Column('election_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('election.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('voting_opens_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('voting_closes_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('election_id', 'code', name='uq_voter_group_election_code')
    )
    op.create_index('ix_voter_group_organization_id', 'voter_group', ['organization_id'])
    op.create_index('ix_voter_group_election_id', 'voter_group', ['election_id'])

    # hierarchy_level
    op.create_table(
        'hierarchy_level',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('voter_group.id', ondelete='CASCADE'), nullable=False),
        sa.Column('depth', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.UniqueConstraint('group_id', 'depth', name='uq_hierarchy_level_group_depth'),
        sa.UniqueConstraint('group_id', 'name', name='uq_hierarchy_level_group_name')
    )
    op.create_index('ix_hierarchy_level_group_id', 'hierarchy_level', ['group_id'])

    # unit_node
    op.create_table(
        'unit_node',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('voter_group.id', ondelete='CASCADE'), nullable=False),
        sa.Column('level_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hierarchy_level.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('unit_node.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('code', sa.String(80), nullable=False),
        sa.Column('path', sa.String(1024), nullable=False),
        sa.Column('depth', sa.Integer(), nullable=False, server_default='1'),
        sa.UniqueConstraint('group_id', 'code', name='uq_unit_node_group_code')
    )
    op.create_index('ix_unit_node_group_id', 'unit_node', ['group_id'])
    op.create_index('ix_unit_node_level_id', 'unit_node', ['level_id'])
    op.create_index('ix_unit_node_parent_id', 'unit_node', ['parent_id'])
    op.create_index('ix_unit_node_path_pattern', 'unit_node', ['path'], postgresql_using='btree')

    # filter_definition
    op.create_table(
        'filter_definition',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('voter_group.id', ondelete='CASCADE'), nullable=False),
        sa.Column('key', sa.String(64), nullable=False),
        sa.Column('label', sa.String(120), nullable=False),
        sa.Column('allowed_values', postgresql.JSONB(), nullable=False),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.UniqueConstraint('group_id', 'key', name='uq_filter_definition_group_key')
    )
    op.create_index('ix_filter_definition_group_id', 'filter_definition', ['group_id'])

    # contest
    op.create_table(
        'contest',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('voter_group.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('scope_level_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hierarchy_level.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('allow_blank', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('allow_null', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='1')
    )
    op.create_index('ix_contest_group_id', 'contest', ['group_id'])
    op.create_index('ix_contest_scope_level_id', 'contest', ['scope_level_id'])

    # contest_breakdown
    op.create_table(
        'contest_breakdown',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contest.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', breakdown_kind_enum, nullable=False),
        sa.Column('level_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hierarchy_level.id', ondelete='CASCADE'), nullable=True),
        sa.Column('filter_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('filter_definition.id', ondelete='CASCADE'), nullable=True),
        sa.Column('label', sa.String(150), nullable=False)
    )
    op.create_index('ix_contest_breakdown_contest_id', 'contest_breakdown', ['contest_id'])

    # constituency
    op.create_table(
        'constituency',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('contest_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('contest.id', ondelete='CASCADE'), nullable=False),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('unit_node.id', ondelete='CASCADE'), nullable=False),
        sa.UniqueConstraint('contest_id', 'node_id', name='uq_constituency_contest_node')
    )
    op.create_index('ix_constituency_contest_id', 'constituency', ['contest_id'])
    op.create_index('ix_constituency_node_id', 'constituency', ['node_id'])

    # candidate
    op.create_table(
        'candidate',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('constituency_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('constituency.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('party_or_front', sa.String(200), nullable=True),
        sa.Column('photo_url', sa.String(500), nullable=True),
        sa.Column('ballot_order', sa.Integer(), nullable=False),
        sa.UniqueConstraint('constituency_id', 'ballot_order', name='uq_candidate_constituency_order')
    )
    op.create_index('ix_candidate_constituency_id', 'candidate', ['constituency_id'])

    # admin_assignment
    op.create_table(
        'admin_assignment',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organization.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('election_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('election.id', ondelete='CASCADE'), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('voter_group.id', ondelete='CASCADE'), nullable=True),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('unit_node.id', ondelete='CASCADE'), nullable=True),
        sa.Column('permission', sa.String(16), nullable=False, server_default='READ'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )
    op.create_index('ix_admin_assignment_organization_id', 'admin_assignment', ['organization_id'])
    op.create_index('ix_admin_assignment_user_id', 'admin_assignment', ['user_id'])
    op.create_index('ix_admin_assignment_election_id', 'admin_assignment', ['election_id'])

    # voter
    op.create_table(
        'voter',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organization.id', ondelete='CASCADE'), nullable=False),
        sa.Column('election_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('election.id', ondelete='CASCADE'), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('voter_group.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('unit_node.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('document_id', sa.String(64), nullable=False),
        sa.Column('full_name', sa.String(250), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('attributes', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('status', voter_status_enum, nullable=False, server_default='IMPORTED'),
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('blocked_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('election_id', 'document_id', name='uq_voter_election_document')
    )
    op.create_index('ix_voter_organization_id', 'voter', ['organization_id'])
    op.create_index('ix_voter_election_id', 'voter', ['election_id'])
    op.create_index('ix_voter_group_id', 'voter', ['group_id'])
    op.create_index('ix_voter_node_id', 'voter', ['node_id'])
    op.execute('CREATE INDEX ix_voter_full_name_trgm ON voter USING gin (full_name gin_trgm_ops);')

    # import_batch
    op.create_table(
        'import_batch',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('election_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('election.id', ondelete='CASCADE'), nullable=False),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('valid_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('duplicate_warnings', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )
    op.create_index('ix_import_batch_election_id', 'import_batch', ['election_id'])

    # import_issue
    op.create_table(
        'import_issue',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('import_batch.id', ondelete='CASCADE'), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('issue_type', sa.String(40), nullable=False),
        sa.Column('document_id', sa.String(64), nullable=True),
        sa.Column('raw_full_name', sa.String(250), nullable=True),
        sa.Column('matched_voter_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('voter.id', ondelete='SET NULL'), nullable=True),
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('resolution', sa.String(40), nullable=False, server_default='PENDING'),
        sa.Column('details', postgresql.JSONB(), nullable=False, server_default='{}')
    )
    op.create_index('ix_import_issue_batch_id', 'import_issue', ['batch_id'])

    # registration_link
    op.create_table(
        'registration_link',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organization.id', ondelete='CASCADE'), nullable=False),
        sa.Column('election_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('election.id', ondelete='CASCADE'), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('voter_group.id', ondelete='CASCADE'), nullable=False),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('unit_node.id', ondelete='CASCADE'), nullable=True),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('label', sa.String(150), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('uses_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', link_status_enum, nullable=False, server_default='ACTIVE'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )
    op.create_index('ix_registration_link_token_hash', 'registration_link', ['token_hash'])
    op.create_index('ix_registration_link_organization_id', 'registration_link', ['organization_id'])
    op.create_index('ix_registration_link_election_id', 'registration_link', ['election_id'])

    # voting_credential
    op.create_table(
        'voting_credential',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('election_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('election.id', ondelete='CASCADE'), nullable=False),
        sa.Column('voter_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('voter.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('ix_voting_credential_election_id', 'voting_credential', ['election_id'])
    op.create_index('ix_voting_credential_voter_id', 'voting_credential', ['voter_id'])
    op.create_index('ix_voting_credential_token_hash', 'voting_credential', ['token_hash'])

    # voter_participation
    op.create_table(
        'voter_participation',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('election_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('election.id', ondelete='CASCADE'), nullable=False),
        sa.Column('voter_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('voter.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('voter_group.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('unit_node.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('election_id', 'voter_id', name='uq_voter_participation_election_voter')
    )
    op.create_index('ix_voter_participation_election_id', 'voter_participation', ['election_id'])
    op.create_index('ix_voter_participation_voter_id', 'voter_participation', ['voter_id'])

    # vote (SIN voter_id - REGLA INVARIANTE #9)
    op.create_table(
        'vote',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('election_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('election.id', ondelete='CASCADE'), nullable=False),
        sa.Column('constituency_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('constituency.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('choice_type', vote_choice_type_enum, nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('candidate.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('encoded_payload', sa.Text(), nullable=False),
        sa.Column('segment_path', sa.String(1024), nullable=False),
        sa.Column('filters_snapshot', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('nullifier', sa.String(64), nullable=False, unique=True),
        sa.Column('receipt_hash', sa.String(64), nullable=False),
        sa.Column('prev_hash', sa.String(64), nullable=True),
        sa.Column('vote_hash', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(choice_type = 'CANDIDATE' AND candidate_id IS NOT NULL) OR (choice_type IN ('BLANK', 'NULL') AND candidate_id IS NULL)",
            name='ck_vote_candidate_consistency'
        )
    )
    op.create_index('ix_vote_election_constituency', 'vote', ['election_id', 'constituency_id'])
    op.create_index('ix_vote_segment_path', 'vote', ['segment_path'], postgresql_using='btree')
    op.create_index('ix_vote_nullifier', 'vote', ['nullifier'])
    op.create_index('ix_vote_receipt_hash', 'vote', ['receipt_hash'])

    # audit_log
    op.create_table(
        'audit_log',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('election_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_role', sa.String(40), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(80), nullable=False),
        sa.Column('entity_id', sa.String(80), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('ip_address', sa.String(64), nullable=True),
        sa.Column('prev_hash', sa.String(64), nullable=True),
        sa.Column('entry_hash', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    )
    op.create_index('ix_audit_log_action', 'audit_log', ['action'])
    op.create_index('ix_audit_log_organization_id', 'audit_log', ['organization_id'])
    op.create_index('ix_audit_log_election_id', 'audit_log', ['election_id'])
    op.create_index('ix_audit_log_created_at', 'audit_log', ['created_at'])

    # ai_call_log
    op.create_table(
        'ai_call_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('function_name', sa.String(80), nullable=False),
        sa.Column('model', sa.String(80), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('duration_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(40), nullable=False, server_default='SUCCESS'),
        sa.Column('summary', sa.Text(), nullable=False)
    )
    op.create_index('ix_ai_call_log_organization_id', 'ai_call_log', ['organization_id'])

    # 4. Trigger de Inmutabilidad en audit_log
    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_audit_log_mutation() RETURNS trigger AS $$
    BEGIN
        RAISE EXCEPTION 'audit_log is append-only. UPDATE and DELETE operations are forbidden.';
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_audit_log_immutable
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();
    """)


def downgrade() -> None:
    op.execute('DROP TRIGGER IF EXISTS trg_audit_log_immutable ON audit_log;')
    op.execute('DROP FUNCTION IF EXISTS prevent_audit_log_mutation();')
    op.drop_table('ai_call_log')
    op.drop_table('audit_log')
    op.drop_table('vote')
    op.drop_table('voter_participation')
    op.drop_table('voting_credential')
    op.drop_table('registration_link')
    op.drop_table('import_issue')
    op.drop_table('import_batch')
    op.drop_table('voter')
    op.drop_table('admin_assignment')
    op.drop_table('candidate')
    op.drop_table('constituency')
    op.drop_table('contest_breakdown')
    op.drop_table('contest')
    op.drop_table('filter_definition')
    op.drop_table('unit_node')
    op.drop_table('hierarchy_level')
    op.drop_table('voter_group')
    op.drop_table('schedule_change')
    op.drop_table('election')
    op.drop_table('election_request')
    op.drop_table('user')
    op.drop_table('organization')
