"""add image_search_url and is_admin

Revision ID: 38fbd9806a21
Revises: f58946f636be
Create Date: 2026-05-18 19:09:33.683451

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '38fbd9806a21'
down_revision = 'f58946f636be'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('units', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('image_search_url', sa.String(length=512), nullable=True)
        )

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0')
        )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_admin')

    with op.batch_alter_table('units', schema=None) as batch_op:
        batch_op.drop_column('image_search_url')
