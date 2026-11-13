"""0006_sprint2_static_ai_tunnel

Revision ID: 0006_sprint2_tunnel
Revises: 0005_sprint2_p2
Create Date: 2026-11-12 20:30:00.000000

"""
import uuid
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0006_sprint2_tunnel'
down_revision: Union[str, None] = '0005_sprint2_p2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == 'postgresql'
    uuid_type = postgresql.UUID(as_uuid=True) if is_postgres else sa.String(36)

    # 1. Crear tabla singleton ai_runtime_config
    table = op.create_table(
        'ai_runtime_config',
        sa.Column('id', uuid_type, primary_key=True),
        sa.Column('llm_base_url', sa.String(255), nullable=False, server_default='https://repackage-remarry-reviving.ngrok-free.dev/v1'),
        sa.Column('llm_model_name', sa.String(128), nullable=False, server_default='votoseguro-lfm3'),
        sa.Column('provider', sa.String(32), nullable=False, server_default='OLLAMA'),
        sa.Column('strict_neural_mode', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('timeout_seconds', sa.Float(), nullable=False, server_default='25.0'),
        sa.Column('last_ping_status', sa.String(32), nullable=True),
        sa.Column('last_ping_latency_ms', sa.Float(), nullable=True),
        sa.Column('last_ping_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 2. Inicializar registro singleton por defecto
    default_id = uuid.uuid4() if is_postgres else str(uuid.uuid4())
    op.bulk_insert(
        table,
        [
            {
                'id': default_id,
                'llm_base_url': 'https://repackage-remarry-reviving.ngrok-free.dev/v1',
                'llm_model_name': 'votoseguro-lfm3',
                'provider': 'OLLAMA',
                'strict_neural_mode': False,
                'timeout_seconds': 25.0,
                'last_ping_status': 'ONLINE_INITIALIZED',
                'last_ping_latency_ms': None,
                'last_ping_at': None,
            }
        ]
    )


def downgrade() -> None:
    op.drop_table('ai_runtime_config')
