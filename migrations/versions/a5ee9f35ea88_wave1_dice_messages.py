"""wave1 dice messages

Revision ID: a5ee9f35ea88
Revises: 6ae4dac194f4
Create Date: 2026-05-18 20:39:02.270658

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a5ee9f35ea88'
down_revision = '6ae4dac194f4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('match_dice_rolls',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('match_id', sa.Integer(), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=False),
    sa.Column('round', sa.Integer(), nullable=False),
    sa.Column('phase', sa.String(length=16), nullable=True),
    sa.Column('formula', sa.String(length=32), nullable=False),
    sa.Column('results_json', sa.Text(), nullable=False),
    sa.Column('total', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('match_dice_rolls', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_match_dice_rolls_match_id'), ['match_id'], unique=False)

    op.create_table('match_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('match_id', sa.Integer(), nullable=False),
    sa.Column('actor_id', sa.Integer(), nullable=False),
    sa.Column('body', sa.String(length=500), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('match_messages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_match_messages_match_id'), ['match_id'], unique=False)


def downgrade():
    with op.batch_alter_table('match_messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_match_messages_match_id'))
    op.drop_table('match_messages')

    with op.batch_alter_table('match_dice_rolls', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_match_dice_rolls_match_id'))
    op.drop_table('match_dice_rolls')
