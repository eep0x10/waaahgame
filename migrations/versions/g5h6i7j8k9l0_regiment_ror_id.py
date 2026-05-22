"""regiment_ror_id

Revision ID: g5h6i7j8k9l0
Revises: f4g5h6i7j8k9
Branch Labels: None
Depends On: None

Create Date: 2026-05-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'g5h6i7j8k9l0'
down_revision = 'f4g5h6i7j8k9'
branch_labels = None
depends_on = None


def upgrade():
    # Guard: skip if column already exists (idempotent for SQLite)
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = [c['name'] for c in insp.get_columns('regiments')]
    if 'ror_id' not in cols:
        op.add_column('regiments',
            sa.Column('ror_id', sa.Integer(), sa.ForeignKey('regiments_of_renown.id'), nullable=True)
        )


def downgrade():
    # SQLite does not support DROP COLUMN natively in older versions;
    # silently skip rather than error.
    try:
        op.drop_column('regiments', 'ror_id')
    except Exception:
        pass
