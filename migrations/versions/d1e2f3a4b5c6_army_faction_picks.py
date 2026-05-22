"""army_faction_picks

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4a5b6
Create Date: 2026-05-21 00:00:00.000000

Add formation_id, sub_faction_id, spell_lore_id, prayer_lore_id,
manifestation_lore_id to armies table.  All nullable strings — the
canonical rule lives in factions.rules_json; we store just the name.
"""
from alembic import op
import sqlalchemy as sa


revision = 'd1e2f3a4b5c6'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('armies') as batch_op:
        batch_op.add_column(sa.Column('formation_id',          sa.String(120), nullable=True))
        batch_op.add_column(sa.Column('sub_faction_id',        sa.String(120), nullable=True))
        batch_op.add_column(sa.Column('spell_lore_id',         sa.String(120), nullable=True))
        batch_op.add_column(sa.Column('prayer_lore_id',        sa.String(120), nullable=True))
        batch_op.add_column(sa.Column('manifestation_lore_id', sa.String(120), nullable=True))


def downgrade():
    with op.batch_alter_table('armies') as batch_op:
        batch_op.drop_column('manifestation_lore_id')
        batch_op.drop_column('prayer_lore_id')
        batch_op.drop_column('spell_lore_id')
        batch_op.drop_column('sub_faction_id')
        batch_op.drop_column('formation_id')
