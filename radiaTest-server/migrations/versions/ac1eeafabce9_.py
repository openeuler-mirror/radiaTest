"""empty message

Revision ID: ac1eeafabce9
Revises: ea6f92a7a48d
Create Date: 2021-12-07 18:11:03.160323

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ac1eeafabce9'
down_revision = 'ea6f92a7a48d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('organization', sa.Column('enterprise', sa.String(length=50), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('organization', 'enterprise')
    # ### end Alembic commands ###
