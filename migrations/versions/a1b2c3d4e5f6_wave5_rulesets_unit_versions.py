"""wave5_rulesets_unit_versions

Revision ID: a1b2c3d4e5f6
Revises: f9803530f860
Create Date: 2026-05-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'f9803530f860'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'rulesets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('game_system_id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=96), nullable=False),
        sa.Column('edition', sa.String(length=32), nullable=False),
        sa.Column('release_date', sa.Date(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('source_url', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['game_system_id'], ['game_systems.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_rulesets_game_system_id', 'rulesets', ['game_system_id'], unique=False)
    op.create_index('ix_rulesets_is_current', 'rulesets', ['is_current'], unique=False)

    op.create_table(
        'unit_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('unit_id', sa.Integer(), nullable=False),
        sa.Column('ruleset_id', sa.Integer(), nullable=False),
        sa.Column('points_cost', sa.Integer(), nullable=True),
        sa.Column('stats_json', sa.JSON(), nullable=True),
        sa.Column('weapons_json', sa.JSON(), nullable=True),
        sa.Column('abilities_json', sa.JSON(), nullable=True),
        sa.Column('keywords_json', sa.JSON(), nullable=True),
        sa.Column('companions_json', sa.JSON(), nullable=True),
        sa.Column('notes_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ruleset_id'], ['rulesets.id'], ),
        sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('unit_id', 'ruleset_id', name='uq_unit_ruleset'),
    )
    op.create_index('ix_unit_versions_ruleset_id', 'unit_versions', ['ruleset_id'], unique=False)
    op.create_index('ix_unit_versions_unit_id', 'unit_versions', ['unit_id'], unique=False)

    with op.batch_alter_table('armies') as batch_op:
        batch_op.add_column(sa.Column('ruleset_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_armies_ruleset_id', ['ruleset_id'], unique=False)
        batch_op.create_foreign_key('fk_armies_ruleset_id', 'rulesets', ['ruleset_id'], ['id'])


def downgrade():
    with op.batch_alter_table('armies') as batch_op:
        batch_op.drop_constraint('fk_armies_ruleset_id', type_='foreignkey')
        batch_op.drop_index('ix_armies_ruleset_id')
        batch_op.drop_column('ruleset_id')

    op.drop_index('ix_unit_versions_unit_id', table_name='unit_versions')
    op.drop_index('ix_unit_versions_ruleset_id', table_name='unit_versions')
    op.drop_table('unit_versions')

    op.drop_index('ix_rulesets_is_current', table_name='rulesets')
    op.drop_index('ix_rulesets_game_system_id', table_name='rulesets')
    op.drop_table('rulesets')
