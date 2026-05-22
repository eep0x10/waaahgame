"""add_unit_category

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-05-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7c8d9e0f1a2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('units') as batch_op:
        batch_op.add_column(
            sa.Column('unit_category', sa.String(length=20), nullable=False,
                      server_default='regular')
        )


def downgrade():
    with op.batch_alter_table('units') as batch_op:
        batch_op.drop_column('unit_category')
