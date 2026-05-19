"""wave4b battlepacks templates match_battlepack

Revision ID: f9803530f860
Revises: a5ee9f35ea88
Create Date: 2026-05-18 21:23:15.339636

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f9803530f860'
down_revision = 'a5ee9f35ea88'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('battlepacks_db',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('system_id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=96), nullable=False),
    sa.Column('format', sa.String(length=32), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('primary_objective', sa.Text(), nullable=True),
    sa.Column('secondary_objectives_json', sa.JSON(), nullable=False),
    sa.Column('deployment_text', sa.Text(), nullable=True),
    sa.Column('special_rules_text', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['system_id'], ['game_systems.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('battlepacks_db', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_battlepacks_db_slug'), ['slug'], unique=True)
        batch_op.create_index(batch_op.f('ix_battlepacks_db_system_id'), ['system_id'], unique=False)

    op.create_table('army_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('system_id', sa.Integer(), nullable=False),
    sa.Column('faction_id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=96), nullable=False),
    sa.Column('name', sa.String(length=96), nullable=False),
    sa.Column('format', sa.String(length=32), nullable=False),
    sa.Column('points_target', sa.Integer(), nullable=False),
    sa.Column('units_json', sa.JSON(), nullable=False),
    sa.Column('regiments_layout_json', sa.JSON(), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['faction_id'], ['factions.id'], ),
    sa.ForeignKeyConstraint(['system_id'], ['game_systems.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('army_templates', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_army_templates_faction_id'), ['faction_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_army_templates_slug'), ['slug'], unique=True)
        batch_op.create_index(batch_op.f('ix_army_templates_system_id'), ['system_id'], unique=False)

    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.add_column(sa.Column('battlepack_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_matches_battlepack_id', 'battlepacks_db', ['battlepack_id'], ['id'])


def downgrade():
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.drop_constraint('fk_matches_battlepack_id', type_='foreignkey')
        batch_op.drop_column('battlepack_id')

    with op.batch_alter_table('army_templates', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_army_templates_system_id'))
        batch_op.drop_index(batch_op.f('ix_army_templates_slug'))
        batch_op.drop_index(batch_op.f('ix_army_templates_faction_id'))

    op.drop_table('army_templates')
    with op.batch_alter_table('battlepacks_db', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_battlepacks_db_system_id'))
        batch_op.drop_index(batch_op.f('ix_battlepacks_db_slug'))

    op.drop_table('battlepacks_db')
