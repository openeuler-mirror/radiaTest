"""empty message

Revision ID: 362cc4ba7466
Revises: ed39b60f18bc
Create Date: 2021-12-15 16:53:52.693744

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '362cc4ba7466'
down_revision = 'ed39b60f18bc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(None, 'job', ['name'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'job', type_='unique')
    # ### end Alembic commands ###
