"""phase3_army_builder

Revision ID: cfc559129f0e
Revises: 38fbd9806a21
Create Date: 2026-05-18 19:35:06.528774

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cfc559129f0e'
down_revision = '38fbd9806a21'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('armies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('faction_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=96), nullable=False),
    sa.Column('battlepack', sa.String(length=16), nullable=False),
    sa.Column('points_limit', sa.Integer(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('public_token', sa.String(length=32), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['faction_id'], ['factions.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('armies', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_armies_faction_id'), ['faction_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_armies_public_token'), ['public_token'], unique=True)
        batch_op.create_index(batch_op.f('ix_armies_user_id'), ['user_id'], unique=False)

    op.create_table('regiments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('army_id', sa.Integer(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['army_id'], ['armies.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('regiments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_regiments_army_id'), ['army_id'], unique=False)

    op.create_table('army_units',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('army_id', sa.Integer(), nullable=False),
    sa.Column('unit_id', sa.Integer(), nullable=False),
    sa.Column('regiment_id', sa.Integer(), nullable=True),
    sa.Column('is_reinforced', sa.Boolean(), nullable=False),
    sa.Column('is_leader', sa.Boolean(), nullable=False),
    sa.Column('is_general', sa.Boolean(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['army_id'], ['armies.id'], ),
    sa.ForeignKeyConstraint(['regiment_id'], ['regiments.id'], ),
    sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('army_units', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_army_units_army_id'), ['army_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_army_units_regiment_id'), ['regiment_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_army_units_unit_id'), ['unit_id'], unique=False)

    # ### end Alembic commands ###


def downgrade():
    with op.batch_alter_table('army_units', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_army_units_unit_id'))
        batch_op.drop_index(batch_op.f('ix_army_units_regiment_id'))
        batch_op.drop_index(batch_op.f('ix_army_units_army_id'))

    op.drop_table('army_units')
    with op.batch_alter_table('regiments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_regiments_army_id'))

    op.drop_table('regiments')
    with op.batch_alter_table('armies', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_armies_user_id'))
        batch_op.drop_index(batch_op.f('ix_armies_public_token'))
        batch_op.drop_index(batch_op.f('ix_armies_faction_id'))

    op.drop_table('armies')
