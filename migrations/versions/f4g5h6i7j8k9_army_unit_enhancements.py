"""army_unit_enhancements

Revision ID: f4g5h6i7j8k9
Revises: e2f3a4b5c6d7
Branch Labels: None
Depends On: None

Create Date: 2026-05-22 00:00:00.000000

Add heroic_trait, artefact, command_trait to army_units table.
Stored as the enhancement name string; canonical data lives in
factions.rules_json.heroic_traits / artefacts / command_traits.
"""
from alembic import op
import sqlalchemy as sa


revision = 'f4g5h6i7j8k9'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('army_units') as batch_op:
        batch_op.add_column(sa.Column('heroic_trait',   sa.String(120), nullable=True))
        batch_op.add_column(sa.Column('artefact',       sa.String(120), nullable=True))
        batch_op.add_column(sa.Column('command_trait',  sa.String(120), nullable=True))


def downgrade():
    with op.batch_alter_table('army_units') as batch_op:
        batch_op.drop_column('command_trait')
        batch_op.drop_column('artefact')
        batch_op.drop_column('heroic_trait')
