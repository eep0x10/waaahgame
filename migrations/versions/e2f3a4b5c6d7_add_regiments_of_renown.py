"""add_regiments_of_renown

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Branch Labels: None
Depends On: None

Create Date: 2026-05-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'e2f3a4b5c6d7'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'regiments_of_renown',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('points_cost', sa.Integer(), nullable=True),
        sa.Column('alliance', sa.String(length=16), nullable=True),
        sa.Column('units_json', sa.Text(), nullable=True),
        sa.Column('eligible_factions_json', sa.Text(), nullable=True),
        sa.Column('is_new', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )


def downgrade():
    op.drop_table('regiments_of_renown')
