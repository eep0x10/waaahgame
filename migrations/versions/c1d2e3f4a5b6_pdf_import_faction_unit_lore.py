"""pdf_import_faction_unit_lore

Revision ID: c1d2e3f4a5b6
Revises: b7c8d9e0f1a2
Create Date: 2026-05-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c1d2e3f4a5b6'
down_revision = 'b7c8d9e0f1a2'
branch_labels = None
depends_on = None


def upgrade():
    # Faction-level PDF columns
    with op.batch_alter_table('factions') as batch_op:
        batch_op.add_column(sa.Column('rules_json', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('description_pt_md', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('pdf_source', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('pdf_imported_at', sa.DateTime(), nullable=True))

    # Per-unit lore column
    with op.batch_alter_table('units') as batch_op:
        batch_op.add_column(sa.Column('lore_pt_md', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('units') as batch_op:
        batch_op.drop_column('lore_pt_md')

    with op.batch_alter_table('factions') as batch_op:
        batch_op.drop_column('pdf_imported_at')
        batch_op.drop_column('pdf_source')
        batch_op.drop_column('description_pt_md')
        batch_op.drop_column('rules_json')
