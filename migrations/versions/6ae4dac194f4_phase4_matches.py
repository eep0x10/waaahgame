"""phase4 matches

Revision ID: 6ae4dac194f4
Revises: cfc559129f0e
Create Date: 2026-05-18 19:49:46.574630

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6ae4dac194f4'
down_revision = 'cfc559129f0e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('matches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('host_id', sa.Integer(), nullable=False),
    sa.Column('opponent_id', sa.Integer(), nullable=True),
    sa.Column('system_id', sa.Integer(), nullable=False),
    sa.Column('format', sa.String(length=16), nullable=False),
    sa.Column('points_limit', sa.Integer(), nullable=False),
    sa.Column('army_host_id', sa.Integer(), nullable=True),
    sa.Column('army_opponent_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('current_round', sa.Integer(), nullable=False),
    sa.Column('current_phase', sa.String(length=16), nullable=False),
    sa.Column('active_player_id', sa.Integer(), nullable=True),
    sa.Column('scores_json', sa.Text(), nullable=True),
    sa.Column('public_token', sa.String(length=24), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['active_player_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['army_host_id'], ['armies.id'], ),
    sa.ForeignKeyConstraint(['army_opponent_id'], ['armies.id'], ),
    sa.ForeignKeyConstraint(['host_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['opponent_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['system_id'], ['game_systems.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_matches_host_id'), ['host_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_matches_opponent_id'), ['opponent_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_matches_public_token'), ['public_token'], unique=True)

    op.create_table('match_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('match_id', sa.Integer(), nullable=False),
    sa.Column('round', sa.Integer(), nullable=False),
    sa.Column('phase', sa.String(length=16), nullable=True),
    sa.Column('actor_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=24), nullable=False),
    sa.Column('payload_json', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('match_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_match_events_match_id'), ['match_id'], unique=False)

    op.create_table('match_casualties',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('match_id', sa.Integer(), nullable=False),
    sa.Column('army_unit_id', sa.Integer(), nullable=False),
    sa.Column('round', sa.Integer(), nullable=False),
    sa.Column('removed', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['army_unit_id'], ['army_units.id'], ),
    sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('match_id', 'army_unit_id', name='uq_casualty_match_unit')
    )
    with op.batch_alter_table('match_casualties', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_match_casualties_army_unit_id'), ['army_unit_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_match_casualties_match_id'), ['match_id'], unique=False)


def downgrade():
    with op.batch_alter_table('match_casualties', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_match_casualties_match_id'))
        batch_op.drop_index(batch_op.f('ix_match_casualties_army_unit_id'))

    op.drop_table('match_casualties')

    with op.batch_alter_table('match_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_match_events_match_id'))

    op.drop_table('match_events')

    with op.batch_alter_table('matches', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_matches_public_token'))
        batch_op.drop_index(batch_op.f('ix_matches_opponent_id'))
        batch_op.drop_index(batch_op.f('ix_matches_host_id'))

    op.drop_table('matches')
